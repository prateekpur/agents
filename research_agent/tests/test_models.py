"""
Tests for data models.
"""

from datetime import datetime

from src.models import AgentMessage, Answer, Question, Source, SourceType


class TestQuestion:
    """Tests for Question model."""

    def test_question_creation(self):
        """Test creating a question."""
        q = Question(question="What is AI?")
        assert q.question == "What is AI?"
        assert q.context is None
        assert isinstance(q.timestamp, datetime)

    def test_question_with_context(self):
        """Test creating a question with context."""
        q = Question(question="What is AI?", context="In the context of machine learning")
        assert q.context == "In the context of machine learning"

    def test_question_with_constraints(self):
        """Test creating a question with constraints."""
        q = Question(question="What is AI?", constraints={"max_length": 500})
        assert q.constraints["max_length"] == 500


class TestSource:
    """Tests for Source model."""

    def test_source_creation(self):
        """Test creating a source."""
        source = Source(
            title="AI Research Paper",
            url="https://example.com",
            source_type=SourceType.RESEARCH,
            confidence=0.9,
        )
        assert source.title == "AI Research Paper"
        assert source.confidence == 0.9
        assert source.source_type == SourceType.RESEARCH

    def test_source_default_confidence(self):
        """Test source default confidence is 1.0."""
        source = Source(title="Test", source_type=SourceType.WEB)
        assert source.confidence == 1.0

    def test_source_with_metadata(self):
        """Test source with metadata."""
        source = Source(
            title="Test",
            source_type=SourceType.INTERNAL,
            metadata={"author": "John Doe", "year": 2026},
        )
        assert source.metadata["author"] == "John Doe"
        assert source.metadata["year"] == 2026


class TestAgentMessage:
    """Tests for AgentMessage model."""

    def test_agent_message_creation(self):
        """Test creating an agent message."""
        msg = AgentMessage(agent_name="researcher", content="Test content")
        assert msg.agent_name == "researcher"
        assert msg.content == "Test content"
        assert isinstance(msg.timestamp, datetime)
        assert len(msg.sources) == 0

    def test_agent_message_with_sources(self):
        """Test agent message with sources."""
        source = Source(title="Test Source", source_type=SourceType.WEB)
        msg = AgentMessage(agent_name="researcher", content="Test content", sources=[source])
        assert len(msg.sources) == 1
        assert msg.sources[0].title == "Test Source"


class TestAnswer:
    """Tests for Answer model."""

    def test_answer_creation(self):
        """Test creating an answer."""
        question = Question(question="What is AI?")
        answer = Answer(
            question=question,
            answer="AI is artificial intelligence",
            sources=[],
            reasoning="Based on research",
            confidence=0.85,
        )
        assert answer.answer == "AI is artificial intelligence"
        assert answer.confidence == 0.85
        assert answer.reasoning == "Based on research"
        assert isinstance(answer.timestamp, datetime)

    def test_answer_with_sources(self):
        """Test answer with sources."""
        question = Question(question="What is AI?")
        sources = [
            Source(title="Source 1", source_type=SourceType.RESEARCH),
            Source(title="Source 2", source_type=SourceType.WEB),
        ]
        answer = Answer(
            question=question,
            answer="Test answer",
            sources=sources,
            reasoning="Test reasoning",
            confidence=0.9,
        )
        assert len(answer.sources) == 2
        assert answer.sources[0].title == "Source 1"

    def test_answer_with_agent_contributions(self):
        """Test answer with agent contributions."""
        question = Question(question="What is AI?")
        msg = AgentMessage(agent_name="researcher", content="Research findings")
        answer = Answer(
            question=question,
            answer="Test answer",
            sources=[],
            reasoning="Test",
            confidence=0.8,
            agent_contributions=[msg],
        )
        assert len(answer.agent_contributions) == 1
        assert answer.agent_contributions[0].agent_name == "researcher"
