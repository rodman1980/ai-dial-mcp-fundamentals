---
title: ADR-003: Recursive Agent Loop
status: Accepted
date: 2025-12-31
decision_makers: [AI DIAL Team]
related: [architecture.md, ADR-001-mcp-protocol-selection.md]
tags: [adr, architecture, agent-pattern]
---

# ADR-003: Recursive Agent Loop

## Status
**Accepted** (2025-12-31)

## Context

AI agents with tool-calling capabilities need a mechanism to handle multi-step workflows where the LLM requests tool execution, processes results, and potentially requests more tools. Several patterns exist:

1. **Recursive Function**: `get_completion()` calls itself when tool calls detected
2. **Explicit Loop**: `while has_tool_calls: execute_and_continue()`
3. **State Machine**: FSM with states (THINKING, CALLING_TOOL, PROCESSING, DONE)
4. **Async Queue**: Producer-consumer pattern with task queue

### Requirements
- Support multi-step workflows (search → get details → update)
- Preserve conversation history across turns
- Handle arbitrary depth (LLM can chain many tool calls)
- Graceful termination (stop when LLM returns final response)
- Simple to understand (educational codebase)

### Constraints
- Azure OpenAI API: Stateless (each request independent)
- Message history must grow monotonically (append-only)
- Tool execution is async (await needed)

## Decision

**Implement recursive `get_completion(messages)` function that calls itself after tool execution until no tool calls remain.**

### Implementation Pattern
```python
async def get_completion(self, messages: list[Message]) -> Message:
    """Get LLM completion with recursive tool execution."""
    ai_message = await self._stream_response(messages)
    
    if ai_message.tool_calls:
        # Append AI message with tool calls
        messages.append(ai_message)
        
        # Execute tools and append results
        await self._call_tools(ai_message, messages)
        
        # Recurse: LLM sees tool results, may request more tools
        return await self.get_completion(messages)
    
    # Base case: no tool calls, return final response
    return ai_message
```

### Execution Flow
```
1. User input → messages
2. get_completion(messages)
3.   → Stream LLM response
4.   → Tool calls detected?
5.     YES:
6.       → Append AI message (with tool calls)
7.       → Execute tools → append tool results
8.       → Recurse: get_completion(messages) [goto 3]
9.     NO:
10.      → Return AI message (final response)
```

## Rationale

### Why Recursion?
1. **Natural Mapping**: Mirrors LLM behavior (think → act → think → act → done)
2. **Automatic Depth**: No manual loop counter or max iterations
3. **Stack Traces**: Debugging shows call chain (helpful for tracing workflows)
4. **Code Clarity**: Base case (no tool calls) vs. recursive case explicit

### Why Not Explicit Loop?
```python
while True:
    ai_message = await stream_response(messages)
    if not ai_message.tool_calls:
        break
    execute_tools(ai_message, messages)
    # Continue loop
```

**Pros:**
- Easier to add loop limit (`while iterations < MAX`)
- Stack depth constant (no recursion limit risk)

**Cons:**
- Less intuitive flow (break condition interrupts narrative)
- More mutable state (loop variable)

**Verdict:** Recursion preferred for educational clarity

### Why Not State Machine?
```python
class AgentState(Enum):
    THINKING, CALLING_TOOL, PROCESSING, DONE

async def run_agent():
    state = AgentState.THINKING
    while state != AgentState.DONE:
        if state == AgentState.THINKING:
            # ... transition logic ...
```

**Pros:**
- Explicit state transitions
- Easier to visualize with diagram

**Cons:**
- High complexity for simple workflow
- Boilerplate for state management

**Verdict:** Overkill for current use case

## Implementation Details

### Function Signature
```python
async def get_completion(self, messages: list[Message]) -> Message:
    """
    Get LLM completion with automatic tool execution.
    
    Implements recursive agent loop: LLM → tools → LLM (repeat until done).
    
    Args:
        messages: Conversation history (mutated by appending tool results)
        
    Returns:
        Final AI message with no tool calls (only content)
    """
```

### Message History Mutation
```python
# messages mutated in-place
messages.append(ai_message)          # Add AI message with tool calls
await self._call_tools(ai_message, messages)  # Appends tool messages
# Subsequent recursion sees updated history
```

### Tool Execution
```python
async def _call_tools(self, ai_message: Message, messages: list[Message]):
    """Execute all tool calls and append results to messages."""
    for tool_call in ai_message.tool_calls:
        try:
            # Extract tool name and arguments
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            
            # Execute via MCP client
            result = await self.mcp_client.call_tool(tool_name, tool_args)
            
            # Append tool result message
            messages.append(Message(
                role=Role.TOOL,
                content=result,
                tool_call_id=tool_call["id"]
            ))
            
        except Exception as e:
            # Append error message (LLM sees failure, can retry or explain)
            messages.append(Message(
                role=Role.TOOL,
                content=f"Error executing {tool_name}: {str(e)}",
                tool_call_id=tool_call["id"]
            ))
```

## Consequences

### Positive
1. **Simplicity**: 15 lines of code vs. 50+ for state machine
2. **Correctness**: Recursion naturally handles arbitrary depth
3. **Debugging**: Call stack shows workflow path
4. **Educational**: Clear base case / recursive case structure
5. **Testability**: Easy to mock `_stream_response()` and verify recursion

