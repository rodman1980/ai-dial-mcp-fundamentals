---
title: ADR-001: MCP Protocol Selection
status: Accepted
date: 2025-12-31
decision_makers: [AI DIAL Team]
related: [architecture.md, setup.md]
tags: [adr, architecture, protocol]
---

# ADR-001: MCP Protocol Selection

## Status
**Accepted** (2025-12-31)

## Context

Building an AI agent system requires a standardized way to expose tools and resources to LLMs. Several options exist:

1. **Custom Protocol**: Build proprietary tool discovery and execution system
2. **OpenAI Plugin Architecture**: Use OpenAI's plugin spec (deprecated)
3. **LangChain Tools**: Use LangChain framework abstractions
4. **Model Context Protocol (MCP)**: Use Anthropic's open standard

### Requirements
- Tool discovery must be dynamic (agent doesn't hardcode tool list)
- Schema transformation needed (internal → LLM-friendly format)
- Support for non-tool resources (diagrams, documentation)
- Bidirectional communication (client can query server capabilities)
- Educational clarity (simple to understand for learning purposes)

### Constraints
- Must integrate with Azure OpenAI (DIAL API)
- Python 3.11+ ecosystem
- Minimal external dependencies
- Clear separation between server and client concerns

## Decision

**We will use Model Context Protocol (MCP) with FastMCP framework.**

### Why MCP?
1. **Open Standard**: Protocol spec maintained by Anthropic, growing ecosystem
2. **Clear Separation**: Server exposes tools, client consumes them - no tight coupling
3. **Rich Feature Set**: Tools, resources, prompts in one protocol
4. **Simple Implementation**: FastMCP reduces boilerplate to decorators
5. **Educational Value**: Clear abstractions teach protocol-based architecture

### Why FastMCP?
1. **Minimal Boilerplate**: `@mcp.tool()` decorator vs. manual JSON-RPC handling
2. **Built-in Transport**: HTTP streams managed automatically
3. **Type Safety**: Pydantic integration for parameter validation
4. **Active Development**: Maintained by Anthropic, regular updates

## Implementation Details

### Server Pattern
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="users-management", host="0.0.0.0", port=8005)

@mcp.tool()
async def get_user_by_id(user_id: int) -> str:
    return await user_client.get_user(user_id)
```

### Client Pattern
```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client(url) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
```

### Schema Transformation
MCP tools provide `inputSchema` (JSON Schema); agent transforms to DIAL format:
```python
{
    "type": "function",
    "function": {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.inputSchema  # Already JSON Schema
    }
}
```

## Consequences

### Positive
1. **Interoperability**: Agent can connect to any MCP server (not just users-management)
2. **Extensibility**: Adding tools = adding decorated functions (no protocol changes)
3. **Clear Boundaries**: Server doesn't know about LLM; client doesn't know about User Service
4. **Testability**: Postman can test MCP server independently of agent
5. **Educational**: Protocol concepts visible (tools/resources/prompts as first-class citizens)

### Negative
1. **Learning Curve**: Developers must understand MCP protocol (vs. simple function calls)
2. **Overhead**: JSON-RPC adds verbosity (method names, jsonrpc version, IDs)
3. **Limited Ecosystem**: MCP newer than alternatives (fewer examples/libraries)
4. **Single Connection**: 1-to-1 client-server pattern (multi-server requires multiple clients)

### Risks
1. **Protocol Changes**: MCP spec evolving; FastMCP may introduce breaking changes
   - *Mitigation*: Pin FastMCP version (2.10.1), test upgrades in isolation
2. **Performance**: HTTP streams slower than WebSockets for high-frequency tool calls
   - *Mitigation*: Acceptable for educational purposes; optimize if production needed
3. **Debugging Complexity**: Network layer adds failure points vs. direct function calls
   - *Mitigation*: Postman collection for isolated server testing

## Alternatives Considered

### Alternative 1: Custom Protocol
**Pros:**
- Full control over wire format
- No external dependencies
- Optimize for specific use case

**Cons:**
- High development cost (build JSON-RPC, session management, schema validation)
- No interoperability with other systems
- Educational value reduced (students learn custom protocol, not standard)

**Verdict:** Rejected - reinventing the wheel

### Alternative 2: LangChain Tools
**Pros:**
- Rich ecosystem (100+ pre-built tools)
- Tight LLM integration
- Active community

**Cons:**
- Opinionated abstractions hide protocol details
- Heavy dependency (entire LangChain framework)
- Server-client separation unclear (tools often bundled with agent)

**Verdict:** Rejected - reduces educational clarity

### Alternative 3: Direct Function Calls (No Protocol)
**Pros:**
- Simplest implementation (Python functions called directly)
- Zero network overhead
- Easy debugging

**Cons:**
- No tool discovery (hardcoded tool list)
- No schema introspection (LLM can't learn tool signatures)
- No separation (server and client tightly coupled)

**Verdict:** Rejected - doesn't teach protocol-based architecture

## Related Decisions
- ADR-002: [String-Based Tool Results](./ADR-002-string-tool-results.md) (formats responses for LLM readability)
- ADR-003: [Recursive Agent Loop](./ADR-003-recursive-agent-loop.md) (handles multi-step workflows)

## References
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/anthropics/fastmcp)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

## Review Notes
- **2025-12-31**: Initial decision based on FastMCP 2.10.1 and Python 3.13
- **Future**: Re-evaluate if MCP ecosystem matures with native multi-server support
