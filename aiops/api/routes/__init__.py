"""API Routes

This module exports all API route modules for the AIOps platform.
"""

from aiops.api.routes import (
    agents,
    analytics,
    health,
    llm,
    notifications,
    system,
    webhooks,
)

__all__ = [
    "agents",
    "analytics",
    "health",
    "llm",
    "notifications",
    "system",
    "webhooks",
]
