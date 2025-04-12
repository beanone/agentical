"""Unit tests for calculator_server.py.

This module provides comprehensive test coverage for the calculator server implementation.
"""

import ast
import pytest
from server.calculator_server import (
    SafeCalculator,
    CalculatorError,
    sanitize_expression,
    calculate,
)


class TestSanitizeExpression:
    """Test cases for the sanitize_expression function."""

    def test_basic_sanitization(self):
        """Test basic expression sanitization."""
        assert sanitize_expression("2 + 3") == "2+3"
        assert sanitize_expression(" 1 *  2 ") == "1*2"
        assert sanitize_expression("(1 + 2) * 3") == "(1+2)*3"

    def test_none_expression(self):
        """Test handling of None expression."""
        with pytest.raises(CalculatorError, match="Expression cannot be None"):
            sanitize_expression(None)

    def test_empty_expression(self):
        """Test handling of empty expression."""
        with pytest.raises(CalculatorError, match="Empty expression"):
            sanitize_expression("")
        with pytest.raises(CalculatorError, match="Empty expression"):
            sanitize_expression("   ")

    def test_invalid_characters(self):
        """Test handling of invalid characters."""
        with pytest.raises(
            CalculatorError, match="Expression contains invalid characters"
        ):
            sanitize_expression("2 + a")
        with pytest.raises(
            CalculatorError, match="Expression contains invalid characters"
        ):
            sanitize_expression("sin(x)")
        with pytest.raises(
            CalculatorError, match="Expression contains invalid characters"
        ):
            sanitize_expression("2 @ 3")


class TestSafeCalculator:
    """Test cases for the SafeCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Fixture to create a SafeCalculator instance."""
        return SafeCalculator()

    def test_basic_arithmetic(self, calculator):
        """Test basic arithmetic operations."""
        cases = [
            ("2 + 3", 5.0),
            ("3 - 1", 2.0),
            ("4 * 5", 20.0),
            ("15 / 3", 5.0),
            ("2 ** 3", 8.0),
        ]
        for expr, expected in cases:
            tree = ast.parse(expr, mode="eval")
            result = calculator.visit(tree.body)
            assert result == expected

    def test_complex_expressions(self, calculator):
        """Test more complex arithmetic expressions."""
        cases = [
            ("2 + 3 * 4", 14.0),  # Order of operations
            ("(2 + 3) * 4", 20.0),  # Parentheses
            ("2 ** 3 + 1", 9.0),  # Power operation
            ("10 / 2 * 3", 15.0),  # Multiple operations
            ("2 + 2 + 2", 6.0),  # Multiple additions
        ]
        for expr, expected in cases:
            tree = ast.parse(expr, mode="eval")
            result = calculator.visit(tree.body)
            assert result == expected

    def test_unary_operations(self, calculator):
        """Test unary operations (positive and negative)."""
        cases = [
            ("-5", -5.0),
            ("+5", 5.0),
            ("-2 + 3", 1.0),
            ("+2 - 3", -1.0),
        ]
        for expr, expected in cases:
            tree = ast.parse(expr, mode="eval")
            result = calculator.visit(tree.body)
            assert result == expected

    def test_division_by_zero(self, calculator):
        """Test division by zero error."""
        with pytest.raises(CalculatorError, match="Division by zero is not allowed"):
            tree = ast.parse("1 / 0", mode="eval")
            calculator.visit(tree.body)

    def test_invalid_operations(self, calculator):
        """Test invalid operations and expressions."""
        # Test function calls
        with pytest.raises(CalculatorError, match="Function calls are not allowed"):
            tree = ast.parse("sin(30)", mode="eval")
            calculator.visit(tree.body)

        # Test variables
        with pytest.raises(CalculatorError, match="Variables are not allowed"):
            tree = ast.parse("x + 1", mode="eval")
            calculator.visit(tree.body)

        # Test unsupported operators
        with pytest.raises(CalculatorError, match="Unsupported expression type"):
            tree = ast.parse("1 if True else 0", mode="eval")
            calculator.visit(tree.body)

    def test_constant_validation(self, calculator):
        """Test constant validation."""
        # Test valid numeric constants
        tree = ast.parse("42", mode="eval")
        assert calculator.visit(tree.body) == 42.0

        # Test invalid constant type
        node = ast.Constant(value="invalid")  # String constant
        with pytest.raises(CalculatorError, match="Unsupported constant type: str"):
            calculator.visit(node)

    def test_unsupported_binary_operator(self, calculator):
        """Test unsupported binary operator."""
        # Create a BinOp node with an unsupported operator
        node = ast.BinOp(
            left=ast.Constant(value=1), right=ast.Constant(value=2), op=ast.BitOr()
        )

        with pytest.raises(CalculatorError, match="Unsupported operator: BitOr"):
            calculator.visit(node)

    def test_unsupported_unary_operator(self, calculator):
        """Test unsupported unary operator."""
        # Create a UnaryOp node with an unsupported operator
        node = ast.UnaryOp(operand=ast.Constant(value=1), op=ast.Invert())

        with pytest.raises(CalculatorError, match="Unsupported unary operator: Invert"):
            calculator.visit(node)


@pytest.mark.asyncio
class TestCalculateFunction:
    """Test cases for the calculate async function."""

    async def test_successful_calculations(self):
        """Test successful calculations with various expressions."""
        test_cases = [
            ("2 + 2", 4.0),
            ("3 * (4 + 2)", 18.0),
            ("10 / 2", 5.0),
            ("2 ** 3", 8.0),
            ("-5 + 3", -2.0),
            ("(2 + 3) * (4 - 1)", 15.0),
        ]

        for expr, expected in test_cases:
            result = await calculate(expr)
            assert result["success"] is True
            assert result["result"] == expected
            assert result["error"] is None
            assert result["expression"] == expr.replace(" ", "")

    async def test_invalid_expressions(self):
        """Test handling of invalid expressions."""
        test_cases = [
            ("", "Empty expression"),
            ("2 + x", "Expression contains invalid characters"),
            ("2 + ", "invalid syntax"),
            ("sin(30)", "Expression contains invalid characters"),
            ("2 ** ** 2", "invalid syntax"),
        ]

        for expr, error_substring in test_cases:
            result = await calculate(expr)
            assert result["success"] is False
            assert result["result"] is None
            assert error_substring.lower() in result["error"].lower()
            assert result["expression"] == expr

    async def test_division_by_zero(self):
        """Test division by zero handling."""
        result = await calculate("1/0")
        assert result["success"] is False
        assert result["result"] is None
        assert "Division by zero" in result["error"]
        assert result["expression"] == "1/0"

    async def test_none_input(self):
        """Test handling of None input."""
        result = await calculate(None)
        assert result["success"] is False
        assert result["result"] is None
        assert "cannot be None" in result["error"]
        assert result["expression"] is None
