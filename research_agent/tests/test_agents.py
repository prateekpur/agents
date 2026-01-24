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
from src.models import AgentMessage, SourceType


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
        """Test source extraction from text."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            sources = agent._extract_sources("Some text with sources")
            
            assert isinstance(sources, list)
    
    def test_extract_sources_with_source_tag(self, agent_config, mock_anthropic_client):
        """Test extracting sources with [Source: ...] format."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            text = "According to research [Source: Climate Report 2025] and [Source: https://example.com/article]"
            sources = agent._extract_sources(text)
            
            assert len(sources) == 2
            assert sources[0].title == "Climate Report 2025"
            assert sources[0].source_type == SourceType.DERIVED
            assert sources[1].url == "https://example.com/article"
            assert sources[1].source_type == SourceType.WEB
    
    def test_extract_sources_with_urls(self, agent_config, mock_anthropic_client):
        """Test extracting sources from URLs in text."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            text = "Research shows https://www.nature.com/articles/123 and data from https://arxiv.org/paper/456"
            sources = agent._extract_sources(text)
            
            assert len(sources) >= 2
            assert any("nature.com" in s.url for s in sources if s.url)
            assert any("arxiv.org" in s.url for s in sources if s.url)
    
    def test_extract_sources_with_citations(self, agent_config, mock_anthropic_client):
        """Test extracting academic citations."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            text = "According to research (Smith, 2024) and studies (Johnson et al., 2023)"
            sources = agent._extract_sources(text)
            
            assert len(sources) >= 2
            assert any("Smith, 2024" in s.title for s in sources)
            assert any("Johnson et al., 2023" in s.title for s in sources)
            assert all(s.source_type == SourceType.RESEARCH for s in sources)
    
    def test_extract_sources_mixed_formats(self, agent_config, mock_anthropic_client):
        """Test extracting sources from mixed formats."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            agent = ConcreteAgent(agent_config)
            
            text = """Based on [Source: WHO Guidelines] and research (Brown, 2025).
            More info at https://www.cdc.gov/report.html"""
            sources = agent._extract_sources(text)
            
            assert len(sources) >= 3
            source_types = [s.source_type for s in sources]
            assert SourceType.DERIVED in source_types or SourceType.WEB in source_types
            assert SourceType.RESEARCH in source_types


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
