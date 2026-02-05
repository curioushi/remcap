"""Configuration loading and validation using Pydantic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ServerConfig(BaseModel):
    """Server configuration."""

    port: int = Field(default=9876, ge=1, le=65535)


class BackendConfig(BaseModel):
    """Backend configuration."""

    type: Literal["rerun", "foxglove"] = "rerun"
    server: ServerConfig = Field(default_factory=ServerConfig)


class DataConfig(BaseModel):
    """Data configuration for a client."""

    type: Literal["points3d", "image", "text", "mesh"]
    size: int | str = Field(
        description="Size of data: int for points3d/text/mesh, 'WxH' for image"
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int | str, info: Any) -> int | str:
        if isinstance(v, str):
            if "x" not in v.lower():
                raise ValueError(f"Image size must be in format 'WxH', got: {v}")
            parts = v.lower().split("x")
            if len(parts) != 2:
                raise ValueError(f"Image size must be in format 'WxH', got: {v}")
            try:
                w, h = int(parts[0]), int(parts[1])
                if w <= 0 or h <= 0:
                    raise ValueError("Width and height must be positive")
            except ValueError as e:
                raise ValueError(f"Invalid image size format: {v}") from e
        elif isinstance(v, int):
            if v <= 0:
                raise ValueError("Size must be positive")
        return v

    def get_image_dimensions(self) -> tuple[int, int]:
        """Get image dimensions if data type is image."""
        if not isinstance(self.size, str):
            raise ValueError("Image size must be a string in format 'WxH'")
        parts = self.size.lower().split("x")
        return int(parts[0]), int(parts[1])


class ClientConfig(BaseModel):
    """Client configuration."""

    language: Literal["python", "cpp", "rust"] = "python"
    count: int = Field(default=1, ge=1)
    data: DataConfig
    frequency_hz: float = Field(default=30.0, gt=0)


class MetricsConfig(BaseModel):
    """Metrics collection configuration."""

    class ServerMetricsConfig(BaseModel):
        memory_sample_interval_ms: int = Field(default=100, ge=10)

    server: ServerMetricsConfig = Field(default_factory=ServerMetricsConfig)
    output_dir: str = "./results"


class BenchmarkConfig(BaseModel):
    """Root benchmark configuration."""

    name: str
    description: str = ""
    duration_sec: float = Field(default=10.0, gt=0)
    backend: BackendConfig = Field(default_factory=BackendConfig)
    clients: list[ClientConfig] = Field(min_length=1)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    @classmethod
    def from_file(cls, path: str | Path) -> BenchmarkConfig:
        """Load configuration from a JSON file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return cls.model_validate(data)

    def to_file(self, path: str | Path) -> None:
        """Save configuration to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)

    def get_total_client_count(self) -> int:
        """Get the total number of client processes."""
        return sum(c.count for c in self.clients)


def load_config(path: str | Path) -> BenchmarkConfig:
    """Load and validate a benchmark configuration file."""
    return BenchmarkConfig.from_file(path)
