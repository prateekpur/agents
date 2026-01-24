"""
Coordinator agent that orchestrates collaboration between agents.
"""
from typing import List
from loguru import logger

from src.agents import ResearcherAgent, FactCheckerAgent, SynthesizerAgent
from src.models import Question, Answer, AgentMessage, Source
from src.config import config


class CoordinatorAgent:
    """Orchestrates collaboration between multiple agents to answer questions."""
    
    def __init__(self):
        """Initialize the coordinator with specialized agents."""
        logger.info("Initializing CoordinatorAgent")
        
        self.researcher = ResearcherAgent(config.researcher_config)
        self.fact_checker = FactCheckerAgent(config.fact_checker_config)
        self.synthesizer = SynthesizerAgent(config.synthesizer_config)
        
        self.agent_messages: List[AgentMessage] = []
    
    async def answer_question(self, question: Question) -> Answer:
        """
        Coordinate agents to answer a question.
        
        Args:
            question: The question to answer
            
        Returns:
            Answer object with the final response and sources
        """
        logger.info(f"Processing question: {question.question}")
        
        # Reset agent messages for this question
        self.agent_messages = []
        
        # Step 1: Research phase
        logger.info("Step 1: Research phase")
        research_result = await self.researcher.process(question.question)
        self.agent_messages.append(research_result)
        logger.debug(f"Research complete: {len(research_result.content)} chars")
        
        # Step 2: Fact-checking phase
        logger.info("Step 2: Fact-checking phase")
        fact_check_result = await self.fact_checker.process(
            question.question,
            context=[research_result]
        )
        self.agent_messages.append(fact_check_result)
        logger.debug(f"Fact-checking complete: {len(fact_check_result.content)} chars")
        
        # Step 3: Synthesis phase
        logger.info("Step 3: Synthesis phase")
        synthesis_result = await self.synthesizer.process(
            question.question,
            context=[research_result, fact_check_result]
        )
        self.agent_messages.append(synthesis_result)
        logger.debug(f"Synthesis complete: {len(synthesis_result.content)} chars")
        
        # Collect all sources
        all_sources = self._collect_sources()
        
        # Calculate confidence based on fact-checker feedback
        confidence = self._calculate_confidence(fact_check_result.content)
        
        # Create the final answer
        answer = Answer(
            question=question,
            answer=synthesis_result.content,
            sources=all_sources,
            reasoning=self._build_reasoning(),
            confidence=confidence,
            agent_contributions=self.agent_messages
        )
        
        logger.info("Question answered successfully")
        return answer
    
    def _collect_sources(self) -> List[Source]:
        """Collect and deduplicate sources from all agents."""
        sources = []
        seen_titles = set()
        
        for message in self.agent_messages:
            for source in message.sources:
                if source.title not in seen_titles:
                    sources.append(source)
                    seen_titles.add(source.title)
        
        return sources
    
    def _calculate_confidence(self, fact_check_content: str) -> float:
        """
        Calculate confidence score based on fact-checker output.
        This is a simple heuristic - can be improved.
        """
        content_lower = fact_check_content.lower()
        
        # Simple keyword-based confidence calculation
        high_confidence_keywords = ['verified', 'accurate', 'confirmed', 'reliable']
        low_confidence_keywords = ['uncertain', 'unverified', 'questionable', 'contradicts']
        
        high_count = sum(1 for kw in high_confidence_keywords if kw in content_lower)
        low_count = sum(1 for kw in low_confidence_keywords if kw in content_lower)
        
        # Calculate score (0.5-1.0 range)
        if high_count + low_count == 0:
            return 0.7  # Default
        
        confidence = 0.5 + (0.5 * (high_count / (high_count + low_count)))
        return round(confidence, 2)
    
    def _build_reasoning(self) -> str:
        """Build the reasoning explanation from agent contributions."""
        reasoning_parts = []
        
        for message in self.agent_messages:
            reasoning_parts.append(
                f"{message.agent_name.upper()}: {message.content[:200]}..."
            )
        
        return "\n\n".join(reasoning_parts)
