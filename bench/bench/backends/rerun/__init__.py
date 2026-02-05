"""Rerun backend implementation."""

from bench.backends.base import BaseBackend, BaseClient, BaseServer
from bench.backends.rerun.client_py import RerunPythonClient
from bench.backends.rerun.server import RerunServer


class RerunBackend(BaseBackend):
    """Rerun backend combining server and client factory."""

    def create_server(self) -> BaseServer:
        return RerunServer()

    def create_client(self, language: str) -> BaseClient:
        if language == "python":
            return RerunPythonClient()
        else:
            raise ValueError(
                f"Unsupported language for Rerun: {language}. "
                f"Supported: {self.supported_languages()}"
            )

    def supported_languages(self) -> list[str]:
        return ["python"]

    @property
    def name(self) -> str:
        return "rerun"


__all__ = ["RerunServer", "RerunPythonClient", "RerunBackend"]
