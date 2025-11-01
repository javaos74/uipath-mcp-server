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

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "mcp_server.log"

    # --- Logging configuration ---
    log_format = "%(asctime)s - %(name)-15s - %(levelname)-8s - %(message)s"
    # File handler via basicConfig
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        filename=log_file,
        filemode="w",
    )
    # Console handler to surface DEBUG logs in terminal
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    # Make our modules verbose
    logging.getLogger("uipath-mcp-server").setLevel(logging.DEBUG)
    logging.getLogger("mcp").setLevel(logging.DEBUG)
    logging.getLogger("uipath_client").setLevel(logging.DEBUG)
    logging.getLogger("oauth").setLevel(logging.DEBUG)

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(
        "src.http_server:app", host=host, port=port, log_level="debug", reload=True
    )


if __name__ == "__main__":
    main()
