from __future__ import annotations

from review_agent.core.findings import Severity
from review_agent.passes.security import SecurityPass
from tests.conftest import find_by_rule, has_rule

pass_runner = SecurityPass()


class TestSecurityPassProperties:
    def test_name(self):
        assert pass_runner.name == "security"

    def test_description(self):
        assert pass_runner.description


class TestSEC000Errors:
    def test_syntax_error(self, make_source):
        path = make_source("def foo(\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC000")

    def test_file_not_found(self, tmp_path):
        path = tmp_path / "missing.py"
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC000")


class TestSEC001Eval:
    def test_eval_detected(self, make_source):
        path = make_source("x = eval('1+1')\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC001")
        match = find_by_rule(findings, "SEC001")[0]
        assert match.severity is Severity.ERROR

    def test_no_eval_clean(self, make_source):
        path = make_source("x = int('42')\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC001")


class TestSEC002Exec:
    def test_exec_detected(self, make_source):
        path = make_source("exec('x = 1')\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC002")
        match = find_by_rule(findings, "SEC002")[0]
        assert match.severity is Severity.ERROR


class TestSEC003HardcodedSecrets:
    def test_password_variable(self, make_source):
        path = make_source('PASSWORD = "admin123"\n')
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC003")

    def test_api_key(self, make_source):
        path = make_source('API_KEY = "sk-1234"\n')
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC003")

    def test_token(self, make_source):
        path = make_source('auth_token = "abc"\n')
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC003")

    def test_empty_string_ignored(self, make_source):
        path = make_source('PASSWORD = ""\n')
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC003")

    def test_non_secret_variable_clean(self, make_source):
        path = make_source('username = "admin"\n')
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC003")

    def test_integer_value_ignored(self, make_source):
        path = make_source("PASSWORD = 12345\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC003")

    def test_annotated_assignment(self, make_source):
        path = make_source('secret: str = "hunter2"\n')
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC003")


class TestSEC004SubprocessShell:
    def test_shell_true_detected(self, make_source):
        path = make_source("""\
            import subprocess
            subprocess.run("ls", shell=True)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC004")

    def test_shell_false_clean(self, make_source):
        path = make_source("""\
            import subprocess
            subprocess.run(["ls"], shell=False)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC004")

    def test_no_shell_kwarg_clean(self, make_source):
        path = make_source("""\
            import subprocess
            subprocess.run(["ls"])
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC004")

    def test_popen_shell_true(self, make_source):
        path = make_source("""\
            import subprocess
            subprocess.Popen("ls", shell=True)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC004")

    def test_aliased_import(self, make_source):
        path = make_source("""\
            import subprocess as sp
            sp.run("ls", shell=True)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC004")


class TestSEC005OsSystem:
    def test_os_system_detected(self, make_source):
        path = make_source("""\
            import os
            os.system("ls")
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC005")

    def test_os_popen_detected(self, make_source):
        path = make_source("""\
            import os
            os.popen("ls")
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC005")


class TestSEC006Deserialization:
    def test_pickle_loads(self, make_source):
        path = make_source("""\
            import pickle
            pickle.loads(data)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC006")

    def test_pickle_load(self, make_source):
        path = make_source("""\
            import pickle
            pickle.load(f)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC006")

    def test_marshal_loads(self, make_source):
        path = make_source("""\
            import marshal
            marshal.loads(data)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC006")


class TestSEC007DynamicImport:
    def test_dunder_import(self, make_source):
        path = make_source('mod = __import__("os")\n')
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC007")
        match = find_by_rule(findings, "SEC007")[0]
        assert match.severity is Severity.INFO


class TestSEC008WeakHashing:
    def test_hashlib_md5(self, make_source):
        path = make_source("""\
            import hashlib
            hashlib.md5(b"data")
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC008")

    def test_hashlib_sha1(self, make_source):
        path = make_source("""\
            import hashlib
            hashlib.sha1(b"data")
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC008")

    def test_hashlib_new_md5(self, make_source):
        path = make_source("""\
            import hashlib
            hashlib.new("md5", b"data")
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC008")

    def test_hashlib_sha256_clean(self, make_source):
        path = make_source("""\
            import hashlib
            hashlib.sha256(b"data")
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC008")


class TestSEC009YamlLoad:
    def test_yaml_load_no_loader(self, make_source):
        path = make_source("""\
            import yaml
            yaml.load(data)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC009")

    def test_yaml_load_with_loader_kwarg_clean(self, make_source):
        path = make_source("""\
            import yaml
            yaml.load(data, Loader=yaml.SafeLoader)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC009")

    def test_yaml_load_with_positional_loader_clean(self, make_source):
        path = make_source("""\
            import yaml
            yaml.load(data, yaml.SafeLoader)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC009")


class TestSEC010SQLInjection:
    def test_fstring_sql(self, make_source):
        path = make_source("""\
            user_id = "1"
            query = f"SELECT * FROM users WHERE id = {user_id}"
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC010")

    def test_percent_format_sql(self, make_source):
        path = make_source("""\
            query = "SELECT * FROM users WHERE id = %s" % user_id
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC010")

    def test_plain_string_clean(self, make_source):
        path = make_source("""\
            name = f"hello {user}"
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "SEC010")


class TestSEC011Assert:
    def test_assert_detected(self, make_source):
        path = make_source("assert x > 0\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "SEC011")
        match = find_by_rule(findings, "SEC011")[0]
        assert match.severity is Severity.INFO


class TestCleanFile:
    def test_no_findings(self, make_source):
        path = make_source("""\
            import os

            name = os.getenv("USER", "default")

            def greet(name):
                return f"Hello, {name}"
        """)
        findings = pass_runner.analyze(path)
        assert len(findings) == 0
