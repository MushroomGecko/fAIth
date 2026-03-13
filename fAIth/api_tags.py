"""
Centralized API tags for OpenAPI documentation.

Prevents typos and provides a single source of truth for endpoint categorization.
"""

from enum import Enum


class APITags(str, Enum):
    """Tags for organizing API endpoints in OpenAPI documentation."""
    HEALTH = "health"
    AI = "ai"
    BACKEND = "backend"