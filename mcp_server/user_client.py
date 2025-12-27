"""
User Management REST Client

HTTP client wrapper for the User Service API (Docker, localhost:8041). Provides async methods
for user CRUD operations (get, search, create, update, delete). Formats responses as code-block
strings for LLM consumption via MCP server tools.

EXECUTION FLOW:
1. Each method constructs GET/POST/PUT/DELETE request to User Service endpoint
2. Sets JSON content-type header and passes query params or request body
3. Raises exception on HTTP error (4xx/5xx); returns string on success (200/201/204)
4. Formats JSON responses via __user_to_string() / __users_to_string() for readability
5. Returns markdown code blocks so LLM can read structured user data

Error handling:
- Network failures raise exceptions (user_client.py doesn't retry)
- HTTP errors (404, 500, etc.) include status code + response body
- Success codes: 200 (GET), 201 (POST/PUT), 204 (DELETE with no body)

External dependencies:
- User Service REST API on localhost:8041 (configurable via USERS_MANAGEMENT_SERVICE_URL)
- Docker container must be running: docker-compose up -d
"""
import os
from typing import Any, Optional

import requests

from models.user_info import UserUpdate, UserCreate

# User Service endpoint from env var with default to localhost (for local dev/testing)
USER_SERVICE_ENDPOINT = os.getenv("USERS_MANAGEMENT_SERVICE_URL", "http://localhost:8041")

