"""
MCP Client Module

Provides an async client for communicating with an MCP (Model Context Protocol) server
via HTTP transport. Handles connection lifecycle, tool discovery/execution, resource access,
and prompt retrieval. Acts as a bridge between the agent and MCP server.

RESPONSIBILITIES:
- Connection management: HTTP streams, client session setup/teardown
- Tool discovery & schema transformation: MCP tool format → DIAL format for LLM
- Tool execution: Parse arguments, call MCP tools, handle TextContent/BlobContent responses
- Resource management: Discover and retrieve binary/text resources from server
- Prompt management: Discover and fetch MCP prompts (LLM guidance)
- Error handling: Graceful fallbacks for optional MCP features (resources, prompts)
"""
from typing import Optional, Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent, GetPromptResult, ReadResourceResult, Resource, TextResourceContents, BlobResourceContents, Prompt
from pydantic import AnyUrl


class MCPClient:
    """
    Async HTTP client for MCP (Model Context Protocol) server.
    
    Handles bidirectional communication with an MCP server, discovery of tools/resources/prompts,
    and tool execution. Implements async context manager protocol for safe resource cleanup.
    
    Attributes:
        mcp_server_url (str): Base URL of the MCP server (e.g., http://localhost:8005/mcp)
        session (Optional[ClientSession]): Active MCP session; None until __aenter__ is called
        _streams_context: Underlying HTTP stream context manager
        _session_context: ClientSession context manager for cleanup
    """

    def __init__(self, mcp_server_url: str) -> None:
        """
        Initialize MCP client (does not connect; use 'async with' to connect).
        
        Args:
            mcp_server_url: URL of MCP server endpoint (e.g., 'http://localhost:8005/mcp')
        """
        self.mcp_server_url = mcp_server_url
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None

    async def __aenter__(self):
        """
        Establish connection to MCP server via HTTP streams.
        
        FLOW:
        1. Create HTTP stream transport (bidirectional)
        2. Wrap in ClientSession for MCP protocol handling
        3. Initialize session (exchange capabilities with server)
        4. Log server capabilities for debugging
        
        Returns:
            self: Returns instance for use in 'async with' statement
            
        Raises:
            ConnectionError: If MCP server is unreachable
            RuntimeError: If initialization handshake fails
        """
        print(f"[MCPClient] Connecting to MCP server at {self.mcp_server_url} ...")
        # Create HTTP stream transport (handles bidirectional communication)
        self._streams_context = streamablehttp_client(self.mcp_server_url)
        read_stream, write_stream, _ = await self._streams_context.__aenter__()
        # Wrap streams in MCP ClientSession for protocol handling
        self._session_context = ClientSession(read_stream, write_stream)
        self.session = await self._session_context.__aenter__()
        # Exchange capabilities with server (validates protocol version, etc.)
        capabilities = await self.session.initialize()
        print(f"[MCPClient] Connected. Capabilities: {capabilities}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up MCP session and HTTP streams.
        
        Ensures orderly shutdown even if exceptions occurred during use.
        Logs cleanup progress for debugging.
        """
        print("[MCPClient] Shutting down MCP client...")
        if self.session and self._session_context:

            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
            print("[MCPClient] Session context closed.")
        if self._streams_context:
            await self._streams_context.__aexit__(exc_type, exc_val, exc_tb)
            print("[MCPClient] Streams context closed.")

    async def get_tools(self) -> list[dict[str, Any]]:
        """
        Discover all tools available on MCP server and transform to DIAL format.
        
        FLOW:
        1. Query MCP server for available tools (includes name, description, input schema)
        2. Transform each tool from MCP format to DIAL format (OpenAI function calling)
        3. DIAL format adds "type": "function" wrapper for LLM consumption
        
        Returns:
            List of tool definitions in DIAL format (dict with 'type' and 'function' keys)
            
        Raises:
            RuntimeError: If session not initialized
        """
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        tools = await self.session.list_tools()
        print(f"[MCPClient] Discovered {len(tools)} tools.")
        # Transform MCP tool format to DIAL (OpenAI function calling) format
        dial_tools = []
        for tool in tools:
            dial_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema  # Already in JSON Schema format
                }
            })
        return dial_tools

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """
        Execute a tool on the MCP server and return result.
        
        FLOW:
        1. Call MCP server with tool name and arguments
        2. Extract first content from response (tools return single content block)
        3. If TextContent: extract and return plain text
           Else: return raw content (could be binary/structured)
        4. Print tool output for debugging
        
        Args:
            tool_name: Name of tool to execute (e.g., 'get_user_by_id')
            tool_args: Dictionary of arguments (JSON-deserializable)
            
        Returns:
            str or bytes: Tool result (usually string for text tools, bytes for binary)
            
        Raises:
            RuntimeError: If session not initialized
            ToolCallException: If MCP server returns error for tool call
        """
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        # Call tool and get response (CallToolResult is list of content blocks)
        tool_result: CallToolResult = await self.session.call_tool(tool_name, tool_args)
        content = tool_result[0]
        print(f"    ⚙️: {content}\n")
        # Extract text from TextContent wrapper, or return raw content
        if isinstance(content, TextContent):
            return content.text
        else:
            return content

    async def get_resources(self) -> list[Resource]:
        """
        Discover all resources available on MCP server.
        
        Resources are static assets (e.g., diagrams, documentation) that servers expose.
        Not all MCP servers provide resources; this method gracefully returns empty list on error.
        
        Returns:
            List of Resource objects with uri and description; empty list if none available
        """
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        try:
            # Attempt to discover resources (optional MCP feature)
            resources = await self.session.list_resources()
            print(f"[MCPClient] Discovered {len(resources)} resources.")
            return resources
        except Exception as e:
            # Graceful fallback: not all servers have resources
            print(f"[MCPClient] No resources or error: {e}")
            return []

    async def get_resource(self, uri: AnyUrl) -> str:
        """
        Retrieve content of a specific resource by URI.
        
        Args:
            uri: Resource URI (e.g., 'users-management://flow-diagram')
            
        Returns:
            str or bytes: Resource content (text or binary blob)
            
        Notes:
            - TextResourceContents returns string
            - BlobResourceContents returns bytes (e.g., image PNG data)
        """
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        result: ReadResourceResult = await self.session.read_resource(uri)
        content = result.contents[0]
        if isinstance(content, TextResourceContents):
            print(f"[MCPClient] Resource {uri} is text.")
            return content.text
        elif isinstance(content, BlobResourceContents):
            print(f"[MCPClient] Resource {uri} is binary (blob), {len(content.blob)} bytes.")
            return content.blob
        else:
            print(f"[MCPClient] Unknown resource content type for {uri}.")
            return content

    async def get_prompts(self) -> list[Prompt]:
        """
        Discover all prompts available on MCP server.
        
        Prompts are domain-specific guidance texts (e.g., best practices for search, profile creation).
        Not all MCP servers provide prompts; this method gracefully returns empty list on error.
        
        Returns:
            List of Prompt objects with name and description; empty list if none available
        """
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        try:
            # Attempt to discover prompts (optional MCP feature)
            prompts = await self.session.list_prompts()
            print(f"[MCPClient] Discovered {len(prompts)} prompts.")
            return prompts
        except Exception as e:
            # Graceful fallback: not all servers have prompts
            print(f"[MCPClient] No prompts or error: {e}")
            return []

    async def get_prompt(self, name: str) -> str:
        """
        Retrieve full content of a specific prompt by name.
        
        Prompts can contain multiple message blocks (e.g., system, user, assistant).
        This method concatenates all text content into a single string.
        
        Args:
            name: Prompt name (e.g., 'search_helper_prompt')
            
        Returns:
            str: Concatenated text content of all message blocks in prompt
        """
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        prompt_result: GetPromptResult = await self.session.get_prompt(name)
        # Concatenate all message content blocks into single string
        combined_content = ""
        for message in prompt_result.messages:
            if hasattr(message, 'content'):
                # Handle TextContent objects (structured content blocks)
                if isinstance(message.content, TextContent):
                    combined_content += message.content.text + "\n"
                # Handle plain string content
                elif isinstance(message.content, str):
                    combined_content += message.content + "\n"
        print(f"[MCPClient] Prompt '{name}' content length: {len(combined_content)}")
        return combined_content
