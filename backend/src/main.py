"""Main entry point for running the HTTP Streamable MCP server."""

import uvicorn
import os
import logging
import sys
from pathlib import Path


def main():
    """Run the HTTP Streamable MCP server."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "mcp_server.log"
    
    
    # --- 1. 중앙 로깅 설정 (프로그램 시작 시 한 번만!) ---
    log_format = '%(asctime)s - %(name)-15s - %(levelname)-8s - %(message)s'
    logging.basicConfig(
        level=logging.DEBUG,    # 파일에 기록할 최소 레벨
        format=log_format,
        filename=log_file,
        filemode='w'
    )
    

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
