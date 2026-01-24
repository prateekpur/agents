"""
Configuration management for the multi-agent system.
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AgentConfig(BaseModel):
    """Configuration for individual agents."""
    
    name: str
    role: str
    model: str = Field(default="claude-sonnet-4-20250514")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)


class SystemConfig(BaseModel):
    """System-wide configuration."""
    
    # API Keys
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    
    # Default model settings
    default_model: str = Field(default_factory=lambda: os.getenv("DEFAULT_MODEL", "claude-haiku-3-5"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.7")))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096")))
    
    # Agent configurations
    coordinator_config: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="coordinator",
            role="Coordinates agent collaboration and synthesizes final answers"
        )
    )
    
    researcher_config: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="researcher",
            role="Conducts research and gathers information"
        )
    )
    
    fact_checker_config: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="fact_checker",
            role="Verifies facts and validates sources"
        )
    )
    
    synthesizer_config: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="synthesizer",
            role="Synthesizes information into coherent answers"
        )
    )


# Global configuration instance
config = SystemConfig()
