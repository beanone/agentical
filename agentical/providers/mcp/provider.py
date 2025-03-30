"""MCP provider implementation."""

import logging
from typing import List, Dict, Any, Optional

from agentical.core import Provider, ProviderConfig, Tool, ProviderError
from agentical.core import ToolExecutor

from .client import MCPClient
from .models import MCPConfig, MCPError, MCPRequest


class MCPProvider(Provider):
    """Provider implementation for MCP servers.
    
    This provider integrates MCP servers with the Agentical framework,
    allowing them to be used as tool providers with MCP protocol support.
    """
    
    def __init__(self, config: ProviderConfig, executor: ToolExecutor):
        """Initialize the MCP provider.
        
        Args:
            config: Provider configuration
            executor: Tool executor for handling tool calls
        """
        self._config = config
        self._executor = executor
        self._logger = logging.getLogger(f"{__name__}.MCPProvider")
        
        # Convert provider config to MCP config
        self._mcp_config = MCPConfig(
            command=config.extra_config.get("command", "npx"),
            args=config.extra_config.get("args", ["-y", "@smithery/cli@latest", "run"]),
            workingDir=config.extra_config.get("workingDir"),
            env=config.extra_config.get("env")
        )
        
        # Create MCP client
        self._client = MCPClient(
            config=self._mcp_config
        )
        
        # Cache for available tools
        self._available_tools = None
        
    def get_name(self) -> str:
        """Get the name of the provider.
        
        Returns:
            The provider's name
        """
        return "mcp"
        
    def get_description(self) -> str:
        """Get a description of the provider.
        
        Returns:
            A brief description of the provider and its capabilities
        """
        return (
            "Model Context Protocol (MCP) provider that enables interaction with "
            "MCP-compatible servers for tool execution."
        )
        
    async def _list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server.
        
        Returns:
            List of available tools and their descriptions
            
        Raises:
            MCPError: If there's an error communicating with the server
        """
        if self._available_tools is None:
            request = MCPRequest(
                method="tools/list",
                params={}
            )
            response = await self._client.send_request(request)
            self._available_tools = response.get("result", [])
            self._logger.info(f"Available tools: {self._available_tools}")
        return self._available_tools
        
    async def run_conversation(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Tool]
    ) -> str:
        """Run a conversation with the MCP server using available tools.
        
        This method:
        1. Ensures the client is connected
        2. Lists available tools from the server
        3. Sends the request to execute the appropriate tool
        
        Args:
            messages: List of conversation messages
            tools: List of available tools
            
        Returns:
            The provider's response
            
        Raises:
            ProviderError: If there's an error communicating with the server
        """
        try:
            # Ensure connected
            if not self._client.is_connected:
                await self._client.connect()
                
            # List available tools
            available_tools = await self._list_tools()
            
            # Get the latest user message
            query = self._build_query(messages)
            
            # If asking about available tools, return the list
            if "what tools" in query.lower():
                tool_descriptions = []
                for tool in available_tools:
                    name = tool.get("name", "Unknown")
                    description = tool.get("description", "No description available")
                    tool_descriptions.append(f"- {name}: {description}")
                return "\n".join([
                    "Available tools:",
                    *tool_descriptions
                ])
            
            # For now, use the first available tool
            # TODO: Implement proper tool selection based on query
            if available_tools:
                tool = available_tools[0]
                request = MCPRequest(
                    method="tools/call",
                    params={
                        "name": tool["name"],
                        "arguments": {
                            "query": query
                        }
                    }
                )
                
                response = await self._client.send_request(request)
                return response.get("result", "No response from server")
            else:
                return "No tools available from the server"
            
        except MCPError as e:
            raise ProviderError(str(e), provider_name=self.get_name())
        except Exception as e:
            raise ProviderError(
                f"Unexpected error: {str(e)}",
                provider_name=self.get_name()
            )
            
    def _build_query(self, messages: List[Dict[str, Any]]) -> str:
        """Build a query string from conversation messages.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            A query string for the MCP server
        """
        # For now, just use the last user message
        for message in reversed(messages):
            if message["role"] == "user":
                return message["content"]
                
        raise ProviderError(
            "No user message found in conversation",
            provider_name=self.get_name()
        )
        
    async def close(self) -> None:
        """Close the connection to the MCP server."""
        if self._client:
            await self._client.close() 