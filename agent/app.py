"""
User Management Agent Application

Orchestrates an interactive console chat with an AI agent that can perform user CRUD operations
via an MCP (Model Context Protocol) server. Connects to a local MCP server, discovers tools/resources,
integrates with Azure OpenAI via DIAL API, and maintains a persistent conversation loop.

EXECUTION FLOW:
1. Connect to MCP server, discover available tools and resources
2. Initialize DialClient with Azure OpenAI API credentials and MCP tools
3. Build initial message history: system prompt + MCP server prompts
4. Enter interactive console loop: accept user input → send to LLM → execute tool calls → iterate
5. Gracefully exit on quit commands, preserving conversation history until shutdown
6. Error handling: network/API failures logged to user without terminating loop

External dependencies:
- MCP Server (localhost:8005) for user management tools [requires Docker User Service running]
- Azure OpenAI endpoint + DIAL_API_KEY environment variable [requires EPAM VPN]
"""
import asyncio
import json
import os

from mcp import Resource
from mcp.types import Prompt

from agent.mcp_client import MCPClient
from agent.dial_client import DialClient
from agent.models.message import Message, Role
from agent.prompts import SYSTEM_PROMPT


async def main():
    """
    Main entry point for the User Management Agent.
    
    Responsibilities:
    - Establish MCP client connection and discover available tools/resources
    - Initialize Azure OpenAI client with tool definitions
    - Maintain conversation history and route user queries through LLM + tool execution loop
    - Provide user feedback at each stage (initialization, tool discovery, chat ready, chat loop)
    
    Environment variables (REQUIRED):
    - DIAL_API_KEY: Azure OpenAI API key for authentication
    - DIAL_API_ENDPOINT (optional): Azure OpenAI endpoint; defaults to placeholder if not set
    
    Raises:
    - RuntimeError if MCP server is unreachable or DIAL_API_KEY is not set
    """
    print("[App] Starting User Management Agent...")
    
    # Configuration: MCP server and DIAL API endpoints
    mcp_server_url = "http://localhost:8005/mcp"
    dial_api_key = os.environ.get("DIAL_API_KEY")
    dial_endpoint = os.environ.get("DIAL_API_ENDPOINT", "https://YOUR_AZURE_OPENAI_ENDPOINT")

    # STEP 1: Connect to MCP server (async context manager ensures cleanup on exit)
    async with MCPClient(mcp_server_url) as mcp_client:
        # Discover available resources (e.g., flow diagrams, API documentation)
        # Note: Not all MCP servers provide resources; graceful fallback to empty list in MCPClient
        resources = await mcp_client.get_resources()
        print(f"[App] MCP Resources: {[r.uri for r in resources]}")

        # Discover available tools (CRUD operations on users) and transform to DIAL format
        # These tools are passed to LLM so it can decide when/how to call them
        tools = await mcp_client.get_tools()
        print(f"[App] MCP Tools: {[t['function']['name'] for t in tools]}")

        # STEP 2: Initialize DIAL client (LLM orchestrator) with discovered tools
        # DIAL client will handle streaming responses and tool call recursion
        dial_client = DialClient(
            api_key=dial_api_key,
            endpoint=dial_endpoint,
            tools=tools,
            mcp_client=mcp_client
        )

        # STEP 3: Build conversation history with system prompt and MCP prompts
        # System prompt defines agent behavior; MCP prompts provide domain-specific guidance
        messages = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]

        # Add MCP server prompts to message history (e.g., search helper, profile creation guide)
        # These provide LLM with best practices for using the tools
        prompts = await mcp_client.get_prompts()
        for prompt in prompts:
            # Use description if available; fall back to name
            messages.append(Message(role=Role.USER, content=prompt.description or prompt.name))

        print("[App] User Management Agent is ready. Type your message (type 'exit', 'quit', or 'q' to stop):")

        # STEP 4: Interactive chat loop - accept user input and maintain conversation
        while True:
            # Read user input from console (blocking; no timeout)
            user_input = input("You: ").strip()
            
            # Exit gracefully on quit commands
            if user_input.lower() in {"exit", "quit", "q"}:
                print("[App] Exiting chat. Goodbye!")
                break
            
            # Skip empty input (user just pressed Enter)
            if not user_input:
                continue
            
            # Add user message to conversation history (preserved across iterations)
            messages.append(Message(role=Role.USER, content=user_input))
            
            # Send message to LLM and get response (with automatic tool call handling)
            # DialClient.get_completion() recursively calls LLM until no tool calls remain
            try:
                ai_message = await dial_client.get_completion(messages)
                messages.append(ai_message)
                # Conversation continues in next iteration with full history intact
            except Exception as e:
                # Error handling: log issue but don't crash loop - user can retry
                # This allows recovery from transient API failures or network issues
                print(f"[App] Error: {e}")


if __name__ == "__main__":
    # Entry point: run async main() using asyncio event loop
    asyncio.run(main())
