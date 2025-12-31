---
title: Setup Guide
description: Complete environment setup, dependencies, and configuration for the MCP-based agent system
version: 1.0.0
last_updated: 2025-12-31
related: [README.md, architecture.md, testing.md]
tags: [setup, installation, environment, dependencies]
---

# Setup Guide

## Table of Contents
- [System Requirements](#system-requirements)
- [Initial Setup](#initial-setup)
- [Python Environment](#python-environment)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [Running the System](#running-the-system)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware
- **CPU:** 2+ cores (recommended: 4+)
- **RAM:** 4GB minimum (recommended: 8GB+)
- **Disk:** 2GB free space for Docker images and virtual environment

### Software
- **Operating System:** macOS 10.15+, Linux (Ubuntu 20.04+), Windows 10+ with WSL2
- **Python:** 3.13 (or 3.11+)
- **Docker:** 20.10+ with Docker Compose
- **Network:** EPAM VPN connection for DIAL API access

### External Services
- **Azure OpenAI (DIAL API):** Requires valid API key
- **Internet Connection:** For package installation and API access

## Initial Setup

### 1. Clone Repository

```bash
# Navigate to workspace
cd ~/Documents/git/git.epam.com

# If not already cloned
git clone <repository-url> ai-dial-mcp-fundamentals
cd ai-dial-mcp-fundamentals
```

**Expected structure:**
```
ai-dial-mcp-fundamentals/
├── agent/
├── mcp_server/
├── docker-compose.yml
└── README.md
```

### 2. Check Python Version

```bash
# Verify Python 3.13 is available
python3.13 --version
# Expected output: Python 3.13.x

# Alternative: check any Python 3.11+
python3 --version
```

**If Python 3.13 not found:**
```bash
# macOS (Homebrew)
brew install python@3.13

# Ubuntu/Debian
sudo apt update
sudo apt install python3.13 python3.13-venv

# Windows (WSL2)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.13 python3.13-venv
```

### 3. Check Docker

```bash
# Verify Docker is installed and running
docker --version
docker-compose --version

# Test Docker daemon
docker ps
```

**If Docker not installed:**
- **macOS:** Install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Linux:** Follow [official Docker installation guide](https://docs.docker.com/engine/install/)
- **Windows:** Install [Docker Desktop with WSL2 backend](https://docs.docker.com/desktop/install/windows-install/)

## Python Environment

### Create Virtual Environment

```bash
# Navigate to project root
cd /Users/Dzianis_Haurylovich/Documents/git/git.epam.com/ai-dial-mcp-fundamentals

# Create virtual environment (if not exists)
python3.13 -m venv dial_mcp

# Activate environment
source dial_mcp/bin/activate

# Verify activation (prompt should show "(dial_mcp)")
which python
# Expected: /Users/.../ai-dial-mcp-fundamentals/dial_mcp/bin/python
```

**For Windows (WSL2):**
```bash
source dial_mcp/bin/activate
```

**For Windows (CMD/PowerShell):**
```powershell
dial_mcp\Scripts\activate
```

### Install Dependencies

#### MCP Server Dependencies

```bash
# Activate environment first
source dial_mcp/bin/activate

# Navigate to MCP server directory
cd mcp_server

# Install requirements
pip install -r requirements.txt
```

**mcp_server/requirements.txt:**
```
fastmcp==2.10.1
requests>=2.28.0
aiohttp>=3.8.0
openai>=1.93.3
```

#### Agent Dependencies

```bash
# Navigate to agent directory
cd ../agent

# Install requirements
pip install -r requirements.txt
```

**agent/requirements.txt:**
```
fastmcp==2.10.1
requests>=2.28.0
aiohttp>=3.8.0
openai==1.93.0
```

### Verify Installation

```bash
# Check installed packages
pip list | grep -E "fastmcp|requests|aiohttp|openai"

# Expected output:
# aiohttp          3.13.2
# fastmcp          2.10.1
# openai           1.93.0
# requests         2.28.0
```

## Docker Setup

### Start User Service

```bash
# Navigate to project root
cd /Users/Dzianis_Haurylovich/Documents/git/git.epam.com/ai-dial-mcp-fundamentals

# Start Docker container
docker-compose up -d
```

**Expected output:**
```
Creating network "ai-dial-mcp-fundamentals_default" with the default driver
Creating ai-dial-mcp-fundamentals_userservice_1 ... done
```

### Verify User Service

```bash
# Check container status
docker-compose ps

# Expected output:
# Name                        State    Ports
# userservice_1               Up       0.0.0.0:8041->8000/tcp

# Test API endpoint
curl http://localhost:8041/v1/users | jq length
# Expected: 1000 (number of mock users)
```

### Docker Compose Configuration

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  userservice:
    image: khshanovskyi/mockuserservice:latest
    ports:
      - "8041:8000"  # Host:Container
    environment:
      - PYTHONUNBUFFERED=1
      - GENERATE_USERS=true
      - USER_COUNT=1000
    volumes:
      - ./data:/app/data  # Persistent storage
```

**Data persistence:**
- User data persists in `./data` directory (SQLite database)
- Delete `./data` to reset users to fresh 1000 mock profiles

### Docker Management

```bash
# Stop User Service
docker-compose down

# Restart with fresh data
rm -rf data/
docker-compose up -d

# View logs
docker-compose logs -f userservice

# Remove all containers
docker-compose down -v
```

## Environment Variables

### Required Variables

#### DIAL_API_KEY

Azure OpenAI API key for DIAL API access.

```bash
# Set for current session
export DIAL_API_KEY="your-api-key-here"

# Persistent (add to ~/.bashrc or ~/.zshrc)
echo 'export DIAL_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**How to obtain:**
1. Contact AI DIAL team for API key
2. Ensure EPAM VPN is connected
3. Verify access to `https://ai-proxy.lab.epam.com`

#### DIAL_API_ENDPOINT (Optional)

Custom DIAL API endpoint (defaults to EPAM proxy).

```bash
# Default (if not set)
export DIAL_API_ENDPOINT="https://ai-proxy.lab.epam.com"
```

#### USERS_MANAGEMENT_SERVICE_URL (Optional)

Custom User Service endpoint (defaults to localhost).

```bash
# Default (if not set)
export USERS_MANAGEMENT_SERVICE_URL="http://localhost:8041"

# For remote User Service
export USERS_MANAGEMENT_SERVICE_URL="http://remote-host:8041"
```

### Verification

```bash
# Check all environment variables
echo $DIAL_API_KEY        # Should show your API key
echo $DIAL_API_ENDPOINT   # Should show endpoint URL (or empty for default)

# Test DIAL API access (requires VPN)
curl -H "Authorization: Bearer $DIAL_API_KEY" \
     https://ai-proxy.lab.epam.com/openai/deployments
```

## Running the System

### Full System Startup

**Terminal 1: User Service (Docker)**
```bash
cd /Users/Dzianis_Haurylovich/Documents/git/git.epam.com/ai-dial-mcp-fundamentals
docker-compose up -d
```

**Terminal 2: MCP Server**
```bash
cd /Users/Dzianis_Haurylovich/Documents/git/git.epam.com/ai-dial-mcp-fundamentals
source dial_mcp/bin/activate
python mcp_server/server.py
```

**Expected output:**
```
[MCP Server] Initializing...
[MCP Server] FastMCP and UserClient initialized.
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8005
```

**Terminal 3: Agent**
```bash
cd /Users/Dzianis_Haurylovich/Documents/git/git.epam.com/ai-dial-mcp-fundamentals
source dial_mcp/bin/activate
export DIAL_API_KEY="your-api-key-here"
python agent/app.py
```

**Expected output:**
```
[App] Starting User Management Agent...
[MCPClient] Connecting to MCP server at http://localhost:8005/mcp ...
[MCPClient] Connected. Capabilities: {'tools': {}, 'resources': {}, 'prompts': {}}
[App] MCP Resources: ['file:///static/flow.png']
[App] MCP Tools: ['get_user_by_id', 'search_user', 'add_user', 'update_user', 'delete_user']
[DialClient] Initializing with endpoint: https://ai-proxy.lab.epam.com
[App] User Management Agent is ready. Type your message (type 'exit', 'quit', or 'q' to stop):
You: 
```

### Individual Components

#### Run MCP Server Only

```bash
source dial_mcp/bin/activate
python mcp_server/server.py
# Server runs on http://localhost:8005/mcp
```

#### Run Agent Only (requires MCP server)

```bash
source dial_mcp/bin/activate
export DIAL_API_KEY="your-api-key-here"
python agent/app.py
```

## Verification

### Test MCP Server

```bash
# From another terminal
curl http://localhost:8005/mcp

# Expected: MCP server info or error if not ready
```

### Test User Service

```bash
# Get first 5 users
curl http://localhost:8041/v1/users | jq '.[0:5]'

# Search for users named "John"
curl "http://localhost:8041/v1/users/search?name=John" | jq length

# Get user by ID
curl http://localhost:8041/v1/users/1 | jq .name
```

### Test Agent

```bash
# In agent terminal
You: search for users named Alice
🤖: Found 15 users matching "Alice"...

You: get details for user ID 1
🤖: User ID: 1
    Name: ...
```

### End-to-End Test

```bash
# In agent terminal
You: Find a user named Bob, then update his company to EPAM
🤖: ⚙️ [Executes search_user]
    ⚙️ [Executes update_user]
    Updated Bob's company to EPAM successfully.
```

## Troubleshooting

### Common Issues

#### 1. "MCP client not connected"

**Symptom:**
```
RuntimeError: MCP client not connected. Call connect() first.
```

**Cause:** Forgot to use async context manager

**Solution:**
```python
# Correct usage
async with MCPClient(url) as mcp_client:
    tools = await mcp_client.get_tools()
```

#### 2. "Connection refused" (MCP Server)

**Symptom:**
```
ConnectionError: Failed to connect to http://localhost:8005/mcp
```

**Cause:** MCP server not running

**Solution:**
```bash
# Start MCP server in separate terminal
python mcp_server/server.py
```

#### 3. "User Service unreachable"

**Symptom:**
```
requests.exceptions.ConnectionError: http://localhost:8041
```

**Cause:** Docker container not running

**Solution:**
```bash
# Check container status
docker-compose ps

# Start if not running
docker-compose up -d

# View logs if failing
docker-compose logs userservice
```

#### 4. "DIAL_API_KEY not set"

**Symptom:**
```
KeyError: 'DIAL_API_KEY'
```

**Cause:** Missing environment variable

**Solution:**
```bash
export DIAL_API_KEY="your-api-key-here"
python agent/app.py
```

#### 5. "Module not found"

**Symptom:**
```
ModuleNotFoundError: No module named 'fastmcp'
```

**Cause:** Virtual environment not activated or dependencies not installed

**Solution:**
```bash
source dial_mcp/bin/activate
pip install -r agent/requirements.txt
pip install -r mcp_server/requirements.txt
```

#### 6. "Tool call failed"

**Symptom:**
```
[DialClient] Tool execution error: ...
```

**Cause:** MCP server error or User Service unavailable

**Solution:**
1. Check MCP server logs (Terminal 2)
2. Verify User Service: `curl http://localhost:8041/v1/users`
3. Check Docker: `docker-compose ps`

#### 7. "Streaming timeout"

**Symptom:**
```
asyncio.TimeoutError: Azure OpenAI streaming timeout
```

**Cause:** Network issue or DIAL API rate limit

**Solution:**
1. Check EPAM VPN connection
2. Verify API key: `echo $DIAL_API_KEY`
3. Wait 60 seconds (rate limit cooldown)

### Diagnostic Commands

```bash
# Check all services
docker-compose ps                    # User Service status
curl http://localhost:8041/v1/users  # User Service API
curl http://localhost:8005/mcp       # MCP Server status
python -c "import fastmcp; print(fastmcp.__version__)"  # FastMCP version

# Check environment
echo $DIAL_API_KEY                   # API key set?
echo $DIAL_API_ENDPOINT              # Custom endpoint?
which python                         # Virtual env active?
pip list | grep fastmcp              # Dependencies installed?

# Network diagnostics
ping ai-proxy.lab.epam.com           # DIAL API reachable? (requires VPN)
curl -I http://localhost:8005        # MCP Server responding?
docker logs ai-dial-mcp-fundamentals_userservice_1  # User Service logs
```

### Clean Restart

```bash
# Stop all services
docker-compose down

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +

# Recreate virtual environment
rm -rf dial_mcp
python3.13 -m venv dial_mcp
source dial_mcp/bin/activate
pip install -r agent/requirements.txt
pip install -r mcp_server/requirements.txt

# Reset User Service data
rm -rf data/

# Start fresh
docker-compose up -d
python mcp_server/server.py  # Terminal 2
python agent/app.py          # Terminal 3
```

## Configuration Files

### Project Root Files

#### .gitignore (Recommended)

```gitignore
# Virtual environment
dial_mcp/
venv/
env/

# Python cache
__pycache__/
*.pyc
*.pyo

# Docker data
data/

# Environment variables (keep secrets out of Git)
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
```

#### .env (Optional)

```bash
# DIAL API Configuration
DIAL_API_KEY=your-api-key-here
DIAL_API_ENDPOINT=https://ai-proxy.lab.epam.com

# User Service Configuration
USERS_MANAGEMENT_SERVICE_URL=http://localhost:8041

# MCP Server Configuration
MCP_SERVER_URL=http://localhost:8005/mcp
```

**Load .env file:**
```bash
# Install python-dotenv
pip install python-dotenv

# In Python code
from dotenv import load_dotenv
load_dotenv()
```

## Next Steps

1. **Run system tests:** See [Testing Guide](./testing.md)
2. **Explore API:** See [API Reference](./api.md)
3. **Understand architecture:** See [Architecture](./architecture.md)

---

**Need help?** Check [Troubleshooting](#troubleshooting) or [Glossary](./glossary.md) for terminology.