class UserClient:
    """
    HTTP client for User Service REST API.
    
    Responsibilities:
    - Wrap REST API calls (GET/POST/PUT/DELETE) with JSON headers
    - Format responses as markdown code blocks for readability
    - Raise exceptions on HTTP errors (4xx/5xx)
    - Return string results (not raw JSON) for consumption by MCP server
    
    Note: Methods are marked async for consistency with MCP server pattern, but use
    synchronous requests.get/post/put/delete. A future refactor could use httpx or aiohttp
    for true async HTTP (see TODO below).
    
    TODO: Migrate to aiohttp or httpx for true async I/O instead of blocking requests.
    """

    def __user_to_string(self, user: dict[str, Any]) -> str:
        """
        Format single user dict as markdown code block.
        
        Converts {"id": 1, "name": "John", ...} to:
        ```
          id: 1
          name: John
          ...
        ```
        This format is readable by LLM and preserves all fields.
        
        Args:
            user: User data dict from User Service API
            
        Returns:
            str: Markdown code block (triple backticks wrapper)
        """
        user_str = "```\n"
        # Iterate all user fields with 2-space indent for readability
        for key, value in user.items():
            user_str += f"  {key}: {value}\n"
        user_str += "```\n"

        return user_str

    def __users_to_string(self, users: list[dict[str, Any]]) -> str:
        """
        Format multiple user dicts as concatenated markdown code blocks.
        
        Used by search_users() to return list of matching users.
        Each user is formatted via __user_to_string(), then joined.
        
        Args:
            users: List of user dicts from User Service search API
            
        Returns:
            str: Multiple markdown code blocks (one per user), separated by newlines
        """
        users_str = ""
        # Concatenate each user's formatted code block
        for value in users:
            users_str += self.__user_to_string(value)
        users_str += "\n"

        return users_str

    async def get_user(self, user_id: int) -> str:
        """
        Retrieve a single user by ID.
        
        HTTP GET /v1/users/{user_id} -> parse JSON -> format as code block
        
        Args:
            user_id: User ID (integer)
            
        Returns:
            str: Markdown code block with user data
            
        Raises:
            Exception: If user not found (404) or service unavailable (5xx)
        """
        headers = {"Content-Type": "application/json"}

        # HTTP GET to fetch single user by ID
        response = requests.get(url=f"{USER_SERVICE_ENDPOINT}/v1/users/{user_id}", headers=headers)

        # Success case: HTTP 200 with JSON user object
        if response.status_code == 200:
            data = response.json()
            return self.__user_to_string(data)

        # Error case: include status code and response body for debugging
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    async def search_users(
            self,
            name: Optional[str] = None,
            surname: Optional[str] = None,
            email: Optional[str] = None,
            gender: Optional[str] = None,
    ) -> str:
        """
        Search for users by partial criteria (name, surname, email, gender).
        
        HTTP GET /v1/users/search?name=...&surname=...&email=...&gender=...
        
        Supports partial matching for name/surname/email (case-insensitive).
        Gender uses exact match (male, female, other, prefer_not_to_say).
        
        Args:
            name: Optional partial first name (e.g., 'john' matches John, Johnny)
            surname: Optional partial last name
            email: Optional partial email (e.g., 'gmail' matches all Gmail users)
            gender: Optional exact gender
            
        Returns:
            str: Markdown code blocks with all matching users (can be empty if no matches)
            
        Raises:
            Exception: If service unavailable (5xx)
        """
        headers = {"Content-Type": "application/json"}

        # Build query params: only include non-None criteria
        params = {}
        if name:
            params["name"] = name
        if surname:
            params["surname"] = surname
        if email:
            params["email"] = email
        if gender:
            params["gender"] = gender

        # HTTP GET with query params to search endpoint
        response = requests.get(url=USER_SERVICE_ENDPOINT + "/v1/users/search", headers=headers, params=params)

        # Success: HTTP 200 with JSON array of matching users
        if response.status_code == 200:
            data = response.json()
            # Print count for user feedback during tool execution
            print(f"Get {len(data)} users successfully")
            return self.__users_to_string(data)

        # Error case: include status code and response body
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    async def add_user(self, user_create_model: UserCreate) -> str:
        """
        Create a new user.
        
        HTTP POST /v1/users with UserCreate Pydantic model (serialized to JSON).
        
        Args:
            user_create_model: UserCreate Pydantic model with required fields
                              (name, surname, email, etc.)
            
        Returns:
            str: Confirmation message with created user data
            
        Raises:
            Exception: If email already exists (conflict) or validation fails (4xx/5xx)
        """
        headers = {"Content-Type": "application/json"}

        # HTTP POST with JSON body containing new user data
        response = requests.post(
            url=f"{USER_SERVICE_ENDPOINT}/v1/users",
            headers=headers,
            json=user_create_model.model_dump()  # Pydantic model -> dict -> JSON
        )

        # Success: HTTP 201 Created with new user data in response
        if response.status_code == 201:
            return f"User successfully added: {response.text}"

        # Error case: unique constraint, validation, or server error
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    async def update_user(self, user_id: int, user_update_model: UserUpdate) -> str:
        """
        Update an existing user by ID.
        
        HTTP PUT /v1/users/{user_id} with UserUpdate Pydantic model.
        Only fields present in the model are updated (PATCH-like semantics).
        
        Args:
            user_id: ID of user to update
            user_update_model: UserUpdate Pydantic model with optional fields to update
            
        Returns:
            str: Confirmation message with updated user data
            
        Raises:
            Exception: If user not found (404), validation fails (4xx), or service unavailable (5xx)
        """
        headers = {"Content-Type": "application/json"}

        # HTTP PUT to update user by ID with JSON body
        response = requests.put(
            url=f"{USER_SERVICE_ENDPOINT}/v1/users/{user_id}",
            headers=headers,
            json=user_update_model.model_dump()  # Pydantic model -> dict -> JSON
        )

        # Success: HTTP 201 with updated user data
        if response.status_code == 201:
            return f"User successfully updated: {response.text}"

        # Error case: user not found, validation error, or server error
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    async def delete_user(self, user_id: int) -> str:
        """
        Delete a user by ID.
        
        HTTP DELETE /v1/users/{user_id} -> returns 204 No Content on success.
        
        Args:
            user_id: ID of user to delete
            
        Returns:
            str: Confirmation message "User successfully deleted"
            
        Raises:
            Exception: If user not found (404) or service unavailable (5xx)
        """
        headers = {"Content-Type": "application/json"}

        # HTTP DELETE to remove user by ID
        response = requests.delete(url=f"{USER_SERVICE_ENDPOINT}/v1/users/{user_id}", headers=headers)

        # Success: HTTP 204 No Content (no response body, user is deleted)
        if response.status_code == 204:
            return "User successfully deleted"

        # Error case: user not found or server error
        raise Exception(f"HTTP {response.status_code}: {response.text}")
