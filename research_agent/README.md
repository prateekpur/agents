# Multi-Agent Collaboration System

A Python-based system where multiple AI agents collaborate to answer questions with high-quality, well-reasoned responses and sources.

## 🎯 Overview

Give the system a question → multiple specialized agents collaborate → get a comprehensive answer with sources and reasoning.

### Architecture

**4 Specialized Agents:**

1. **Researcher** - Gathers comprehensive information from multiple perspectives
2. **Fact-Checker** - Verifies accuracy and validates sources
3. **Synthesizer** - Combines information into coherent answers
4. **Coordinator** - Orchestrates the workflow and produces final output

## 🚀 Quick Start

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Configure API key:**

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

3. **Run example:**

```bash
python main.py
```

## 📖 Usage

```python
import asyncio
from src.models import Question
from src.coordinator import CoordinatorAgent

async def main():
    coordinator = CoordinatorAgent()

    question = Question(
        question="What are the benefits of renewable energy?",
        context="Focus on solar and wind"
    )

    answer = await coordinator.answer_question(question)

    print(f"Answer: {answer.answer}")
    print(f"Confidence: {answer.confidence:.0%}")
    print(f"Sources: {len(answer.sources)}")

asyncio.run(main())
```

## 📁 Project Structure

```
research_agent/
├── src/
│   ├── agents/
│   │   ├── base_agent.py      # Base agent class
│   │   ├── researcher.py      # Research agent
│   │   ├── fact_checker.py    # Fact-checker agent
│   │   └── synthesizer.py     # Synthesizer agent
│   ├── config.py              # Configuration
│   ├── models.py              # Data models
│   └── coordinator.py         # Main orchestrator
├── tests/
├── main.py                    # Example usage
└── requirements.txt
```

## ✨ Features

- ✅ Multi-agent collaboration workflow
- 🔍 Comprehensive research capabilities
- ✓ Fact-checking and validation
- 📝 Answer synthesis with attribution
- 🎯 Confidence scoring
- 📚 Source tracking
- 🔄 Async/await support
- 📊 Structured data models

## 🔧 Configuration

Edit `.env`:

```env
ANTHROPIC_API_KEY=your_key_here
DEFAULT_MODEL=claude-sonnet-4-20250514
TEMPERATURE=0.7
MAX_TOKENS=4096
```

## 🧪 Testing

```bash
pytest
```

## 📝 Requirements

- Python 3.11+
- Anthropic API key (Claude Sonnet 4)

## 🚧 Future Enhancements

- [ ] Web search integration
- [ ] REST API interface
- [ ] Web UI
- [ ] Additional specialized agents
- [ ] Multi-turn conversations
- [ ] Parallel agent execution

## 📄 License

MIT License
