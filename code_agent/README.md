# Python Agent Project

A Python agent framework powered by GitHub Copilot for intelligent code analysis and refactoring.

## Project Structure

```
.
├── src/
│   ├── agent.py           # Main agent implementation
│   ├── config.py          # Configuration settings
│   ├── copilot_client.py  # GitHub Copilot API client
│   ├── orchestrator.py    # Orchestrates agent workflow
│   ├── schemas.py         # Data models
│   └── agents/
│       ├── scanner.py     # Code structure analysis
│       ├── analysis.py    # Bug and logic analysis
│       ├── style.py       # Code style analysis
│       └── planner.py     # Refactoring plan generation
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── .gitignore           # Git ignore patterns
└── README.md            # This file
```

## Features

- AI-powered code analysis using GitHub Copilot models
- Automated code structure scanning
- Bug and security vulnerability detection
- Style and quality analysis (PEP 8 compliance)
- Intelligent refactoring plan generation
- Support for multiple AI providers (GitHub Models, OpenAI, Azure OpenAI)

## Installation

1. Create a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your API credentials:

```bash
cp .env.example .env
# Edit .env and add your API key (see Configuration section below)
```

## Configuration

This project supports three AI provider options:

### Option 1: GitHub Models (Recommended for Copilot)

Get a GitHub token with Copilot access:
1. Go to https://github.com/settings/tokens
2. Create a personal access token with appropriate permissions
3. Add to your `.env` file:

```bash
GITHUB_TOKEN=your_github_token_here
GITHUB_MODEL=gpt-4o
```

### Option 2: OpenAI API

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
```

### Option 3: Azure OpenAI

```bash
OPENAI_API_KEY=your_azure_api_key_here
OPENAI_API_BASE=https://your-resource.openai.azure.com/
OPENAI_API_VERSION=2024-02-01
OPENAI_MODEL=gpt-4
```

## Usage

### Running the Agent

The agent accepts a Python file as input and generates a comprehensive refactoring plan.

**Basic Usage:**

```bash
cd src
python3 agent.py path/to/your/file.py
```

**Examples:**

```bash
# Analyze a file in the current directory
python3 agent.py ../sample.py

# Analyze with absolute path
python3 agent.py /path/to/mycode.py

# Alternative syntax
python3 agent.py --file mycode.py

# Enable verbose output
python3 agent.py mycode.py --verbose

# Save output to file
python3 agent.py mycode.py --output refactor_plan.json
```

**Help:**

```bash
python3 agent.py --help
```

**What the Agent Does:**

1. **Scans** code structure (functions, classes, imports)
2. **Analyzes** for bugs, security issues, and logic errors
3. **Checks** code style and quality (PEP 8, best practices)
4. **Generates** a prioritized refactoring plan with actionable steps

### Using the Agent in Your Code

```python
from orchestrator import Orchestrator

# Create an orchestrator
orchestrator = Orchestrator()

# Analyze and get refactoring plan
code = """
def calculate_tax(amount):
    return amount * 0.18
"""

result = orchestrator.run(code)

# View the plan
print(result.summary)
for step in result.steps:
    print(f"{step.step}. {step.action} - {step.rationale}")
```

### Using Individual Agents

```python
from agents.scanner import ScannerAgent
from agents.analysis import AnalysisAgent
from copilot_client import CopilotClient

# Use the scanner
scanner = ScannerAgent()
scan_result = scanner.run(code)

# Use analysis agent
analysis = AnalysisAgent()
issues = analysis.run({"code": code, "scan": scan_result})

# Use Copilot client directly for code generation
copilot = CopilotClient()
generated_code = copilot.generate_code(
    task_description="Create a function to validate email addresses",
    language="python"
)
```

## How It Works

The agent framework uses a multi-stage pipeline powered by GitHub Copilot:

1. **Scanner Agent**: Analyzes code structure (functions, classes, imports) and identifies initial issues
2. **Analysis Agent**: Deep analysis for bugs, security vulnerabilities, and logic errors
3. **Style Agent**: Reviews code quality, PEP 8 compliance, and best practices
4. **Planner Agent**: Creates a prioritized refactoring plan based on all identified issues

All agents use the `CopilotClient` which provides a unified interface for:
- GitHub Models API (Copilot)
- OpenAI API
- Azure OpenAI

## Development

### Adding New Agents

Create a new agent in `src/agents/`:

```python
from copilot_client import CopilotClient
import logging

logger = logging.getLogger(__name__)

class CustomAgent:
    def __init__(self):
        self.copilot = CopilotClient()
    
    def run(self, data: dict):
        # Your implementation using self.copilot
        response = self.copilot.generate_completion(
            system_prompt="Your system prompt",
            user_prompt="Your user prompt"
        )
        return response
```

### Using Copilot for Code Generation

The `CopilotClient` provides several helpful methods:

```python
# Generate code
code = copilot.generate_code(
    task_description="Create a REST API endpoint",
    context="Using Flask framework",
    language="python"
)

# Analyze code
analysis = copilot.analyze_code(
    code=your_code,
    analysis_type="bugs"  # or "style", "performance", "general"
)

# Custom completions
response = copilot.generate_completion(
    system_prompt="You are an expert...",
    user_prompt="Task description...",
    temperature=0.7,
    max_tokens=2000,
    response_format={"type": "json_object"}  # Optional JSON mode
)
```

### Environment Variables

Available environment variables (set in `.env`):

- `GITHUB_TOKEN`: GitHub personal access token for Copilot models
- `GITHUB_MODEL`: GitHub model to use (default: gpt-4o)
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_API_BASE`: Azure OpenAI endpoint (optional)
- `OPENAI_MODEL`: Model name (default: gpt-4)
- `AGENT_NAME`: Agent name (default: CodeAgent)
- `LOG_LEVEL`: Logging level (default: INFO)

## Troubleshooting

**Error: "No API credentials found"**
- Make sure you've created a `.env` file from `.env.example`
- Add at least one of: GITHUB_TOKEN, OPENAI_API_KEY

**Import errors**
- Ensure you've activated your virtual environment
- Run `pip install -r requirements.txt`

**API rate limits**
- GitHub Models and OpenAI have rate limits
- Consider adding retry logic or reducing request frequency

## License

This project is open source and available under the MIT License.
