"""
Base agent class for the multi-agent system.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from anthropic import Anthropic
import os

from src.models import AgentMessage, Source
from src.config import AgentConfig


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent with configuration."""
        self.config = config
        self.name = config.name
        self.role = config.role
        
        # Initialize the Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        self.client = Anthropic(api_key=api_key)
    
    async def process(self, input_text: str, context: Optional[List[AgentMessage]] = None) -> AgentMessage:
        """
        Process input and return an agent message.
        
        Args:
            input_text: The input text to process
            context: Optional list of previous agent messages for context
            
        Returns:
            AgentMessage containing the agent's response
        """
        # Build the prompt with context
        prompt = self._build_prompt(input_text, context)
        
        # Get response from the LLM
        response_text, sources = await self._get_llm_response(prompt)
        
        # Create and return the agent message
        return AgentMessage(
            agent_name=self.name,
            content=response_text,
            sources=sources
        )
    
    @abstractmethod
    def _build_prompt(self, input_text: str, context: Optional[List[AgentMessage]] = None) -> str:
        """
        Build the prompt for the LLM based on the agent's role.
        
        Args:
            input_text: The input text
            context: Optional context from other agents
            
        Returns:
            The formatted prompt string
        """
        pass
    
    async def _get_llm_response(self, prompt: str) -> tuple[str, List[Source]]:
        """
        Get response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            Tuple of (response_text, sources)
        """
        try:
            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            
            # Extract sources from response (placeholder - can be enhanced)
            sources = self._extract_sources(response_text)
            
            return response_text, sources
            
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")
    
    def _extract_sources(self, text: str) -> List[Source]:
        """
        Extract sources from the response text.
        This is a placeholder - implement actual source extraction logic.
        
        Args:
            text: The response text
            
        Returns:
            List of extracted sources
        """
        # Placeholder implementation
        return []
