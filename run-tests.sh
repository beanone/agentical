#! /bin/bash

# Exit on any error
set -e

# Function to print error messages
error() {
    echo "ERROR: $1" >&2
    exit 1
}

# Function to print section headers
section() {
    echo -e "\n=== $1 ==="
}

# Check for virtual environment and activate it
section "Virtual Environment Setup"
if [ ! -d ".venv" ]; then
    error "Virtual environment not found. Please create one using 'python -m venv .venv'"
fi
source .venv/bin/activate || error "Failed to activate virtual environment"

# Check required tools
section "Dependency Verification"
python -c "import pytest, coverage, ruff" 2>/dev/null || error "Missing required dependencies. Please run: pip install pytest pytest-cov coverage ruff"

# Format code and remove trailing spaces
section "Code Formatting"
echo "Formatting code..."
ruff format . || error "Code formatting failed"

echo "Removing trailing spaces..."
find . -type f -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} + || error "Failed to remove trailing spaces"

# Run Ruff with strict checks on all Python files
section "Code Quality Checks"
echo "Running Ruff checks..."
ruff check . --no-fix --no-cache || error "Ruff checks failed. Please fix the issues before proceeding"

# Run tests with coverage
section "Running Tests"
echo "Running tests with coverage..."
# Run pytest with coverage
pytest tests/ -v \
    --cov=agentical \
    --cov=server \
    --cov-report=term \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=80 || TEST_EXIT_CODE=$?

# Get the coverage percentage
COVERAGE_FLOAT=$(coverage report | grep "TOTAL" | tail -1 | awk '{print $6}' | sed 's/%//')
COVERAGE=$(echo "$COVERAGE_FLOAT" | awk '{printf "%.0f", $1}')

# Set badge color based on coverage
if [ "$COVERAGE" -ge 90 ]; then
    COLOR="brightgreen"
elif [ "$COVERAGE" -ge 80 ]; then
    COLOR="green"
elif [ "$COVERAGE" -ge 70 ]; then
    COLOR="yellowgreen"
elif [ "$COVERAGE" -ge 60 ]; then
    COLOR="yellow"
else
    COLOR="red"
    error "Coverage below 60%. Please improve test coverage before release."
fi

# Create badges directory if it doesn't exist
mkdir -p docs/assets/badges

# Download coverage badge (use the original float value for display)
curl -s "https://img.shields.io/badge/coverage-${COVERAGE_FLOAT}%25-${COLOR}" > docs/assets/badges/coverage.svg || error "Failed to generate coverage badge"

# Generate test result badge
if [ ${TEST_EXIT_CODE:-0} -eq 0 ]; then
    curl -s "https://img.shields.io/badge/tests-passing-brightgreen" > docs/assets/badges/tests.svg
else
    curl -s "https://img.shields.io/badge/tests-failing-red" > docs/assets/badges/tests.svg
    error "Tests failed. Please fix failing tests before release."
fi

# Generate code quality badge based on Ruff output
section "Final Quality Check"
if ruff check . > /dev/null 2>&1; then
    curl -s "https://img.shields.io/badge/code%20quality-passing-brightgreen" > docs/assets/badges/quality.svg
else
    curl -s "https://img.shields.io/badge/code%20quality-issues%20found-yellow" > docs/assets/badges/quality.svg
    error "Code quality issues found. Please fix them before release."
fi

# Print summary
section "Summary"
echo "✓ All checks passed successfully!"
echo "✓ Coverage report generated at: htmlcov/index.html"
echo "✓ Coverage XML report generated at: coverage.xml"
echo "✓ Badges generated in docs/assets/badges/"

# Try to open coverage report if requested
if [ "$1" = "--open-report" ]; then
    if grep -q Microsoft /proc/version; then
        # If running in WSL, try to use Windows browser
        cmd.exe /C start $(wslpath -w htmlcov/index.html) 2>/dev/null || \
        echo "Could not open browser in WSL. Coverage report is available at: htmlcov/index.html"
    else
        # For non-WSL environments
        if command -v xdg-open &> /dev/null; then
            xdg-open htmlcov/index.html 2>/dev/null || \
            echo "Could not open browser. Coverage report is available at: htmlcov/index.html"
        elif command -v open &> /dev/null; then
            open htmlcov/index.html
        elif command -v start &> /dev/null; then
            start htmlcov/index.html
        else
            echo "Could not detect a way to open the browser. Coverage report is available at: htmlcov/index.html"
        fi
    fi
fi

# Exit with success
exit ${TEST_EXIT_CODE:-0}