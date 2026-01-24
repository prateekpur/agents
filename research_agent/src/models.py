"""
Data models for the multi-agent system.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Types of sources."""

    WEB = "web"
    RESEARCH = "research"
    INTERNAL = "internal"
    DERIVED = "derived"


class Source(BaseModel):
    """A source of information."""

    title: str
    url: str | None = None
    source_type: SourceType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    content_snippet: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    """Message from an agent."""

    agent_name: str
    content: str
    sources: list[Source] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Question(BaseModel):
    """A question to be answered by the system."""

    question: str
    context: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class Answer(BaseModel):
    """Final answer from the system."""

    question: Question
    answer: str
    sources: list[Source]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    agent_contributions: list[AgentMessage] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
