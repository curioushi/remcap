"""Backend implementations for different log servers."""

from bench.backends.base import (
    BaseBackend,
    BaseClient,
    BaseServer,
    ClientConfig,
    ServerConfig,
)

# Backend registry
BACKENDS: dict[str, type[BaseBackend]] = {}


def register_backend(name: str, backend_cls: type[BaseBackend]) -> None:
    """Register a backend implementation."""
    BACKENDS[name] = backend_cls


def get_backend(name: str) -> BaseBackend:
    """Get a backend instance by name."""
    if name not in BACKENDS:
        available = ", ".join(BACKENDS.keys()) or "none"
        raise ValueError(f"Unknown backend: {name}. Available: {available}")
    return BACKENDS[name]()


def list_backends() -> list[str]:
    """List all registered backends."""
    return list(BACKENDS.keys())


# Register backends
try:
    from bench.backends.rerun import RerunBackend
    register_backend("rerun", RerunBackend)
except ImportError:
    pass

# TODO: Register foxglove when implemented


__all__ = [
    "BaseBackend",
    "BaseServer",
    "BaseClient",
    "ServerConfig",
    "ClientConfig",
    "BACKENDS",
    "register_backend",
    "get_backend",
    "list_backends",
]
