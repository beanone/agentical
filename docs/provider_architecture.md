# Provider Architecture

## Overview

The MCP (Machine Control Protocol) Tool Provider system in Agentical is designed to integrate LLM backends with external tools through a robust, fault-tolerant connection management system. The architecture follows a layered approach with clear separation of concerns.

```mermaid
graph TD
    subgraph "MCP Tool Provider"
        subgraph "API Layer"
            LLM[LLM Backend]
            Config[Config Provider]
        end

        subgraph "MCP Integration"
            Provider[MCP Tool Provider]
            Tools[Tool Registry]
        end

        subgraph "Connection Layer"
            Conn[Connection Service]
            Health[Health Monitor]
        end

        subgraph "Server Layer"
            Server1[MCP Server 1]
            Server2[MCP Server 2]
        end

        LLM --> Provider
        Config --> Provider
        Provider --> Tools
        Provider --> Conn
        Conn --> Health
        Conn --> Server1
        Conn --> Server2
    end

    classDef default fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef focus fill:#4a148c,stroke:#4a148c,stroke-width:2px,color:#fff;
    classDef active fill:#1b5e20,stroke:#1b5e20,stroke-width:2px,color:#fff;

    class LLM,Config,Server1,Server2 default;
    class Provider,Tools focus;
    class Conn,Health active;
```

## Connection Management

The connection system manages server connections, health monitoring, and resource lifecycle:

```mermaid
graph LR
    subgraph "Connection Management"
        direction TB
        Provider[MCP Provider]
        
        subgraph "Connection Service"
            Connect[Connect]
            Monitor[Monitor]
            Cleanup[Cleanup]
        end
        
        subgraph "Connection Manager"
            Retry[Retry Logic]
            Resources[Resource Mgmt]
            State[State Tracking]
        end
        
        Provider --> Connect
        Connect --> Retry
        Monitor --> State
        Cleanup --> Resources
    end

    classDef default fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef focus fill:#1b5e20,stroke:#1b5e20,stroke-width:2px,color:#fff;
    classDef active fill:#e65100,stroke:#e65100,stroke-width:2px,color:#fff;

    class Provider default;
    class Connect,Monitor,Cleanup focus;
    class Retry,Resources,State active;
```

## Health Monitoring

The health monitoring system ensures reliable server connections through regular heartbeat checks and automatic recovery:

```mermaid
stateDiagram-v2
    direction LR
    
    [*] --> Healthy: Initialize
    Healthy --> Unhealthy: Miss Heartbeat
    Unhealthy --> Reconnecting: Max Misses (2)
    Reconnecting --> Healthy: Success
    Reconnecting --> Failed: Max Retries (3)
    Failed --> [*]: Cleanup
    
    note right of Healthy
        Heartbeat Check
        Every 30 seconds
        (HEARTBEAT_INTERVAL)
    end note
    
    note right of Unhealthy
        Missed heartbeat
        Retries: 0/2
        (MAX_HEARTBEAT_MISS)
    end note
    
    note right of Reconnecting
        Exponential backoff
        Base delay: 1.0s
        (BASE_DELAY)
    end note
```

Features:
- Regular heartbeat checks (every 30 seconds)
- Configurable miss tolerance (default: 2)
- Automatic reconnection with exponential backoff
- Maximum retry attempts (default: 3)
- Proper cleanup on failure

## Resource Management

```mermaid
graph TD
    subgraph Resources["Resource Management"]
        Stack[AsyncExitStack]
        Sessions[Active Sessions]
        Transports[IO Transports]
        
        Stack --> |Manages|Sessions
        Stack --> |Manages|Transports
        
        subgraph Cleanup["Cleanup Handlers"]
            Server[Server Cleanup]
            Connection[Connection Cleanup]
            Transport[Transport Cleanup]
        end
        
        Sessions --> Server
        Transports --> Transport
        Stack --> Connection
    end
    
    classDef default fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef focus fill:#4a148c,stroke:#4a148c,stroke-width:2px,color:#fff;
    classDef active fill:#1b5e20,stroke:#1b5e20,stroke-width:2px,color:#fff;

    class Sessions,Transports,Server,Connection,Transport default;
    class Stack focus;
    class Cleanup active;
```

Key features:
- Proper async resource management
- Ordered cleanup
- Connection state tracking
- Transport management
- Session lifecycle management

## Core Components

### 1. MCPToolProvider

The main facade that integrates LLMs with MCP tools. Key responsibilities:

