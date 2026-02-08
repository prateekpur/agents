from __future__ import annotations

import json
from pathlib import Path

from review_agent.__main__ import main, collect_python_files, run_analysis
from review_agent.core.findings import Severity


class TestCollectPythonFiles:
    def test_single_file(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\n")
        result = collect_python_files([f], recursive=False)
        assert result == [f]

    def test_ignores_non_python(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hello")
        result = collect_python_files([f], recursive=False)
        assert result == []

    def test_directory_non_recursive(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("y = 2\n")
        result = collect_python_files([tmp_path], recursive=False)
        assert len(result) == 1

    def test_directory_recursive(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("y = 2\n")
        result = collect_python_files([tmp_path], recursive=True)
        assert len(result) == 2

    def test_deduplication(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\n")
        result = collect_python_files([f, f], recursive=False)
        assert len(result) == 1


class TestRunAnalysis:
    def test_all_passes(self, make_source):
        path = make_source("""\
            PASSWORD = "secret"
            def foo(x=[]):
                return eval("1")
        """)
        findings = run_analysis([path], ["correctness", "security"], Severity.HINT)
        assert len(findings) > 0
        rules = {f.rule_id for f in findings}
        assert "COR003" in rules
        assert "SEC001" in rules
        assert "SEC003" in rules

    def test_severity_filter(self, make_source):
        path = make_source("""\
            PASSWORD = "secret"
            eval("1")
        """)
        all_findings = run_analysis([path], ["security"], Severity.HINT)
        error_only = run_analysis([path], ["security"], Severity.ERROR)
        assert len(error_only) <= len(all_findings)
        for f in error_only:
            assert f.severity is Severity.ERROR


class TestMainCLI:
    def test_clean_file_returns_zero(self, make_source):
        path = make_source("x = 1\n")
        exit_code = main([str(path), "-q"])
        assert exit_code == 0

    def test_error_findings_return_one(self, make_source):
        path = make_source("eval('1')\n")
        exit_code = main([str(path), "-p", "security", "-q"])
        assert exit_code == 1

    def test_json_output(self, make_source, capsys):
        path = make_source("eval('1')\n")
        main([str(path), "-p", "security", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["rule_id"] == "SEC001"

    def test_specific_pass_selection(self, make_source):
        path = make_source("""\
            PASSWORD = "secret"
            def foo(x=[]):
                pass
        """)
        sec_findings = run_analysis([path], ["security"], Severity.HINT)
        cor_findings = run_analysis([path], ["correctness"], Severity.HINT)
        sec_rules = {f.rule_id for f in sec_findings}
        cor_rules = {f.rule_id for f in cor_findings}
        assert "SEC003" in sec_rules
        assert "SEC003" not in cor_rules
        assert "COR003" in cor_rules
        assert "COR003" not in sec_rules

    def test_no_files_returns_zero(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        exit_code = main([str(empty_dir), "-q"])
        assert exit_code == 0

    def test_suggestions_flag(self, make_source, capsys):
        path = make_source("eval('1')\n")
        main([str(path), "-p", "security", "--suggestions"])
        captured = capsys.readouterr()
        assert "Suggestion:" in captured.out

    def test_recursive_flag(self, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("eval('1')\n")
        exit_code = main([str(tmp_path), "-r", "-p", "security", "-q"])
        assert exit_code == 1

    def test_severity_filter_cli(self, make_source, capsys):
        path = make_source("""\
            import os
            os.system("ls")
        """)
        main([str(path), "-p", "security", "-s", "error", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        for item in data:
            assert item["severity"] == "error"
