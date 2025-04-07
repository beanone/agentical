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

# Run tests with coverage
echo "Running tests with coverage..."
pytest tests/ -v --cov=./ --cov-report=term --cov-report=html

# Print coverage report location
echo -e "\nCoverage report generated at: htmlcov/index.html"

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