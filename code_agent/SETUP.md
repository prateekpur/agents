# Setup Guide - GitHub Copilot Integration

## Quick Start

Follow these steps to get your Copilot-powered agent running:

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `openai` - For GitHub Copilot/OpenAI API access
- `python-dotenv` - For environment variable management
- `pydantic` - For data validation

### Step 2: Configure API Credentials

```bash
cp .env.example .env
```

Then edit `.env` and choose ONE of these options:

#### Option A: GitHub Models (Recommended)
```bash
GITHUB_TOKEN=ghp_your_token_here
GITHUB_MODEL=gpt-4o
```

Get your token: https://github.com/settings/tokens

#### Option B: OpenAI
```bash
OPENAI_API_KEY=sk-your_key_here
OPENAI_MODEL=gpt-4
```

#### Option C: Azure OpenAI
```bash
OPENAI_API_KEY=your_azure_key
OPENAI_API_BASE=https://your-resource.openai.azure.com/
OPENAI_API_VERSION=2024-02-01
OPENAI_MODEL=gpt-4
```

### Step 3: Test the Integration

```bash
python3 test_integration.py
```

This will verify:
- ✓ All modules import correctly
- ✓ API credentials are configured
- ✓ CopilotClient can initialize
- ✓ All agents can initialize

### Step 4: Run the Agent

```bash
cd src
python3 agent.py
```

You should see output showing:
- Code analysis results
- Identified issues
- Refactoring plan with steps

## Verification Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with API credentials
- [ ] Test script passes (`python3 test_integration.py`)
- [ ] Agent runs successfully (`cd src && python3 agent.py`)

## What Was Changed

The integration converted your mocked agents to use real AI:

| File | Status | Description |
|------|--------|-------------|
| `requirements.txt` | ✓ Updated | Added openai, python-dotenv, pydantic |
| `src/config.py` | ✓ Updated | Added API configuration |
| `src/copilot_client.py` | ✓ Created | Unified AI client |
| `src/agents/scanner.py` | ✓ Updated | AI-powered code scanning |
| `src/agents/analysis.py` | ✓ Updated | AI-powered bug detection |
| `src/agents/style.py` | ✓ Updated | AI-powered style analysis |
| `src/agents/planner.py` | ✓ Updated | AI-powered refactoring plans |
| `.env.example` | ✓ Created | Configuration template |
| `README.md` | ✓ Updated | Usage documentation |
| `COPILOT_INTEGRATION.md` | ✓ Created | Integration details |
| `test_integration.py` | ✓ Created | Integration tests |

## Troubleshooting

### "ModuleNotFoundError: No module named 'dotenv'"
**Solution**: Run `pip install -r requirements.txt`

### "No API credentials found"
**Solution**: 
1. Create `.env` file: `cp .env.example .env`
2. Add your API key to `.env`

### "ValueError: No API credentials found"
**Solution**: Make sure you set at least ONE of:
- `GITHUB_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_API_BASE` + `OPENAI_API_KEY`

### Import errors with agents
**Solution**: Make sure to run scripts from the correct directory:
```bash
# Run agent.py from src/
cd src
python3 agent.py

# Or run test from project root
python3 test_integration.py
```

### "API rate limit exceeded"
**Solution**: 
- Wait a few minutes and try again
- Use a different API provider
- Implement rate limiting in your code

## Next Steps

1. **Test with your own code**: Modify the `SAMPLE_CODE` in `src/agent.py`
2. **Customize prompts**: Edit system prompts in agent files to tune analysis
3. **Add new agents**: Create specialized agents for specific tasks
4. **Integrate into your workflow**: Use the orchestrator in your own scripts

## Support

- See `README.md` for detailed usage examples
- See `COPILOT_INTEGRATION.md` for architecture details
- Check agent files in `src/agents/` for implementation details

## Is It Complete?

**YES!** The integration is complete when:

✓ All dependencies are installed  
✓ API credentials are configured in `.env`  
✓ Test script passes all checks  
✓ Agent runs and produces AI-generated analysis  

Run `python3 test_integration.py` to verify completion status.
