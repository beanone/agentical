"""Calculator Tool for Agentical Framework.

This module provides MCP-compliant tools for safe mathematical expression evaluation.
"""

import ast
import operator
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("calculator")


class CalculatorError(Exception):
    """Raised when there is an error performing a calculator operation."""

    pass


class SafeCalculator(ast.NodeVisitor):
    """Safe calculator that evaluates mathematical expressions using AST."""

    def __init__(self):
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,  # Unary minus
            ast.UAdd: operator.pos,  # Unary plus
        }

    def visit_BinOp(self, node: ast.BinOp) -> float:
        """Handle binary operations (e.g., 1 + 2, 3 * 4)."""
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(node.op, ast.Div) and right == 0:
            raise CalculatorError("Division by zero is not allowed")

        op = self.operators.get(type(node.op))
        if op is None:
            raise CalculatorError(f"Unsupported operator: {type(node.op).__name__}")

        return op(left, right)

    def visit_Constant(self, node: ast.Constant) -> float:
        """Handle numeric constants (for Python 3.8+)."""
        if not isinstance(node.value, (int, float)):
            raise CalculatorError(
                f"Unsupported constant type: {type(node.value).__name__}"
            )
        return float(node.value)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        """Handle unary operations (e.g., -1, +2)."""
        operand = self.visit(node.operand)
        op = self.operators.get(type(node.op))
        if op is None:
            raise CalculatorError(
                f"Unsupported unary operator: {type(node.op).__name__}"
            )
        return op(operand)

    def visit_Call(self, node: ast.Call) -> float:
        """Block function calls for security."""
        raise CalculatorError("Function calls are not allowed")

    def visit_Name(self, node: ast.Name) -> float:
        """Block variable names for security."""
        raise CalculatorError("Variables are not allowed")

    def generic_visit(self, node: ast.AST) -> float:
        """Block any other AST nodes for security."""
        raise CalculatorError(f"Unsupported expression type: {type(node).__name__}")


def sanitize_expression(expression: str) -> str:
    """Remove whitespace and validate basic string content."""
    if expression is None:
        raise CalculatorError("Expression cannot be None")
    cleaned = "".join(expression.split())
    if not cleaned:
        raise CalculatorError("Empty expression")
    if any(char not in "0123456789.+-*/() " for char in cleaned):
        raise CalculatorError("Expression contains invalid characters")
    return cleaned


@mcp.tool()
async def calculate(expression: str) -> dict[str, Any]:
    """Calculate the result of a mathematical expression.

    Args:
        expression: A string containing a mathematical expression
                   Supported operations: +, -, *, /, ** (power)
                   Example: "2 + 3 * (4 - 1)"

    Returns:
        Dictionary containing:
            - success: bool indicating if the calculation was successful
            - result: The calculated result as a float if successful, None if not
            - error: Error message if not successful, None if successful
            - expression: The sanitized expression that was evaluated

    Example:
        >>> result = await calculate("2 + 3 * (4 - 1)")
        >>> print(result)
        {
            'success': True,
            'result': 11.0,
            'error': None,
            'expression': '2+3*(4-1)'
        }
    """
    try:
        # Sanitize input
        cleaned_expr = sanitize_expression(expression)

        # Parse the expression into an AST
        tree = ast.parse(cleaned_expr, mode="eval")

        # Evaluate the expression safely
        calculator = SafeCalculator()
        result = calculator.visit(tree.body)

        return {
            "success": True,
            "result": float(result),
            "error": None,
            "expression": cleaned_expr,
        }
    except (SyntaxError, CalculatorError) as e:
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "expression": expression,
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"Calculation failed: {e!s}",
            "expression": expression,
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