```python
class MCPToolProvider:
    """Main facade for integrating LLMs with MCP tools."""
    
    def __init__(
        self, 
        llm_backend: LLMBackend,
        config_provider: Optional[MCPConfigProvider] = None,
        server_configs: Optional[Dict[str, ServerConfig]] = None
    ):
        self.exit_stack = AsyncExitStack()
        self.connection_service = MCPConnectionService(self.exit_stack)
        self.tool_registry = ToolRegistry()
        self.llm_backend = llm_backend
```

Key features:
- Server connection management
- Tool discovery and registration
- Query processing with LLM integration
- Resource cleanup and management

### 2. Connection Management

```mermaid
sequenceDiagram
    participant App as Application
    participant Provider as MCPToolProvider
    participant Service as ConnectionService
    participant Manager as ConnectionManager
    participant Health as HealthMonitor
    participant Server as MCP Server
    
    App->>Provider: mcp_connect(server_name)
    activate Provider
    Provider->>Service: connect(server_name, config)
    activate Service
    Service->>Manager: connect_with_retry()
    activate Manager
    Manager->>Server: establish_connection()
    Server-->>Manager: connection_established
    Manager-->>Service: session
    deactivate Manager
    Service->>Health: start_monitoring(server)
    Service-->>Provider: session
    deactivate Service
    Provider->>Server: list_tools()
    Server-->>Provider: tools
    Provider->>Provider: register_tools()
    Provider-->>App: connection_complete
    deactivate Provider
```

#### Connection Service (`MCPConnectionService`)

Provides high-level connection management with:
- Health monitoring
- Automatic reconnection
- Resource cleanup
- Session management

```python
class MCPConnectionService(ServerReconnector, ServerCleanupHandler):
    """Unified service for managing MCP server connections and health."""
    
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_HEARTBEAT_MISS = 2   # attempts before reconnection
```

Key responsibilities:
- Maintains server health status
- Schedules regular heartbeat checks
- Triggers reconnection on failures
- Manages cleanup on permanent failures

#### Connection Manager (`MCPConnectionManager`)

Handles low-level connection details:
- Connection establishment with retry
- Resource management
- Connection state tracking
- Error handling

```python
class MCPConnectionManager:
    """Manages connections to MCP servers."""
    
    MAX_RETRIES = 3
    BASE_DELAY = 1.0
```

### 3. Health Monitoring

The health monitoring system is implemented in the `MCPConnectionService` class:

```python
class MCPConnectionService(ServerReconnector, ServerCleanupHandler):
    """Unified service for managing MCP server connections and health."""
    
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_HEARTBEAT_MISS = 2   # attempts before reconnection
```

Key responsibilities:
- Maintains server health status
- Schedules regular heartbeat checks
- Triggers reconnection on failures
- Manages cleanup on permanent failures

### 4. Tool Registry

Manages tool discovery and registration:
- Tool metadata storage
- Server-tool mapping
- Tool validation
- Access control

## Error Handling and Recovery

```mermaid
flowchart TD
    subgraph ErrorHandling["Error Handling System"]
        Detection[Error Detection]
        Classification[Error Classification]
        Recovery[Recovery Strategy]
        
        Detection --> Classification
        Classification --> Recovery
        
        subgraph Strategies["Recovery Strategies"]
            Retry[Retry with Backoff]
            Reconnect[Reconnection]
            Cleanup[Resource Cleanup]
            
            Recovery --> Retry
            Recovery --> Reconnect
            Recovery --> Cleanup
        end
    end
    
    classDef default fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef focus fill:#4a148c,stroke:#4a148c,stroke-width:2px,color:#fff;
    classDef active fill:#1b5e20,stroke:#1b5e20,stroke-width:2px,color:#fff;

    class Detection,Classification,Recovery focus;
    class Retry,Reconnect,Cleanup active;
```

Features:
- Exponential backoff retry
- Automatic reconnection
- Resource cleanup
- Error categorization
- Comprehensive logging

## Resource Management

```mermaid
graph TD
    subgraph Resources["Resource Management"]
        Stack[AsyncExitStack]
        Sessions[Active Sessions]
        Transports[IO Transports]
        
        Stack --> |Manages|Sessions
        Stack --> |Manages|Transports
        
        subgraph Cleanup["Cleanup Handlers"]
            Server[Server Cleanup]
            Connection[Connection Cleanup]
            Transport[Transport Cleanup]
        end
        
        Sessions --> Server
        Transports --> Transport
        Stack --> Connection
    end
    
    classDef default fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef focus fill:#4a148c,stroke:#4a148c,stroke-width:2px,color:#fff;
    classDef active fill:#1b5e20,stroke:#1b5e20,stroke-width:2px,color:#fff;

    class Sessions,Transports,Server,Connection,Transport default;
    class Stack focus;
    class Cleanup active;
```

Key features:
- Proper async resource management
- Ordered cleanup
- Connection state tracking
- Transport management
- Session lifecycle management 