#!/usr/bin/env python3
"""
Test script for ScannerAgent edge cases and validation.
"""

import sys
sys.path.insert(0, 'src')

from agents.scanner import ScannerAgent
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def test_empty_code():
    """Test scanner with empty code."""
    print("\n=== Test 1: Empty Code ===")
    scanner = ScannerAgent()
    try:
        result = scanner.run("")
        print("❌ Should have raised ValueError for empty code")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")

def test_large_code():
    """Test scanner with excessively large code."""
    print("\n=== Test 2: Large Code (>500KB) ===")
    scanner = ScannerAgent()
    large_code = "x = 1\n" * 100000  # ~600KB
    try:
        result = scanner.run(large_code)
        print("❌ Should have raised ValueError for large code")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")

def test_syntax_error():
    """Test scanner with syntax error."""
    print("\n=== Test 3: Syntax Error ===")
    scanner = ScannerAgent()
    bad_code = "def foo(\n    print('missing closing paren')"
    try:
        result = scanner.run(bad_code)
        print("❌ Should have raised SyntaxError")
    except SyntaxError as e:
        print(f"✓ Correctly raised SyntaxError: {e}")

def test_valid_code():
    """Test scanner with valid code."""
    print("\n=== Test 4: Valid Code ===")
    scanner = ScannerAgent()
    valid_code = """
def greet(name):
    return f"Hello, {name}!"

class Person:
    def __init__(self, name):
        self.name = name
"""
    try:
        result = scanner.run(valid_code)
        print(f"✓ Scan successful!")
        print(f"  Functions: {result.structure.functions}")
        print(f"  Classes: {result.structure.classes}")
        print(f"  Issues found: {len(result.issues)}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Run all tests."""
    print("=" * 60)
    print("ScannerAgent Edge Case Tests")
    print("=" * 60)
    
    test_empty_code()
    test_large_code()
    test_syntax_error()
    test_valid_code()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
