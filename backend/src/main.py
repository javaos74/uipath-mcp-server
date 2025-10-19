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

    # --- 1. 중앙 로깅 설정 (프로그램 시작 시 한 번만!) ---
    log_format = "%(asctime)s - %(name)-15s - %(levelname)-8s - %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,  # 파일에 기록할 최소 레벨
        format=log_format,
        filename=log_file,
        filemode="w",
    )

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(
        "src.http_server:app", host=host, port=port, log_level="info", reload=True
    )


if __name__ == "__main__":
    main()
