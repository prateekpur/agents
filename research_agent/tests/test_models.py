"""
Tests for the multi-agent system.
"""
import pytest
from src.models import Question, Source, SourceType


def test_question_creation():
    """Test creating a question."""
    q = Question(question="What is AI?")
    assert q.question == "What is AI?"
    assert q.context is None


def test_source_creation():
    """Test creating a source."""
    source = Source(
        title="AI Research Paper",
        url="https://example.com",
        source_type=SourceType.RESEARCH,
        confidence=0.9
    )
    assert source.title == "AI Research Paper"
    assert source.confidence == 0.9
    assert source.source_type == SourceType.RESEARCH
