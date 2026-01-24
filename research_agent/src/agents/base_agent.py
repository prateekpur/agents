"""
Base agent class for the multi-agent system.
"""

import os
import re
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse

from anthropic import Anthropic
from loguru import logger

from src.config import AgentConfig
from src.models import AgentMessage, Source, SourceType


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

    async def process(
        self, input_text: str, context: list[AgentMessage] | None = None
    ) -> AgentMessage:
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
        return AgentMessage(agent_name=self.name, content=response_text, sources=sources)

    @abstractmethod
    def _build_prompt(self, input_text: str, context: list[AgentMessage] | None = None) -> str:
        """
        Build the prompt for the LLM based on the agent's role.

        Args:
            input_text: The input text
            context: Optional context from other agents

        Returns:
            The formatted prompt string
        """
        pass

    async def _get_llm_response(self, prompt: str) -> tuple[str, list[Source]]:
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
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Extract sources from response (placeholder - can be enhanced)
            sources = self._extract_sources(response_text)

            return response_text, sources

        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")

    def _extract_sources(self, text: str) -> list[Source]:
        """
        Extract sources from the response text.
        Looks for patterns like [Source: ...] or citations in the text.

        Args:
            text: The response text

        Returns:
            List of extracted sources
        """
        # Input validation
        if not isinstance(text, str):
            logger.warning(f"Invalid input type for source extraction: {type(text)}")
            return []

        if not text.strip():
            return []

        sources = []
        seen_urls = set()

        try:
            # Pattern 1: [Source: description] format
            source_pattern = r"\[Source:\s*([^\]]+)\]"
            # Improved URL pattern with better character handling
            url_pattern = (
                r"(https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.~:?#\[\]@!$&'()*+,;=-])*)?)"
            )

            matches = re.finditer(source_pattern, text, re.IGNORECASE)

            for match in matches:
                source_text = match.group(1).strip()

                if not source_text:
                    continue

                # Check if it contains a URL
                url_match = re.search(url_pattern, source_text)
                url = self._validate_url(url_match.group(1)) if url_match else None

                # Skip duplicate URLs
                if url and url in seen_urls:
                    continue

                if url:
                    seen_urls.add(url)
                    # Properly extract title by removing URL from position
                    title = source_text[: url_match.start()].strip()
                    if not title:
                        title = self._extract_title_from_url(url)
                else:
                    title = source_text

                source = Source(
                    title=title,
                    url=url,
                    source_type=SourceType.WEB if url else SourceType.DERIVED,
                    content_snippet=None,
                )
                sources.append(source)

            # Pattern 2: Look for URLs in parentheses or standalone
            # Skip URLs already found in [Source: ...] tags
            # Improved pattern to not capture closing brackets or parens
            url_pattern_standalone = r"(?<!\[Source:\s)https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.~:?#@!$&'()*+,;=-])*)?(?=[\s\]\).,;:]|$)"
            url_matches = re.finditer(url_pattern_standalone, text)

            for match in url_matches:
                url = self._validate_url(match.group(0))
                if url and url not in seen_urls:
                    seen_urls.add(url)

                    # Try to find surrounding context for title
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]

                    # Extract a simple title from context
                    title = self._extract_title_from_context(context, url)

                    source = Source(
                        title=title,
                        url=url,
                        source_type=SourceType.WEB,
                        content_snippet=context[:100] if len(context) > 100 else context,
                    )
                    sources.append(source)

            # Pattern 3: Look for academic citations like (Author, Year)
            citation_pattern = r"\(([A-Z][a-z]+(?:\s+et\s+al\.?)?,\s*\d{4})\)"
            citation_matches = re.finditer(citation_pattern, text)

            for match in citation_matches:
                citation = match.group(1)
                source = Source(
                    title=citation, source_type=SourceType.RESEARCH, content_snippet=None
                )
                sources.append(source)

        except re.error as e:
            logger.error(f"Regex error in source extraction: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in source extraction: {e}")
            return []

        return sources

    def _validate_url(self, url: str) -> Optional[str]:
        """
        Validate and normalize URL.

        Args:
            url: The URL to validate

        Returns:
            Validated URL or None if invalid
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return url
        except Exception as e:
            logger.debug(f"Invalid URL encountered: {url}, error: {e}")
        return None

    def _extract_title_from_url(self, url: str) -> str:
        """
        Extract a reasonable title from URL when no title text is available.

        Args:
            url: The URL to extract title from

        Returns:
            A title derived from the URL
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc or url
        except Exception:
            return url

    def _extract_title_from_context(self, context: str, url: str) -> str:
        """
        Extract a meaningful title from the surrounding context of a URL.

        Args:
            context: Text surrounding the URL
            url: The URL itself

        Returns:
            A title for the source
        """
        # Remove the URL from context
        context_clean = context.replace(url, "").strip()

        # Look for sentences before the URL
        sentences = re.split(r"[.!?]\s+", context_clean)
        if sentences:
            # Get the last sentence before URL or first after
            title = sentences[-1] if sentences[-1] else sentences[0] if len(sentences) > 1 else url
            # Clean and truncate
            title = re.sub(r"\s+", " ", title).strip()
            if len(title) > 100:
                title = title[:97] + "..."
            return title if title else url

        return url
