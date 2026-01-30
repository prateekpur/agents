"""
LLM Client for code generation and analysis.
Supports multiple providers: GitHub Models, OpenAI, and Azure OpenAI.
"""

import logging
from typing import Optional, List, Dict, Any
from openai import OpenAI, AzureOpenAI
import config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with Large Language Models.
    Supports GitHub Models API, OpenAI API, and Azure OpenAI.
    """
    
    def __init__(self):
        """Initialize the LLM client based on available configuration."""
        self.client = None
        self.model = None
        
        # Priority 1: GitHub Models
        if config.GITHUB_TOKEN:
            logger.info("Initializing GitHub Models client")
            self.client = OpenAI(
                base_url="https://models.inference.ai.azure.com",
                api_key=config.GITHUB_TOKEN
            )
            self.model = config.GITHUB_MODEL
            logger.info(f"Using GitHub model: {self.model}")
        
        # Priority 2: Azure OpenAI
        elif config.OPENAI_API_BASE:
            logger.info("Initializing Azure OpenAI client")
            self.client = AzureOpenAI(
                api_key=config.OPENAI_API_KEY,
                api_version=config.OPENAI_API_VERSION,
                azure_endpoint=config.OPENAI_API_BASE
            )
            self.model = config.OPENAI_MODEL
            logger.info(f"Using Azure OpenAI model: {self.model}")
        
        # Priority 3: Standard OpenAI API
        elif config.OPENAI_API_KEY:
            logger.info("Initializing OpenAI client")
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model = config.OPENAI_MODEL
            logger.info(f"Using OpenAI model: {self.model}")
        
        else:
            raise ValueError(
                "No API credentials found. Please set one of:\n"
                "- GITHUB_TOKEN (for GitHub Models)\n"
                "- OPENAI_API_KEY (for OpenAI)\n"
                "- OPENAI_API_BASE + OPENAI_API_KEY (for Azure OpenAI)"
            )
    
    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a completion using the configured model.
        
        Args:
            system_prompt: System message to guide the model
            user_prompt: User message with the actual request
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})
        
        Returns:
            Generated text response
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if response_format:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise
    
    def generate_code(
        self,
        task_description: str,
        context: Optional[str] = None,
        language: str = "python"
    ) -> str:
        """
        Generate code for a specific task.
        
        Args:
            task_description: Description of what the code should do
            context: Optional context or existing code
            language: Programming language
        
        Returns:
            Generated code
        """
        system_prompt = f"""You are an expert {language} programmer. 
Generate clean, efficient, and well-documented code."""
        
        user_prompt = f"Task: {task_description}"
        if context:
            user_prompt += f"\n\nContext:\n{context}"
        
        return self.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3  # Lower temperature for code generation
        )
    
    def analyze_code(
        self,
        code: str,
        analysis_type: str = "general"
    ) -> str:
        """
        Analyze code for issues, improvements, or patterns.
        
        Args:
            code: Code to analyze
            analysis_type: Type of analysis (general, bugs, style, performance)
        
        Returns:
            Analysis results
        """
        analysis_prompts = {
            "general": "Analyze this code for potential issues, improvements, and best practices.",
            "bugs": "Identify potential bugs, errors, and edge cases in this code.",
            "style": "Review this code for style issues, naming conventions, and code quality.",
            "performance": "Analyze this code for performance issues and optimization opportunities."
        }
        
        system_prompt = "You are an expert code reviewer with deep knowledge of software engineering best practices."
        user_prompt = f"{analysis_prompts.get(analysis_type, analysis_prompts['general'])}\n\nCode:\n```\n{code}\n```"
        
        return self.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5
        )
