# MCP Integration Architecture

## Overview

The MCP Integration architecture provides a flexible way to connect LLM providers with MCP-compatible tools while maintaining a clean separation of concerns.

## Core Components

```mermaid
graph TD
    subgraph Application_Layer["USER APPLICATION LAYER"]
        App[Your Application]
        Chat[Chat Client]
        App --> Chat
        note1[Choose how to integrate:<br/>1. Use Chat Client<br/>2. Use Provider directly]
        note1 -.-> App
    end

    subgraph Integration_Layer
        Provider[MCPToolProvider]
        Chat --> Provider
    end

    subgraph MCP_Layer
        MCP[MCPClient]
        Session[MCPSession]
        Config[MCPConfig]
        MCP --> Session
        MCP --> Config
        Provider --> MCP
    end

    subgraph LLM_Layer[LLM Layer - Choose Your Provider]
        LLMBackend["LLMBackend (Interface)"]
        Adapter[SchemaAdapter]
        
        Gemini[GeminiBackend]
        OpenAI[OpenAIBackend]
        Anthropic[AnthropicBackend]
        
        LLMBackend --> Gemini
        LLMBackend --> OpenAI
        LLMBackend --> Anthropic
        Adapter -.- Anthropic
        Provider --> LLMBackend
        
        note2[Different LLM implementations:<br/>- OpenAI GPT<br/>- Google Gemini<br/>- Anthropic Claude]
        note2 -.-> LLMBackend
    end

    subgraph Tool_Layer[Tool Layer - Add MCP Servers]
        Tools[MCP Tools]
        Session --> Tools
        GlamaLink["glama.ai/mcp/servers"]
        SmitheryLink["smithery.ai"]
        CustomTools["server/ (local implementations)"]
        note3[Implement your own MCP Servers<br/>or use from public repos]
        note3 -.-> GlamaLink
        note3 -.-> SmitheryLink
        note3 -.-> CustomTools
        GlamaLink --> Tools
        SmitheryLink --> Tools
        CustomTools --> Tools
    end

    classDef userLayer fill:#e6ffe6,stroke:#333,stroke-width:5px,color:#000,font-weight:900,font-size:18px
    classDef note fill:#ffd6d6,stroke:#662222,stroke-width:2px,color:#662222
    classDef implementation fill:#fffbe6,stroke:#333,stroke-width:2px,color:#664400,font-weight:bold
    classDef link fill:#fffbe6,stroke:#333,stroke-width:2px,color:#664400,font-weight:bold

    class Application_Layer userLayer
    class LLMBackend interface
    class note1 note
    class note2 note
    class note3 note
    class Gemini implementation
    class OpenAI implementation
    class Anthropic implementation
    class Adapter implementation
    class GlamaLink link
    class SmitheryLink link
    class CustomTools link

    click GlamaLink "https://glama.ai/mcp/servers" _blank
    click SmitheryLink "https://smithery.ai" _blank
    click CustomTools "https://github.com/beanone/agentical/tree/main/server" _blank
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