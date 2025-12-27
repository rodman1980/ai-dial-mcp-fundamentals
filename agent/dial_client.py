"""
DIAL Client Module

Orchestrates AI model interactions via Azure OpenAI DIAL API. Handles streaming responses,
tool call execution via MCP client, and recursive agent loop until no more tool calls remain.

RESPONSIBILITIES:
- Stream LLM responses from Azure OpenAI with tool calling enabled
- Collect tool call deltas from streaming chunks and reconstruct complete calls
- Execute tool calls via MCPClient and collect results
- Maintain recursive agent loop: LLM response → tool execution → new LLM response
- Provide user-friendly feedback with emojis and formatted output
"""
import json
from collections import defaultdict
from typing import Any

from openai import AsyncAzureOpenAI

from agent.models.message import Message, Role
from agent.mcp_client import MCPClient


class DialClient:
    """
    Azure OpenAI (DIAL API) client for agentic interactions with tool calling.
    
    Manages streaming responses, tool invocation, and recursive completion until
    the LLM stops requesting tool calls. Integrates tightly with MCPClient for
    executing MCP server tools.
    
    Attributes:
        tools: List of tool definitions in DIAL format (dict with 'type' and 'function')
        mcp_client: MCPClient instance for executing discovered tools
        openai: AsyncAzureOpenAI client for API communication
    """

    def __init__(self, api_key: str, endpoint: str, tools: list[dict[str, Any]], mcp_client: MCPClient):
        """
        Initialize DIAL client.
        
        Args:
            api_key: Azure OpenAI API key (from DIAL_API_KEY environment variable)
            endpoint: Azure OpenAI endpoint URL
            tools: List of tool definitions in DIAL format (from MCPClient.get_tools())
            mcp_client: Connected MCPClient instance for tool execution
        """
        self.tools = tools
        self.mcp_client = mcp_client
        self.openai = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2025-01-01-preview"
        )

    def _collect_tool_calls(self, tool_deltas):
        """
        Reconstruct complete tool calls from streaming deltas.
        
        When LLM streams tool calls (tool_call_start → function_name → arguments deltas → end),
        we accumulate them here. Uses defaultdict to handle out-of-order deltas gracefully.
        
        Args:
            tool_deltas: List of delta objects from stream chunks (has .index, .id, .function, .type)
            
        Returns:
            List of complete tool call dicts with 'id', 'function' (name + arguments), and 'type'
        """
        tool_dict = defaultdict(lambda: {"id": None, "function": {"arguments": "", "name": None}, "type": None})

        for delta in tool_deltas:
            idx = delta.index
            # Accumulate tool call fields as they arrive in stream
            if delta.id: tool_dict[idx]["id"] = delta.id
            if delta.function.name: tool_dict[idx]["function"]["name"] = delta.function.name
            # Arguments arrive in chunks - concatenate them
            if delta.function.arguments: tool_dict[idx]["function"]["arguments"] += delta.function.arguments
            if delta.type: tool_dict[idx]["type"] = delta.type

        return list(tool_dict.values())

    async def _stream_response(self, messages: list[Message]) -> Message:
        """
        Stream LLM response from Azure OpenAI and collect tool calls.
        
        FLOW:
        1. Send messages + tools to OpenAI with streaming enabled
        2. Iterate stream chunks, accumulating content and tool deltas
        3. Print streaming content in real-time (emoji prefix for user feedback)
        4. Return AI message with content and reconstructed tool calls
        
        Returns:
            Message with role=AI, content (may be empty if only tool calls), tool_calls list
        """
        stream = await self.openai.chat.completions.create(
            **{
                "model": "gpt-4o",
                "messages": [msg.to_dict() for msg in messages],
                "tools": self.tools,
                "temperature": 0.0,
                "stream": True
            }
        )

        content = ""
        tool_deltas = []

        print("🤖: ", end="", flush=True)

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # Stream content
            if delta.content:
                print(delta.content, end="", flush=True)
                content += delta.content

            if delta.tool_calls:
                tool_deltas.extend(delta.tool_calls)

        print()
        return Message(
            role=Role.AI,
            content=content,
            tool_calls=self._collect_tool_calls(tool_deltas) if tool_deltas else []
        )

    async def get_completion(self, messages: list[Message]) -> Message:
        """
        Get LLM completion with automatic tool call execution.
        
        Implements agentic loop: LLM response → tool execution → recursive completion.
        Continues until LLM stops requesting tool calls.
        
        Args:
            messages: Conversation history (list of Message objects)
            
        Returns:
            Final AI message with no tool calls (only content)
        """
        ai_message: Message = await self._stream_response(messages)

        # Agentic loop: if LLM requested tools, execute them and recurse
        if ai_message.tool_calls:
            messages.append(ai_message)
            await self._call_tools(ai_message, messages)
            # Recursively call LLM again with tool results in history
            return await self.get_completion(messages)

        # Base case: no tool calls, return final response
        return ai_message

    async def _call_tools(self, ai_message: Message, messages: list[Message]):
        """
        Execute all tool calls from LLM response.
        
        For each tool call:
        1. Extract tool name and parse JSON arguments
        2. Call MCP tool via mcp_client
        3. Append tool result message to history (for next LLM call)
        4. Handle errors gracefully - add error message to history instead of crashing
        
        Args:
            ai_message: AI message containing tool_calls
            messages: Conversation history to append tool result messages to
            
        Notes:
            - Tool results must include tool_call_id for LLM to correlate responses
            - Error handling ensures loop continues even if individual tools fail
        """
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call["function"]["name"]
            # Parse tool arguments from JSON string
            try:
                tool_args = json.loads(tool_call["function"]["arguments"])
            except Exception as e:
                print(f"[DialClient] Failed to parse tool arguments for {tool_name}: {e}")
                tool_args = {}
            print(f"[DialClient] Executing tool: {tool_name} with args: {tool_args}")
            
            # Execute tool with error handling
            try:
                result = await self.mcp_client.call_tool(tool_name, tool_args)
                tool_msg = Message(
                    role=Role.TOOL,
                    content=str(result),
                    tool_call_id=tool_call["id"]
                )
                print(f"[DialClient] Tool {tool_name} executed successfully.")
            except Exception as e:
                # Fallback: send error message to LLM (allows agent to adapt)
                error_msg = f"Tool {tool_name} failed: {e}"
                tool_msg = Message(
                    role=Role.TOOL,
                    content=error_msg,
                    tool_call_id=tool_call["id"]
                )
                print(f"[DialClient] {error_msg}")
            messages.append(tool_msg)