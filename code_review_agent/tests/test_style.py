from __future__ import annotations

from review_agent.passes.style import StylePass
from tests.conftest import find_by_rule, has_rule

pass_runner = StylePass()


class TestStylePassProperties:
    def test_name(self):
        assert pass_runner.name == "style"

    def test_description(self):
        assert pass_runner.description


class TestSTY000FileNotFound:
    def test_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.py"
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY000")


class TestSTY001LineTooLong:
    def test_long_line_detected(self, make_source):
        long_line = "x = " + "a" * 100 + "\n"
        path = make_source(long_line)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY001")

    def test_short_line_clean(self, make_source):
        path = make_source("x = 1\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY001")


class TestSTY002TrailingWhitespace:
    def test_trailing_space(self, make_source):
        path = make_source("x = 1   \n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY002")


class TestSTY003ConsecutiveBlankLines:
    def test_too_many_blanks(self, make_source):
        path = make_source("x = 1\n\n\n\ny = 2\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY003")

    def test_two_blanks_clean(self, make_source):
        path = make_source("x = 1\n\n\ny = 2\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY003")


class TestSTY004NoNewlineAtEOF:
    def test_missing_newline(self, make_source):
        path = make_source("x = 1")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY004")


class TestSTY005ImportOrdering:
    def test_out_of_order_imports(self, make_source):
        path = make_source("""\
            from review_agent.core import findings
            import os
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY005")

    def test_correct_order_clean(self, make_source):
        path = make_source("""\
            import os
            import sys
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY005")


class TestSTY010ClassName:
    def test_snake_case_class(self, make_source):
        path = make_source("class my_class:\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY010")

    def test_pascal_case_clean(self, make_source):
        path = make_source("class MyClass:\n    pass\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY010")


class TestSTY011FunctionName:
    def test_camel_case_function(self, make_source):
        path = make_source("def myFunction():\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY011")

    def test_snake_case_clean(self, make_source):
        path = make_source("def my_function():\n    pass\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY011")

    def test_dunder_methods_ignored(self, make_source):
        path = make_source("class Foo:\n    def __init__(self):\n        pass\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY011")


class TestSTY012FunctionNameTooLong:
    def test_very_long_name(self, make_source):
        long_name = "a" * 41
        path = make_source(f"def {long_name}():\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY012")


class TestSTY013ArgumentName:
    def test_camel_case_arg(self, make_source):
        path = make_source("def foo(myArg):\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY013")

    def test_self_cls_ignored(self, make_source):
        path = make_source("class A:\n    def foo(self, cls):\n        pass\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY013")


class TestSTY015VariableName:
    def test_camel_case_variable(self, make_source):
        path = make_source("myVariable = 1\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "STY015")

    def test_snake_case_clean(self, make_source):
        path = make_source("my_variable = 1\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY015")

    def test_single_char_ignored(self, make_source):
        path = make_source("x = 1\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "STY015")
