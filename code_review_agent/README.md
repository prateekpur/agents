# Code Review Agent

An automated code review agent that analyzes code for issues and provides actionable findings.

## Overview

Code Review Agent performs static analysis passes over your codebase to identify:

- **Correctness issues**: Bugs, logic errors, and potential runtime failures
- **Style violations**: Formatting and naming convention issues
- **Security vulnerabilities**: eval/exec, hardcoded secrets, shell injection, insecure deserialization, weak hashing, SQL injection
- **Performance concerns**: Inefficient code patterns

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Project Structure

```
code_review_agent/
├── pyproject.toml
├── README.md
└── review_agent/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   └── findings.py      # Finding data models and severity levels
    └── passes/
        ├── __init__.py
        ├── correctness.py   # Correctness analysis pass
        ├── security.py      # Security vulnerability detection
        └── style.py         # Style and naming convention checks
```

## Usage

```python
from review_agent.core.findings import Finding, Severity
from review_agent.passes.correctness import CorrectnessPass

# Run correctness analysis
pass_runner = CorrectnessPass()
findings = pass_runner.analyze("path/to/code.py")

for finding in findings:
    print(f"[{finding.severity.name}] {finding.message} at line {finding.line}")
```

## Development

Run tests:

```bash
pytest
```

Run linting:

```bash
ruff check .
mypy review_agent/
```

## License

MIT
