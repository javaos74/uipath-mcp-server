"""Main entry point for running the HTTP Streamable MCP server."""

import uvicorn
import os


def main():
    """Run the HTTP Streamable MCP server."""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "src.http_server:app",
        host=host,
        port=port,
        log_level="info",
        reload=True
    )


if __name__ == "__main__":
    main()
