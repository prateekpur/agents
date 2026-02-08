from __future__ import annotations

from review_agent.passes.correctness import CorrectnessPass
from tests.conftest import find_by_rule, has_rule

pass_runner = CorrectnessPass()


class TestCorrectnessPassProperties:
    def test_name(self):
        assert pass_runner.name == "correctness"

    def test_description(self):
        assert pass_runner.description


class TestCOR001SyntaxError:
    def test_syntax_error_detected(self, make_source):
        path = make_source("def foo(\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR001")
        assert findings.error_count == 1


class TestCOR000FileNotFound:
    def test_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.py"
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR000")


class TestCOR002NoneComparison:
    def test_eq_none(self, make_source):
        path = make_source("x = 1\nif x == None:\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR002")

    def test_neq_none(self, make_source):
        path = make_source("x = 1\nif x != None:\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR002")

    def test_none_eq_x(self, make_source):
        path = make_source("x = 1\nif None == x:\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR002")

    def test_is_none_clean(self, make_source):
        path = make_source("x = 1\nif x is None:\n    pass\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "COR002")


class TestCOR003MutableDefaults:
    def test_list_default(self, make_source):
        path = make_source("def foo(x=[]):\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR003")

    def test_dict_default(self, make_source):
        path = make_source("def foo(x={}):\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR003")

    def test_set_default(self, make_source):
        path = make_source("def foo(x={1, 2}):\n    pass\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR003")

    def test_none_default_clean(self, make_source):
        path = make_source("def foo(x=None):\n    pass\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "COR003")


class TestCOR004UnreachableCode:
    def test_after_return(self, make_source):
        path = make_source("""\
            def foo():
                return 1
                x = 2
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR004")

    def test_after_raise(self, make_source):
        path = make_source("""\
            def foo():
                raise ValueError()
                x = 2
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR004")

    def test_no_unreachable(self, make_source):
        path = make_source("""\
            def foo():
                x = 1
                return x
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "COR004")


class TestCOR005BareExcept:
    def test_bare_except_detected(self, make_source):
        path = make_source("""\
            try:
                pass
            except:
                pass
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR005")

    def test_typed_except_clean(self, make_source):
        path = make_source("""\
            try:
                pass
            except Exception:
                pass
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "COR005")


class TestCOR006AlwaysTrueAssert:
    def test_always_true(self, make_source):
        path = make_source('assert True\n')
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR006")

    def test_always_true_string(self, make_source):
        path = make_source('assert "nonempty"\n')
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR006")


class TestCOR007AlwaysFalseAssert:
    def test_always_false(self, make_source):
        path = make_source("assert False\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR007")

    def test_assert_zero(self, make_source):
        path = make_source("assert 0\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "COR007")


class TestCleanFile:
    def test_no_findings(self, make_source):
        path = make_source("""\
            def add(a, b):
                return a + b
        """)
        findings = pass_runner.analyze(path)
        assert len(findings) == 0
