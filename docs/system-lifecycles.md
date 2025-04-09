# System Lifecycles

This document outlines the core lifecycles in the Agentical system and their key interactions.
For a more detailed view of each lifecycle, including implementation details and advanced state transitions, see [System Lifecycles (Detailed)](system-lifecycles-detailed.md).

## Table of Contents
- [1. System Overview](#1-system-overview)
- [2. Provider Lifecycle](#2-provider-lifecycle)
- [3. Connection Lifecycle](#3-connection-lifecycle)
- [4. Tool Lifecycle](#4-tool-lifecycle)
- [5. Health Monitoring](#5-health-monitoring)

## 1. System Overview

The system consists of five core lifecycles that work together:

```mermaid
graph TD
    subgraph "System Lifecycles"
        PL[Provider Lifecycle]
        CL[Connection Lifecycle]
        TL[Tool Lifecycle]
        HM[Health Monitoring]
        RM[Resource Management]

        %% Core relationships
        PL --> CL
        PL --> TL
        CL <--> HM
        TL --> RM
        CL --> RM
    end

    %% Style definitions
    classDef default fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef focus fill:#4a148c,stroke:#4a148c,stroke-width:2px,color:#fff;
    classDef active fill:#1b5e20,stroke:#1b5e20,stroke-width:2px,color:#fff;

    class PL focus;
    class CL,TL active;
    class HM,RM default;
```

## 2. Provider Lifecycle

The Provider lifecycle manages the overall system:

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> Ready: Configuration loaded
    Ready --> Operating: Connection established
    Operating --> Ready: Connection closed
    Operating --> [*]: Cleanup requested
    Ready --> [*]: Cleanup requested

    %%{init: {'theme': 'dark', 'themeVariables': { 'mainBkg': '#1a1a1a', 'nodeBorder': '#333', 'lineColor': '#333', 'textColor': '#fff' }}}%%
```

Key States:
- **Initializing**: Loading configuration and setting up services
- **Ready**: System is configured and ready for connections
- **Operating**: Actively processing requests
- **Cleanup**: Graceful shutdown and resource release

## 3. Connection Lifecycle

Manages server connections:

```mermaid
stateDiagram-v2
    [*] --> Connecting
    Connecting --> Connected: Connection established
    Connected --> Reconnecting: Connection lost
    Reconnecting --> Connected: Reconnection successful
    Reconnecting --> [*]: Max retries exceeded
    Connected --> [*]: Cleanup

    %%{init: {'theme': 'dark', 'themeVariables': { 'mainBkg': '#1a1a1a', 'nodeBorder': '#333', 'lineColor': '#333', 'textColor': '#fff' }}}%%
```

Key States:
- **Connecting**: Establishing initial connection
- **Connected**: Active server connection
- **Reconnecting**: Handling connection issues
- **Cleanup**: Connection teardown

## 4. Tool Lifecycle

Handles tool registration and execution:

```mermaid
stateDiagram-v2
    [*] --> Registering
    Registering --> Ready: Tools registered
    Ready --> Executing: Tool requested
    Executing --> Ready: Execution complete
    Ready --> [*]: Cleanup

    %%{init: {'theme': 'dark', 'themeVariables': { 'mainBkg': '#1a1a1a', 'nodeBorder': '#333', 'lineColor': '#333', 'textColor': '#fff' }}}%%
```

Key States:
- **Registering**: Adding tools to registry
- **Ready**: Tools available for use
- **Executing**: Processing tool request
- **Cleanup**: Tool cleanup and deregistration

## 5. Health Monitoring

Monitors system health:

```mermaid
stateDiagram-v2
    [*] --> Monitoring
    Monitoring --> Healthy: Health check passed
    Monitoring --> Unhealthy: Health check failed
    Unhealthy --> Recovery: Auto-recovery
    Recovery --> Monitoring: Recovery complete
    Healthy --> Monitoring: Next check

    %%{init: {'theme': 'dark', 'themeVariables': { 'mainBkg': '#1a1a1a', 'nodeBorder': '#333', 'lineColor': '#333', 'textColor': '#fff' }}}%%
```

Key States:
- **Monitoring**: Regular health checks
- **Healthy**: System operating normally
- **Unhealthy**: Issues detected
- **Recovery**: Automatic recovery process