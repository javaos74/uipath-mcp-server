"""Main entry point for running the HTTP Streamable MCP server."""

import uvicorn
import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv


def main():
    """Run the HTTP Streamable MCP server."""
    # Load environment variables from .env file
    # Try to load from backend/.env first, then from parent directory
    backend_env = Path(__file__).parent.parent / ".env"
    root_env = Path(__file__).parent.parent.parent / ".env"

    if backend_env.exists():
        load_dotenv(backend_env)
        logging.info(f"Loaded environment from {backend_env}")
    elif root_env.exists():
        load_dotenv(root_env)
        logging.info(f"Loaded environment from {root_env}")

    # Logging is now configured in http_server.py to work with reload=True
    # This ensures logs are written to file even after auto-reload

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(
        "src.http_server:app", host=host, port=port, log_level="debug", reload=True
    )


if __name__ == "__main__":
    main()
