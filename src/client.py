# Import necessary libraries
import asyncio  # For handling asynchronous operations
import os       # For environment variable access
import sys      # For system-specific parameters and functions
import json     # For handling JSON data
import argparse # For command line arguments
from pathlib import Path
from typing import Dict, Optional, List

# Import MCP client components
from contextlib import AsyncExitStack  # For managing multiple async tasks
from mcp import ClientSession, StdioServerParameters  # MCP session management
from mcp.client.stdio import stdio_client  # MCP client for standard I/O communication

# Import Google's Gen AI SDK
from google import genai
from google.genai import types
from google.genai.types import Tool, FunctionDeclaration
from google.genai.types import GenerateContentConfig

from dotenv import load_dotenv  # For loading API keys from a .env file

# Load environment variables from .env file
load_dotenv()

class MCPClient:
    def __init__(self):
        """Initialize the MCP client and configure the Gemini API."""
        self.session: Optional[ClientSession] = None  # MCP session for communication
        self.exit_stack = AsyncExitStack()  # Manages async resource cleanup
        self.available_servers: Dict[str, dict] = {}

        # Retrieve the Gemini API key from environment variables
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found. Please add it to your .env file.")

        # Configure the Gemini AI client
        self.genai_client = genai.Client(api_key=gemini_api_key)

    @staticmethod
    def load_mcp_config(config_path: str | Path) -> Dict[str, dict]:
        """
        Load MCP configurations from a JSON file.
        
        Args:
            config_path: Path to the MCP configuration file
            
        Returns:
            Dict of server names to their configurations
        """
        with open(config_path) as f:
            config = json.load(f)
            
        # Validate each server configuration
        for server_name, server_config in config.items():
            if not isinstance(server_config, dict):
                raise ValueError(f"Configuration for {server_name} must be a dictionary")
            if "command" not in server_config:
                raise ValueError(f"Configuration for {server_name} must contain 'command' field")
            if "args" not in server_config or not isinstance(server_config["args"], list):
                raise ValueError(f"Configuration for {server_name} must contain 'args' as a list")
                
        return config

    def list_available_servers(self) -> List[str]:
        """List all available MCP servers from the loaded configuration."""
        return list(self.available_servers.keys())

    async def mcp_connect(self, server_name: str):
        """
        Connect to a specific MCP server by name.
        
        Args:
            server_name: Name of the server as defined in the configuration
            
        Raises:
            ValueError: If server_name is invalid or configuration is incomplete
            TypeError: If configuration values are of incorrect type
        """
        if not isinstance(server_name, str):
            raise TypeError(f"server_name must be a string, got {type(server_name)}")
            
        if not server_name:
            raise ValueError("server_name cannot be empty")
            
        if server_name not in self.available_servers:
            raise ValueError(f"Unknown server: {server_name}. Available servers: {self.list_available_servers()}")
            
        config = self.available_servers[server_name]
        
        # Validate required configuration fields
        if not isinstance(config, dict):
            raise TypeError(f"Configuration for {server_name} must be a dictionary")
            
        if "command" not in config:
            raise ValueError(f"Configuration for {server_name} missing required 'command' field")
            
        if not isinstance(config["command"], str):
            raise TypeError(f"'command' for {server_name} must be a string")
            
        if "args" not in config:
            raise ValueError(f"Configuration for {server_name} missing required 'args' field")
            
        if not isinstance(config["args"], list):
            raise TypeError(f"'args' for {server_name} must be a list")
        
        # Create server parameters with validated fields
        params = {
            "command": config["command"],
            "args": config["args"]
        }
        
        # Only include env if it exists and is a dictionary
        if "env" in config:
            if not isinstance(config["env"], dict):
                raise TypeError(f"'env' for {server_name} must be a dictionary")
            params["env"] = config["env"]
            
        try:
            server_params = StdioServerParameters(**params)
        except Exception as e:
            raise ValueError(f"Failed to create server parameters: {str(e)}")

        try:
            # Connect to the server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            self.stdio, self.write = stdio_transport
            
            # Initialize session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            # Initialize and get tools
            await self.session.initialize()
            response = await self.session.list_tools()
            
            print(f"\nConnected to server '{server_name}' with tools:", 
                  [tool.name for tool in response.tools])
            
            # Convert tools for Gemini
            self.function_declarations = convert_mcp_tools_to_gemini(response.tools)
            
        except Exception as e:
            await self.cleanup()  # Ensure resources are cleaned up on error
            raise ConnectionError(f"Failed to connect to server '{server_name}': {str(e)}")

    async def interactive_server_selection(self) -> str:
        """
        Interactively prompt the user to select an MCP server.
        
        Returns:
            Selected server name
        """
        servers = self.list_available_servers()
        
        if not servers:
            raise ValueError("No MCP servers available in configuration")
            
        print("\nAvailable MCP servers:")
        for idx, server in enumerate(servers, 1):
            print(f"{idx}. {server}")
            
        while True:
            try:
                choice = input("\nSelect a server (enter number): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(servers):
                    return servers[idx]
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    async def process_query(self, query: str) -> str:
        """
        Process a user query using the Gemini API and execute tool calls if needed.

        Args:
            query (str): The user's input query.

        Returns:
            str: The response generated by the Gemini model.
        """
        if not self.session:
            raise ValueError("Not connected to any MCP server. Please select and connect to a server first.")

        # Format user input as a structured Content object for Gemini
        user_prompt_content = types.Content(
            role='user',  # Indicates that this is a user message
            parts=[types.Part.from_text(text=query)]  # Convert the text query into a Gemini-compatible format
        )

        # Send user input to Gemini AI and include available tools for function calling
        response = self.genai_client.models.generate_content(
            model='gemini-2.0-flash-001',  # Specifies which Gemini model to use
            contents=[user_prompt_content],  # Send user input to Gemini
            config=types.GenerateContentConfig(
                tools=self.function_declarations,  # Pass the list of available MCP tools for Gemini to use
            ),
        )

        # Initialize variables to store final response text and assistant messages
        final_text = []  # Stores the final formatted response

        # Process the response received from Gemini
        for candidate in response.candidates:
            if candidate.content.parts:  # Ensure response has content
                for part in candidate.content.parts:
                    if isinstance(part, types.Part):  # Check if part is a valid Gemini response unit
                        if part.function_call:  # If Gemini suggests a function call, process it
                            # Extract function call details
                            function_call_part = part  # Store the function call response
                            tool_name = function_call_part.function_call.name  # Name of the MCP tool Gemini wants to call
                            tool_args = function_call_part.function_call.args  # Arguments required for the tool execution

                            # Print debug info: Which tool is being called and with what arguments
                            print(f"\n[Gemini requested tool call: {tool_name} with args {tool_args}]")

                            # Execute the tool using the MCP server
                            try:
                                result = await self.session.call_tool(tool_name, tool_args)  # Call MCP tool with arguments
                                function_response = {"result": result.content}  # Store the tool's output
                            except Exception as e:
                                function_response = {"error": str(e)}  # Handle errors if tool execution fails

                            # Format the tool response for Gemini in a way it understands
                            function_response_part = types.Part.from_function_response(
                                name=tool_name,  # Name of the function/tool executed
                                response=function_response  # The result of the function execution
                            )

                            # Structure the tool response as a Content object for Gemini
                            function_response_content = types.Content(
                                role='tool',  # Specifies that this response comes from a tool
                                parts=[function_response_part]  # Attach the formatted response part
                            )

                            # Send tool execution results back to Gemini for processing
                            response = self.genai_client.models.generate_content(
                                model='gemini-2.0-flash-001',  # Use the same model
                                contents=[
                                    user_prompt_content,  # Include original user query
                                    function_call_part,  # Include Gemini's function call request
                                    function_response_content,  # Include tool execution result
                                ],
                                config=types.GenerateContentConfig(
                                    tools=self.function_declarations,  # Provide the available tools for continued use
                                ),
                            )

                            # Extract final response text from Gemini after processing the tool call
                            final_text.append(response.candidates[0].content.parts[0].text)
                        else:
                            # If no function call was requested, simply add Gemini's text response
                            final_text.append(part.text)

        # Return the combined response as a single formatted string
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat session with the user."""
        print("\nMCP Client Started! Type 'quit' to exit.")

        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == 'quit':
                break

            # Process the user's query and display the response
            response = await self.process_query(query)
            print("\n" + response)

    async def cleanup(self):
        """Clean up resources before exiting."""
        await self.exit_stack.aclose()

    @staticmethod
    def parse_arguments():
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description='MCP Client')
        parser.add_argument(
            '--config', '-c',
            type=str,
            default='config.json',
            help='Path to MCP configuration file (default: config.json)'
        )
        return parser.parse_args()

def clean_schema(schema):
    """
    Recursively removes 'title' fields from the JSON schema.

    Args:
        schema (dict): The schema dictionary.

    Returns:
        dict: Cleaned schema without 'title' fields.
    """
    if isinstance(schema, dict):
        schema.pop("title", None)  # Remove title if present

        # Recursively clean nested properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            for key in schema["properties"]:
                schema["properties"][key] = clean_schema(schema["properties"][key])

    return schema

def convert_mcp_tools_to_gemini(mcp_tools):
    """
    Converts MCP tool definitions to the correct format for Gemini API function calling.

    Args:
        mcp_tools (list): List of MCP tool objects with 'name', 'description', and 'inputSchema'.

    Returns:
        list: List of Gemini Tool objects with properly formatted function declarations.
    """
    gemini_tools = []

    for tool in mcp_tools:
        # Ensure inputSchema is a valid JSON schema and clean it
        parameters = clean_schema(tool.inputSchema)
        
        # Handle empty object properties for tools like read_graph
        if not parameters.get("properties"):
            parameters["properties"] = {
                "random_string": {
                    "type": "string",
                    "description": "Dummy parameter for no-parameter tools"
                }
            }

        # Construct the function declaration
        function_declaration = FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=parameters  # Now correctly formatted
        )

        # Wrap in a Tool object
        gemini_tool = Tool(function_declarations=[function_declaration])
        gemini_tools.append(gemini_tool)

    return gemini_tools

async def main():
    """Main function to start the MCP client with server selection."""
    # Parse command line arguments
    args = MCPClient.parse_arguments()
    config_path = args.config

    # Check if configuration file exists
    if not Path(config_path).exists():
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please provide a valid configuration file using --config or -c option.")
        print("Example: python client.py --config my_config.json")
        sys.exit(1)

    client = MCPClient()
    try:
        # Load configurations
        print(f"\nLoading MCP configurations from: {config_path}")
        client.available_servers = MCPClient.load_mcp_config(config_path)
        
        # Let user select server
        selected_server = await client.interactive_server_selection()
        
        # Connect to selected server
        await client.mcp_connect(selected_server)
        
        # Start chat loop
        await client.chat_loop()
    except json.JSONDecodeError:
        print(f"Error: '{config_path}' is not a valid JSON file.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())


