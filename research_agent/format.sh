#!/bin/bash

# Auto-fix script for formatting and linting

echo "Auto-fixing code..."

echo "1. Running Black (formatter)..."
python -m black src/ tests/ main.py

echo ""
echo "2. Running Ruff (auto-fix)..."
python -m ruff check --fix src/ tests/ main.py

echo ""
echo "Auto-fix complete!"
