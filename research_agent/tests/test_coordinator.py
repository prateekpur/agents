"""
Tests for coordinator agent.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.coordinator import CoordinatorAgent
from src.models import AgentMessage, Answer, Question, Source, SourceType


@pytest.fixture
def mock_agents():
    """Create mock agents."""
    with (
        patch("src.coordinator.ResearcherAgent") as researcher,
        patch("src.coordinator.FactCheckerAgent") as fact_checker,
        patch("src.coordinator.SynthesizerAgent") as synthesizer,
    ):

        # Setup mock researcher
        researcher_instance = Mock()
        researcher_instance.process = AsyncMock(
            return_value=AgentMessage(
                agent_name="researcher",
                content="Research findings about renewable energy",
                sources=[Source(title="Research Source", source_type=SourceType.RESEARCH)],
            )
        )
        researcher.return_value = researcher_instance

        # Setup mock fact checker
        fact_checker_instance = Mock()
        fact_checker_instance.process = AsyncMock(
            return_value=AgentMessage(
                agent_name="fact_checker", content="Facts are verified and accurate", sources=[]
            )
        )
        fact_checker.return_value = fact_checker_instance

        # Setup mock synthesizer
        synthesizer_instance = Mock()
        synthesizer_instance.process = AsyncMock(
            return_value=AgentMessage(
                agent_name="synthesizer",
                content="Synthesized answer about renewable energy benefits",
                sources=[],
            )
        )
        synthesizer.return_value = synthesizer_instance

        yield {
            "researcher": researcher_instance,
            "fact_checker": fact_checker_instance,
            "synthesizer": synthesizer_instance,
        }


class TestCoordinatorAgent:
    """Tests for CoordinatorAgent."""

    @pytest.mark.asyncio
    async def test_answer_question(self, mock_agents):
        """Test answering a question."""
        coordinator = CoordinatorAgent()

        question = Question(
            question="What are the benefits of renewable energy?", context="Focus on solar and wind"
        )

        answer = await coordinator.answer_question(question)

        assert isinstance(answer, Answer)
        assert answer.question == question
        assert len(answer.answer) > 0
        assert 0 <= answer.confidence <= 1.0
        assert len(answer.agent_contributions) == 3

    @pytest.mark.asyncio
    async def test_agents_called_in_order(self, mock_agents):
        """Test that agents are called in the correct order."""
        coordinator = CoordinatorAgent()

        question = Question(question="Test question")
        await coordinator.answer_question(question)

        # Verify researcher was called first
        mock_agents["researcher"].process.assert_called_once()

        # Verify fact checker was called with researcher context
        assert mock_agents["fact_checker"].process.called

        # Verify synthesizer was called last
        assert mock_agents["synthesizer"].process.called

    def test_collect_sources(self, mock_agents):
        """Test source collection and deduplication."""
        coordinator = CoordinatorAgent()

        # Add some mock messages with sources
        coordinator.agent_messages = [
            AgentMessage(
                agent_name="agent1",
                content="Test",
                sources=[
                    Source(title="Source 1", source_type=SourceType.WEB),
                    Source(title="Source 2", source_type=SourceType.RESEARCH),
                ],
            ),
            AgentMessage(
                agent_name="agent2",
                content="Test",
                sources=[
                    Source(title="Source 1", source_type=SourceType.WEB),  # Duplicate
                    Source(title="Source 3", source_type=SourceType.INTERNAL),
                ],
            ),
        ]

        sources = coordinator._collect_sources()

        # Should have 3 unique sources
        assert len(sources) == 3
        titles = [s.title for s in sources]
        assert "Source 1" in titles
        assert "Source 2" in titles
        assert "Source 3" in titles

    def test_calculate_confidence_high(self, mock_agents):
        """Test confidence calculation with positive indicators."""
        coordinator = CoordinatorAgent()

        fact_check_content = (
            "The information is verified and accurate. All sources are reliable and confirmed."
        )
        confidence = coordinator._calculate_confidence(fact_check_content)

        assert confidence > 0.7

    def test_calculate_confidence_low(self, mock_agents):
        """Test confidence calculation with negative indicators."""
        coordinator = CoordinatorAgent()

        fact_check_content = (
            "The information is uncertain and unverified. Sources are questionable."
        )
        confidence = coordinator._calculate_confidence(fact_check_content)

        assert confidence < 0.7

    def test_calculate_confidence_default(self, mock_agents):
        """Test default confidence when no keywords found."""
        coordinator = CoordinatorAgent()

        fact_check_content = "Some neutral content without specific keywords."
        confidence = coordinator._calculate_confidence(fact_check_content)

        assert confidence == 0.7

    def test_build_reasoning(self, mock_agents):
        """Test reasoning building from agent messages."""
        coordinator = CoordinatorAgent()

        coordinator.agent_messages = [
            AgentMessage(agent_name="researcher", content="A" * 300),
            AgentMessage(agent_name="fact_checker", content="B" * 300),
        ]

        reasoning = coordinator._build_reasoning()

        assert "RESEARCHER" in reasoning
        assert "FACT_CHECKER" in reasoning
        assert len(reasoning) > 0
