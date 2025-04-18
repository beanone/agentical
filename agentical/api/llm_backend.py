"""LLMBackend abstract base class."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from mcp.types import Tool as MCPTool, Resource as MCPResource, Prompt as MCPPrompt

# Type variables for LLM-specific context
Context = TypeVar("Context")


class LLMBackend(ABC, Generic[Context]):
    """Abstract base class for LLM backends.

    This class defines the interface that all LLM implementations must follow.
    It is designed to be independent of specific LLM implementations, while
    working directly with MCP tools, resources, and prompts.

    Type Parameters:
        Context: The type used for conversation context in this LLM implementation
    """

    @abstractmethod
    async def process_query(
        self,
        query: str,
        tools: list[MCPTool],
        resources: list[MCPResource],
        prompts: list[MCPPrompt],
        execute_tool: callable,
        context: Context | None = None,
    ) -> str:
        """Process a user query using the LLM and execute tool calls if needed.

        Args:
            query: The user's input query
            tools: List of available MCP tools
            resources: List of available MCP resources
            prompts: List of available MCP prompts
            execute_tool: Callback function to execute a tool
            context: Optional conversation context/history

        Returns:
            The response generated by the LLM model
        """
        pass

    @abstractmethod
    def convert_tools(self, tools: list[MCPTool]) -> list[MCPTool]:
        """Convert MCP tools to the format expected by this LLM.

        Args:
            tools: List of MCP tools to convert

        Returns:
            Tools in the format expected by this LLM implementation
        """
        pass
