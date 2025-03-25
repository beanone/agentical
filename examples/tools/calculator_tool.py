"""Calculator Tool for Agentical Framework.

This module provides a simple calculator tool.

Public Interface:
    - create_calculator_tool(): Create the calculator tool definition
    - calculator_handler(): Handle calculator tool calls
    - collect_input(): Collect user input for calculator parameters

Examples:
    Basic arithmetic:
    >>> SafeCalculator.evaluate("2 + 3 * 4")
    14
    >>> SafeCalculator.evaluate("10 / 2")
    5.0
    
    Exponents and negation:
    >>> SafeCalculator.evaluate("2 ** 3")
    8
    >>> SafeCalculator.evaluate("-5")
    -5
    
    Complex expressions:
    >>> SafeCalculator.evaluate("(2 + 3) * (4 - 1)")
    15
    >>> SafeCalculator.evaluate("2 ** 3 + 4 * 2")
    16
"""

import ast
import operator
from typing import Dict, Any, Union, Optional

from agentical.types import Tool, ToolParameter


class CalculatorError(Exception):
    """Raised when there is an error evaluating an expression."""
    pass


class SafeCalculator:
    """Calculator that safely evaluates mathematical expressions.
    
    This class uses Python's ast module to parse and evaluate expressions,
    only allowing safe mathematical operations.
    """
    
    # Supported operators
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    def evaluate(self, expression: str) -> Union[int, float]:
        """Safely evaluate a mathematical expression.
        
        Args:
            expression: The expression to evaluate
            
        Returns:
            The result of the evaluation
            
        Raises:
            CalculatorError: If the expression is invalid or contains unsafe operations
        """
        # Strip whitespace and check for empty expression
        expression = expression.strip()
        if not expression:
            raise CalculatorError("Expression cannot be empty")
            
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError:
            raise CalculatorError("Invalid expression syntax")
            
        try:
            return self._eval_node(tree.body)
        except Exception as e:
            raise CalculatorError(f"Error evaluating expression: {str(e)}")
    
    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        """Recursively evaluate an AST node.
        
        Args:
            node: The AST node to evaluate
            
        Returns:
            The result of evaluating the node
            
        Raises:
            CalculatorError: If the node type is not supported
        """
        # Numbers
        if isinstance(node, ast.Num):
            return node.n
            
        # Binary operations
        if isinstance(node, ast.BinOp):
            if type(node.op) not in self._OPERATORS:
                raise CalculatorError(f"Unsupported operator: {type(node.op).__name__}")
                
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            
            try:
                return self._OPERATORS[type(node.op)](left, right)
            except ZeroDivisionError:
                raise CalculatorError("Division by zero")
            except Exception as e:
                raise CalculatorError(f"Operation error: {str(e)}")
                
        # Unary operations (like -5)
        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in self._OPERATORS:
                raise CalculatorError(f"Unsupported operator: {type(node.op).__name__}")
                
            operand = self._eval_node(node.operand)
            return self._OPERATORS[type(node.op)](operand)
            
        raise CalculatorError(f"Unsupported expression type: {type(node).__name__}")


def create_calculator_tool() -> Tool:
    """Create a calculator tool definition.
    
    Returns:
        Tool definition for evaluating mathematical expressions
    """
    return Tool(
        name="calculator",
        description="Safely evaluate mathematical expressions",
        parameters={
            "expression": ToolParameter(
                type="string",
                description=(
                    "Mathematical expression to evaluate. "
                    "Supports +, -, *, /, ** (power), and parentheses."
                ),
                required=True
            )
        }
    )


async def collect_input() -> Dict[str, Any]:
    """Collect input parameters from user.
    
    Returns:
        Dictionary of parameters for the calculator tool
        
    Raises:
        CalculatorError: If input validation fails
    """
    # Get expression
    expression = input("Enter mathematical expression: ").strip()
    if not expression:
        raise CalculatorError("Expression cannot be empty")
        
    return {"expression": expression}


async def calculator_handler(params: Dict[str, Any]) -> str:
    """Handle calculator tool execution.
    
    Args:
        params: Dictionary containing:
            - expression: Mathematical expression to evaluate
            
    Returns:
        The result of evaluating the expression
        
    Raises:
        CalculatorError: If there is an error evaluating the expression
    """
    # Get expression
    expression = params.get("expression")
    if expression is None:
        raise CalculatorError("Expression parameter is required")
    
    # Strip whitespace and check for empty expression
    expression = expression.strip()
    if not expression:
        raise CalculatorError("Expression cannot be empty")
        
    # Create calculator and evaluate
    calculator = SafeCalculator()
    try:
        result = calculator.evaluate(expression)
        return str(result)
    except CalculatorError:
        raise
    except Exception as e:
        raise CalculatorError(f"Error evaluating expression: {str(e)}") 