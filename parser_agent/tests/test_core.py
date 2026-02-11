import re
from hn_part_time_jobs import strip_html, compile_keywords, matches_part_time, extract_first_line


def test_strip_html_basic():
    html = "<p>Hello <strong>World</strong></p>"
    out = strip_html(html)
    assert "Hello" in out and "World" in out


def test_matches_part_time_basic():
    text = "We're hiring a part-time contractor for a small project"
    patterns = compile_keywords()
    matched = matches_part_time(text, patterns)
    assert matched, f"Expected a match but got none: {matched}"


def test_extract_first_line():
    s = "\n\nCompany X - Part time role\nDetails: remote"
    first = extract_first_line(s)
    assert "Company X" in first
