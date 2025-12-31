---
title: Roadmap & Future Enhancements
description: Planned improvements, known limitations, and long-term vision for the MCP-based agent system
version: 1.0.0
last_updated: 2025-12-31
related: [architecture.md, testing.md]
tags: [roadmap, features, enhancements]
---

# Roadmap & Future Enhancements

## Current Status (v1.0.0)

### Implemented Features ✅
- [x] MCP Server with 5 CRUD tools (get, search, add, update, delete)
- [x] MCP Client with tool discovery and execution
- [x] Agent with recursive completion loop
- [x] Azure OpenAI integration (DIAL API)
- [x] Streaming responses with tool calling
- [x] Docker-based User Service (1000 mock users)
- [x] Postman collection for MCP protocol testing
- [x] Console chat interface
- [x] String-based tool results (LLM-friendly formatting)
- [x] Session management (mcp-session-id)
- [x] Resource support (flow diagram PNG)
- [x] Prompt support (search/creation guidance)

### Known Limitations ⚠️
- Single MCP server connection only (no multi-server support)
- Synchronous UserClient (uses `requests`, not async `aiohttp`)
- No retry logic for network failures
- No caching (repeated tool calls duplicate work)
- No pagination (large search results may truncate)
- No unit tests (manual verification only)
- Message history grows unbounded (no truncation)
- No rate limiting protection (Azure OpenAI throttles)

## Short-Term Roadmap (Next 3 Months)

### Phase 1: Stability & Testing
**Priority:** High  
**Effort:** Medium

- [ ] **Unit Tests**: Add pytest suite for core components
  - `test_mcp_client.py`: Tool discovery, execution, error handling
  - `test_dial_client.py`: Streaming, tool call accumulation, recursion
  - `test_user_client.py`: HTTP calls, response formatting
  - Coverage target: 80%+

- [ ] **Integration Tests**: Automated end-to-end scenarios
  - User lifecycle (create → read → update → delete)
  - Multi-step workflows (search → get → update)
  - Error handling (404, 409, network failures)

- [ ] **Error Handling Improvements**
  - Retry logic with exponential backoff (3 retries, 1s/2s/4s delays)
  - Rate limit detection and cooldown (parse HTTP 429)
  - Connection pooling for User Service HTTP calls

- [ ] **Message History Management**
  - Implement truncation strategy (keep last N messages or token budget)
  - Add conversation summary (compress old messages into system prompt)
  - Configurable history size (env var: MAX_HISTORY_MESSAGES)

### Phase 2: Performance & Scalability
**Priority:** Medium  
**Effort:** Medium

- [ ] **Async HTTP Client**
  - Migrate `user_client.py` from `requests` to `aiohttp`
  - Benefits: True async I/O, connection pooling, better performance
  - Breaking change: None (internal implementation detail)

- [ ] **Tool Result Caching**
  - Cache tool results by (tool_name, args) hash
  - TTL: 60 seconds (configurable)
  - Invalidation: On create/update/delete operations
  - Library: `aiocache` or custom LRU

- [ ] **Pagination Support**
  - Add `limit` and `offset` parameters to `search_user`
  - User Service: Implement pagination endpoints
  - Agent: Handle paginated results (e.g., "Show next 10 users")

