# Provider Architecture

## Table of Contents
- [Overview](#overview)
- [Core Components](#core-components)
  - [MCPToolProvider](#mcptoolprovider)
  - [Connection Management](#connection-management)
  - [Health Monitoring](#health-monitoring)
  - [Resource Management](#resource-management)
  - [Logging System](#logging-system)
- [Implementation Details](#implementation-details)
  - [Connection Service](#connection-service)
  - [Connection Manager](#connection-manager)
  - [Tool Registry](#tool-registry)

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

## Core Components

### MCPToolProvider

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

### Connection Management

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

### Health Monitoring

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

### Resource Management

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

### Logging System

The logging system provides comprehensive observability across the MCP Tool Provider:

```mermaid
graph TD
    subgraph Logging["Logging System"]
        Config[Logging Config]
        Handler[Log Handlers]
        Formatter[Log Formatters]
        Filter[Log Filters]

        Config --> Handler
        Handler --> Formatter
        Formatter --> Filter

        subgraph Output["Output Destinations"]
            File[File Handler]
            Console[Console Handler]
            Rotating[Rotating File Handler]
        end

        Handler --> File
        Handler --> Console
        Handler --> Rotating
    end

    classDef default fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef focus fill:#4a148c,stroke:#4a148c,stroke-width:2px,color:#fff;
    classDef active fill:#1b5e20,stroke:#1b5e20,stroke-width:2px,color:#fff;

    class Config,Handler,Formatter,Filter default;
    class File,Console,Rotating focus;
    class Output active;
```

Key features:
- Structured logging with timestamps and log levels
- Configurable log rotation
- Multiple output destinations (file, console)
- Log message sanitization
- Contextual logging with correlation IDs

Implementation details:
```python
def setup_logging(level: int | None = None, log_dir: str | None = None):
    """Configure logging for the MCP Tool Provider."""

    # Set up basic configuration
    logging.basicConfig(
        level=level or logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Add file handler if log directory specified
    if log_dir:
        file_handler = RotatingFileHandler(
            filename=os.path.join(log_dir, 'mcp.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        logging.getLogger().addHandler(file_handler)
```

Logging levels:
- DEBUG: Detailed information for debugging
- INFO: General operational information
- WARNING: Warning conditions
- ERROR: Error conditions
- CRITICAL: Critical conditions

## Implementation Details

### Connection Service

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

### Connection Manager

Handles low-level connection details:
- Connection establishment with retry
- Resource management

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

### Tool Registry

The tool registry manages the lifecycle of MCP tools:

```python
class ToolRegistry:
    """Manages the lifecycle of MCP tools."""

    def __init__(self):
        self.tools = {}

    def register_tool(self, tool: MCPTool):
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[MCPTool]:
        return self.tools.get(name)

    def validate_tool(self, tool: MCPTool) -> bool:
        # Implementation of tool validation logic
        return True

    def get_all_tools(self) -> Dict[str, MCPTool]:
        return self.tools
```

Key features:
- Tool registration and discovery
- Tool validation and schema management
- Tool lifecycle management
- Tool version tracking