"""
Configuration settings for the agent.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Agent configuration
AGENT_NAME = os.getenv("AGENT_NAME", "CodeAgent")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# LLM Provider Configuration
# You can use any of these providers:
# 1. GitHub Models API
# 2. Azure OpenAI
# 3. OpenAI API

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")  # Optional: for Azure OpenAI
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-02-01")  # For Azure
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")  # Default model

# GitHub Models configuration
# Set GITHUB_TOKEN to use GitHub's model API
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_MODEL = os.getenv("GITHUB_MODEL", "gpt-4o")

# Create necessary directories
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
