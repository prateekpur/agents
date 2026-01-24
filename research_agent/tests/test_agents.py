"""
Tests for base agent and specific agents.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.agents.base_agent import BaseAgent
from src.agents.researcher import ResearcherAgent
from src.agents.fact_checker import FactCheckerAgent
from src.agents.synthesizer import SynthesizerAgent
from src.config import AgentConfig
from src.models import AgentMessage


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    def _build_prompt(self, input_text, context=None):
        """Build a simple test prompt."""
        return f"Test prompt: {input_text}"


@pytest.fixture
def agent_config():
    """Create a test agent configuration."""
    return AgentConfig(
        name="test_agent",
        role="Test role",
        model="claude-sonnet-4-20250514",
        temperature=0.7,
        max_tokens=1000
    )


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    with patch('src.agents.base_agent.Anthropic') as mock_client:
        # Mock the messages.create method
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response from LLM")]
        mock_instance.messages.create.return_value = mock_response
        mock_client.return_value = mock_instance
        yield mock_instance


class TestBaseAgent:
    """Tests for BaseAgent."""
    
    def test_agent_initialization(self, agent_config, mock_anthropic_client):
        """Test agent initialization."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            assert agent.name == "test_agent"
            assert agent.role == "Test role"
            assert agent.config == agent_config
    
    def test_agent_requires_api_key(self, agent_config):
        """Test that agent raises error without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
                ConcreteAgent(agent_config)
    
    @pytest.mark.asyncio
    async def test_process(self, agent_config, mock_anthropic_client):
        """Test processing input."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            result = await agent.process("Test input")
            
            assert isinstance(result, AgentMessage)
            assert result.agent_name == "test_agent"
            assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_get_llm_response(self, agent_config, mock_anthropic_client):
        """Test getting LLM response."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            response, sources = await agent._get_llm_response("Test prompt")
            
            assert response == "Test response from LLM"
            assert isinstance(sources, list)
            mock_anthropic_client.messages.create.assert_called_once()
    
    def test_extract_sources(self, agent_config, mock_anthropic_client):
        """Test source extraction (placeholder implementation)."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            sources = agent._extract_sources("Some text with sources")
            
            # Current implementation returns empty list
            assert isinstance(sources, list)


class TestResearcherAgent:
    """Tests for ResearcherAgent."""
    
    def test_build_prompt_without_context(self, agent_config, mock_anthropic_client):
        """Test building research prompt without context."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ResearcherAgent(agent_config)
            
            prompt = agent._build_prompt("What is AI?")
            
            assert "research agent" in prompt.lower()
            assert "What is AI?" in prompt
            assert "comprehensive" in prompt.lower()
    
    def test_build_prompt_with_context(self, agent_config, mock_anthropic_client):
        """Test building research prompt with context."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ResearcherAgent(agent_config)
            
            context = [
                AgentMessage(agent_name="other", content="Previous context")
            ]
            prompt = agent._build_prompt("What is AI?", context)
            
            assert "What is AI?" in prompt
            assert "Previous context" in prompt


class TestFactCheckerAgent:
    """Tests for FactCheckerAgent."""
    
    def test_build_prompt_without_context(self, agent_config, mock_anthropic_client):
        """Test building fact-check prompt without context."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = FactCheckerAgent(agent_config)
            
            prompt = agent._build_prompt("AI is intelligent")
            
            assert "fact-checker" in prompt.lower()
            assert "AI is intelligent" in prompt
            assert "verify" in prompt.lower()
    
    def test_build_prompt_with_context(self, agent_config, mock_anthropic_client):
        """Test building fact-check prompt with context."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            from src.models import Source, SourceType
            
            agent = FactCheckerAgent(agent_config)
            
            context = [
                AgentMessage(
                    agent_name="researcher",
                    content="Research findings",
                    sources=[Source(title="Test Source", source_type=SourceType.WEB)]
                )
            ]
            prompt = agent._build_prompt("Claim to verify", context)
            
            assert "Research findings" in prompt
            assert "Test Source" in prompt


class TestSynthesizerAgent:
    """Tests for SynthesizerAgent."""
    
    def test_build_prompt_without_context(self, agent_config, mock_anthropic_client):
        """Test building synthesis prompt without context."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = SynthesizerAgent(agent_config)
            
            prompt = agent._build_prompt("What is AI?")
            
            assert "synthesizer" in prompt.lower()
            assert "What is AI?" in prompt
            assert "coherent" in prompt.lower()
    
    def test_build_prompt_with_context(self, agent_config, mock_anthropic_client):
        """Test building synthesis prompt with context."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = SynthesizerAgent(agent_config)
            
            context = [
                AgentMessage(agent_name="researcher", content="Research data"),
                AgentMessage(agent_name="fact_checker", content="Verified facts")
            ]
            prompt = agent._build_prompt("What is AI?", context)
            
            assert "Research data" in prompt
            assert "Verified facts" in prompt
            assert "RESEARCHER" in prompt
            assert "FACT_CHECKER" in prompt
