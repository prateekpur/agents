"""
Synthesizer agent that combines information into coherent answers.
"""
from typing import List, Optional

from src.agents.base_agent import BaseAgent
from src.models import AgentMessage


class SynthesizerAgent(BaseAgent):
    """Agent responsible for synthesizing information into coherent answers."""
    
    def _build_prompt(self, input_text: str, context: Optional[List[AgentMessage]] = None) -> str:
        """Build the synthesis prompt."""
        
        base_prompt = f"""You are a synthesizer agent. Your role is to combine information from multiple 
sources into a clear, coherent, and well-structured answer.

Question: {input_text}

Instructions:
1. Integrate information from all available sources
2. Resolve any contradictions or inconsistencies
3. Structure the answer logically and clearly
4. Maintain accuracy while being comprehensive
5. Include proper attribution to sources
6. Highlight key points and insights
7. Note any caveats or limitations

Provide a well-reasoned, synthesized answer."""

        if context:
            context_text = "\n\nInformation to synthesize:\n"
            for msg in context:
                context_text += f"\n--- {msg.agent_name.upper()} ---\n{msg.content}\n"
                if msg.sources:
                    context_text += "\nSources:\n"
                    for source in msg.sources:
                        context_text += f"- {source.title}\n"
            base_prompt += context_text
        
        return base_prompt
