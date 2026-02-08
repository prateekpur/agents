"""Finding data models and severity levels for code review results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(Enum):
    """Severity levels for code review findings."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"

    def __lt__(self, other: "Severity") -> bool:
        """Enable sorting by severity (ERROR is highest)."""
        order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2, Severity.HINT: 3}
        return order[self] < order[other]


@dataclass
class Location:
    """Represents a location in source code."""

    file: Path
    line: int
    column: int = 0
    end_line: int | None = None
    end_column: int | None = None

    def __str__(self) -> str:
        """Format location as 'file:line:column'."""
        return f"{self.file}:{self.line}:{self.column}"


@dataclass
class Finding:
    """Represents a single code review finding."""

    message: str
    severity: Severity
    location: Location
    rule_id: str
    category: str = "general"
    suggestion: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        """Format finding for display."""
        prefix = f"[{self.severity.name}]"
        loc = str(self.location)
        return f"{prefix} {loc}: {self.message} ({self.rule_id})"

    def to_dict(self) -> dict[str, object]:
        """Convert finding to dictionary representation."""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "location": {
                "file": str(self.location.file),
                "line": self.location.line,
                "column": self.location.column,
                "end_line": self.location.end_line,
                "end_column": self.location.end_column,
            },
            "rule_id": self.rule_id,
            "category": self.category,
            "suggestion": self.suggestion,
            "metadata": self.metadata,
        }


class FindingCollection:
    """A collection of findings with filtering and grouping capabilities."""

    def __init__(self, findings: list[Finding] | None = None) -> None:
        """Initialize with optional list of findings."""
        self._findings: list[Finding] = findings or []

    def add(self, finding: Finding) -> None:
        """Add a finding to the collection."""
        self._findings.append(finding)

    def extend(self, findings: list[Finding]) -> None:
        """Add multiple findings to the collection."""
        self._findings.extend(findings)

    def filter_by_severity(self, severity: Severity) -> "FindingCollection":
        """Return findings matching the given severity."""
        return FindingCollection([f for f in self._findings if f.severity == severity])

    def filter_by_file(self, file: Path) -> "FindingCollection":
        """Return findings for a specific file."""
        return FindingCollection([f for f in self._findings if f.location.file == file])

    def filter_by_category(self, category: str) -> "FindingCollection":
        """Return findings matching the given category."""
        return FindingCollection([f for f in self._findings if f.category == category])

    def sorted_by_severity(self) -> list[Finding]:
        """Return findings sorted by severity (ERROR first)."""
        return sorted(self._findings, key=lambda f: f.severity)

    def sorted_by_location(self) -> list[Finding]:
        """Return findings sorted by file and line number."""
        return sorted(self._findings, key=lambda f: (str(f.location.file), f.location.line))

    @property
    def error_count(self) -> int:
        """Count of ERROR severity findings."""
        return len(self.filter_by_severity(Severity.ERROR))

    @property
    def warning_count(self) -> int:
        """Count of WARNING severity findings."""
        return len(self.filter_by_severity(Severity.WARNING))

    def __len__(self) -> int:
        """Return the number of findings."""
        return len(self._findings)

    def __iter__(self):
        """Iterate over findings."""
        return iter(self._findings)

    def __bool__(self) -> bool:
        """Return True if there are any findings."""
        return len(self._findings) > 0
