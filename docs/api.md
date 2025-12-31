---
title: API Reference
description: Complete reference for MCP server tools, resources, prompts, and User Service endpoints
version: 1.0.0
last_updated: 2025-12-31
related: [architecture.md, setup.md]
tags: [api, tools, mcp, rest]
---

# API Reference

## Table of Contents
- [MCP Server Tools](#mcp-server-tools)
- [MCP Resources](#mcp-resources)
- [MCP Prompts](#mcp-prompts)
- [User Service REST API](#user-service-rest-api)
- [Tool Schema Examples](#tool-schema-examples)

## MCP Server Tools

The MCP server exposes 5 tools for user management operations via the `@mcp.tool()` decorator.

### get_user_by_id

Retrieve a single user by unique identifier.

**Signature:**
```python
async def get_user_by_id(user_id: int) -> str
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user_id` | `int` | Yes | Unique user identifier (1-1000 for mock data) |

**Returns:**
Formatted string with user details in markdown code block:
```
User ID: 42
Name: Alice
Surname: Johnson
Email: alice.johnson@example.com
Phone: +1234567890
...
```

**Errors:**
- `404`: User not found
- `500`: User Service unavailable

**Example usage:**
```python
result = await mcp_client.call_tool("get_user_by_id", {"user_id": 42})
```

**LLM prompt example:**
```
"Get details for user ID 42"
```

---

### search_user

Search for users using optional filters (name, surname, email, gender).

**Signature:**
```python
async def search_user(
    name: Optional[str] = None,
    surname: Optional[str] = None,
    email: Optional[str] = None,
    gender: Optional[str] = None
) -> str
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | `str` | No | Partial first name (case-insensitive, e.g., "john" matches "John", "Johnny") |
| `surname` | `str` | No | Partial last name (case-insensitive) |
| `email` | `str` | No | Partial email (case-insensitive, e.g., "gmail" finds all Gmail users) |
| `gender` | `str` | No | Exact gender match: "male", "female", "other", "prefer_not_to_say" |

**Returns:**
Formatted string with list of matching users (or "No users found"):
```
Found 3 users:

User ID: 15
Name: John
Surname: Doe
Email: john.doe@example.com
...

User ID: 28
Name: Johnny
...
```

**Errors:**
- `500`: User Service unavailable

**Example usage:**
```python
result = await mcp_client.call_tool("search_user", {
    "name": "alice",
    "gender": "female"
})
```

**LLM prompt examples:**
```
"Find all users named Alice"
"Search for users with Gmail addresses"
"List all male users at Google"
```

---

### add_user

Create a new user with validated data.

**Signature:**
```python
async def add_user(
    name: str,
    surname: str,
    email: str,
    about_me: str,
    phone: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    gender: Optional[str] = None,
    company: Optional[str] = None,
    salary: Optional[float] = None,
    address: Optional[dict] = None,
    credit_card: Optional[dict] = None
) -> str
```

**Parameters:**
| Name | Type | Required | Description | Constraints |
|------|------|----------|-------------|-------------|
| `name` | `str` | Yes | First name | 2-50 chars, letters only |
| `surname` | `str` | Yes | Last name | 2-50 chars, letters only |
| `email` | `str` | Yes | Email address | Must be unique, valid format |
| `about_me` | `str` | Yes | Biography/description | 0+ chars, rich text |
| `phone` | `str` | No | Phone number | E.164 format preferred: +1234567890 |
| `date_of_birth` | `str` | No | Birth date | YYYY-MM-DD format |
| `gender` | `str` | No | Gender | "male", "female", "other", "prefer_not_to_say" |
| `company` | `str` | No | Company name | Any string |
| `salary` | `float` | No | Annual salary (USD) | Realistic range: 30000-200000 |
| `address` | `dict` | No | Physical address | See Address schema below |
| `credit_card` | `dict` | No | Payment card | See CreditCard schema below |

**Address Schema:**
```json
{
    "country": "United States",
    "city": "New York",
    "street": "123 Main St",
    "flat_house": "Apt 5B"
}
```

**CreditCard Schema:**
```json
{
    "num": "1234-5678-9012-3456",
    "cvv": "123",
    "exp_date": "12/2025"
}
```

**Returns:**
Confirmation message with created user data:
```
User successfully created:

User ID: 1001
Name: Bob
Surname: Smith
Email: bob@example.com
...
```

**Errors:**
- `400`: Invalid data (email format, missing required fields)
- `409`: Email already exists
- `500`: User Service unavailable

**Example usage:**
```python
result = await mcp_client.call_tool("add_user", {
    "name": "Bob",
    "surname": "Smith",
    "email": "bob@example.com",
    "about_me": "Software engineer",
    "company": "EPAM",
    "salary": 120000.0,
    "address": {
        "country": "United States",
        "city": "Boston",
        "street": "456 Tech Ave",
        "flat_house": "Suite 200"
    }
})
```

**LLM prompt examples:**
```
"Add a new user named Bob Smith with email bob@example.com"
"Create a user profile for Alice Johnson, software engineer at Google"
```

---

### update_user

Update an existing user with partial data (PATCH semantics).

**Signature:**
```python
async def update_user(
    user_id: int,
    name: Optional[str] = None,
    surname: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    gender: Optional[str] = None,
    company: Optional[str] = None,
    salary: Optional[float] = None,
    address: Optional[dict] = None,
    credit_card: Optional[dict] = None
) -> str
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user_id` | `int` | Yes | User to update |
| All others | various | No | Only provided fields are updated |

**Returns:**
Confirmation message with updated user data:
```
User successfully updated:

User ID: 42
Name: Alice (updated)
Company: EPAM (updated)
...
```

**Errors:**
- `404`: User not found
- `400`: Invalid data format
- `500`: User Service unavailable

**Example usage:**
```python
result = await mcp_client.call_tool("update_user", {
    "user_id": 42,
    "company": "EPAM",
    "salary": 150000.0
})
```

**LLM prompt examples:**
```
"Update user 42's company to EPAM"
"Change Alice Johnson's email to alice.new@example.com"
```

---

### delete_user

Delete a user by ID.

**Signature:**
```python
async def delete_user(user_id: int) -> str
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user_id` | `int` | Yes | User to delete |

**Returns:**
Confirmation message:
```
User successfully deleted
```

**Errors:**
- `404`: User not found
- `500`: User Service unavailable

**Example usage:**
```python
result = await mcp_client.call_tool("delete_user", {"user_id": 42})
```

**LLM prompt examples:**
```
"Delete user with ID 42"
"Remove Alice Johnson from the system"
```

---

## MCP Resources

Resources are static files exposed by the MCP server via `@mcp.resource()`.

### users-management-flow

**URI:** `file:///static/flow.png`

**Description:** API flow diagram showing User Service endpoints and request/response patterns.

**Type:** Binary (PNG image)

**Usage:**
```python
resources = await mcp_client.get_resources()
flow_diagram = resources[0]  # First resource
content = await mcp_client.read_resource(flow_diagram.uri)
```

**Purpose:** Visual reference for understanding User Service REST API structure.

---

## MCP Prompts

Prompts are domain-specific guidance for LLM tool usage via `@mcp.prompt()`.

### search-users-helper

**Name:** `search-users-helper`

**Description:** Best practices for user search operations.

**Content:**
```
When searching for users:
1. Use partial matching for name/surname/email (case-insensitive)
2. Combine filters for precise results (e.g., name + company)
3. If no results, suggest alternative searches (e.g., try surname instead)
4. For ambiguous matches, ask user to clarify (e.g., "Found 5 Johns, which one?")
5. Use gender filter only when explicitly requested
```

**Usage:**
Agent automatically includes this prompt in conversation history during initialization.

---

### profile-creation-guide

**Name:** `profile-creation-guide`

**Description:** Guidelines for creating realistic user profiles.

**Content:**
```
When creating user profiles:
1. Ensure email uniqueness (check if user exists first)
2. Use realistic salaries ($30k-$200k USD range)
3. Format dates as YYYY-MM-DD
4. Phone numbers should follow E.164 format: +1234567890
5. About_me should be descriptive (50-200 chars)
6. Address requires all fields: country, city, street, flat_house
7. Credit card format: XXXX-XXXX-XXXX-XXXX, CVV: XXX, Exp: MM/YYYY
8. Always validate data before submission
```

**Usage:**
Agent automatically includes this prompt in conversation history during initialization.

---

## User Service REST API

The User Service (Docker container) provides the underlying REST API consumed by the MCP server.

**Base URL:** `http://localhost:8041`

### Endpoints

#### GET /v1/users

List all users (no pagination, returns all 1000 mock users).

**Response:**
```json
[
    {
        "id": 1,
        "name": "Alice",
        "surname": "Johnson",
        "email": "alice@example.com",
        ...
    },
    ...
]
```

---

#### GET /v1/users/{user_id}

Get user by ID.

**Path parameters:**
- `user_id`: Integer

**Response:**
```json
{
    "id": 42,
    "name": "Alice",
    "surname": "Johnson",
    "email": "alice@example.com",
    "phone": "+1234567890",
    "date_of_birth": "1990-05-15",
    "address": {
        "country": "United States",
        "city": "New York",
        "street": "123 Main St",
        "flat_house": "Apt 5B"
    },
    "gender": "female",
    "company": "Google",
    "salary": 120000.0,
    "about_me": "Software engineer with 10 years experience",
    "credit_card": {
        "num": "1234-5678-9012-3456",
        "cvv": "123",
        "exp_date": "12/2025"
    }
}
```

---

#### GET /v1/users/search

Search users by filters.

**Query parameters:**
- `name`: String (partial match)
- `surname`: String (partial match)
- `email`: String (partial match)
- `gender`: String (exact match)

**Response:** Array of user objects (same as GET /v1/users)

---

#### POST /v1/users

Create new user.

**Request body:**
```json
{
    "name": "Bob",
    "surname": "Smith",
    "email": "bob@example.com",
    "about_me": "New user",
    "phone": "+9876543210",
    ...
}
```

**Response:** Created user object (HTTP 201)

---

#### PUT /v1/users/{user_id}

Update user (PATCH semantics - only provided fields updated).

**Path parameters:**
- `user_id`: Integer

**Request body:** Partial user object

**Response:** Updated user object (HTTP 201)

---

#### DELETE /v1/users/{user_id}

Delete user.

**Path parameters:**
- `user_id`: Integer

**Response:** HTTP 204 (no content)

---

## Tool Schema Examples

### MCP Tool Schema (Internal)

```json
{
    "name": "search_user",
    "description": "Search for users by optional criteria...",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Partial first name match..."
            },
            "surname": {"type": "string"},
            "email": {"type": "string"},
            "gender": {"type": "string"}
        },
        "additionalProperties": false
    }
}
```

### DIAL Tool Schema (OpenAI Format)

Transformed by MCPClient for LLM consumption:

```json
{
    "type": "function",
    "function": {
        "name": "search_user",
        "description": "Search for users by optional criteria...",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "..."},
                "surname": {"type": "string"},
                "email": {"type": "string"},
                "gender": {"type": "string"}
            },
            "additionalProperties": false
        }
    }
}
```

### Tool Call (From LLM)

```json
{
    "id": "call_abc123",
    "type": "function",
    "function": {
        "name": "search_user",
        "arguments": "{\"name\": \"Alice\", \"gender\": \"female\"}"
    }
}
```

### Tool Result (To LLM)

```json
{
    "role": "tool",
    "content": "Found 2 users:\n\nUser ID: 42\nName: Alice\n...",
    "tool_call_id": "call_abc123"
}
```

---

## Feature-to-Code-to-Test Traceability Matrix

| Feature | Code Module | REST Endpoint | Test Method |
|---------|------------|---------------|-------------|
| Get user by ID | [mcp_server/server.py](../mcp_server/server.py#L48) | GET /v1/users/{id} | Postman: `tools/call` → get_user_by_id |
| Search users | [mcp_server/server.py](../mcp_server/server.py#L82) | GET /v1/users/search | Postman: `tools/call` → search_user |
| Create user | [mcp_server/server.py](../mcp_server/server.py#L112) | POST /v1/users | Postman: `tools/call` → add_user |
| Update user | [mcp_server/server.py](../mcp_server/server.py#L165) | PUT /v1/users/{id} | Postman: `tools/call` → update_user |
| Delete user | [mcp_server/server.py](../mcp_server/server.py#L71) | DELETE /v1/users/{id} | Postman: `tools/call` → delete_user |
| Tool discovery | [agent/mcp_client.py](../agent/mcp_client.py#L121) | N/A (MCP protocol) | Postman: `tools/list` |
| Resource access | [agent/mcp_client.py](../agent/mcp_client.py#L190) | N/A (MCP protocol) | Postman: `resources/list` |
| Prompt retrieval | [agent/mcp_client.py](../agent/mcp_client.py#L242) | N/A (MCP protocol) | Postman: `prompts/list` |

---

**Next:** [Setup Guide](./setup.md) for environment configuration  
**See also:** [Architecture](./architecture.md) for data flow diagrams
