"""Correctness analysis pass for detecting bugs and logic errors."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from pathlib import Path

from review_agent.core.findings import Finding, FindingCollection, Location, Severity


class BasePass(ABC):
    """Base class for all analysis passes."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this pass."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what this pass checks."""
        ...

    @abstractmethod
    def analyze(self, file_path: Path) -> FindingCollection:
        """Analyze a file and return findings."""
        ...

    def analyze_multiple(self, file_paths: list[Path]) -> FindingCollection:
        """Analyze multiple files and return combined findings."""
        collection = FindingCollection()
        for file_path in file_paths:
            collection.extend(list(self.analyze(file_path)))
        return collection


class CorrectnessPass(BasePass):
    """
    Analyzes Python code for correctness issues.

    Detects:
    - Undefined variables
    - Unused imports
    - Unreachable code after return/raise
    - Comparison with None using == instead of 'is'
    - Mutable default arguments
    - Bare except clauses
    """

    @property
    def name(self) -> str:
        return "correctness"

    @property
    def description(self) -> str:
        return "Detects bugs, logic errors, and potential runtime failures"

    def analyze(self, file_path: Path) -> FindingCollection:
        """Analyze a Python file for correctness issues."""
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
                    rule_id="COR001",
                    category="correctness",
                )
            )
            return findings
        except FileNotFoundError:
            findings.add(
                Finding(
                    message=f"File not found: {file_path}",
                    severity=Severity.ERROR,
                    location=Location(file=file_path, line=1, column=0),
                    rule_id="COR000",
                    category="correctness",
                )
            )
            return findings

        checker = _CorrectnessChecker(file_path, findings)
        checker.visit(tree)

        return findings


class _CorrectnessChecker(ast.NodeVisitor):
    """AST visitor that checks for correctness issues."""

    def __init__(self, file_path: Path, findings: FindingCollection) -> None:
        self.file_path = file_path
        self.findings = findings
        self.defined_names: set[str] = set()
        self.imported_names: set[str] = set()
        self.used_names: set[str] = set()

    def _add_finding(
        self,
        message: str,
        severity: Severity,
        line: int,
        column: int,
        rule_id: str,
        suggestion: str | None = None,
    ) -> None:
        """Helper to add a finding."""
        self.findings.add(
            Finding(
                message=message,
                severity=severity,
                location=Location(file=self.file_path, line=line, column=column),
                rule_id=rule_id,
                category="correctness",
                suggestion=suggestion,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        """Track imported names."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self.imported_names.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track imported names from 'from' imports."""
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check for comparison with None using == instead of 'is'."""
        for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
            left = node.left if i == 0 else node.comparators[i - 1]

            if isinstance(op, (ast.Eq, ast.NotEq)):
                if isinstance(comparator, ast.Constant) and comparator.value is None:
                    op_text = "==" if isinstance(op, ast.Eq) else "!="
                    is_text = "is" if isinstance(op, ast.Eq) else "is not"
                    self._add_finding(
                        message=f"Comparison to None should use '{is_text}' instead of '{op_text}'",
                        severity=Severity.WARNING,
                        line=node.lineno,
                        column=node.col_offset,
                        rule_id="COR002",
                        suggestion=f"Use '{is_text} None' instead of '{op_text} None'",
                    )
                elif isinstance(left, ast.Constant) and left.value is None:
                    op_text = "==" if isinstance(op, ast.Eq) else "!="
                    is_text = "is" if isinstance(op, ast.Eq) else "is not"
                    self._add_finding(
                        message=f"Comparison to None should use '{is_text}' instead of '{op_text}'",
                        severity=Severity.WARNING,
                        line=node.lineno,
                        column=node.col_offset,
                        rule_id="COR002",
                        suggestion=f"Use 'None {is_text}' instead of 'None {op_text}'",
                    )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for issues."""
        self._check_mutable_defaults(node)
        self._check_unreachable_code(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definitions for issues."""
        self._check_mutable_defaults(node)
        self._check_unreachable_code(node.body)
        self.generic_visit(node)

    def _check_mutable_defaults(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Check for mutable default arguments."""
        for default in node.args.defaults + node.args.kw_defaults:
            if default is None:
                continue
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                type_name = type(default).__name__.lower()
                self._add_finding(
                    message=f"Mutable default argument: {type_name}",
                    severity=Severity.WARNING,
                    line=default.lineno,
                    column=default.col_offset,
                    rule_id="COR003",
                    suggestion="Use None as default and create the mutable object inside the function",
                )

    def _check_unreachable_code(self, body: list[ast.stmt]) -> None:
        """Check for unreachable code after return/raise/break/continue."""
        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                if i < len(body) - 1:
                    next_stmt = body[i + 1]
                    self._add_finding(
                        message="Unreachable code detected",
                        severity=Severity.WARNING,
                        line=next_stmt.lineno,
                        column=next_stmt.col_offset,
                        rule_id="COR004",
                        suggestion="Remove or move the unreachable code",
                    )
                break

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Check for bare except clauses."""
        if node.type is None:
            self._add_finding(
                message="Bare 'except:' clause catches all exceptions including KeyboardInterrupt",
                severity=Severity.WARNING,
                line=node.lineno,
                column=node.col_offset,
                rule_id="COR005",
                suggestion="Use 'except Exception:' to catch most exceptions, or be more specific",
            )
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        """Check for assertions with side effects or always-true conditions."""
        if isinstance(node.test, ast.Constant):
            if node.test.value:
                self._add_finding(
                    message="Assertion is always true",
                    severity=Severity.INFO,
                    line=node.lineno,
                    column=node.col_offset,
                    rule_id="COR006",
                    suggestion="Remove the assertion or fix the condition",
                )
            else:
                self._add_finding(
                    message="Assertion is always false",
                    severity=Severity.WARNING,
                    line=node.lineno,
                    column=node.col_offset,
                    rule_id="COR007",
                    suggestion="This will always raise AssertionError - is this intentional?",
                )
        self.generic_visit(node)
