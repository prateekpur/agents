from __future__ import annotations

import argparse
import sys
from pathlib import Path

from review_agent.core.findings import FindingCollection, Severity
from review_agent.passes import CorrectnessPass, SecurityPass, StylePass


PASSES = {
    "correctness": CorrectnessPass,
    "security": SecurityPass,
    "style": StylePass,
}


def collect_python_files(paths: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            pattern = "**/*.py" if recursive else "*.py"
            files.extend(path.glob(pattern))
    return sorted(set(files))


def format_finding_text(finding, show_suggestions: bool) -> str:
    line = str(finding)
    if show_suggestions and finding.suggestion:
        line += f"\n    Suggestion: {finding.suggestion}"
    return line


def format_findings_json(findings: FindingCollection) -> str:
    import json
    return json.dumps([f.to_dict() for f in findings], indent=2)


def run_analysis(
    files: list[Path],
    pass_names: list[str],
    min_severity: Severity,
) -> FindingCollection:
    all_findings = FindingCollection()

    for name in pass_names:
        pass_cls = PASSES[name]
        pass_instance = pass_cls()
        for file_path in files:
            findings = pass_instance.analyze(file_path)
            all_findings.extend(list(findings))

    severity_order = [Severity.ERROR, Severity.WARNING, Severity.INFO, Severity.HINT]
    min_idx = severity_order.index(min_severity)
    allowed = set(severity_order[: min_idx + 1])

    filtered = FindingCollection()
    for f in all_findings:
        if f.severity in allowed:
            filtered.add(f)

    return filtered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="review-agent",
        description="Analyze Python code for correctness and style issues",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to analyze",
    )
    parser.add_argument(
        "-p", "--pass",
        dest="passes",
        action="append",
        choices=list(PASSES.keys()),
        help="Analysis passes to run (default: all)",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively search directories",
    )
    parser.add_argument(
        "-s", "--severity",
        choices=["error", "warning", "info", "hint"],
        default="hint",
        help="Minimum severity to report (default: hint)",
    )
    parser.add_argument(
        "--suggestions",
        action="store_true",
        help="Show fix suggestions",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only output findings, no summary",
    )

    args = parser.parse_args(argv)

    pass_names = args.passes or list(PASSES.keys())
    min_severity = Severity(args.severity)

    files = collect_python_files(args.paths, args.recursive)
    if not files:
        if not args.quiet:
            print("No Python files found", file=sys.stderr)
        return 0

    findings = run_analysis(files, pass_names, min_severity)

    if args.json:
        print(format_findings_json(findings))
    else:
        for f in findings.sorted_by_location():
            print(format_finding_text(f, args.suggestions))

        if not args.quiet:
            print(f"\n{len(findings)} finding(s) in {len(files)} file(s)", file=sys.stderr)
            if findings.error_count:
                print(f"  Errors: {findings.error_count}", file=sys.stderr)
            if findings.warning_count:
                print(f"  Warnings: {findings.warning_count}", file=sys.stderr)

    if findings.error_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
