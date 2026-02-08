from __future__ import annotations

from review_agent.core.findings import Severity
from review_agent.passes.performance import PerformancePass
from tests.conftest import find_by_rule, has_rule

pass_runner = PerformancePass()


class TestPerformancePassProperties:
    def test_name(self):
        assert pass_runner.name == "performance"

    def test_description(self):
        assert pass_runner.description


class TestPERF000Errors:
    def test_syntax_error(self, make_source):
        path = make_source("def foo(\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF000")

    def test_file_not_found(self, tmp_path):
        path = tmp_path / "missing.py"
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF000")


class TestPERF001RangeLen:
    def test_range_len_detected(self, make_source):
        path = make_source("""\
            data = [1, 2, 3]
            for i in range(len(data)):
                print(data[i])
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF001")

    def test_direct_iteration_clean(self, make_source):
        path = make_source("""\
            data = [1, 2, 3]
            for item in data:
                print(item)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF001")

    def test_enumerate_clean(self, make_source):
        path = make_source("""\
            data = [1, 2, 3]
            for i, item in enumerate(data):
                print(i, item)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF001")

    def test_range_with_step_clean(self, make_source):
        path = make_source("""\
            for i in range(0, 10, 2):
                print(i)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF001")


class TestPERF002StringConcatInLoop:
    def test_string_plus_eq_detected(self, make_source):
        path = make_source("""\
            result = ""
            for item in items:
                result += "x"
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF002")

    def test_fstring_plus_eq_detected(self, make_source):
        path = make_source("""\
            result = ""
            for item in items:
                result += f"{item},"
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF002")

    def test_integer_plus_eq_clean(self, make_source):
        path = make_source("""\
            total = 0
            for x in items:
                total += 1
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF002")


class TestPERF003AppendInLoop:
    def test_simple_append_detected(self, make_source):
        path = make_source("""\
            result = []
            for item in data:
                result.append(item)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF003")

    def test_filtered_append_detected(self, make_source):
        path = make_source("""\
            result = []
            for item in data:
                if item > 0:
                    result.append(item)
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF003")

    def test_complex_loop_body_clean(self, make_source):
        path = make_source("""\
            result = []
            for item in data:
                x = transform(item)
                result.append(x)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF003")


class TestPERF004MembershipOnList:
    def test_in_list_literal_detected(self, make_source):
        path = make_source("""\
            x = 1
            if x in [1, 2, 3]:
                pass
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF004")

    def test_not_in_list_literal_detected(self, make_source):
        path = make_source("""\
            x = "a"
            if x not in ["a", "b", "c"]:
                pass
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF004")

    def test_in_set_literal_clean(self, make_source):
        path = make_source("""\
            x = 1
            if x in {1, 2, 3}:
                pass
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF004")

    def test_short_list_ignored(self, make_source):
        path = make_source("""\
            x = 1
            if x in [1, 2]:
                pass
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF004")


class TestPERF005ConstructorVsLiteral:
    def test_dict_constructor(self, make_source):
        path = make_source("x = dict()\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF005")

    def test_list_constructor(self, make_source):
        path = make_source("x = list()\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF005")

    def test_tuple_constructor(self, make_source):
        path = make_source("x = tuple()\n")
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF005")

    def test_dict_literal_clean(self, make_source):
        path = make_source("x = {}\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF005")

    def test_constructor_with_args_clean(self, make_source):
        path = make_source("x = list(range(10))\n")
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF005")


class TestPERF006SortedMinMax:
    def test_sorted_first_element(self, make_source):
        path = make_source("""\
            data = [3, 1, 2]
            smallest = sorted(data)[0]
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF006")
        match = find_by_rule(findings, "PERF006")[0]
        assert "min" in match.suggestion

    def test_sorted_last_element(self, make_source):
        path = make_source("""\
            data = [3, 1, 2]
            largest = sorted(data)[-1]
        """)
        findings = pass_runner.analyze(path)
        assert has_rule(findings, "PERF006")
        match = find_by_rule(findings, "PERF006")[0]
        assert "max" in match.suggestion

    def test_sorted_middle_element_clean(self, make_source):
        path = make_source("""\
            data = [3, 1, 2]
            median = sorted(data)[1]
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF006")

    def test_plain_sorted_clean(self, make_source):
        path = make_source("""\
            data = [3, 1, 2]
            ordered = sorted(data)
        """)
        findings = pass_runner.analyze(path)
        assert not has_rule(findings, "PERF006")


class TestCleanFile:
    def test_no_findings(self, make_source):
        path = make_source("""\
            data = [1, 2, 3]

            for i, item in enumerate(data):
                print(i, item)

            doubled = [x * 2 for x in data]

            smallest = min(data)

            if 5 in {1, 2, 3, 4, 5}:
                print("found")
        """)
        findings = pass_runner.analyze(path)
        assert len(findings) == 0
