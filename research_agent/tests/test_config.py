"""
Tests for configuration.
"""
import pytest
import os
from src.config import AgentConfig, SystemConfig


class TestAgentConfig:
    """Tests for AgentConfig."""
    
    def test_agent_config_creation(self):
        """Test creating agent config."""
        config = AgentConfig(
            name="test_agent",
            role="Testing agent"
        )
        assert config.name == "test_agent"
        assert config.role == "Testing agent"
        assert config.model == "claude-sonnet-4-20250514"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
    
    def test_agent_config_custom_values(self):
        """Test agent config with custom values."""
        config = AgentConfig(
            name="test_agent",
            role="Testing",
            model="custom-model",
            temperature=0.5,
            max_tokens=2000
        )
        assert config.model == "custom-model"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000
    
    def test_temperature_bounds(self):
        """Test temperature validation."""
        # Valid temperatures
        config = AgentConfig(name="test", role="test", temperature=0.0)
        assert config.temperature == 0.0
        
        config = AgentConfig(name="test", role="test", temperature=2.0)
        assert config.temperature == 2.0


class TestSystemConfig:
    """Tests for SystemConfig."""
    
    def test_system_config_creation(self):
        """Test creating system config."""
        config = SystemConfig()
        assert config.default_model == "claude-sonnet-4-20250514"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
    
    def test_agent_configs_exist(self):
        """Test that all agent configs are created."""
        config = SystemConfig()
        assert config.coordinator_config is not None
        assert config.researcher_config is not None
        assert config.fact_checker_config is not None
        assert config.synthesizer_config is not None
    
    def test_agent_config_properties(self):
        """Test agent config properties."""
        config = SystemConfig()
        
        assert config.researcher_config.name == "researcher"
        assert "research" in config.researcher_config.role.lower()
        
        assert config.fact_checker_config.name == "fact_checker"
        assert "fact" in config.fact_checker_config.role.lower()
        
        assert config.synthesizer_config.name == "synthesizer"
        assert "synthe" in config.synthesizer_config.role.lower()
