# MCP Integration Architecture

## Overview

The MCP Integration architecture provides a flexible way to connect LLM providers with MCP-compatible tools while maintaining a clean separation of concerns.

## Core Components

```mermaid
graph TB
    subgraph "MCP Layer"
        MCP[MCPClient]
        Session[MCPSession]
        Config[MCPConfig]
        MCP --> Session
        MCP --> Config
    end

    subgraph "LLM Layer"
        LLMBackend[LLMBackend]
        Gemini[GeminiBackend]
        OpenAI[OpenAIBackend]
        Anthropic[AnthropicBackend]
        LLMBackend --> Gemini
        LLMBackend --> OpenAI
        LLMBackend --> Anthropic
    end

    subgraph "Integration Layer"
        Provider[MCPToolProvider]
        Provider --> MCP
        Provider --> LLMBackend
    end

    subgraph "Tool Layer"
        Tools[MCP Tools]
        Session --> Tools
    end
```

## Component Interactions

```mermaid
sequenceDiagram
    participant Client as MCPToolProvider
    participant LLM as LLMBackend
    participant MCP as MCPClient
    participant Session as MCPSession
    participant Tools as MCP Tools

    Client->>MCP: Initialize with config
    MCP->>Session: Create session
    Session->>Tools: Discover available tools
    Client->>LLM: Initialize backend
    
    Note over Client,Tools: Query Processing Flow
    Client->>LLM: Process query
    LLM->>Session: Request tool execution
    Session->>Tools: Execute tool
    Tools-->>Session: Tool result
    Session-->>LLM: Tool response
    LLM-->>Client: Final response
```

## Configuration Structure

```mermaid
classDiagram
    class MCPConfig {
        +Dict~str,MCPServerConfig~ servers
        +str default_server
    }
    
    class MCPServerConfig {
        +str command
        +List~str~ args
        +Dict~str,str~ env
        +str working_dir
    }
    
    class LLMConfig {
        +str provider
        +Dict~str,any~ config
    }
    
    MCPConfig --> MCPServerConfig
```

## Key Abstractions

### MCPSession
- Manages connection to MCP server
- Handles tool discovery and execution
- Provides resource cleanup

### LLMBackend
- Abstract interface for LLM providers
- Handles message processing
- Manages tool integration with LLM

### MCPToolProvider
- Main facade for the integration
- Coordinates between LLM and MCP
- Manages configuration and lifecycle

## Configuration Example

```json
{
    "mcp": {
        "servers": {
            "terminal-server": {
                "command": "python",
                "args": ["server/terminal_server.py"]
            },
            "knowledge-graph": {
                "command": "npx",
                "args": ["-y", "@beanone/knowledge-graph"],
                "env": {
                    "MEMORY_FILE_PATH": "data/memory.json"
                }
            }
        },
        "default_server": "terminal-server"
    },
    "llm": {
        "provider": "gemini",
        "config": {
            "api_key": "YOUR_API_KEY",
            "model": "gemini-pro"
        }
    }
}
```

## Design Decisions

1. **Separation of Concerns**
   - MCP layer handles tool communication
   - LLM layer handles message processing
   - Integration layer coordinates between them

2. **Flexibility**
   - Pluggable LLM backends
   - Multiple MCP server support
   - Configurable tool integration

3. **Resource Management**
   - Proper session cleanup
   - Async context management
   - Error handling

4. **Extensibility**
   - Easy to add new LLM backends
   - Support for multiple tools
   - Configurable behaviors

## Next Steps

1. [ ] Implement core abstractions
2. [ ] Add provider implementations
3. [ ] Create configuration management
4. [ ] Add error handling
5. [ ] Write tests 