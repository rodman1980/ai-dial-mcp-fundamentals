---
title: ADR-002: String-Based Tool Results
status: Accepted
date: 2025-12-31
decision_makers: [AI DIAL Team]
related: [architecture.md, api.md, ADR-001-mcp-protocol-selection.md]
tags: [adr, architecture, data-format]
---

# ADR-002: String-Based Tool Results

## Status
**Accepted** (2025-12-31)

## Context

MCP tools must return values to the agent, which then passes them to the LLM for interpretation. Several data format options exist:

1. **Raw JSON**: Return Python dicts/lists, serialize to JSON
2. **Pydantic Models**: Return typed objects with `.model_dump_json()`
3. **Formatted Strings**: Return markdown code blocks or plain text
4. **Binary Data**: Return bytes for images/files

### Requirements
- LLM must easily parse tool results (no confusion)
- Human-readable output (for debugging and user transparency)
- Support structured data (user objects with nested fields)
- Consistent formatting across all tools

### LLM Behavior Observations
- Raw JSON often confuses LLMs (interprets as code to execute)
- Code blocks (triple backticks) signal "data to read, not execute"
- Plain text enables natural language interpretation
- Structured formatting (key-value pairs) reduces ambiguity

## Decision

**MCP server tools will return formatted strings (markdown code blocks), not raw JSON or Pydantic models.**

### Implementation Pattern
```python
def __user_to_string(user_dict: dict) -> str:
    """Format user data as markdown code block."""
    return f"""```
User ID: {user_dict['id']}
Name: {user_dict['name']}
Surname: {user_dict['surname']}
Email: {user_dict['email']}
Phone: {user_dict.get('phone', 'N/A')}
Company: {user_dict.get('company', 'N/A')}
Salary: ${user_dict.get('salary', 0):,.2f}
...
```"""

@mcp.tool()
async def get_user_by_id(user_id: int) -> str:  # Returns str, not dict
    user_dict = await fetch_user(user_id)
    return __user_to_string(user_dict)  # Format before returning
```

### Format Specification
- **Code Blocks**: Triple backticks (```) for structured data
- **Key-Value Pairs**: `Field: Value` on separate lines
- **Lists**: Numbered or bulleted items
- **Separation**: Blank lines between records
- **Optional Fields**: Show "N/A" or omit (consistent per tool)

## Rationale

### Why Strings Over JSON?
1. **LLM Readability**: Models trained on human-readable text, not JSON
2. **Reduced Ambiguity**: Code blocks signal "reference data" vs. "code to run"
3. **Natural Language**: LLM can describe results in prose ("User Alice has email...")
4. **Error Handling**: Malformed JSON breaks parsing; strings always valid

### Why Code Blocks?
1. **Visual Separation**: Clearly delineates data from conversation
2. **Whitespace Preservation**: Formatting survives token encoding
3. **Copy-Paste Friendly**: Users can extract data if needed
4. **Markdown Standard**: Widely recognized format

### Why Not Pydantic Models?
1. **Serialization Overhead**: `.model_dump_json()` adds boilerplate
2. **Type Coupling**: MCP server shouldn't depend on agent's type system
3. **Format Flexibility**: Strings allow custom formatting per use case

## Examples

### Example 1: Single User (get_user_by_id)
```python
return """```
User ID: 42
Name: Alice
Surname: Johnson
Email: alice@example.com
Phone: +1234567890
Company: Google
Salary: $120,000.00
About: Software engineer with 10 years experience
```"""
```

### Example 2: Multiple Users (search_user)
```python
return f"""Found {len(users)} users:

```
User ID: 15
Name: John
Surname: Doe
Email: john.doe@example.com
...
```

```
User ID: 28
Name: Johnny
Surname: Smith
Email: johnny@example.com
...
```
"""
```

### Example 3: Empty Result (search_user)
```python
return "No users found matching your criteria."
```

### Example 4: Success Confirmation (delete_user)
```python
return "User successfully deleted"
```

## Consequences

### Positive
1. **LLM Performance**: Models interpret results correctly without confusion
2. **Debugging**: Developers can read tool outputs directly in logs
3. **User Transparency**: Agent can show formatted data to users without transformation
4. **Consistency**: All tools follow same formatting pattern
5. **Flexibility**: Easy to adjust formatting without changing protocol

### Negative
1. **Parsing Overhead**: If client needs structured data, must parse strings back to JSON
2. **Size Inflation**: Formatted strings larger than compact JSON
3. **No Type Safety**: Strings don't enforce schema (vs. Pydantic models)
4. **Format Drift**: Multiple developers may format inconsistently without strict guidelines

### Risks
1. **Ambiguous Formatting**: LLM may misinterpret poorly formatted strings
   - *Mitigation*: Use consistent key-value format with clear labels
2. **Large Datasets**: 100+ users may exceed token limits
   - *Mitigation*: Limit search results, add pagination if needed
3. **Special Characters**: User data with backticks (```) breaks code blocks
   - *Mitigation*: Escape backticks or use alternative delimiters

