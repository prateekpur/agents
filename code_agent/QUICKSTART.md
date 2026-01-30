# Quick Start Guide

## Setup (One-time)

```bash
# 1. Navigate to project
cd /Users/prateekpuri/ai_agent/miscllaneous1978/agents/code_agent

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Verify setup
python3 test_integration.py
```

## Usage

### Basic Analysis

```bash
# Activate virtual environment first
source .venv/bin/activate

# Analyze a Python file
cd src
python3 agent.py path/to/your_file.py
```

### Examples

```bash
# Analyze the sample file
python3 agent.py ../sample.py

# Save output to JSON file
python3 agent.py ../sample.py --output ../my_analysis.json

# Verbose mode (see detailed logs)
python3 agent.py ../sample.py --verbose

# Get help
python3 agent.py --help
```

## What the Agent Does

1. **Scanner Agent**: Extracts code structure (functions, classes, imports)
2. **Analysis Agent**: Finds bugs, security issues, logic errors
3. **Style Agent**: Checks PEP 8 compliance and code quality
4. **Planner Agent**: Creates prioritized refactoring plan

## Output Format

The agent outputs a JSON refactoring plan with:
- **summary**: Overall description of refactoring goals
- **steps**: Array of prioritized refactoring steps
  - `step`: Step number
  - `action`: What to do
  - `rationale`: Why it's important

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'openai'` | Run `pip install -r requirements.txt` |
| `File not found` | Check file path is correct |
| `No API credentials found` | Edit `.env` and add `GITHUB_TOKEN` |
| Import errors | Make sure to run from `src/` directory |

## Configuration

Edit `.env` file to change:
- **GITHUB_TOKEN**: Your GitHub token for API access
- **GITHUB_MODEL**: Model to use (default: gpt-4o)
- **LOG_LEVEL**: Logging verbosity (INFO, DEBUG, WARNING, ERROR)

## Available Models

The agent supports multiple providers:

1. **GitHub Models** (default): `GITHUB_TOKEN` + `GITHUB_MODEL`
2. **OpenAI**: `OPENAI_API_KEY` + `OPENAI_MODEL`
3. **Azure OpenAI**: `OPENAI_API_BASE` + `OPENAI_API_KEY` + `OPENAI_MODEL`

Switch providers by editing `.env` file.

## Next Steps

- Analyze your own Python files
- Integrate with CI/CD pipelines
- Customize agent prompts in `src/agents/`
- Add new agent types for specific analysis needs