### Negative
1. **Stack Depth**: Python recursion limit (~1000 calls) could be hit with pathological LLM
2. **Memory**: Each recursion frame holds `messages` list (grows over time)
3. **Tail Call**: Python doesn't optimize tail recursion (stack frames accumulate)

### Risks
1. **Infinite Loop**: LLM repeatedly requests same tool (no progress)
   - *Mitigation*: Add max iterations guard (e.g., `if len(messages) > 100: raise`)
2. **Stack Overflow**: Very long conversation (100+ tool calls)
   - *Mitigation*: Acceptable for educational use; refactor to loop if production needed
3. **Error Propagation**: Exception in tool execution breaks recursion
   - *Mitigation*: Catch exceptions, append error message, continue (LLM handles gracefully)

## Examples

### Example 1: Single Tool Call
```
User: "Find user named Alice"
→ get_completion([USER: "Find user named Alice"])
  → LLM: tool_call = search_user(name="Alice")
  → Append AI message, execute tool, append TOOL result
  → get_completion([USER, AI, TOOL])  # Recursion
    → LLM: "Found 15 users named Alice"
    → No tool calls → Return
```

### Example 2: Multi-Step Workflow
```
User: "Find Bob and update his company to EPAM"
→ get_completion([USER: "Find Bob..."])
  → LLM: tool_call = search_user(name="Bob")
  → Append AI message, execute tool, append TOOL result
  → get_completion([USER, AI, TOOL])  # Recursion 1
    → LLM: tool_call = get_user_by_id(user_id=42)
    → Append AI message, execute tool, append TOOL result
    → get_completion([USER, AI, TOOL, AI, TOOL])  # Recursion 2
      → LLM: tool_call = update_user(user_id=42, company="EPAM")
      → Append AI message, execute tool, append TOOL result
      → get_completion([USER, AI, TOOL, AI, TOOL, AI, TOOL])  # Recursion 3
        → LLM: "Updated Bob's company to EPAM"
        → No tool calls → Return
```

## Alternatives Considered

### Alternative 1: Explicit While Loop
```python
async def get_completion(messages):
    while True:
        ai_message = await stream_response(messages)
        if not ai_message.tool_calls:
            return ai_message
        messages.append(ai_message)
        await call_tools(ai_message, messages)
```

**Pros:**
- No recursion limit risk
- Easier to add loop counter

**Cons:**
- Less clear flow (break interrupts)
- Mutable state (loop variable)

**Verdict:** Rejected for educational clarity

### Alternative 2: Generator Pattern
```python
async def agent_loop(messages):
    while True:
        ai_message = await stream_response(messages)
        yield ai_message
        if not ai_message.tool_calls:
            break
        # Execute tools
```

**Pros:**
- Lazy evaluation (stream results)
- Pausable execution

**Cons:**
- Complex for caller (must iterate generator)
- Doesn't fit request-response pattern

**Verdict:** Rejected - doesn't match use case

### Alternative 3: Max Iterations Guard
```python
async def get_completion(messages, max_iterations=10):
    if max_iterations == 0:
        raise RuntimeError("Max iterations reached")
    ai_message = await stream_response(messages)
    if ai_message.tool_calls:
        # ...
        return await get_completion(messages, max_iterations - 1)
    return ai_message
```

**Pros:**
- Prevents infinite loops
- Explicit depth limit

**Cons:**
- Extra parameter in signature
- Hardcoded limit may be too low/high

**Verdict:** Could add in future (currently no limit)

## Performance Considerations

### Stack Depth Analysis
- **Typical usage**: 2-5 recursions (short workflows)
- **Worst case**: Python limit ~1000 (extremely pathological LLM)
- **Mitigation**: If production needed, refactor to explicit loop

### Memory Usage
```python
# Each recursion frame holds:
- messages: list (grows with appends, but shared reference)
- ai_message: Message object (~1KB)
- Local variables: minimal

# 100 recursions ≈ 100KB (negligible)
```

## Testing Strategy

### Unit Test (Mock LLM)
```python
async def test_recursive_completion():
    # Mock LLM: first call returns tool, second call no tools
    mock_responses = [
        Message(role=Role.AI, tool_calls=[...]),
        Message(role=Role.AI, content="Done")
    ]
    
    client = DialClient(...)
    result = await client.get_completion([...])
    
    assert result.content == "Done"
    assert len(mock_responses) == 2  # Both calls made
```

### Integration Test (Real LLM)
```bash
# Run agent
python agent/app.py

# Test multi-step
You: Find user named Alice and update her company to EPAM

# Verify:
# 1. search_user called (recursion 1)
# 2. get_user_by_id called (recursion 2)
# 3. update_user called (recursion 3)
# 4. Final response returned (base case)
```

## Related Decisions
- ADR-001: [MCP Protocol Selection](./ADR-001-mcp-protocol-selection.md) (defines tool execution interface)
- ADR-002: [String-Based Tool Results](./ADR-002-string-tool-results.md) (formats tool results consumed by recursion)

## References
- [LangChain Agent Executor](https://python.langchain.com/docs/modules/agents/) - Similar recursive pattern
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling) - Tool call protocol

## Review Notes
- **2025-12-31**: Initial decision for educational codebase
- **Future**: Add max iterations guard if production deployment planned
- **Future**: Consider refactoring to explicit loop if stack depth becomes issue
