---
title: Glossary
description: Definitions of key terms, abbreviations, and domain concepts for MCP-based agent systems
version: 1.0.0
last_updated: 2025-12-31
related: [README.md, architecture.md]
tags: [glossary, terminology, definitions]
---

# Glossary

## A

### Agentic Loop
Recursive pattern where an AI agent iteratively calls tools and processes results until no more tool calls are needed. In this project: LLM → tool execution → LLM (with results) → repeat until done.

### AI Message
Message with role "assistant" (AI) containing LLM-generated content and/or tool calls. Represents the agent's response in conversation history.

### Async Context Manager
Python pattern (`async with`) for managing resources with automatic cleanup. Used for MCP client connections and HTTP streams.

### Azure OpenAI
Microsoft's cloud service providing OpenAI models (GPT-4o, etc.) via REST API. This project uses Azure OpenAI through DIAL API proxy.

## C

### ClientSession
MCP SDK class managing bidirectional communication with an MCP server. Handles protocol handshake, capability negotiation, and request/response routing.

### CRUD
**C**reate, **R**ead, **U**pdate, **D**elete - standard operations for data management. This project implements all 5 user CRUD operations (read includes get + search).

## D

### DIAL API
AI DIAL (AI Development and Integration Abstraction Layer) - EPAM's proxy for Azure OpenAI APIs. Provides unified interface for multiple LLM providers with authentication and rate limiting.

### Delta
Incremental chunk in streaming responses. OpenAI streams tool calls as deltas (e.g., function name, then arguments in pieces). The agent accumulates deltas to reconstruct complete tool calls.

## E

### E.164 Format
International phone number format: `+[country code][number]` (e.g., `+12025551234`). Used for user phone field validation.

### EPAM VPN
Virtual Private Network required to access DIAL API endpoints. Must be active for agent to communicate with Azure OpenAI.

## F

### FastMCP
Python framework for building MCP servers with minimal boilerplate. Uses decorators (`@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()`) to expose functionality.

### Function Calling
OpenAI feature allowing LLMs to request tool execution by generating structured JSON. The agent parses these requests and routes them to the MCP server.

## G

### GPT-4o
OpenAI's "omni" model (text + vision + audio). This project uses GPT-4o via Azure OpenAI for tool-calling capabilities.

## H

### HTTP Streams
Bidirectional communication channel using HTTP for MCP protocol. FastMCP uses `streamable-http` transport for server-client messaging.

## I

### InputSchema
JSON Schema defining tool parameters (name, type, required fields). MCP servers provide inputSchema for each tool; agents transform this to DIAL format for LLM consumption.

## J

### JSON-RPC
Remote procedure call protocol using JSON. MCP protocol is built on JSON-RPC 2.0 (includes `jsonrpc`, `id`, `method`, `params`, `result`/`error`).

### JSON Schema
Standard for describing JSON data structures. Used by MCP for tool parameter definitions and by OpenAI for function calling.

## L

### LLM
**Large Language Model** - AI model trained on text data (e.g., GPT-4o, Claude). This project uses Azure OpenAI's GPT-4o for agent intelligence.

## M

### MCP (Model Context Protocol)
Open protocol for connecting AI agents to external tools, data sources, and services. Standardizes tool discovery, execution, and resource access.

### MCP Client
Agent component implementing MCP protocol to connect to MCP servers. Discovers tools, executes them, and retrieves resources/prompts.

### MCP Server
Service exposing tools, resources, and prompts via MCP protocol. This project's server provides user management tools backed by User Service API.

### Message History
Ordered list of conversation messages (system, user, AI, tool) maintained by the agent. Sent to LLM on each completion request to preserve context.

## P

### PATCH Semantics
HTTP pattern where only provided fields are updated (partial update). Used by `update_user` tool (vs. PUT which replaces entire resource).

### Prompt (MCP)
Domain-specific guidance provided by MCP servers to help LLMs use tools correctly. This project includes search and profile-creation prompts.

### Pydantic
Python library for data validation using type annotations. Used for `UserCreate`, `UserUpdate`, `Message`, and other models.

## R

### Recursive Completion
Pattern where `get_completion()` calls itself after executing tools. Enables multi-step workflows without explicit state machines.

### Resource (MCP)
Static file or data exposed by MCP server (e.g., documentation, diagrams). This project exposes a flow diagram PNG as a resource.

### Role
Message classification in conversation: SYSTEM (instructions), USER (human input), AI (assistant output), TOOL (execution result).

## S

### Session ID
Unique identifier (`mcp-session-id`) tracking MCP client-server connection. Required in HTTP header for all MCP protocol requests after initialization.

### Streamable HTTP
MCP transport using HTTP for bidirectional streaming. Enables real-time communication between MCP client and server without WebSockets.

### Streaming Response
LLM output delivered incrementally as chunks (deltas). Used by Azure OpenAI to reduce latency - agent displays text as it's generated.

### System Prompt
Initial message (role=SYSTEM) defining agent behavior and constraints. This project's prompt instructs the agent on tool usage and professional tone.

## T

### Tool
Function exposed by MCP server for agent execution. This project provides 5 tools: `get_user_by_id`, `search_user`, `add_user`, `update_user`, `delete_user`.

### Tool Call
LLM-generated request to execute a tool, containing tool name and arguments (JSON). Agent extracts this from streaming deltas and routes to MCP client.