## Implementation Details

### Helper Functions (user_client.py)
```python
def __user_to_string(user: dict) -> str:
    """Format single user as code block."""
    return f"""```
User ID: {user['id']}
Name: {user['name']}
Surname: {user['surname']}
Email: {user['email']}
...
```"""

def __users_to_string(users: list[dict]) -> str:
    """Format multiple users as list of code blocks."""
    if not users:
        return "No users found matching your criteria."
    formatted = [__user_to_string(u) for u in users]
    return f"Found {len(users)} users:\n\n" + "\n\n".join(formatted)
```

### Confirmation Messages
```python
# Create/Update: Show new data
return f"User successfully created:\n\n{__user_to_string(user)}"

# Delete: Simple confirmation
return "User successfully deleted"

# Error: Plain text message
return f"Error: User with ID {user_id} not found"
```

## Alternatives Considered

### Alternative 1: Raw JSON Strings
```python
return json.dumps({"id": 42, "name": "Alice", ...})
```

**Pros:**
- Parseable by both humans and machines
- Standard format

**Cons:**
- LLMs often misinterpret as code
- Less readable for humans (no whitespace)
- Escaping issues with nested quotes

**Verdict:** Rejected - LLM confusion risk

### Alternative 2: Pydantic Models
```python
return UserResponse(id=42, name="Alice", ...).model_dump_json()
```

**Pros:**
- Type safety
- Automatic validation

**Cons:**
- Serialization boilerplate
- Type coupling (server depends on shared models)
- Still returns JSON string (LLM readability issue persists)

**Verdict:** Rejected - doesn't solve LLM readability

### Alternative 3: Plain Text (No Code Blocks)
```python
return "User ID: 42\nName: Alice\n..."
```

**Pros:**
- Simplest implementation
- No formatting overhead

**Cons:**
- Visual separation poor (blends with conversation)
- Whitespace handling fragile
- Harder to extract data programmatically

**Verdict:** Rejected - code blocks improve clarity

## Testing Strategy

### Unit Tests (Not Implemented)
```python
def test_user_to_string():
    user = {"id": 1, "name": "Test", "email": "test@example.com"}
    result = __user_to_string(user)
    assert "User ID: 1" in result
    assert "```" in result  # Has code block
    assert "Name: Test" in result
```

### Manual Verification
1. Run agent: `python agent/app.py`
2. Execute tool: "Get user with ID 1"
3. Check output: Should show code block with all fields
4. LLM response: Should correctly interpret user data

## Related Decisions
- ADR-001: [MCP Protocol Selection](./ADR-001-mcp-protocol-selection.md) (defines tool interface)
- ADR-003: [Recursive Agent Loop](./ADR-003-recursive-agent-loop.md) (consumes tool results)

## References
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/prompt-engineering) - Formatting guidelines
- [Markdown Specification](https://spec.commonmark.org/) - Code block syntax

## Review Notes
- **2025-12-31**: Initial decision based on GPT-4o behavior
- **Future**: Monitor LLM improvements; may revisit if structured outputs improve
