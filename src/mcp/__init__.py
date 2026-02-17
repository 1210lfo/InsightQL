"""
MCP Tools Module
Implements the 4 MCP tools for Supabase analytics.
"""

from .client import MCPClient
from .tools import (
    get_schema_metadata,
    get_metric_definition,
    validate_query_plan,
    execute_analytics_query,
)

__all__ = [
    "MCPClient",
    "get_schema_metadata",
    "get_metric_definition",
    "validate_query_plan",
    "execute_analytics_query",
]
