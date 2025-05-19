"""
Tool Configuration Module

This module defines the configuration models for various tools in the system.
These models are used to configure and initialize tools with their required parameters.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Base configuration for all tools."""

    tool_name: str = Field(..., description="Name of the tool")
    enabled: bool = Field(default=True, description="Whether the tool is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific configuration")

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration including defaults."""
        return self.config


class EmbeddingToolConfig(ToolConfig):
    """Configuration for embedding tool."""

    model_name: str = Field(..., description="Name of the embedding model")
    dimensions: int = Field(default=768, description="Number of dimensions in embeddings")
    batch_size: int = Field(default=32, description="Batch size for processing")
    cache_enabled: bool = Field(default=True, description="Whether to cache embeddings")


class SearchToolConfig(ToolConfig):
    """Configuration for search tool."""

    index_name: str = Field(..., description="Name of the search index")
    max_results: int = Field(default=10, description="Maximum number of results to return")
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum similarity score"
    )
    filters: Dict[str, Any] = Field(default_factory=dict, description="Default search filters")


class CodeToolConfig(ToolConfig):
    """Configuration for code-related tools."""

    language: str = Field(default="python", description="Programming language")
    max_file_size: int = Field(default=1000000, description="Maximum file size in bytes")
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".py", ".js", ".ts", ".html", ".css"],
        description="Allowed file extensions",
    )
    formatting_enabled: bool = Field(default=True, description="Whether to format code")
    linting_enabled: bool = Field(default=True, description="Whether to lint code")
