from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture()
def make_source(tmp_path: Path):
    _counter = 0

    def _make(code: str, *, filename: str | None = None) -> Path:
        nonlocal _counter
        _counter += 1
        name = filename or f"test_{_counter}.py"
        p = tmp_path / name
        p.write_text(textwrap.dedent(code))
        return p

    return _make


def find_by_rule(findings, rule_id: str):
    return [f for f in findings if f.rule_id == rule_id]


def has_rule(findings, rule_id: str) -> bool:
    return len(find_by_rule(findings, rule_id)) > 0
