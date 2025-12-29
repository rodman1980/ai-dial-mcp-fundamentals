"""
Users Management MCP Server

Exposes CRUD tools for user profile management via MCP (Model Context Protocol).
Provides 5 tools (get, list, search, create, update, delete), 1 resource (flow diagram),
and 2 prompts (search guidance, profile creation guidance) for AI agents to discover and use.

RESPONSIBILITIES:
- HTTP client (UserClient) wraps User Service REST API (Docker, port 8041)
- Tool definitions: Async functions returning formatted strings (user data)
- Resource: PNG image file (flow diagram of API endpoints)
- Prompts: Domain-specific guidance for LLM (search and profile creation best practices)
- Server transport: HTTP streams (streamable-http) for agent-server communication

External dependency:
- User Service (Docker: localhost:8041) - provides REST API for CRUD operations
"""
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from models.user_info import UserSearchRequest, UserCreate, UserUpdate, Address, CreditCard
from user_client import UserClient


# === MCP SERVER INITIALIZATION ===
print("[MCP Server] Initializing...")
# FastMCP server listens on 0.0.0.0:8005 for agent connections
mcp = FastMCP(
    name="users-management-mcp-server",
    host="0.0.0.0",
    port=8005
)
# UserClient wraps HTTP calls to User Service (Docker, port 8041)
user_client = UserClient()
print("[MCP Server] FastMCP and UserClient initialized.")


# ==================== TOOLS ====================
# MCP tools are async functions that return strings (formatted data for LLM)
# Each tool will be discovered by agent and exposed for LLM tool calling

@mcp.tool()
async def get_user_by_id(user_id: int) -> str:
    """
    Retrieve a single user by ID.
    
    Args:
        user_id: Unique user identifier (integer)
        
    Returns:
        str: Formatted user data (all fields in code block)
        
    Error handling:
        Raises if user not found (HTTP 404) or service unavailable
    """
    print(f"[TOOL] get_user_by_id called with user_id={user_id}")
    return await user_client.get_user(user_id)

@mcp.tool()
async def delete_user(user_id: int) -> str:
    """
    Delete a user by ID.
    
    Args:
        user_id: Unique user identifier to delete
        
    Returns:
        str: Confirmation message "User successfully deleted"
        
    Error handling:
        Raises if user not found or service unavailable
    """
    print(f"[TOOL] delete_user called with user_id={user_id}")
    return await user_client.delete_user(user_id)

@mcp.tool()
async def search_user(
    name: Optional[str] = None,
    surname: Optional[str] = None,
    email: Optional[str] = None,
    gender: Optional[str] = None
) -> str:
    """
    Search for users by optional criteria (name, surname, email, gender).
    
    Supports partial matching (case-insensitive) for name/surname/email.
    Gender uses exact matching (male, female, other, prefer_not_to_say).
    
    Args:
        name: Partial first name match (e.g., 'john' finds John, Johnny, etc.)
        surname: Partial last name match
        email: Partial email match (e.g., 'gmail' finds all Gmail users)
        gender: Exact gender match
        
    Returns:
        str: Formatted list of matching users (can be empty)
        
    Notes:
        - All parameters are optional; omit to ignore that criterion
        - Returns count of found users in console for debugging
    """
    print(f"[TOOL] search_user called with name={name}, surname={surname}, email={email}, gender={gender}")
    return await user_client.search_users(name=name, surname=surname, email=email, gender=gender)

@mcp.tool()
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
) -> str:
    """
    Create a new user with provided data.
    
    Required fields: name, surname, email, about_me
    Optional fields: phone, address, company, salary, date_of_birth, gender, credit card
    
    Args:
        name: First name (2-50 characters, letters only)
        surname: Last name (2-50 characters, letters only)
        email: Unique email address (must be unique in system)
        about_me: Biography/description (rich text, 0+ characters)
        phone: Phone number (E.164 format preferred: +1234567890)
        date_of_birth: Birth date (YYYY-MM-DD format)
        gender: Gender (male, female, other, prefer_not_to_say)
        company: Company name
        salary: Annual salary (USD, realistic range: $30k-$200k)
        address: Complete address (country, city, street, flat_house)
        credit_card: Credit card information (num, cvv, exp_date)
        
    Returns:
        str: Confirmation message with user data (HTTP 201 Created)
        
    Error handling:
        Raises if email already exists or service unavailable
    """
    print(f"[TOOL] add_user called with email={email}")
    address_obj = Address(**address) if address else None
    credit_card_obj = CreditCard(**credit_card) if credit_card else None

    user = UserCreate(
        name=name,
        surname=surname,
        email=email,
        about_me=about_me,
        phone=phone,
        date_of_birth=date_of_birth,
        gender=gender,
        company=company,
        salary=salary,
        address=address_obj,
        credit_card=credit_card_obj
    )
    return await user_client.add_user(user)

