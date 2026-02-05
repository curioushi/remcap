"""Abstract base classes for backend implementations."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ServerConfig:
    """Configuration for a server instance."""

    port: int = 9876
    memory_sample_interval_ms: int = 100

    @classmethod
    def from_config(cls, backend_config: Any, metrics_config: Any) -> ServerConfig:
        return cls(
            port=backend_config.server.port,
            memory_sample_interval_ms=metrics_config.server.memory_sample_interval_ms,
        )


@dataclass
class ClientConfig:
    """Configuration for a client instance."""

    language: str
    data_type: str
    data_size: int | str
    frequency_hz: float
    duration_sec: float

    @classmethod
    def from_config(cls, client_config: Any, duration_sec: float) -> ClientConfig:
        return cls(
            language=client_config.language,
            data_type=client_config.data.type,
            data_size=client_config.data.size,
            frequency_hz=client_config.frequency_hz,
            duration_sec=duration_sec,
        )


class BaseServer(ABC):
    """Abstract base class for server implementations."""

    @abstractmethod
    def start(self, config: ServerConfig, temp_dir: Path) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def is_running(self) -> bool:
        ...

    @abstractmethod
    def get_address(self) -> str:
        ...

    @abstractmethod
    def get_metrics(self) -> Any:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class BaseClient(ABC):
    """Abstract base class for client implementations."""

    @abstractmethod
    def start(
        self,
        config: ClientConfig,
        server_addr: str,
        metrics_file: Path,
        client_id: str,
    ) -> subprocess.Popen[bytes]:
        ...

    @property
    @abstractmethod
    def language(self) -> str:
        ...


class BaseBackend(ABC):
    """Abstract base class combining server and client factory."""

    @abstractmethod
    def create_server(self) -> BaseServer:
        ...

    @abstractmethod
    def create_client(self, language: str) -> BaseClient:
        ...

    @abstractmethod
    def supported_languages(self) -> list[str]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
