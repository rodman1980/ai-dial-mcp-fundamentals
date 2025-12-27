"""
User Information Data Models

Pydantic models for user CRUD operations via MCP server tools. Provides request/response
validation and serialization for User Service REST API interactions.

MODEL HIERARCHY:
- Address: Nested model for user physical address
- CreditCard: Nested model for payment information
- UserCreate: Request schema for POST /v1/users (create new user, all fields required except optional ones)
- UserUpdate: Request schema for PUT /v1/users/{id} (patch user, all fields optional for selective updates)
- UserSearchRequest: Query schema for GET /v1/users/search (optional filters by name/email/surname/gender)

VALIDATION:
- Pydantic automatically validates types at instantiation time (raises ValidationError if invalid)
- Required fields have no default; optional fields have None default
- String formats not validated here (done by User Service backend)

ERROR HANDLING:
- Missing required fields raise ValidationError (caught by MCP server tools)
- Type mismatches raise ValidationError (e.g., salary must be float, not string)
- Extra fields are silently ignored by default Pydantic behavior
"""
from typing import Optional

from pydantic import BaseModel


class Address(BaseModel):
    """
    Physical address nested model.
    
    Used as optional nested object in UserCreate and UserUpdate.
    All fields required when address is provided.
    """
    country: str  # Full country name
    city: str     # City name
    street: str   # Street address
    flat_house: str  # Apartment/unit number (e.g., "Apt 123")


class CreditCard(BaseModel):
    """
    Payment card nested model.
    
    Used as optional nested object in UserCreate and UserUpdate.
    All fields required when credit card is provided.
    
    WARNING: Fields store non-functional test data (not real payment processing).
    """
    num: str      # 16-digit card number (format: XXXX-XXXX-XXXX-XXXX)
    cvv: str      # 3-digit verification code
    exp_date: str  # Expiration date (format: MM/YYYY, must be future date)


class UserCreate(BaseModel):
    """
    Request schema for creating a new user (POST /v1/users).
    
    All required fields must be provided; optional fields default to None.
    
    Validation:
    - Pydantic validates types automatically (raises ValidationError if invalid)
    - Empty strings are allowed (not validated for length/format here)
    - address and credit_card must be valid nested objects if provided
    
    Usage:
        user_data = UserCreate(name="John", surname="Doe", email="john@example.com", about_me="...")
        user_create_json = user_data.model_dump()  # For JSON serialization
    """
    # Required fields (all must be provided)
    name: str
    surname: str
    email: str
    about_me: str
    
    # Optional fields (default to None if not provided)
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[Address] = None
    gender: Optional[str] = None
    company: Optional[str] = None
    salary: Optional[float] = None
    credit_card: Optional[CreditCard] = None


class UserUpdate(BaseModel):
    """
    Request schema for updating an existing user (PUT /v1/users/{user_id}).
    
    All fields are optional (PATCH-like semantics). Only provided fields are updated.
    
    Validation:
    - Pydantic validates types automatically (raises ValidationError if invalid)
    - All fields default to None, allowing selective updates
    - address and credit_card must be valid nested objects if provided
    
    Usage:
        partial_update = UserUpdate(name="Jane")  # Only update name
        update_json = partial_update.model_dump()
    
    NOTE: credit_card field has type annotation bug (should be CreditCard, not UserCreate).
    See TODO in code refactoring section.
    """
    # All fields are optional for selective updates (PATCH semantics)
    name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[Address] = None
    gender: Optional[str] = None
    company: Optional[str] = None
    salary: Optional[float] = None
    credit_card: Optional[CreditCard] = None  # TODO: Fix type hint (currently UserCreate, should be CreditCard)


class UserSearchRequest(BaseModel):
    """
    Query schema for searching users (GET /v1/users/search?name=...&email=...).
    
    All fields are optional (can combine multiple criteria for AND filtering).
    
    Validation:
    - Pydantic validates types automatically
    - Empty query (all None) returns all users
    - Partial matches: name="john" finds John, Johnny, Johnson (case-insensitive)
    
    Search semantics:
    - name, surname, email: Partial matching (case-insensitive substring)
    - gender: Exact match (male, female, other, prefer_not_to_say)
    - Multiple criteria: AND logic (all must match)
    
    Usage:
        search = UserSearchRequest(name="john", gender="male")  # Find males named John*
        params = search.model_dump(exclude_none=True)  # For query params
    """
    # All fields are optional filters for search query
    name: Optional[str] = None      # Partial first name match (e.g., "john")
    surname: Optional[str] = None   # Partial last name match
    email: Optional[str] = None     # Partial email match (e.g., "gmail" for Gmail users)
    gender: Optional[str] = None    # Exact gender match
