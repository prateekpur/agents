"""
Data models for the multi-agent system.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SourceType(str, Enum):
    """Types of sources."""
    WEB = "web"
    RESEARCH = "research"
    INTERNAL = "internal"
    DERIVED = "derived"


class Source(BaseModel):
    """A source of information."""
    
    title: str
    url: Optional[str] = None
    source_type: SourceType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    content_snippet: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    

class AgentMessage(BaseModel):
    """Message from an agent."""
    
    agent_name: str
    content: str
    sources: List[Source] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Question(BaseModel):
    """A question to be answered by the system."""
    
    question: str
    context: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class Answer(BaseModel):
    """Final answer from the system."""
    
    question: Question
    answer: str
    sources: List[Source]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    agent_contributions: List[AgentMessage] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
