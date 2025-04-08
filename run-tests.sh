#! /bin/bash

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Format code and remove trailing spaces
echo "Formatting code..."
ruff format .

echo "Removing trailing spaces..."
find . -type f -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} +

# Run Ruff to fix code style issues
echo "Running Ruff fixes..."
ruff check --fix .

# Run tests with coverage and store exit code
echo "Running tests with coverage..."
pytest tests/ -v --cov=./ --cov-report=term --cov-report=html
TEST_EXIT_CODE=$?

# Generate coverage badge
COVERAGE=$(coverage report | grep "TOTAL" | awk '{print $4}' | sed 's/%//')
if [ -n "$COVERAGE" ]; then
    if [ $COVERAGE -ge 90 ]; then
        COLOR="brightgreen"
    elif [ $COVERAGE -ge 80 ]; then
        COLOR="green"
    elif [ $COVERAGE -ge 70 ]; then
        COLOR="yellowgreen"
    elif [ $COVERAGE -ge 60 ]; then
        COLOR="yellow"
    else
        COLOR="red"
    fi

    # Download coverage badge
    curl -s "https://img.shields.io/badge/coverage-${COVERAGE}%25-${COLOR}" > docs/assets/badges/coverage.svg
fi

# Generate test result badge
if [ $TEST_EXIT_CODE -eq 0 ]; then
    curl -s "https://img.shields.io/badge/tests-passing-brightgreen" > docs/assets/badges/tests.svg
else
    curl -s "https://img.shields.io/badge/tests-failing-red" > docs/assets/badges/tests.svg
fi

# Generate code quality badge based on Ruff output
echo "Checking code quality..."
if ruff check . > /dev/null 2>&1; then
    curl -s "https://img.shields.io/badge/code%20quality-passing-brightgreen" > docs/assets/badges/quality.svg
else
    curl -s "https://img.shields.io/badge/code%20quality-issues%20found-yellow" > docs/assets/badges/quality.svg
fi

# Print coverage report location
echo -e "\nCoverage report generated at: htmlcov/index.html"
echo "Badges generated in docs/assets/badges/"

# Try to open coverage report only if explicitly requested
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

# Return the test exit code
echo "Test exit code: $TEST_EXIT_CODE"