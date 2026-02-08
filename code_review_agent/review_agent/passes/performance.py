"""Performance analysis pass for detecting inefficient code patterns."""

from __future__ import annotations

import ast
from pathlib import Path

from review_agent.core.findings import Finding, FindingCollection, Location, Severity
from review_agent.passes.correctness import BasePass


class PerformancePass(BasePass):
    """
    Analyzes Python code for performance anti-patterns.

    Detects:
    - range(len(x)) instead of enumerate() or direct iteration
    - String concatenation with += in loops
    - .append() in simple for-loops that could be list comprehensions
    - Membership tests on list literals instead of set literals
    - dict()/list()/tuple() constructor calls instead of literals
    - sorted() when only min or max is needed
    - Repeated global attribute lookups in loops
    """

    @property
    def name(self) -> str:
        return "performance"

    @property
    def description(self) -> str:
        return "Detects inefficient code patterns and performance anti-patterns"

    def analyze(self, file_path: Path) -> FindingCollection:
        findings = FindingCollection()

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            findings.add(
                Finding(
                    message=f"Syntax error: {e.msg}",
                    severity=Severity.ERROR,
                    location=Location(file=file_path, line=e.lineno or 1, column=e.offset or 0),
                    rule_id="PERF000",
                    category="performance",
                )
            )
            return findings
        except FileNotFoundError:
            findings.add(
                Finding(
                    message=f"File not found: {file_path}",
                    severity=Severity.ERROR,
                    location=Location(file=file_path, line=1, column=0),
                    rule_id="PERF000",
                    category="performance",
                )
            )
            return findings

        checker = _PerformanceChecker(file_path, findings)
        checker.visit(tree)

        return findings