@mcp.tool()
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
) -> str:
    """
    Update an existing user by ID. Only provided fields are updated (PATCH semantics).
    
    Args:
        user_id: ID of user to update
        All other args: Same as add_user, but optional (only updates provided fields)
        
    Returns:
        str: Confirmation message with updated user data (HTTP 201)
        
    Error handling:
        Raises if user not found (HTTP 404) or service unavailable
    """
    print(f"[TOOL] update_user called for user_id={user_id}")
    address_obj = Address(**address) if address else None
    credit_card_obj = CreditCard(**credit_card) if credit_card else None

    user_update = UserUpdate(
        name=name,
        surname=surname,
        email=email,
        phone=phone,
        date_of_birth=date_of_birth,
        gender=gender,
        company=company,
        salary=salary,
        address=address_obj,
        credit_card=credit_card_obj
    )
    return await user_client.update_user(user_id, user_update)

# ==================== MCP RESOURCES ====================
# Resources are static assets (images, docs, etc.) that agents can retrieve
# Not all servers have resources; this one provides a flow diagram

@mcp.resource(uri="users-management://flow-diagram", mime_type="image/png")
async def get_flow_diagram() -> bytes:
    """
    Retrieve a PNG image of the User Service API flow (Swagger screenshot).
    
    Resource URI: users-management://flow-diagram
    MIME type: image/png (binary content)
    
    Returns:
        bytes: PNG image data loaded from flow.png file
        
    Notes:
        - File must exist at mcp_server/flow.png
        - Useful for showing API endpoints available in User Service
    """
    print("[RESOURCE] get_flow_diagram called, returning flow.png bytes.")
    flow_path = Path(__file__).parent / "flow.png"
    with open(flow_path, "rb") as f:
        return f.read()


# ==================== MCP PROMPTS ====================
# Prompts provide domain-specific guidance to LLM clients
# These are discoverable by agents and can be included in message history

@mcp.prompt()
async def search_helper_prompt() -> str:
    """
    Provide guidance for formulating effective user search queries.
    
    This prompt is included in agent message history to guide LLM on:
    - Available search fields (name, surname, email, gender)
    - Partial matching semantics (case-insensitive)
    - Example search patterns and combinations
    - Best practices for targeted searches
    
    Returns:
        str: Multi-line guidance text for LLM
    """
    return (
        "You are helping users search through a dynamic user database. The database contains "
        "realistic synthetic user profiles with the following searchable fields:\n"
        "\n## Available Search Parameters\n"
        "- **name**: First name (partial matching, case-insensitive)\n"
        "- **surname**: Last name (partial matching, case-insensitive)\n"
        "- **email**: Email address (partial matching, case-insensitive)\n"
        "- **gender**: Exact match (male, female, other, prefer_not_to_say)\n"
        "\n## Search Strategy Guidance\n"
        "... (see README for full text) ..."
    )

@mcp.prompt()
async def profile_creator_prompt() -> str:
    """
    Provide guidance for creating realistic user profiles.
    
    This prompt is included in agent message history to guide LLM on:
    - Required fields (name, surname, email, about_me)
    - Optional fields (phone, date_of_birth, address, company, credit card)
    - Data validation rules (format, constraints, uniqueness)
    - Realistic value ranges (salary, age distribution)
    - Cultural sensitivity and diversity best practices
    
    Returns:
        str: Multi-line guidance text for LLM
    """
    return (
        "You are helping create realistic user profiles for the system. Follow these guidelines "
        "to ensure data consistency and realism.\n"
        "\n## Required Fields\n"
        "- **name**: 2-50 characters, letters only, culturally appropriate\n"
        "- **surname**: 2-50 characters, letters only  \n"
        "- **email**: Valid format, must be unique in system\n"
        "- **about_me**: Rich, realistic biography (see guidelines below)\n"
        "... (see README for full text) ..."
    )

