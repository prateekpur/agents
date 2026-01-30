#!/usr/bin/env python3
"""
Test script to verify LLM integration is complete.
Run this after installing dependencies to check everything works.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        import config
        print("✓ config imported")
    except Exception as e:
        print(f"✗ config import failed: {e}")
        return False
    
    try:
        from llm_client import LLMClient
        print("✓ llm_client imported")
    except Exception as e:
        print(f"✗ llm_client import failed: {e}")
        return False
    
    try:
        import schemas
        print("✓ schemas imported")
    except Exception as e:
        print(f"✗ schemas import failed: {e}")
        return False
    
    try:
        from agents.scanner import ScannerAgent
        from agents.analysis import AnalysisAgent
        from agents.style import StyleAgent
        from agents.planner import PlannerAgent
        print("✓ All agents imported")
    except Exception as e:
        print(f"✗ Agent import failed: {e}")
        return False
    
    try:
        from orchestrator import Orchestrator
        print("✓ orchestrator imported")
    except Exception as e:
        print(f"✗ orchestrator import failed: {e}")
        return False
    
    return True


def test_configuration():
    """Test that configuration is set up."""
    print("\nTesting configuration...")
    
    import config
    
    has_github = bool(config.GITHUB_TOKEN)
    has_openai = bool(config.OPENAI_API_KEY)
    has_azure = bool(config.OPENAI_API_BASE)
    
    if has_github:
        print(f"✓ GitHub token configured (model: {config.GITHUB_MODEL})")
    elif has_openai and has_azure:
        print(f"✓ Azure OpenAI configured (model: {config.OPENAI_MODEL})")
    elif has_openai:
        print(f"✓ OpenAI configured (model: {config.OPENAI_MODEL})")
    else:
        print("✗ No API credentials found!")
        print("  Please set one of:")
        print("  - GITHUB_TOKEN in .env")
        print("  - OPENAI_API_KEY in .env")
        print("  - OPENAI_API_BASE + OPENAI_API_KEY in .env")
        return False
    
    return True


def test_client_initialization():
    """Test that LLMClient can be initialized."""
    print("\nTesting LLMClient initialization...")
    
    try:
        from llm_client import LLMClient
        client = LLMClient()
        print(f"✓ LLMClient initialized successfully")
        print(f"  Using model: {client.model}")
        return True
    except ValueError as e:
        print(f"✗ LLMClient initialization failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_agent_initialization():
    """Test that agents can be initialized."""
    print("\nTesting agent initialization...")
    
    try:
        from agents.scanner import ScannerAgent
        from agents.analysis import AnalysisAgent
        from agents.style import StyleAgent
        from agents.planner import PlannerAgent
        
        scanner = ScannerAgent()
        analysis = AnalysisAgent()
        style = StyleAgent()
        planner = PlannerAgent()
        
        print("✓ All agents initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Agent initialization failed: {e}")
        return False


def main():
    print("=" * 60)
    print("LLM Integration Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        print("\n⚠ Import test failed. Have you run 'pip install -r requirements.txt'?")
        all_passed = False
    
    # Test configuration
    if not test_configuration():
        print("\n⚠ Configuration test failed. Have you created .env file?")
        all_passed = False
    
    # Test client initialization
    if not test_client_initialization():
        all_passed = False
    
    # Test agent initialization
    if not test_agent_initialization():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed! Integration is complete.")
        print("\nYou can now run:")
        print("  cd src && python3 agent.py")
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        print("\nSetup steps:")
        print("1. pip install -r requirements.txt")
        print("2. cp .env.example .env")
        print("3. Edit .env and add your API credentials")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
