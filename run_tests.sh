#!/bin/bash

# Test Runner for Price Comparison Tool
# This script runs all unit and integration tests

set -e  # Exit on any error


# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$SCRIPT_DIR/tests"

echo "Price Comparison Tool - Test Suite"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is required but not installed."
    exit 1
fi

# Install test dependencies
echo "Installing test dependencies..."
cd "$TESTS_DIR"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "Test dependencies installed successfully"
    else
        echo "Failed to install test dependencies"
        exit 1
    fi
else
    echo "Error: requirements.txt not found in tests directory"
    exit 1
fi

# Run the tests
echo "Running API parsing tests..."
cd "$SCRIPT_DIR"

# Run pytest with verbose output
python3 -m pytest tests/test_api_parsing.py -v --tb=short

if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed. Check the output above for details."
    exit 1
fi

echo "Test coverage summary:"
python3 -m pytest tests/test_api_parsing.py --tb=no -q

echo "Test suite completed successfully!"