"""
Observability Module - LangSmith Integration
Tracing setup for InsightQL agent using LangSmith.
"""

import logging
import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable

from src.config import get_config

logger = logging.getLogger(__name__)

# Track if tracing is set up
_tracing_initialized = False


def setup_tracing() -> None:
    """
    Setup LangSmith tracing via environment variables.
    
    LangSmith reads from environment variables:
    - LANGSMITH_TRACING=true
    - LANGSMITH_API_KEY=lsv2_pt_xxx
    - LANGSMITH_PROJECT=InsightQL
    - LANGSMITH_ENDPOINT=https://api.smith.langchain.com
    
    LangGraph automatically integrates with LangSmith when these are set.
    """
    global _tracing_initialized
    
    if _tracing_initialized:
        return
    
    config = get_config()
    
    if config.langsmith.enabled and config.langsmith.api_key:
        # Set environment variables for LangSmith
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = config.langsmith.api_key
        os.environ["LANGSMITH_PROJECT"] = config.langsmith.project
        os.environ["LANGSMITH_ENDPOINT"] = config.langsmith.endpoint
        
        logger.info(f"LangSmith tracing enabled for project: {config.langsmith.project}")
    else:
        os.environ["LANGSMITH_TRACING"] = "false"
        logger.debug("LangSmith tracing disabled")
    
    _tracing_initialized = True


def trace_node(node_name: str):
    """
    Decorator to add metadata to LangGraph node execution.
    LangSmith automatically traces LangGraph nodes.
    
    Args:
        node_name: Name of the node for logging
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            logger.debug(f"Entering node: {node_name}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Exiting node: {node_name}")
                return result
            except Exception as e:
                logger.error(f"Error in node {node_name}: {e}")
                raise
        return wrapper
    return decorator


def trace_mcp_tool(tool_name: str):
    """
    Decorator to trace MCP tool calls.
    
    Args:
        tool_name: Name of the MCP tool for logging
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            logger.debug(f"Calling MCP tool: {tool_name}")
            try:
                result = await func(*args, **kwargs)
                if isinstance(result, dict):
                    row_count = result.get("row_count", "N/A")
                    exec_time = result.get("execution_time_ms", "N/A")
                    logger.debug(f"MCP {tool_name} returned {row_count} rows in {exec_time}ms")
                return result
            except Exception as e:
                logger.error(f"MCP tool {tool_name} failed: {e}")
                raise
        return wrapper
    return decorator


class TracingContext:
    """
    Context manager for tracing a complete agent run.
    With LangSmith, tracing is automatic via LangGraph.
    """
    
    def __init__(self, query: str, user_id: str = "anonymous"):
        self.query = query
        self.user_id = user_id
        self._metadata: dict[str, Any] = {}
    
    def __enter__(self):
        logger.debug(f"Starting agent run for user {self.user_id}: {self.query[:50]}...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(f"Agent run failed: {exc_val}")
        else:
            logger.debug("Agent run completed successfully")
        return False
    
    def add_attribute(self, key: str, value: Any) -> None:
        """Add metadata attribute for logging."""
        self._metadata[key] = value
        logger.debug(f"Trace attribute: {key}={value}")


def get_tracer():
    """
    Compatibility function - returns None since LangSmith handles tracing.
    """
    return None
