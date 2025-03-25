"""Tests for the calculator tool."""

import pytest
from unittest.mock import patch
from typing import Dict, Any

from examples.tools.calculator_tool import (
    SafeCalculator,
    CalculatorError,
    create_calculator_tool,
    calculator_handler,
    collect_input
)


def test_safe_calculator_basic_operations() -> None:
    """Test basic calculator operations."""
    calculator = SafeCalculator()
    
    # Test addition
    assert calculator.evaluate("2 + 3") == 5
    
    # Test subtraction
    assert calculator.evaluate("5 - 3") == 2
    
    # Test multiplication
    assert calculator.evaluate("4 * 3") == 12
    
    # Test division
    assert calculator.evaluate("10 / 2") == 5
    assert calculator.evaluate("5 / 2") == 2.5  # Test floating point division
    
    # Test power
    assert calculator.evaluate("2 ** 3") == 8
    assert calculator.evaluate("2 ** 0.5") == 2 ** 0.5  # Test fractional powers
    
    # Test negative numbers
    assert calculator.evaluate("-5") == -5
    assert calculator.evaluate("-(2 + 3)") == -5


def test_safe_calculator_complex_expressions() -> None:
    """Test more complex calculator expressions."""
    calculator = SafeCalculator()
    
    # Test order of operations
    assert calculator.evaluate("2 + 3 * 4") == 14
    assert calculator.evaluate("(2 + 3) * 4") == 20
    
    # Test nested expressions
    assert calculator.evaluate("2 * (3 + (4 - 1))") == 12
    
    # Test multiple operations
    assert calculator.evaluate("2 + 3 - 4 * 5 / 2") == -5
    
    # Test floating point operations
    assert abs(calculator.evaluate("3.14159 * 2") - 6.28318) < 1e-5
    assert abs(calculator.evaluate("10 / 3") - 3.33333) < 1e-5


def test_safe_calculator_whitespace_handling() -> None:
    """Test calculator handles whitespace correctly."""
    calculator = SafeCalculator()
    
    # Test various whitespace patterns
    assert calculator.evaluate("2+3") == 5
    assert calculator.evaluate("2 + 3") == 5
    assert calculator.evaluate(" 2 + 3 ") == 5
    assert calculator.evaluate("2  +  3") == 5
    assert calculator.evaluate("\t2\t+\t3\t") == 5
    assert calculator.evaluate("\n2 + 3\n") == 5


def test_safe_calculator_invalid_expressions() -> None:
    """Test that invalid expressions raise appropriate errors."""
    calculator = SafeCalculator()
    
    # Test invalid syntax
    with pytest.raises(CalculatorError, match="Invalid expression syntax"):
        calculator.evaluate("2 +")
    
    # Test division by zero
    with pytest.raises(CalculatorError, match="Division by zero"):
        calculator.evaluate("1 / 0")
    
    # Test unsupported operations
    with pytest.raises(CalculatorError, match="Unsupported expression type"):
        calculator.evaluate("'test' + 2")
    
    # Test invalid characters
    with pytest.raises(CalculatorError):
        calculator.evaluate("2 $ 3")
    
    # Test empty expression
    with pytest.raises(CalculatorError):
        calculator.evaluate("")
    
    # Test only whitespace
    with pytest.raises(CalculatorError):
        calculator.evaluate("   ")


def test_create_calculator_tool() -> None:
    """Test creating the calculator tool definition."""
    tool = create_calculator_tool()
    
    # Verify tool properties
    assert tool.name == "calculator"
    assert "safely evaluate" in tool.description.lower()
    
    # Verify parameters
    assert "expression" in tool.parameters
    assert tool.parameters["expression"].type == "string"
    assert tool.parameters["expression"].required is True
    assert "mathematical expression" in tool.parameters["expression"].description.lower()


@pytest.mark.asyncio
async def test_calculator_handler_valid_expressions() -> None:
    """Test calculator handler with valid expressions."""
    # Test basic expression
    result1 = await calculator_handler({"expression": "2 + 2"})
    assert result1 == "4"
    
    # Test complex expression
    result2 = await calculator_handler({"expression": "(3 + 4) * 2"})
    assert result2 == "14"
    
    # Test negative numbers
    result3 = await calculator_handler({"expression": "-5 + 3"})
    assert result3 == "-2"
    
    # Test floating point numbers
    result4 = await calculator_handler({"expression": "3.14 * 2"})
    assert abs(float(result4) - 6.28) < 1e-5


@pytest.mark.asyncio
async def test_calculator_handler_invalid_expressions() -> None:
    """Test calculator handler with invalid expressions."""
    # Test missing expression parameter
    with pytest.raises(CalculatorError, match="Expression parameter is required"):
        await calculator_handler({})
    
    # Test empty expression
    with pytest.raises(CalculatorError, match="Expression cannot be empty"):
        await calculator_handler({"expression": ""})
    
    # Test invalid expression
    with pytest.raises(CalculatorError, match="Invalid expression syntax"):
        await calculator_handler({"expression": "2 +"})
    
    # Test division by zero
    with pytest.raises(CalculatorError, match="Division by zero"):
        await calculator_handler({"expression": "1 / 0"})


@pytest.mark.asyncio
async def test_collect_input() -> None:
    """Test collecting input from user."""
    # Test valid input
    with patch("builtins.input", return_value="2 + 2"):
        params = await collect_input()
        assert params == {"expression": "2 + 2"}
    
    # Test empty input
    with patch("builtins.input", return_value=""):
        with pytest.raises(CalculatorError, match="Expression cannot be empty"):
            await collect_input()
    
    # Test whitespace-only input
    with patch("builtins.input", return_value="   "):
        with pytest.raises(CalculatorError, match="Expression cannot be empty"):
            await collect_input() 