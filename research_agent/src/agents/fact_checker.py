"""
Fact-checker agent that verifies information and validates sources.
"""
from typing import List, Optional

from src.agents.base_agent import BaseAgent
from src.models import AgentMessage


class FactCheckerAgent(BaseAgent):
    """Agent responsible for fact-checking and validating information."""
    
    def _build_prompt(self, input_text: str, context: Optional[List[AgentMessage]] = None) -> str:
        """Build the fact-checking prompt."""
        
        base_prompt = f"""You are a fact-checker agent. Your role is to verify the accuracy of information 
and validate sources. Be critical and thorough in your assessment.

Question/Claim to verify: {input_text}

Instructions:
1. Identify key claims that need verification
2. Assess the credibility and reliability of sources
3. Look for contradictions or inconsistencies
4. Verify facts against known reliable sources
5. Rate confidence level for each claim (high/medium/low)
6. Flag any misinformation or unverified claims

Provide a detailed fact-check analysis."""

        if context:
            context_text = "\n\nInformation to verify:\n"
            for msg in context:
                context_text += f"\n{msg.agent_name}:\n{msg.content}\n"
                if msg.sources:
                    context_text += "Sources:\n"
                    for source in msg.sources:
                        context_text += f"- {source.title}\n"
            base_prompt += context_text
        
        return base_prompt