# Reference text (kept for documentation, not returned as prompt)
"""
You are helping users search through a dynamic user database. The database contains 
realistic synthetic user profiles with the following searchable fields:

## Available Search Parameters
- **name**: First name (partial matching, case-insensitive)
- **surname**: Last name (partial matching, case-insensitive)  
- **email**: Email address (partial matching, case-insensitive)
- **gender**: Exact match (male, female, other, prefer_not_to_say)

## Search Strategy Guidance

### For Name Searches
- Use partial names: "john" finds John, Johnny, Johnson, etc.
- Try common variations: "mike" vs "michael", "liz" vs "elizabeth"
- Consider cultural name variations

### For Email Searches  
- Search by domain: "gmail" for all Gmail users
- Search by name patterns: "john" for emails containing john
- Use company names to find business emails

### For Demographic Analysis
- Combine gender with other criteria for targeted searches
- Use broad searches first, then narrow down

### Effective Search Combinations
- Name + Gender: Find specific demographic segments
- Email domain + Surname: Find business contacts
- Partial names: Cast wider nets for common names

## Example Search Patterns
```
"Find all Johns" → name="john"
"Gmail users named Smith" → email="gmail" + surname="smith"  
"Female users with company emails" → gender="female" + email="company"
"Users with Johnson surname" → surname="johnson"
```

## Tips for Better Results
1. Start broad, then narrow down
2. Try variations of names (John vs Johnny)
3. Use partial matches creatively
4. Combine multiple criteria for precision
5. Remember searches are case-insensitive

When helping users search, suggest multiple search strategies and explain 
why certain approaches might be more effective for their goals.
"""


# Guides creation of realistic user profiles
"""
You are helping create realistic user profiles for the system. Follow these guidelines 
to ensure data consistency and realism.

## Required Fields
- **name**: 2-50 characters, letters only, culturally appropriate
- **surname**: 2-50 characters, letters only  
- **email**: Valid format, must be unique in system
- **about_me**: Rich, realistic biography (see guidelines below)

## Optional Fields Best Practices
- **phone**: Use E.164 format (+1234567890) when possible
- **date_of_birth**: YYYY-MM-DD format, realistic ages (18-80)
- **gender**: Use standard values (male, female, other, prefer_not_to_say)
- **company**: Real-sounding company names
- **salary**: $30,000-$200,000 range for employed individuals

## Address Guidelines
Provide complete, realistic addresses:
- **country**: Full country names
- **city**: Actual city names  
- **street**: Realistic street addresses
- **flat_house**: Apartment/unit format (Apt 123, Unit 5B, Suite 200)

## Credit Card Guidelines  
Generate realistic but non-functional card data:
- **num**: 16 digits formatted as XXXX-XXXX-XXXX-XXXX
- **cvv**: 3 digits (000-999)
- **exp_date**: MM/YYYY format, future dates only

## Biography Creation ("about_me")
Create engaging, realistic biographies that include:

### Personality Elements
- 1-3 personality traits (curious, adventurous, analytical, etc.)
- Authentic voice and writing style
- Cultural and demographic appropriateness

### Interests & Hobbies  
- 2-4 specific hobbies or activities
- 1-3 broader interests or passion areas
- 1-2 life goals or aspirations

### Biography Templates
Use varied narrative structures:
- "I'm a [trait] person who loves [hobbies]..."
- "When I'm not working, you can find me [activity]..."  
- "Life is all about balance for me. I enjoy [interests]..."
- "As someone who's [trait], I find great joy in [hobby]..."

## Data Validation Reminders
- Email uniqueness is enforced (check existing users)
- Phone numbers should follow consistent formatting
- Date formats must be exact (YYYY-MM-DD)
- Credit card expiration dates must be in the future
- Salary values should be realistic for the demographic

## Cultural Sensitivity
- Match names to appropriate cultural backgrounds
- Consider regional variations in address formats
- Use realistic company names for the user's location
- Ensure hobbies and interests are culturally appropriate

When creating profiles, aim for diversity in:
- Geographic representation
- Age distribution  
- Interest variety
- Socioeconomic backgrounds
- Cultural backgrounds
"""


# ==================== SERVER ENTRY POINT ====================
if __name__ == "__main__":
    """
    Start the MCP server.
    
    FLOW:
    1. FastMCP server binds to 0.0.0.0:8005
    2. Uses streamable-http transport for bidirectional communication
    3. Agents connect via MCPClient and discover tools/resources/prompts
    4. Server handles concurrent tool calls via async functions
    5. Blocks until process terminated (SIGTERM/SIGINT)
    
    Prerequisites:
    - User Service running on localhost:8041 (docker-compose up -d)
    
    To stop: Ctrl+C or systemctl stop
    """
    print("[MCP Server] Starting server on 0.0.0.0:8005 with streamable-http transport...")
    mcp.run(transport="streamable-http", mount_path="/mcp")
    print("[MCP Server] Server stopped.")
