"""
Python Agent - Main Module

A simple agent framework for executing tasks and managing state.
"""

import logging
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import schemas
from orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    """Represents the state of the agent."""
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    is_running: bool = False


class Agent:
    """
    A simple agent that can execute tasks and maintain state.
    """
    
    def __init__(self, name: str = "Agent"):
        """
        Initialize the agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.state = AgentState()
        logger.info(f"Agent '{self.name}' initialized")
    
    def process(self, input_data: str) -> str:
        """
        Process input data and return a response.
        
        Args:
            input_data: Input string to process
            
        Returns:
            Processed response string
        """
        logger.info(f"Processing input: {input_data}")
        
        # Add to history
        self.state.history.append(input_data)
        
        # Simple echo response for now
        response = f"Agent '{self.name}' processed: {input_data}"
        
        logger.info(f"Response: {response}")
        return response
    
    def start(self) -> None:
        """Start the agent."""
        self.state.is_running = True
        logger.info(f"Agent '{self.name}' started")
    
    def stop(self) -> None:
        """Stop the agent."""
        self.state.is_running = False
        logger.info(f"Agent '{self.name}' stopped")
    
    def get_state(self) -> AgentState:
        """Get the current state of the agent."""
        return self.state
    
    def reset(self) -> None:
        """Reset the agent state."""
        self.state = AgentState()
        logger.info(f"Agent '{self.name}' state reset")


def load_code_from_file(file_path: str) -> str:
    """
    Load code from a file.
    
    Args:
        file_path: Path to the code file
        
    Returns:
        Code content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        if not code.strip():
            raise ValueError(f"File is empty: {file_path}")
        
        logger.info(f"Loaded {len(code)} characters from {file_path}")
        return code
    
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def main():
    """Main entry point for the agent."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Code Analysis Agent - Analyze Python code and generate refactoring plans',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s mycode.py                    # Analyze a single file
  %(prog)s /path/to/script.py           # Analyze file with absolute path
  %(prog)s --file mycode.py             # Alternative syntax
  
The agent will:
  1. Scan code structure (functions, classes, imports)
  2. Analyze for bugs and logic issues
  3. Check code style and quality
  4. Generate a prioritized refactoring plan
        """
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        help='Path to Python file to analyze'
    )
    
    parser.add_argument(
        '-f', '--file',
        dest='file_arg',
        help='Path to Python file to analyze (alternative syntax)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file for refactoring plan (JSON format)'
    )
    
    args = parser.parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get file path from either positional or named argument
    file_path = args.file or args.file_arg
    
    if not file_path:
        parser.print_help()
        print("\n❌ Error: No file specified", file=sys.stderr)
        print("Please provide a Python file to analyze", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load code from file
        print(f"\n📂 Loading code from: {file_path}")
        code = load_code_from_file(file_path)
        print(f"✓ Loaded {len(code)} characters")
        
        # Run orchestrator
        print("\n🤖 Starting code analysis...")
        orchestrator = Orchestrator()
        result = orchestrator.run(code)
        
        # Display results
        print("\n" + "=" * 70)
        print("📋 REFACTOR PLAN")
        print("=" * 70)
        
        output_json = result.model_dump_json(indent=2)
        print(output_json)
        
        print("\n" + "=" * 70)
        
        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"\n💾 Refactoring plan saved to: {args.output}")
        
        print("\n✓ Analysis complete!")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except ValueError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