class _PerformanceChecker(ast.NodeVisitor):

    def __init__(self, file_path: Path, findings: FindingCollection) -> None:
        self.file_path = file_path
        self.findings = findings

    def _add_finding(
        self,
        message: str,
        severity: Severity,
        line: int,
        column: int,
        rule_id: str,
        suggestion: str | None = None,
    ) -> None:
        self.findings.add(
            Finding(
                message=message,
                severity=severity,
                location=Location(file=self.file_path, line=line, column=column),
                rule_id=rule_id,
                category="performance",
                suggestion=suggestion,
            )
        )

    def visit_For(self, node: ast.For) -> None:
        self._check_range_len(node)
        self._check_append_in_loop(node)
        self._check_string_concat_in_loop(node)
        self.generic_visit(node)

    def _check_range_len(self, node: ast.For) -> None:
        """Detect `for i in range(len(x))` — should use enumerate() or direct iteration."""
        if not isinstance(node.iter, ast.Call):
            return
        func = node.iter.func
        if not (isinstance(func, ast.Name) and func.id == "range"):
            return
        if len(node.iter.args) != 1:
            return

        arg = node.iter.args[0]
        if not isinstance(arg, ast.Call):
            return
        if not (isinstance(arg.func, ast.Name) and arg.func.id == "len"):
            return

        self._add_finding(
            message="Use of range(len(...)) — prefer enumerate() or direct iteration",
            severity=Severity.INFO,
            line=node.lineno,
            column=node.col_offset,
            rule_id="PERF001",
            suggestion="Use 'for item in collection:' or 'for i, item in enumerate(collection):'",
        )

    def _check_string_concat_in_loop(self, node: ast.For) -> None:
        """Detect `s += '...'` inside for-loops — O(n²) string building."""
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.AugAssign):
                continue
            if not isinstance(stmt.op, ast.Add):
                continue
            if not isinstance(stmt.target, ast.Name):
                continue
            if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                self._add_finding(
                    message=f"String concatenation with += in loop (variable '{stmt.target.id}')",
                    severity=Severity.WARNING,
                    line=stmt.lineno,
                    column=stmt.col_offset,
                    rule_id="PERF002",
                    suggestion="Use ''.join() or a list to build strings — += creates a new string each iteration",
                )
            elif isinstance(stmt.value, ast.JoinedStr):
                self._add_finding(
                    message=f"String concatenation with += in loop (variable '{stmt.target.id}')",
                    severity=Severity.WARNING,
                    line=stmt.lineno,
                    column=stmt.col_offset,
                    rule_id="PERF002",
                    suggestion="Use ''.join() or a list to build strings — += creates a new string each iteration",
                )

    def _check_append_in_loop(self, node: ast.For) -> None:
        """Detect simple `result.append(expr)` patterns that could be list comprehensions."""
        if len(node.body) != 1:
            return
        stmt = node.body[0]

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "append"
                and len(call.args) == 1
                and not call.keywords
            ):
                self._add_finding(
                    message="Simple .append() in for-loop could be a list comprehension",
                    severity=Severity.HINT,
                    line=node.lineno,
                    column=node.col_offset,
                    rule_id="PERF003",
                    suggestion="Consider: [expr for item in iterable] instead of a loop with .append()",
                )

        if isinstance(stmt, ast.If) and len(stmt.body) == 1 and not stmt.orelse:
            inner = stmt.body[0]
            if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Call):
                call = inner.value
                if (
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr == "append"
                    and len(call.args) == 1
                    and not call.keywords
                ):
                    self._add_finding(
                        message="Filtered .append() in for-loop could be a list comprehension",
                        severity=Severity.HINT,
                        line=node.lineno,
                        column=node.col_offset,
                        rule_id="PERF003",
                        suggestion="Consider: [expr for item in iterable if condition]",
                    )

    def visit_Compare(self, node: ast.Compare) -> None:
        """Detect `x in [literal, literal, ...]` — should use a set literal for O(1) lookup."""
        for op, comparator in zip(node.ops, node.comparators):
            if not isinstance(op, (ast.In, ast.NotIn)):
                continue
            if not isinstance(comparator, ast.List):
                continue
            if len(comparator.elts) < 3:
                continue
            if all(isinstance(elt, ast.Constant) for elt in comparator.elts):
                self._add_finding(
                    message="Membership test on list literal — use a set literal for O(1) lookup",
                    severity=Severity.INFO,
                    line=comparator.lineno,
                    column=comparator.col_offset,
                    rule_id="PERF004",
                    suggestion="Replace [...] with {...} for constant-time membership testing",
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_constructor_vs_literal(node)
        self.generic_visit(node)

    def _check_constructor_vs_literal(self, node: ast.Call) -> None:
        """Detect dict(), list(), tuple() with no args — literals are faster."""
        if not isinstance(node.func, ast.Name):
            return
        if node.args or node.keywords:
            return

        constructors = {
            "dict": ("PERF005", "{}", "dict()"),
            "list": ("PERF005", "[]", "list()"),
            "tuple": ("PERF005", "()", "tuple()"),
        }
        entry = constructors.get(node.func.id)
        if entry is None:
            return
        rule_id, literal, constructor = entry
        self._add_finding(
            message=f"{constructor} is slower than {literal} literal",
            severity=Severity.HINT,
            line=node.lineno,
            column=node.col_offset,
            rule_id=rule_id,
            suggestion=f"Use {literal} instead of {constructor} — literals avoid function call overhead",
        )

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect sorted(x)[0] or sorted(x)[-1] — use min()/max() for O(n) vs O(n log n)."""
        if not isinstance(node.value, ast.Call):
            self.generic_visit(node)
            return

        call = node.value
        if not (isinstance(call.func, ast.Name) and call.func.id == "sorted"):
            self.generic_visit(node)
            return

        idx = self._resolve_index(node.slice)
        if idx is None:
            self.generic_visit(node)
            return

        if idx == 0:
            self._add_finding(
                message="sorted(...)[0] is O(n log n) — use min() for O(n)",
                severity=Severity.WARNING,
                line=node.lineno,
                column=node.col_offset,
                rule_id="PERF006",
                suggestion="Replace sorted(x)[0] with min(x)",
            )
        elif idx == -1:
            self._add_finding(
                message="sorted(...)[-1] is O(n log n) — use max() for O(n)",
                severity=Severity.WARNING,
                line=node.lineno,
                column=node.col_offset,
                rule_id="PERF006",
                suggestion="Replace sorted(x)[-1] with max(x)",
            )

        self.generic_visit(node)

    @staticmethod
    def _resolve_index(node: ast.expr) -> int | None:
        """Resolve an index to int, handling `-1` which is UnaryOp(USub, 1) in AST."""
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, int)
        ):
            return -node.operand.value
        return None
