from __future__ import annotations

from pathlib import Path

from review_agent.core.findings import Finding, FindingCollection, Location, Severity


class TestSeverity:
    def test_ordering(self):
        assert Severity.ERROR < Severity.WARNING
        assert Severity.WARNING < Severity.INFO
        assert Severity.INFO < Severity.HINT

    def test_values(self):
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"
        assert Severity.HINT.value == "hint"

    def test_from_string(self):
        assert Severity("error") is Severity.ERROR
        assert Severity("hint") is Severity.HINT


class TestLocation:
    def test_str_format(self):
        loc = Location(file=Path("foo.py"), line=10, column=5)
        assert str(loc) == "foo.py:10:5"

    def test_defaults(self):
        loc = Location(file=Path("a.py"), line=1)
        assert loc.column == 0
        assert loc.end_line is None
        assert loc.end_column is None


class TestFinding:
    def _make_finding(self, **overrides):
        defaults = {
            "message": "test message",
            "severity": Severity.WARNING,
            "location": Location(file=Path("t.py"), line=1, column=0),
            "rule_id": "TST001",
        }
        defaults.update(overrides)
        return Finding(**defaults)

    def test_str_contains_severity_and_rule(self):
        f = self._make_finding()
        s = str(f)
        assert "[WARNING]" in s
        assert "TST001" in s
        assert "test message" in s

    def test_to_dict_keys(self):
        f = self._make_finding(suggestion="fix it")
        d = f.to_dict()
        assert d["message"] == "test message"
        assert d["severity"] == "warning"
        assert d["rule_id"] == "TST001"
        assert d["suggestion"] == "fix it"
        assert d["location"]["line"] == 1

    def test_default_category(self):
        f = self._make_finding()
        assert f.category == "general"

    def test_custom_category(self):
        f = self._make_finding(category="security")
        assert f.category == "security"

    def test_metadata_default_empty(self):
        f = self._make_finding()
        assert f.metadata == {}


class TestFindingCollection:
    def _make(self, *severities: Severity) -> FindingCollection:
        col = FindingCollection()
        for i, sev in enumerate(severities):
            col.add(
                Finding(
                    message=f"msg {i}",
                    severity=sev,
                    location=Location(file=Path("t.py"), line=i + 1, column=0),
                    rule_id=f"T{i:03d}",
                )
            )
        return col

    def test_len(self):
        col = self._make(Severity.ERROR, Severity.WARNING)
        assert len(col) == 2

    def test_bool_empty(self):
        assert not FindingCollection()

    def test_bool_nonempty(self):
        assert self._make(Severity.ERROR)

    def test_iter(self):
        col = self._make(Severity.ERROR, Severity.WARNING)
        items = list(col)
        assert len(items) == 2

    def test_extend(self):
        col = FindingCollection()
        f = Finding(
            message="x",
            severity=Severity.ERROR,
            location=Location(file=Path("t.py"), line=1, column=0),
            rule_id="T000",
        )
        col.extend([f, f])
        assert len(col) == 2

    def test_error_count(self):
        col = self._make(Severity.ERROR, Severity.WARNING, Severity.ERROR)
        assert col.error_count == 2

    def test_warning_count(self):
        col = self._make(Severity.WARNING, Severity.WARNING, Severity.INFO)
        assert col.warning_count == 2

    def test_filter_by_severity(self):
        col = self._make(Severity.ERROR, Severity.WARNING, Severity.ERROR)
        errors = col.filter_by_severity(Severity.ERROR)
        assert len(errors) == 2

    def test_filter_by_file(self):
        col = FindingCollection()
        col.add(
            Finding(
                message="a",
                severity=Severity.ERROR,
                location=Location(file=Path("a.py"), line=1, column=0),
                rule_id="T000",
            )
        )
        col.add(
            Finding(
                message="b",
                severity=Severity.ERROR,
                location=Location(file=Path("b.py"), line=1, column=0),
                rule_id="T001",
            )
        )
        filtered = col.filter_by_file(Path("a.py"))
        assert len(filtered) == 1

    def test_filter_by_category(self):
        col = FindingCollection()
        col.add(
            Finding(
                message="a",
                severity=Severity.ERROR,
                location=Location(file=Path("t.py"), line=1, column=0),
                rule_id="T000",
                category="security",
            )
        )
        col.add(
            Finding(
                message="b",
                severity=Severity.ERROR,
                location=Location(file=Path("t.py"), line=2, column=0),
                rule_id="T001",
                category="style",
            )
        )
        assert len(col.filter_by_category("security")) == 1

    def test_sorted_by_severity(self):
        col = self._make(Severity.HINT, Severity.ERROR, Severity.WARNING)
        result = col.sorted_by_severity()
        severities = [f.severity for f in result]
        assert severities == [Severity.ERROR, Severity.WARNING, Severity.HINT]

    def test_sorted_by_location(self):
        col = FindingCollection()
        col.add(
            Finding(
                message="b",
                severity=Severity.ERROR,
                location=Location(file=Path("b.py"), line=5, column=0),
                rule_id="T000",
            )
        )
        col.add(
            Finding(
                message="a",
                severity=Severity.ERROR,
                location=Location(file=Path("a.py"), line=1, column=0),
                rule_id="T001",
            )
        )
        result = col.sorted_by_location()
        assert str(result[0].location.file) == "a.py"
