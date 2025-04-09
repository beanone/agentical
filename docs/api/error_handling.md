# Error Handling

## Table of Contents
- [Overview](#overview)
- [Exception Hierarchy](#exception-hierarchy)
- [Error Recovery Patterns](#error-recovery-patterns)
  - [Connection Recovery](#connection-recovery)
  - [Tool Execution Recovery](#tool-execution-recovery)
  - [LLM Processing Recovery](#llm-processing-recovery)
- [Error Handling Implementation](#error-handling-implementation)
  - [Connection Error Handling](#connection-error-handling)
  - [Tool Execution Error Handling](#tool-execution-error-handling)
  - [LLM Error Handling](#llm-error-handling)
- [Resource Management](#resource-management)
- [Logging Strategy](#logging-strategy)
- [Best Practices](#best-practices)

## Overview

This document covers error handling and recovery patterns in Agentical. It provides comprehensive guidance on handling various types of errors and implementing robust recovery mechanisms.

## Exception Hierarchy

```python
class AgenticalError(Exception):
    """Base exception for all Agentical errors."""
    pass

class ConfigurationError(AgenticalError):
    """Error in configuration loading or validation."""
    pass

class ConnectionError(AgenticalError):
    """Error in server connection or communication."""
    pass

class ToolExecutionError(AgenticalError):
    """Error during tool execution."""
    pass

class LLMError(AgenticalError):
    """Error in LLM processing."""
    pass
```

## Error Recovery Patterns

### Connection Recovery

The framework implements robust connection recovery with automatic retry and health monitoring:

```python
class MCPConnectionService:
    async def connect_with_recovery(self, server_name: str, config: ServerConfig):
        """Connect to a server with automatic recovery."""
        try:
            # Initial connection attempt
            session = await self._connect_with_retry(server_name, config)

            # Start health monitoring
            monitor_task = asyncio.create_task(
                self._monitor_health_with_recovery(session)
            )

            # Register cleanup
            self.exit_stack.push_async_callback(
                self._cleanup_monitoring,
                monitor_task
            )

            return session

        except ConnectionError as e:
            logger.error(
                "Connection failed, attempting recovery",
                extra={"server": server_name, "error": str(e)}
            )
            # Implement recovery logic
            await self._attempt_recovery(server_name, config)
```

### Tool Execution Recovery

Tool execution includes automatic retry and fallback mechanisms:

```python
async def execute_tool_with_recovery(
    tool: Tool,
    max_retries: int = 3,
    **kwargs
) -> CallToolResult:
    """Execute a tool with automatic recovery."""
    last_error = None

    for attempt in range(max_retries):
        try:
            # Validate and execute
            validate_parameters(tool, kwargs)
            result = await tool.execute(**kwargs)

            return CallToolResult(success=True, output=result)

        except ValidationError as e:
            # No recovery for validation errors
            return CallToolResult(
                success=False,
                error=f"Parameter validation failed: {e}"
            )

        except ToolExecutionError as e:
            last_error = e
            logger.warning(
                "Tool execution failed, retrying",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e)
                }
            )

            # Implement recovery delay
            await asyncio.sleep(1 * (attempt + 1))

    # All retries failed
    return CallToolResult(
        success=False,
        error=f"Tool execution failed after {max_retries} attempts: {last_error}"
    )
```

### LLM Processing Recovery

LLM processing includes fallback mechanisms and context preservation:

```python
class OpenAIBackend(LLMBackend):
    async def process_query_with_recovery(
        self,
        query: str,
        tools: list[Tool],
        execute_tool: callable,
        context: Context | None = None
    ) -> str:
        """Process query with automatic recovery."""
        try:
            return await self.process_query(query, tools, execute_tool, context)

        except LLMError as e:
            logger.error(
                "LLM processing failed, attempting recovery",
                extra={"error": str(e)}
            )

            # Implement recovery strategies
            if isinstance(e, RateLimitError):
                # Handle rate limiting
                await self._handle_rate_limit()
                return await self.process_query(query, tools, execute_tool, context)

            elif isinstance(e, ContextError):
                # Handle context issues
                return await self._process_with_fallback_context(
                    query, tools, execute_tool
                )

            else:
                # General recovery
                return await self._process_with_fallback_model(
                    query, tools, execute_tool
                )
```

## Error Handling Implementation

### Connection Error Handling

```python
class MCPConnectionService:
    async def connect(self, server_name: str, config: ServerConfig):
        try:
            session = await self._connect_with_retry(server_name, config)
            await self._start_health_monitoring(session)
            return session
        except Exception as e:
            logger.error(
                "Connection failed",
                extra={
                    "server": server_name,
                    "error": str(e)
                }
            )
            raise ConnectionError(f"Failed to connect to {server_name}: {e}")
```

### Tool Execution Error Handling

```python
async def execute_tool(tool: Tool, **kwargs) -> CallToolResult:
    try:
        # Validate parameters
        validate_parameters(tool, kwargs)

        # Execute tool
        result = await tool.execute(**kwargs)

        return CallToolResult(
            success=True,
            output=result
        )
    except ValidationError as e:
        return CallToolResult(
            success=False,
            error=f"Parameter validation failed: {e}"
        )
    except Exception as e:
        return CallToolResult(
            success=False,
            error=f"Tool execution failed: {e}"
        )
```

### LLM Error Handling

```python
class OpenAIBackend(LLMBackend):
    async def process_query(self, query: str, tools: list[Tool], execute_tool: callable):
        try:
            # Process with OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": query}],
                tools=self.convert_tools(tools)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI processing error: {e}")
            raise LLMError(f"Failed to process query: {e}")
```

## Resource Management

The framework uses `AsyncExitStack` for guaranteed resource cleanup:

```python
class MCPToolProvider:
    def __init__(self):
        self.exit_stack = AsyncExitStack()

    async def cleanup(self, server_name: str | None = None):
        """Clean up resources for a specific server or all servers."""
        try:
            if server_name:
                await self._cleanup_server(server_name)
            else:
                await self.exit_stack.aclose()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            raise
```

## Logging Strategy

The framework implements comprehensive logging:

```python
import logging
from agentical.utils.log_utils import sanitize_log_message

logger = logging.getLogger(__name__)

# Example logging pattern
try:
    result = await operation()
    logger.info(
        "Operation successful",
        extra={
            "operation": "name",
            "duration_ms": duration,
            "result": sanitize_log_message(str(result))
        }
    )
except Exception as e:
    logger.error(
        "Operation failed",
        extra={
            "operation": "name",
            "error": sanitize_log_message(str(e))
        },
        exc_info=True
    )
```

## Best Practices

1. **Exception Handling**
   - Use specific exception types
   - Provide clear error messages
   - Include context in exceptions
   - Proper exception propagation

2. **Resource Management**
   - Use context managers
   - Implement proper cleanup
   - Handle cleanup errors
   - Log cleanup operations

3. **Error Recovery**
   - Implement retry mechanisms
   - Use exponential backoff
   - Monitor system health
   - Graceful degradation
   - Preserve context during recovery
   - Implement fallback strategies

4. **Logging**
   - Structured logging format
   - Appropriate log levels
   - Sanitize sensitive data
   - Include relevant context
   - Log recovery attempts
   - Track recovery success rates