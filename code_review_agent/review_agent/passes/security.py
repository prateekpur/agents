"""Security analysis pass for detecting common security vulnerabilities."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from review_agent.core.findings import Finding, FindingCollection, Location, Severity
from review_agent.passes.correctness import BasePass

# Regex: variable names that likely hold secrets (password, token, api_key, etc.)
_SECRET_NAME_PATTERN = re.compile(
    r"(password|passwd|secret|api_key|apikey|token|auth|credential|private_key)",
    re.IGNORECASE,
)

_DANGEROUS_CALLS: dict[str, str] = {
    "eval": "SEC001",
    "exec": "SEC002",
}

# (module, function) -> (rule_id, message)
_DANGEROUS_MODULE_CALLS: dict[tuple[str, str], tuple[str, str]] = {
    ("os", "system"): ("SEC005", "Use of os.system() allows shell injection"),
    ("os", "popen"): ("SEC005", "Use of os.popen() allows shell injection"),
    ("pickle", "loads"): ("SEC006", "Deserializing untrusted data with pickle can execute arbitrary code"),
    ("pickle", "load"): ("SEC006", "Deserializing untrusted data with pickle can execute arbitrary code"),
    ("marshal", "loads"): ("SEC006", "Deserializing untrusted data with marshal can execute arbitrary code"),
    ("shelve", "open"): ("SEC006", "shelve uses pickle internally — untrusted data risk"),
    ("yaml", "load"): ("SEC009", "yaml.load() without SafeLoader can execute arbitrary code"),
}

_WEAK_HASHES: set[str] = {"md5", "sha1"}

# Matches SQL keywords at word boundaries for injection detection
_SQL_KEYWORD_PATTERN = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\b",
    re.IGNORECASE,
)


class SecurityPass(BasePass):
    """
    Analyzes Python code for security vulnerabilities.

    Detects:
    - Use of eval() and exec()
    - Hardcoded secrets and passwords
    - subprocess calls with shell=True
    - Dangerous os.system() / os.popen() usage
    - Insecure deserialization (pickle, marshal, shelve)
    - Dynamic code import via __import__()
    - Weak hash algorithms (MD5, SHA1)
    - yaml.load() without SafeLoader
    - SQL string formatting (potential injection)
    - assert used for security validation
    """

    @property
    def name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Detects common security vulnerabilities and dangerous patterns"

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
                    rule_id="SEC000",
                    category="security",
                )
            )
            return findings
        except FileNotFoundError:
            findings.add(
                Finding(
                    message=f"File not found: {file_path}",
                    severity=Severity.ERROR,
                    location=Location(file=file_path, line=1, column=0),
                    rule_id="SEC000",
                    category="security",
                )
            )
            return findings

        checker = _SecurityChecker(file_path, source, findings)
        checker.visit(tree)

        return findings


class _SecurityChecker(ast.NodeVisitor):

    def __init__(
        self, file_path: Path, source: str, findings: FindingCollection
    ) -> None:
        self.file_path = file_path
        self.source = source
        self.source_lines = source.splitlines()
        self.findings = findings
        self._import_aliases: dict[str, str] = {}

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
                category="security",
                suggestion=suggestion,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self._import_aliases[local_name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self._import_aliases[local_name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_dangerous_builtins(node)
        self._check_subprocess_shell(node)
        self._check_dangerous_module_calls(node)
        self._check_dynamic_import(node)
        self._check_weak_hashing(node)
        self.generic_visit(node)

    def _check_dangerous_builtins(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            return
        func_name = node.func.id
        rule_id = _DANGEROUS_CALLS.get(func_name)
        if rule_id is None:
            return
        self._add_finding(
            message=f"Use of {func_name}() is a security risk — allows arbitrary code execution",
            severity=Severity.ERROR,
            line=node.lineno,
            column=node.col_offset,
            rule_id=rule_id,
            suggestion=f"Avoid {func_name}(). Use ast.literal_eval() for safe parsing or a dedicated parser",
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._check_hardcoded_secret(target.id, node.value, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            self._check_hardcoded_secret(
                node.target.id, node.value, node.lineno, node.col_offset
            )
        self.generic_visit(node)

    def _check_hardcoded_secret(
        self, name: str, value: ast.expr, line: int, column: int
    ) -> None:
        if not _SECRET_NAME_PATTERN.search(name):
            return
        if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value:
            self._add_finding(
                message=f"Possible hardcoded secret in variable '{name}'",
                severity=Severity.WARNING,
                line=line,
                column=column,
                rule_id="SEC003",
                suggestion="Use environment variables or a secrets manager instead of hardcoded values",
            )

    def _check_subprocess_shell(self, node: ast.Call) -> None:
        func_name = self._resolve_call_name(node.func)
        if func_name is None:
            return

        parts = func_name.split(".")
        if len(parts) != 2:
            return
        module, attr = parts
        resolved_module = self._import_aliases.get(module, module)
        if resolved_module != "subprocess":
            return
        if attr not in ("run", "call", "check_call", "check_output", "Popen"):
            return

        for keyword in node.keywords:
            if keyword.arg == "shell":
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    self._add_finding(
                        message=f"subprocess.{attr}() called with shell=True",
                        severity=Severity.WARNING,
                        line=node.lineno,
                        column=node.col_offset,
                        rule_id="SEC004",
                        suggestion="Avoid shell=True. Pass arguments as a list to prevent shell injection",
                    )

    def _check_dangerous_module_calls(self, node: ast.Call) -> None:
        func_name = self._resolve_call_name(node.func)
        if func_name is None:
            return

        parts = func_name.split(".")
        if len(parts) != 2:
            return
        module, attr = parts
        resolved_module = self._import_aliases.get(module, module)

        key = (resolved_module, attr)
        entry = _DANGEROUS_MODULE_CALLS.get(key)
        if entry is None:
            return
        rule_id, message = entry

        # yaml.load() is safe when Loader= kwarg or second positional arg is provided
        if key == ("yaml", "load"):
            for keyword in node.keywords:
                if keyword.arg == "Loader":
                    return
            if len(node.args) >= 2:
                return

        self._add_finding(
            message=message,
            severity=Severity.WARNING,
            line=node.lineno,
            column=node.col_offset,
            rule_id=rule_id,
            suggestion="See https://owasp.org for secure alternatives",
        )

    def _check_dynamic_import(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            self._add_finding(
                message="Use of __import__() enables dynamic code loading",
                severity=Severity.INFO,
                line=node.lineno,
                column=node.col_offset,
                rule_id="SEC007",
                suggestion="Use importlib.import_module() for clearer intent, or static imports where possible",
            )

    def _check_weak_hashing(self, node: ast.Call) -> None:
        func_name = self._resolve_call_name(node.func)
        if func_name is None:
            return

        parts = func_name.split(".")
        if len(parts) != 2:
            return
        module, attr = parts
        resolved_module = self._import_aliases.get(module, module)

        if resolved_module == "hashlib" and attr in _WEAK_HASHES:
            self._add_finding(
                message=f"Use of weak hash algorithm: hashlib.{attr}()",
                severity=Severity.WARNING,
                line=node.lineno,
                column=node.col_offset,
                rule_id="SEC008",
                suggestion="Use hashlib.sha256() or stronger. MD5/SHA1 are broken for security purposes",
            )

        # hashlib.new("md5") — alternative API for weak algorithms
        if resolved_module == "hashlib" and attr == "new" and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                if first_arg.value.lower() in _WEAK_HASHES:
                    self._add_finding(
                        message=f"Use of weak hash algorithm: hashlib.new('{first_arg.value}')",
                        severity=Severity.WARNING,
                        line=node.lineno,
                        column=node.col_offset,
                        rule_id="SEC008",
                        suggestion="Use 'sha256' or stronger. MD5/SHA1 are broken for security purposes",
                    )

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        self._check_sql_fstring(node, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant):
            if isinstance(node.left.value, str):
                self._check_sql_pattern(node.left.value, node.lineno, node.col_offset)
        self.generic_visit(node)

    def _check_sql_fstring(self, node: ast.JoinedStr, line: int, column: int) -> None:
        string_parts: list[str] = []
        has_interpolation = False
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                string_parts.append(value.value)
            else:
                has_interpolation = True

        if has_interpolation:
            combined = " ".join(string_parts).strip()
            self._check_sql_pattern(combined, line, column)

    def _check_sql_pattern(self, text: str, line: int, column: int) -> None:
        if _SQL_KEYWORD_PATTERN.search(text):
            self._add_finding(
                message="Possible SQL injection — query built with string formatting",
                severity=Severity.WARNING,
                line=line,
                column=column,
                rule_id="SEC010",
                suggestion="Use parameterized queries (e.g., cursor.execute('SELECT * FROM t WHERE id=?', (id,)))",
            )

    def visit_Assert(self, node: ast.Assert) -> None:
        self._add_finding(
            message="assert statements are removed when Python runs with -O (optimized mode)",
            severity=Severity.INFO,
            line=node.lineno,
            column=node.col_offset,
            rule_id="SEC011",
            suggestion="Use explicit if/raise for security checks — assert is for debugging only",
        )
        self.generic_visit(node)

    def _resolve_call_name(self, func: ast.expr) -> str | None:
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        if isinstance(func, ast.Name):
            return func.id
        return None
