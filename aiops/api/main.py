"""FastAPI application for AIOps framework.

DEPRECATED: This file is kept for backward compatibility.
The new modular app structure is in aiops.api.app

For new deployments, use:
    from aiops.api.app import app

This file now simply imports and re-exports the app from the new location.
"""

import os
import warnings

# Show deprecation warning in development
if os.getenv("ENVIRONMENT", "development").lower() != "production":
    warnings.warn(
        "aiops.api.main is deprecated. Use aiops.api.app instead.",
        DeprecationWarning,
        stacklevel=2
    )

# Import the new app
from aiops.api.app import app
from aiops import __version__

# Legacy create_app function for backward compatibility
def create_app():
    """Create FastAPI application.

    DEPRECATED: Returns the app from aiops.api.app
    """
    return app


# For direct execution: python -m aiops.api.main
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "aiops.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
