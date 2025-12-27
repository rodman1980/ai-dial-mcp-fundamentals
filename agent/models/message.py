"""
Conversation Message Models

Pydantic models for managing dialogue flow in agent-LLM interactions.
Abstracts OpenAI message format for internal use, with to_dict() method for API serialization.

MESSAGE FLOW:
1. App creates Message(role=SYSTEM, content=system_prompt)
2. Message history accumulated: USER messages (inputs) + AI messages (outputs) + TOOL messages (results)
3. Before sending to LLM: Message.to_dict() converts to OpenAI format
4. LLM response parsed: extract content (text) + tool_calls (if any)
5. For each tool_call: append TOOL message with result + tool_call_id (correlates response to request)
6. Conversation loop: new AI response → check tool_calls → execute → append TOOL result → recurse

SERIALIZATION:
- to_dict() excludes None fields (reduces JSON size for LLM API)
- role is always included (required by OpenAI API)
- tool_call_id is only set in TOOL messages (correlates result to request)
- tool_calls is only set in AI messages (when LLM decides to call tools)
"""
from enum import StrEnum
from typing import Any
from pydantic import BaseModel


class Role(StrEnum):
    """
    Message role enumeration.
    
    Maps internal role names to OpenAI API role values:
    - SYSTEM: System prompt (agent instructions)
    - USER: Human input (user messages in conversation)
    - AI: LLM output (assistant messages with content/tool_calls)
    - TOOL: Tool execution result (tool messages with tool_call_id)
    
    Note: Role.AI maps to "assistant" for OpenAI compatibility.
    """
    SYSTEM = "system"      # System prompt (agent behavior instructions)
    USER = "user"          # User/human message in conversation
    AI = "assistant"       # LLM (assistant) message with content or tool calls
    TOOL = "tool"          # Tool execution result message


class Message(BaseModel):
    """
    Conversation message for agent-LLM interaction.
    
    Represents a single message in the conversation history. Used to track:
    - User inputs (USER role)
    - LLM outputs with content and/or tool calls (AI role)
    - Tool execution results (TOOL role)
    - System instructions (SYSTEM role)
    
    Attributes:
        role: Message role (SYSTEM/USER/AI/TOOL) - always included in serialization
        content: Message text content (optional, None for tool-only AI messages)
        tool_call_id: ID linking TOOL message to originating tool_call (for correlation)
        name: Optional sender name (not typically used in agent conversations)
        tool_calls: List of tool calls in AI message (None if no tools called)
    
    Serialization:
    - to_dict() converts to OpenAI message format
    - Excludes None fields to minimize API payload
    - Always includes role field
    """
    role: Role
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize message to OpenAI API format.
        
        Converts internal Message model to dict with:
        - role as string value (for OpenAI API compatibility)
        - Excludes None fields (reduces payload size)
        - Includes conditional fields based on message type:
          * AI messages: content, tool_calls
          * TOOL messages: content, tool_call_id
          * USER/SYSTEM messages: content, name
        
        Returns:
            dict: OpenAI-compatible message dict with role always included
            
        Example outputs:
            SYSTEM: {"role": "system", "content": "You are a..."}
            USER: {"role": "user", "content": "Find user 123"}
            AI with content: {"role": "assistant", "content": "I'll search..."}
            AI with tools: {"role": "assistant", "tool_calls": [...]}
            TOOL result: {"role": "tool", "content": "...", "tool_call_id": "call_123"}
        """
        # Always include role (required by OpenAI API)
        result = {"role": str(self.role.value)}
        
        # Conditionally include optional fields (reduce payload if not present)
        if self.content:
            result["content"] = self.content
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        
        return result
