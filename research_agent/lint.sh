#!/bin/bash

# Lint script for the multi-agent system

echo "Running linters..."

echo "1. Running Black (formatter)..."
python -m black --check src/ tests/ main.py

echo ""
echo "2. Running Ruff (linter)..."
python -m ruff check src/ tests/ main.py

echo ""
echo "3. Running MyPy (type checker)..."
python -m mypy src/ --ignore-missing-imports

echo ""
echo "Linting complete!"
