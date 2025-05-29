"""
Vercel API entry point for the Inbox Zen MCP Email Processing Server
This file serves as the main FastAPI app for Vercel's serverless deployment
"""

import os
import sys
from pathlib import Path

# Add the project root and src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Apply serverless optimizations
try:
    from .serverless_utils import IS_SERVERLESS, optimize_for_serverless

    if IS_SERVERLESS:
        optimize_for_serverless()
except ImportError:
    IS_SERVERLESS = False

# Import the FastAPI app from webhook.py
from src.webhook import app

# Vercel expects the ASGI app to be named 'app'
# The FastAPI app from webhook.py is already named 'app', so we can use it directly
app = app

# For local development compatibility
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
