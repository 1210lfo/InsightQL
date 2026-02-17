"""
MCP Client for Supabase
Handles HTTP communication with Supabase MCP endpoint.
"""

import json
import logging
import time
from functools import lru_cache
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_config

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPAuthError(MCPClientError):
    """Authentication error with MCP server."""
    pass


class MCPTimeoutError(MCPClientError):
    """Timeout communicating with MCP server."""
    pass


class MCPClient:
    """
    HTTP Client for Supabase MCP Server.
    
    Supports both the hosted MCP server (mcp.supabase.com) and 
    custom Edge Functions.
    """
    
    def __init__(
        self,
        endpoint: str | None = None,
        access_token: str | None = None,
        project_ref: str | None = None,
        timeout_ms: int | None = None,
    ):
        """
        Initialize MCP Client.
        
        Args:
            endpoint: MCP server endpoint URL
            access_token: Supabase Personal Access Token
            project_ref: Supabase project reference
            timeout_ms: Request timeout in milliseconds
        """
        config = get_config()
        
        self.endpoint = endpoint or config.mcp.endpoint
        self.access_token = access_token or config.supabase.access_token
        self.project_ref = project_ref or config.supabase.project_ref
        self.timeout = (timeout_ms or config.mcp.timeout_ms) / 1000  # Convert to seconds
        
        # Build URL with project ref if provided
        if self.project_ref and "?" not in self.endpoint:
            self.endpoint = f"{self.endpoint}?project_ref={self.project_ref}"
        
        self._client: httpx.AsyncClient | None = None
    
    @property
    def headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "insightql-agent/0.1.0",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self.headers,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def discovery(self) -> dict[str, Any]:
        """
        Discover available tools from the MCP server.
        
        Returns:
            Server capabilities and available tools
        """
        client = await self._get_client()
        try:
            response = await client.get(self.endpoint)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise MCPAuthError("Authentication failed. Check your access token.") from e
            raise MCPClientError(f"MCP discovery failed: {e}") from e
        except httpx.TimeoutException as e:
            raise MCPTimeoutError("MCP discovery timed out") from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call an MCP tool using JSON-RPC 2.0 format.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool response
        """
        client = await self._get_client()
        
        # JSON-RPC 2.0 format for MCP
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            }
        }
        
        start_time = time.time()
        try:
            logger.info(f"Calling MCP tool: {tool_name}")
            logger.debug(f"Arguments: {json.dumps(arguments, indent=2)}")
            
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            
            result = response.json()
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Extract content from JSON-RPC response
            if "result" in result:
                result = result["result"]
            
            logger.info(f"MCP tool {tool_name} completed in {elapsed_ms}ms")
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise MCPAuthError("Authentication failed. Check your access token.") from e
            if e.response.status_code == 404:
                raise MCPClientError(f"Tool '{tool_name}' not found") from e
            raise MCPClientError(f"MCP tool call failed: {e}") from e
        except httpx.TimeoutException as e:
            raise MCPTimeoutError(f"MCP tool '{tool_name}' timed out") from e


# Singleton instance
_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def cleanup_mcp_client():
    """Cleanup the global MCP client."""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None
