"""Style analysis pass for naming conventions and formatting issues."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from review_agent.core.findings import Finding, FindingCollection, Location, Severity


class StylePass:
    """
    Analyzes Python code for style and convention issues.

    Checks:
    - Naming conventions (snake_case, PascalCase, UPPER_CASE)
    - Line length limits
    - Import ordering and grouping
    - Trailing whitespace
    - Blank line usage
    """

    MAX_LINE_LENGTH = 100
    MAX_FUNCTION_NAME_LENGTH = 40
    MAX_VARIABLE_NAME_LENGTH = 30

    SNAKE_CASE_PATTERN = re.compile(r"^_?_?[a-z][a-z0-9_]*_?_?$")
    PASCAL_CASE_PATTERN = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")
    UPPER_CASE_PATTERN = re.compile(r"^_?_?[A-Z][A-Z0-9_]*_?_?$")

    @property
    def name(self) -> str:
        return "style"

    @property
    def description(self) -> str:
        return "Checks naming conventions, formatting, and code style"

    def analyze(self, file_path: Path) -> FindingCollection:
        findings = FindingCollection()

        try:
            source = file_path.read_text(encoding="utf-8")
            lines = source.splitlines(keepends=True)
        except FileNotFoundError:
            findings.add(
                Finding(
                    message=f"File not found: {file_path}",
                    severity=Severity.ERROR,
                    location=Location(file=file_path, line=1, column=0),
                    rule_id="STY000",
                    category="style",
                )
            )
            return findings

        self._check_line_issues(file_path, lines, findings)

        try:
            tree = ast.parse(source, filename=str(file_path))
            self._check_imports(file_path, tree, findings)
            checker = _StyleChecker(file_path, findings, self)
            checker.visit(tree)
        except SyntaxError:
            pass

        return findings

    def _check_line_issues(
        self, file_path: Path, lines: list[str], findings: FindingCollection
    ) -> None:
        consecutive_blank_lines = 0

        for line_num, line in enumerate(lines, start=1):
            line_without_newline = line.rstrip("\n\r")

            if len(line_without_newline) > self.MAX_LINE_LENGTH:
                findings.add(
                    Finding(
                        message=f"Line too long ({len(line_without_newline)} > {self.MAX_LINE_LENGTH})",
                        severity=Severity.INFO,
                        location=Location(file=file_path, line=line_num, column=self.MAX_LINE_LENGTH),
                        rule_id="STY001",
                        category="style",
                        suggestion=f"Break this line to be under {self.MAX_LINE_LENGTH} characters",
                    )
                )

            if line_without_newline != line_without_newline.rstrip():
                findings.add(
                    Finding(
                        message="Trailing whitespace",
                        severity=Severity.HINT,
                        location=Location(file=file_path, line=line_num, column=len(line_without_newline.rstrip())),
                        rule_id="STY002",
                        category="style",
                        suggestion="Remove trailing whitespace",
                    )
                )

            if line_without_newline.strip() == "":
                consecutive_blank_lines += 1
                if consecutive_blank_lines > 2:
                    findings.add(
                        Finding(
                            message="Too many consecutive blank lines",
                            severity=Severity.HINT,
                            location=Location(file=file_path, line=line_num, column=0),
                            rule_id="STY003",
                            category="style",
                            suggestion="Use at most 2 consecutive blank lines",
                        )
                    )
            else:
                consecutive_blank_lines = 0

        if lines and not lines[-1].endswith("\n"):
            findings.add(
                Finding(
                    message="File does not end with newline",
                    severity=Severity.HINT,
                    location=Location(file=file_path, line=len(lines), column=0),
                    rule_id="STY004",
                    category="style",
                    suggestion="Add a newline at end of file",
                )
            )

    def _check_imports(
        self, file_path: Path, tree: ast.AST, findings: FindingCollection
    ) -> None:
        imports: list[tuple[int, str, str]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_type = self._classify_import(alias.name)
                    imports.append((node.lineno, import_type, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    import_type = self._classify_import(node.module)
                    imports.append((node.lineno, import_type, node.module))

        imports.sort(key=lambda x: x[0])

        expected_order = ["stdlib", "third_party", "local"]
        current_group_idx = 0

        for line, import_type, module in imports:
            try:
                type_idx = expected_order.index(import_type)
            except ValueError:
                continue

            if type_idx < current_group_idx:
                findings.add(
                    Finding(
                        message=f"Import '{module}' is out of order (expected {expected_order[current_group_idx]} imports)",
                        severity=Severity.INFO,
                        location=Location(file=file_path, line=line, column=0),
                        rule_id="STY005",
                        category="style",
                        suggestion="Group imports: stdlib, then third-party, then local",
                    )
                )
            else:
                current_group_idx = type_idx

    def _classify_import(self, module_name: str) -> str:
        stdlib_modules = {
            "abc", "ast", "asyncio", "base64", "collections", "contextlib",
            "copy", "dataclasses", "datetime", "decimal", "enum", "functools",
            "hashlib", "hmac", "html", "http", "importlib", "inspect", "io",
            "itertools", "json", "logging", "math", "operator", "os", "pathlib",
            "pickle", "platform", "pprint", "queue", "random", "re", "secrets",
            "shutil", "signal", "socket", "sqlite3", "string", "subprocess",
            "sys", "tempfile", "threading", "time", "traceback", "typing",
            "unittest", "urllib", "uuid", "warnings", "weakref", "xml", "zipfile",
        }
        top_level = module_name.split(".")[0]
        if top_level in stdlib_modules:
            return "stdlib"
        if top_level.startswith(".") or top_level == "review_agent":
            return "local"
        return "third_party"

    def is_snake_case(self, name: str) -> bool:
        return bool(self.SNAKE_CASE_PATTERN.match(name))

    def is_pascal_case(self, name: str) -> bool:
        return bool(self.PASCAL_CASE_PATTERN.match(name))

    def is_upper_case(self, name: str) -> bool:
        return bool(self.UPPER_CASE_PATTERN.match(name))


class _StyleChecker(ast.NodeVisitor):

    def __init__(
        self, file_path: Path, findings: FindingCollection, style_pass: StylePass
    ) -> None:
        self.file_path = file_path
        self.findings = findings
        self.style_pass = style_pass
        self._in_class = False

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
                category="style",
                suggestion=suggestion,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not self.style_pass.is_pascal_case(node.name):
            self._add_finding(
                message=f"Class name '{node.name}' should use PascalCase",
                severity=Severity.WARNING,
                line=node.lineno,
                column=node.col_offset,
                rule_id="STY010",
                suggestion=f"Rename to '{self._to_pascal_case(node.name)}'",
            )

        old_in_class = self._in_class
        self._in_class = True
        self.generic_visit(node)
        self._in_class = old_in_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function_name(node)
        self._check_argument_names(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function_name(node)
        self._check_argument_names(node)
        self.generic_visit(node)

    def _check_function_name(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        if node.name.startswith("__") and node.name.endswith("__"):
            return

        if not self.style_pass.is_snake_case(node.name):
            self._add_finding(
                message=f"Function name '{node.name}' should use snake_case",
                severity=Severity.WARNING,
                line=node.lineno,
                column=node.col_offset,
                rule_id="STY011",
                suggestion=f"Rename to '{self._to_snake_case(node.name)}'",
            )

        if len(node.name) > self.style_pass.MAX_FUNCTION_NAME_LENGTH:
            self._add_finding(
                message=f"Function name '{node.name}' is too long ({len(node.name)} > {self.style_pass.MAX_FUNCTION_NAME_LENGTH})",
                severity=Severity.INFO,
                line=node.lineno,
                column=node.col_offset,
                rule_id="STY012",
                suggestion="Consider a shorter, more concise name",
            )

    def _check_argument_names(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.arg in ("self", "cls"):
                continue
            if not self.style_pass.is_snake_case(arg.arg):
                self._add_finding(
                    message=f"Argument name '{arg.arg}' should use snake_case",
                    severity=Severity.WARNING,
                    line=arg.lineno,
                    column=arg.col_offset,
                    rule_id="STY013",
                    suggestion=f"Rename to '{self._to_snake_case(arg.arg)}'",
                )

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            name = node.id
            if name.startswith("_"):
                return
            if name.isupper() or (name.upper() == name and "_" in name):
                if not self.style_pass.is_upper_case(name):
                    self._add_finding(
                        message=f"Constant '{name}' should use UPPER_CASE",
                        severity=Severity.INFO,
                        line=node.lineno,
                        column=node.col_offset,
                        rule_id="STY014",
                    )
            elif not self.style_pass.is_snake_case(name) and not self.style_pass.is_upper_case(name):
                if len(name) > 1:
                    self._add_finding(
                        message=f"Variable name '{name}' should use snake_case",
                        severity=Severity.INFO,
                        line=node.lineno,
                        column=node.col_offset,
                        rule_id="STY015",
                        suggestion=f"Rename to '{self._to_snake_case(name)}'",
                    )
        self.generic_visit(node)

    def _to_snake_case(self, name: str) -> str:
        result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        result = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", result)
        return result.lower()

    def _to_pascal_case(self, name: str) -> str:
        parts = name.replace("-", "_").split("_")
        return "".join(word.capitalize() for word in parts if word)
