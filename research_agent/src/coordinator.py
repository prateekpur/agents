"""
Coordinator agent that orchestrates collaboration between agents.
"""

import re

from loguru import logger

from src.agents import FactCheckerAgent, ResearcherAgent, SynthesizerAgent
from src.config import config
from src.models import AgentMessage, Answer, Question, Source


class CoordinatorAgent:
    """Orchestrates collaboration between multiple agents to answer questions."""

    def __init__(self):
        """Initialize the coordinator with specialized agents."""
        logger.info("Initializing CoordinatorAgent")

        self.researcher = ResearcherAgent(config.researcher_config)
        self.fact_checker = FactCheckerAgent(config.fact_checker_config)
        self.synthesizer = SynthesizerAgent(config.synthesizer_config)

        self.agent_messages: list[AgentMessage] = []

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
            question.question, context=[research_result]
        )
        self.agent_messages.append(fact_check_result)
        logger.debug(f"Fact-checking complete: {len(fact_check_result.content)} chars")

        # Step 3: Synthesis phase
        logger.info("Step 3: Synthesis phase")
        synthesis_result = await self.synthesizer.process(
            question.question, context=[research_result, fact_check_result]
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
            agent_contributions=self.agent_messages,
        )

        logger.info("Question answered successfully")
        return answer

    def _collect_sources(self) -> list[Source]:
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
        Uses word boundary matching and balanced formula.
        """
        # Input validation
        if not isinstance(fact_check_content, str):
            logger.warning(
                f"Invalid input type for confidence calculation: {type(fact_check_content)}"
            )
            return 0.5

        if not fact_check_content.strip():
            logger.debug("Empty fact check content, using default confidence")
            return 0.5

        content_lower = fact_check_content.lower()

        # Expanded keyword lists
        high_confidence_keywords = [
            "verified",
            "accurate",
            "confirmed",
            "reliable",
            "factual",
            "substantiated",
            "corroborated",
            "validated",
            "authentic",
        ]
        low_confidence_keywords = [
            "uncertain",
            "unverified",
            "questionable",
            "contradicts",
            "false",
            "misleading",
            "disputed",
            "debunked",
            "inaccurate",
        ]

        # Use word boundaries for exact matches
        def count_keyword_matches(keywords: list[str], content: str) -> int:
            """Count exact word matches using regex word boundaries."""
            total = 0
            for keyword in keywords:
                pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
                matches = len(re.findall(pattern, content))
                total += matches
            return total

        high_count = count_keyword_matches(high_confidence_keywords, content_lower)
        low_count = count_keyword_matches(low_confidence_keywords, content_lower)

        logger.debug(f"Confidence indicators - High: {high_count}, Low: {low_count}")

        total_indicators = high_count + low_count

        # No indicators found - return neutral
        if total_indicators == 0:
            logger.debug("No confidence indicators found, using default: 0.5")
            return 0.5

        # Calculate balanced confidence score
        positive_ratio = high_count / total_indicators

        # Maps 0 -> 0.1, 0.5 -> 0.5, 1.0 -> 0.9 (more balanced than before)
        confidence = 0.1 + (0.8 * positive_ratio)

        result = round(confidence, 2)
        logger.debug(f"Final confidence score: {result}")
        return result

    def _build_reasoning(self) -> str:
        """Build the reasoning explanation from agent contributions."""
        reasoning_parts = []

        for message in self.agent_messages:
            reasoning_parts.append(f"{message.agent_name.upper()}: {message.content[:200]}...")

        return "\n\n".join(reasoning_parts)
