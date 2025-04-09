# System Architecture and Lifecycles

1. Core Components

1.1 MCPToolProvider
- Main facade class that integrates LLMs with MCP tools
- Manages server connections, tool discovery, and query processing
- Handles connection health monitoring and resource cleanup
- Key lifecycle methods:
    - initialize(): Loads server configurations
    - mcp_connect(): Connects to a specific server
    - mcp_connect_all(): Connects to all available servers
    - process_query(): Processes user queries using LLM and tools
    - cleanup(): Cleans up resources

1.2 LLM Backend
- Abstract base class (LLMBackend) defining the interface for LLM implementations
- Current implementations:
    - OpenAIBackend: OpenAI GPT integration
    - GeminiBackend: Google Gemini integration
    - AnthropicBackend: Anthropic Claude integration
- Key lifecycle methods:
    - process_query(): Processes queries using the LLM
    - convert_tools(): Converts MCP tools to LLM-specific format

1.3 MCP Connection Management
- MCPConnectionService: Unified service for managing server connections
- MCPConnectionManager: Handles connection establishment and maintenance
- Features:
    - Automatic retry with exponential backoff
    - Health monitoring
    - Resource cleanup
    - Support for both WebSocket and stdio connections

1.4 Tool Registry
- ToolRegistry: Manages registration and lookup of MCP tools
- Features:
    - Server-based tool organization
    - Tool discovery and lookup
    - Cleanup and removal of tools

1.5 Configuration Management
- MCPConfigProvider: Protocol for configuration loading
- Implementations:
    - FileBasedMCPConfigProvider: Loads from JSON files
    - DictBasedMCPConfigProvider: Loads from dictionaries
- Handles validation using Pydantic models

2. Server Lifecycle

2.1 Server Types
- Calculator Server: Safe mathematical expression evaluation
- Weather Server: Weather information retrieval
- File System Server: File operations
- Terminal Server: Command execution
- Memory Server: State management

2.2 Server Implementation
- Each server implements the MCP protocol using FastMCP
- Tools are registered using the @mcp.tool() decorator
- Servers run in stdio mode for communication

3. System Lifecycle

3.1 Initialization
- Load environment variables
- Configure logging
- Initialize LLM backend
- Load server configurations
- Initialize MCPToolProvider

3.2 Connection Phase
- Connect to servers (single or all)
- Register available tools
- Start health monitoring
- Initialize conversation context

3.3 Operation Phase
- Process user queries
- LLM determines tool usage
- Execute tools through MCP
- Format and return responses
- Maintain conversation context

3.4 Cleanup Phase
- Stop health monitoring
- Disconnect from servers
- Clean up resources
- Close connections

4. Error Handling and Recovery

4.1 Connection Management
- Automatic retry with exponential backoff
- Health monitoring with heartbeat checks
- Automatic reconnection on failure
- Graceful cleanup of failed connections

4.2 Error Handling
- Comprehensive error handling at all levels
- Detailed error messages and logging
- Proper resource cleanup on errors
- Error propagation with context

5. Security Features

5.1 Input Validation
- Pydantic models for configuration validation
- Input sanitization for tools
- Safe expression evaluation in calculator
- Environment variable validation

5.2 Logging Security
- Sensitive data redaction
- Structured logging
- Log rotation and management
- Different log levels for different components

6. Monitoring and Maintenance

6.1 Health Monitoring
- Heartbeat checks
- Connection state tracking
- Failure detection and recovery
- Resource usage monitoring

6.2 Logging
- Comprehensive logging at all levels
- Structured log messages
- Performance metrics
- Error tracking and debugging

7. Configuration Management

7.1 Server Configuration
- JSON-based configuration
- Environment variable support
- Validation and error checking
- Flexible configuration providers

7.2 Tool Configuration
- Tool registration and discovery
- Server-specific tool management
- Tool format conversion
- Tool cleanup and removal
