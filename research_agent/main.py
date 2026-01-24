"""
Main entry point for the multi-agent collaboration system.
"""

import asyncio
import sys

from loguru import logger

from src.coordinator import CoordinatorAgent
from src.models import Question


async def main():
    """Main function to run the multi-agent system."""

    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/agent_system.log", rotation="10 MB", level="DEBUG")

    logger.info("Starting Multi-Agent Collaboration System")

    # Initialize the coordinator
    coordinator = CoordinatorAgent()

    # Example question
    question = Question(
        question="What are the main benefits and challenges of renewable energy adoption?",
        context="Focus on solar and wind energy in the context of climate change mitigation.",
    )

    # Get the answer
    logger.info(f"Asking question: {question.question}")
    answer = await coordinator.answer_question(question)

    # Display the results
    print("\n" + "=" * 80)
    print("QUESTION:")
    print("=" * 80)
    print(question.question)
    print()

    print("=" * 80)
    print("ANSWER:")
    print("=" * 80)
    print(answer.answer)
    print()

    print("=" * 80)
    print("METADATA:")
    print("=" * 80)
    print(f"Confidence: {answer.confidence:.2%}")
    print(f"Sources: {len(answer.sources)}")
    print(f"Agents involved: {len(answer.agent_contributions)}")
    print()

    if answer.sources:
        print("=" * 80)
        print("SOURCES:")
        print("=" * 80)
        for i, source in enumerate(answer.sources, 1):
            print(f"{i}. {source.title}")
            if source.url:
                print(f"   URL: {source.url}")
        print()

    logger.info("Multi-Agent Collaboration System completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