### Tool Call ID
Unique identifier correlating tool execution result with original request. Required in tool message (`tool_call_id`) for LLM to match response to call.

### Tool Delta
Incremental chunk in streaming tool call (e.g., function name, partial arguments). Agent accumulates deltas to reconstruct complete tool call object.

### Tool Message
Message with role=TOOL containing execution result. Includes `tool_call_id` to link back to original request from AI message.

## U

### User Service
Docker container providing REST API for user CRUD operations. Generates 1000 mock users on startup, persists data in SQLite.

### UserClient
Python class wrapping User Service HTTP calls. Formats JSON responses as markdown code blocks for LLM readability.

## V

### Virtual Environment (venv)
Isolated Python environment with independent packages. This project uses `dial_mcp/` venv to avoid global package conflicts.

## Abbreviations

| Abbr | Full Term | Description |
|------|-----------|-------------|
| AI | Artificial Intelligence | Machine learning models (LLMs) |
| API | Application Programming Interface | Interface for software communication |
| CRUD | Create, Read, Update, Delete | Standard data operations |
| DIAL | Development Integration Abstraction Layer | EPAM's AI API proxy |
| HTTP | Hypertext Transfer Protocol | Web communication standard |
| JSON | JavaScript Object Notation | Data interchange format |
| LLM | Large Language Model | AI text generation model |
| MCP | Model Context Protocol | Tool integration protocol |
| REST | Representational State Transfer | API architectural style |
| RPC | Remote Procedure Call | Network request/response pattern |
| SDK | Software Development Kit | Library for building software |
| URI | Uniform Resource Identifier | Resource address (e.g., file://) |
| UUID | Universally Unique Identifier | Random unique ID |
| VPN | Virtual Private Network | Secure network connection |

## Domain-Specific Terms

### Address Object
Nested user data structure with fields: `country`, `city`, `street`, `flat_house`. Optional in user create/update.

### CreditCard Object
Nested user data structure with fields: `num` (card number), `cvv` (verification code), `exp_date` (expiration). Test data only (non-functional).

### Mock Users
1000 randomly generated user profiles created by User Service on startup. Stored in SQLite database for testing/demo purposes.

### Session Initialization
Two-step MCP handshake: 1) `init` request creates session ID, 2) `init-notification` confirms client ready. Required before tool/resource access.

### TextContent
MCP response type for tool results containing plain text (vs. BlobContent for binary). Used by all tools in this project.

## Common Patterns

### Context Manager Pattern
```python
async with MCPClient(url) as client:
    # Use client
    # Automatic cleanup on exit
```

### Tool Schema Transformation
```python
# MCP format → DIAL format
{
    "type": "function",
    "function": {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.inputSchema
    }
}
```

### Recursive Agent Loop
```python
async def get_completion(messages):
    response = await llm(messages)
    if response.tool_calls:
        execute_tools(response.tool_calls)
        return await get_completion(messages)  # Recurse
    return response
```

### Message Serialization
```python
# Internal format → OpenAI API format
{
    "role": message.role.value,
    "content": message.content,
    "tool_calls": message.tool_calls  # If present
}
```

## Workflow Terminology

### Discovery Phase
Initial agent startup: connect to MCP server, list tools/resources/prompts, transform schemas for LLM.

### Execution Phase
Tool invocation: LLM generates tool call → agent extracts → MCP client executes → result returned to LLM.

### Streaming Phase
LLM response generation: Azure OpenAI sends deltas (content + tool calls) → agent accumulates → final message constructed.

### Cleanup Phase
Session teardown: close MCP connection, release HTTP streams, exit context managers.

## Error Types

### HTTP 404
User Service: Resource not found (user ID doesn't exist, already deleted).

### HTTP 409
User Service: Conflict (duplicate email when creating user).

### HTTP 500
User Service or MCP Server: Internal error (database failure, unexpected exception).

### ConnectionError
Network failure: MCP server unreachable, User Service unavailable, DIAL API timeout.

### ValidationError
Pydantic: Invalid data format (missing required field, wrong type, out-of-range value).

### RuntimeError
Agent: MCP client not connected (forgot `async with` context manager).

## Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| MCP Server | FastMCP 2.10.1 | Tool/resource/prompt provider |
| Agent | Python 3.13 | Orchestration and logic |
| LLM Client | openai 1.93.0 | Azure OpenAI API wrapper |
| HTTP Client | aiohttp 3.8+ | Async HTTP requests |
| Data Validation | Pydantic | Schema validation |
| User Service | Docker (Python/FastAPI) | REST API backend |
| Database | SQLite | User data persistence |
| Protocol | JSON-RPC 2.0 | MCP communication |
| Transport | Streamable HTTP | MCP client-server channel |

## Related Standards

- **OpenAI Function Calling:** [OpenAI Documentation](https://platform.openai.com/docs/guides/function-calling)
- **MCP Protocol Specification:** [MCP Docs](https://modelcontextprotocol.io/)
- **JSON-RPC 2.0:** [Specification](https://www.jsonrpc.org/specification)
- **E.164 Phone Format:** [ITU Standard](https://www.itu.int/rec/T-REC-E.164/)
- **Pydantic Models:** [Pydantic Docs](https://docs.pydantic.dev/)

---

**See also:**
- [Architecture](./architecture.md) for system design
- [API Reference](./api.md) for tool details
- [Setup Guide](./setup.md) for environment configuration
