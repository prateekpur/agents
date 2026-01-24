"""
Researcher agent that gathers information and conducts research.
"""
from typing import List, Optional

from src.agents.base_agent import BaseAgent
from src.models import AgentMessage


class ResearcherAgent(BaseAgent):
    """Agent responsible for conducting research and gathering information."""
    
    def _build_prompt(self, input_text: str, context: Optional[List[AgentMessage]] = None) -> str:
        """Build the research prompt."""
        
        base_prompt = f"""You are a research agent. Your role is to gather comprehensive information 
about the given question. Focus on finding accurate, relevant information from multiple perspectives.

Question: {input_text}

Instructions:
1. Identify key concepts and topics in the question
2. Consider multiple angles and perspectives
3. Gather relevant facts, data, and information
4. Cite sources where applicable (use [Source: description] format)
5. Note any assumptions or limitations

Provide a comprehensive research summary with sources."""

        if context:
            context_text = "\n\nContext from other agents:\n"
            for msg in context:
                context_text += f"\n{msg.agent_name}: {msg.content}\n"
            base_prompt += context_text
        
        return base_prompt