- [ ] **Streaming Tool Execution** (Experimental)
  - Stream tool results incrementally (e.g., user records as they're found)
  - Requires MCP protocol extension or custom streaming

### Phase 3: Multi-Server Support
**Priority:** High  
**Effort:** High

#### Problem Statement
Current architecture: 1 MCP client → 1 MCP server (users-management only).

**Desired:** Agent connects to multiple MCP servers simultaneously:
- `users-management` (CRUD operations)
- `fetch` MCP server (web scraping: `https://remote.mcpservers.org/fetch/mcp`)
- Future: `database`, `email`, `calendar` servers

#### Proposed Solution

**Option A: Multiple MCPClient Instances**
```python
# In app.py
async with MCPClient(users_mcp_url) as users_client, \
           MCPClient(fetch_mcp_url) as fetch_client:
    
    # Combine tools from both servers
    all_tools = await users_client.get_tools() + await fetch_client.get_tools()
    
    # Route tool calls to correct client
    dial_client = DialClient(tools=all_tools, clients={
        "users-management": users_client,
        "fetch": fetch_client
    })
```

**Challenge:** How to route tool calls to correct server?

**Solution:** Tool name prefixing or metadata
```python
# Option 1: Prefix tool names
users_client.get_tools() → [{"name": "users.get_user_by_id", ...}]
fetch_client.get_tools() → [{"name": "fetch.get_webpage", ...}]

# Option 2: Add server metadata to tool schema
{"name": "get_user_by_id", "_mcp_server": "users-management", ...}
```

**Implementation:**
```python
# In dial_client.py
async def _call_tools(self, ai_message, messages):
    for tool_call in ai_message.tool_calls:
        tool_name = tool_call["function"]["name"]
        
        # Route to correct client
        if tool_name.startswith("users."):
            client = self.clients["users-management"]
            actual_name = tool_name.replace("users.", "")
        elif tool_name.startswith("fetch."):
            client = self.clients["fetch"]
            actual_name = tool_name.replace("fetch.", "")
        
        result = await client.call_tool(actual_name, args)
```

**Tasks:**
- [ ] Refactor `DialClient` to accept multiple MCP clients
- [ ] Implement tool routing logic
- [ ] Add tool name prefixing or metadata
- [ ] Test with `fetch` MCP server
- [ ] Document multi-server patterns

**Use Case Example:**
```
You: Search Wikipedia for "Albert Einstein" and save his bio to our user database

Agent workflow:
1. ⚙️ fetch.get_webpage(url="https://en.wikipedia.org/wiki/Albert_Einstein")
2. ⚙️ users.add_user(name="Albert", surname="Einstein", about_me="...")
3. Response: "Added Albert Einstein to database (ID: 1001)"
```

## Mid-Term Roadmap (6-12 Months)

### Advanced Features

#### 1. Structured Outputs (OpenAI API)
**Motivation:** JSON outputs for programmatic consumption

**Implementation:**
```python
# Use OpenAI's structured outputs feature
response = await openai.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"}
)
```

**Benefits:**
- Guaranteed valid JSON (no parsing errors)
- Type-safe results (Pydantic validation)
- Better for non-text tools (e.g., data export)

**Trade-off:** Loses string formatting benefits (see ADR-002)

#### 2. Conversation Branching
**Motivation:** Allow users to explore alternative paths

**Feature:**
- Save conversation state at any point
- Fork conversation to explore "what if" scenarios
- Merge branches (combine results from multiple paths)

**Use Case:**
```
Main conversation:
You: Find user Alice
🤖: Found 15 users named Alice

[Branch 1] You: Update the first one's company to EPAM
[Branch 2] You: Delete the first one

User chooses branch and continues from there
```

#### 3. Tool Composition
**Motivation:** Build higher-level tools from primitives

**Example:**
```python
@mcp.tool()
async def transfer_users_between_companies(
    from_company: str,
    to_company: str
) -> str:
    """Composite tool: search → get → update (for each user)."""
    users = await search_user(company=from_company)
    results = []
    for user in users:
        result = await update_user(user['id'], company=to_company)
        results.append(result)
    return format_batch_results(results)
```

**Benefits:**
- Reduce LLM steps (1 composite tool vs. N individual calls)
- Encapsulate domain logic (user doesn't specify workflow)
- Better error handling (atomic operations, rollback)

#### 4. Observability & Monitoring
**Tools:**
- OpenTelemetry for distributed tracing (MCP calls → User Service)
- Prometheus metrics (tool execution latency, error rates)
- Grafana dashboards (real-time agent performance)

**Metrics to Track:**
- Tool call frequency (which tools used most?)
- Average latency per tool
- Error rate by tool and error type
- Conversation length distribution
- Token usage per conversation

#### 5. Authentication & Authorization
**Current:** No security (localhost only)

**Production Requirements:**
- API key authentication for MCP server
- User identity propagation (agent tracks who's calling)
- RBAC: Different users have different tool access
- Audit logging: Track all tool executions with user context

**Implementation:**
```python
# MCP server
@mcp.tool()
async def delete_user(user_id: int, auth_context: dict) -> str:
    if not auth_context.get("is_admin"):
        raise PermissionError("Only admins can delete users")
    return await user_client.delete_user(user_id)
```

### Infrastructure Improvements

#### 1. Production Deployment
**Components:**
- MCP Server: Docker container with health checks
- User Service: Migrate from mock to real database (PostgreSQL)
- Agent: Web API (FastAPI) instead of console chat
- Load Balancer: nginx for horizontal scaling

**Architecture:**
```
[Users] → [API Gateway] → [Agent Service (N replicas)]
                              ↓
                         [MCP Server (N replicas)]
                              ↓
                         [User Service (PostgreSQL)]
```

#### 2. Configuration Management
**Current:** Environment variables hardcoded

**Proposed:** Centralized config (YAML/JSON)
```yaml
# config.yaml
mcp_servers:
  users:
    url: http://localhost:8005/mcp
    enabled: true
  fetch:
    url: https://remote.mcpservers.org/fetch/mcp
    enabled: false

agent:
  max_history_messages: 50
  tool_timeout_seconds: 30
  retry_attempts: 3

dial:
  endpoint: https://ai-proxy.lab.epam.com
  model: gpt-4o
  temperature: 0.0
```

#### 3. CI/CD Pipeline
**GitHub Actions Workflow:**
```yaml
# .github/workflows/test.yml
name: Test & Deploy

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ --cov
      - name: Lint
        run: ruff check .
  
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Build Docker image
        run: docker build -t mcp-server:latest .
      - name: Push to registry
        run: docker push mcp-server:latest
```

## Long-Term Vision (12+ Months)

### Research Areas

#### 1. Autonomous Agent Swarms
**Concept:** Multiple specialized agents collaborate on complex tasks

**Example:**
- Researcher Agent: Scrapes web for information
- Analyzer Agent: Processes data, extracts insights
- Writer Agent: Composes reports
- Coordinator Agent: Orchestrates workflow

**Communication:** Agents use MCP to expose tools to each other

#### 2. Dynamic Tool Generation
**Concept:** Agent learns to create new tools from examples

**Example:**
```
You: I often need to search for users and update their company. Make this easier.

Agent: Created composite tool "update_user_company_by_name"
  - Input: name, new_company
  - Steps: search_user → get_user_by_id → update_user
```

**Implementation:** Code generation + sandboxed execution

#### 3. Tool Marketplace
**Concept:** Centralized registry of MCP servers (like npm for tools)

**Features:**
- Browse available MCP servers by category
- Install/uninstall servers dynamically
- Version management (semver)
- Security scanning (tool permissions, data access)

**Usage:**
```bash
mcp install users-management@2.0.0
mcp install stripe-payments@1.5.2
mcp list
```

#### 4. Multimodal Tools
**Concept:** Tools that accept/return images, audio, video

**Example:**
```python
@mcp.tool()
async def analyze_user_photo(user_id: int, photo: bytes) -> str:
    """Analyze user profile photo for demographics."""
    # Use vision model to extract age, gender, etc.
    return analysis_result
```

**Challenge:** MCP protocol primarily text-based (binary support limited)

## Community & Contributions

### Open Questions
- Should we contribute multi-server support back to FastMCP?
- How to standardize tool naming conventions across MCP servers?
- What's the best caching strategy for tool results?

### Contribution Areas
- Implement features from roadmap
- Write additional tools (email, calendar, database)
- Improve documentation (tutorials, examples)
- Report bugs and suggest enhancements

### Feedback Welcome
- **GitHub Issues:** Feature requests, bug reports
- **Pull Requests:** Code contributions with tests
- **Documentation:** Clarifications, examples, translations

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| MCP protocol breaking changes | High | Medium | Pin FastMCP version, test upgrades in isolation |
| Azure OpenAI rate limits | High | High | Implement retry logic, caching, rate limit detection |
| Python recursion limit hit | Medium | Low | Add max iterations guard, refactor to loop if needed |
| Memory leak (unbounded history) | Medium | Medium | Implement message truncation/summarization |
| User Service database corruption | High | Low | Regular backups, transaction safety |
| Multi-server routing complexity | High | Medium | Thorough testing, clear documentation |
| Security vulnerabilities | High | Medium | Add authentication, input validation, audit logging |

## Success Metrics

### Educational Success
- [ ] 90%+ of users complete setup without issues
- [ ] Users understand MCP protocol after exploring codebase
- [ ] Documentation rated 4+ stars (clarity, completeness)

### Technical Success
- [ ] Agent handles 95%+ of user requests correctly
- [ ] Average tool execution latency < 2 seconds
- [ ] Zero unhandled exceptions in production
- [ ] Test coverage > 80%

### Adoption Success
- [ ] 100+ developers explore the codebase
- [ ] 10+ community contributions (PRs, issues)
- [ ] 3+ derived projects (forks with custom tools)

---

## Summary

**Immediate priorities:**
1. Add unit and integration tests
2. Implement retry logic and error handling
3. Support multiple MCP servers

**Future vision:**
- Production-ready deployment with monitoring
- Agent swarms and tool marketplaces
- Multimodal tool support

**Get involved:**
- Implement roadmap features
- Report bugs and suggest improvements
- Share your MCP server implementations

---

**Last updated:** 2025-12-31  
**Next review:** 2026-03-31  
**Contact:** AI DIAL Team
