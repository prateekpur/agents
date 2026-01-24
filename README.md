# Agents Repository

A collection of AI agent projects leveraging multi-agent collaboration patterns and advanced language models.

## 📁 Projects

### [Research Agent](./research_agent)

**Multi-Agent Collaboration System** - A Python-based system where multiple specialized AI agents collaborate to answer questions with high-quality, well-reasoned responses and comprehensive source attribution.

**Key Features:**
- 🤖 **4 Specialized Agents**: Researcher, Fact-Checker, Synthesizer, and Coordinator
- 🔍 **Intelligent Source Extraction**: Automatic citation detection and URL validation
- ✅ **Confidence Scoring**: Advanced keyword-based confidence calculation with word boundary matching
- 📊 **Comprehensive Testing**: 39+ unit tests with pytest
- 🎨 **Code Quality**: Black formatting, Ruff linting, MyPy type checking
- 🚀 **Async/Await**: Built with Python async patterns for performance
- 🔗 **Claude Sonnet 4**: Powered by Anthropic's latest model

**Tech Stack:**
- Python 3.11+
- Anthropic Claude API
- Pydantic for data validation
- pytest for testing
- loguru for logging

**Quick Start:**
```bash
cd research_agent
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
python main.py
```

See the [Research Agent README](./research_agent/README.md) for detailed documentation.

---

## 🛠️ Development

### Code Quality Tools

All projects maintain high code quality standards:

```bash
# Format code
python -m black .

# Lint code
python -m ruff check .

# Type check
python -m mypy .

# Run tests
python -m pytest tests/ -v
```

### Repository Structure

```
agents/
├── research_agent/          # Multi-agent Q&A system
│   ├── src/
│   │   ├── agents/         # Agent implementations
│   │   ├── models.py       # Data models
│   │   ├── config.py       # Configuration
│   │   └── coordinator.py  # Orchestration logic
│   ├── tests/              # Comprehensive test suite
│   ├── main.py             # Example usage
│   └── README.md           # Detailed documentation
└── README.md               # This file
```

## 🚀 Future Projects

This repository is designed to host multiple agent-based projects:
- **Code Review Agent** - Automated code analysis and review
- **Data Analysis Agent** - Multi-agent data exploration system
- **Research Assistant** - Academic paper analysis and summarization
- **Task Orchestrator** - Complex workflow automation

## 📝 License

See individual project directories for license information.

## 🤝 Contributing

1. Create feature branches from `main`
2. Follow the existing code style
3. Add tests for new functionality
4. Ensure all tests pass before committing
5. Update documentation as needed

## 📧 Contact

Repository: [github.com/prateekpur/agents](https://github.com/prateekpur/agents)
