"""Configuration management for MCP Client"""
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import json

load_dotenv()


class MCPServerConfig(BaseModel):
    """MCP Server configuration (SSE-based)"""
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    token: Optional[str] = None
    timeout: int = 30
    sse_read_timeout: int = 300
    enabled: bool = True


class AppConfig(BaseModel):
    """Application configuration"""
    openai_api_key: str = Field(default="")
    mcpServers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    
    @classmethod
    def load_from_env(cls) -> "AppConfig":
        """Load configuration from environment"""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            mcpServers={}
        )
    
    def save_to_file(self, filepath: str = "config.json"):
        """Save configuration to file"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, filepath: str = "config.json") -> "AppConfig":
        """Load configuration from file"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        except FileNotFoundError:
            return cls.load_from_env()


# Global config instance
config = AppConfig.load_from_file()
