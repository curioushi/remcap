"""Rerun server implementation."""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import psutil

from bench.backends.base import BaseServer, ServerConfig
from bench.metrics import MemorySample, ServerMetrics


def _kill_process_on_port(port: int) -> None:
    """Kill any process using the specified port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                try:
                    subprocess.run(["kill", "-9", pid], check=False)
                except Exception:
                    pass
            time.sleep(0.5)
    except Exception:
        pass


class RerunServer(BaseServer):
    """Rerun gRPC server implementation."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._config: ServerConfig | None = None
        self._temp_dir: Path | None = None
        self._metrics = ServerMetrics()
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def rrd_file(self) -> Path:
        """Path to the rrd file."""
        if self._temp_dir is None:
            raise RuntimeError("Server not started")
        return self._temp_dir / "benchmark.rrd"

    def start(self, config: ServerConfig, temp_dir: Path) -> None:
        self._config = config
        self._temp_dir = temp_dir
        self._metrics = ServerMetrics()
        self._stop_event.clear()

        # Kill any existing process on the port
        _kill_process_on_port(config.port)

        cmd = ["rerun", "--serve-grpc", "--port", str(config.port), "--save", str(self.rrd_file)]

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(1.0)

        if self._proc.poll() is not None:
            stdout, stderr = self._proc.communicate()
            raise RuntimeError(
                f"Rerun server failed to start.\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        self._metrics.start_time = time.time()

        self._monitor_thread = threading.Thread(
            target=self._monitor_memory,
            daemon=True,
        )
        self._monitor_thread.start()

    def _monitor_memory(self) -> None:
        if self._proc is None or self._config is None:
            return

        interval_sec = self._config.memory_sample_interval_ms / 1000.0

        try:
            process = psutil.Process(self._proc.pid)
        except psutil.NoSuchProcess:
            return

        while not self._stop_event.is_set():
            try:
                mem_info = process.memory_info()
                memory_mb = mem_info.rss / (1024 * 1024)

                sample = MemorySample(
                    timestamp=time.time(),
                    memory_mb=memory_mb,
                )
                self._metrics.memory_samples.append(sample)

            except psutil.NoSuchProcess:
                break
            except Exception:
                pass

            self._stop_event.wait(interval_sec)

    def stop(self) -> None:
        self._stop_event.set()

        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=2.0)

        self._metrics.end_time = time.time()

        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
            self._proc = None

        # Get rrd file size
        if self.rrd_file.exists():
            self._metrics.rrd_file_size_mb = self.rrd_file.stat().st_size / (1024 * 1024)

    def get_metrics(self) -> ServerMetrics:
        """Get collected server metrics."""
        return self._metrics

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def get_address(self) -> str:
        if self._config is None:
            raise RuntimeError("Server not started")
        return f"rerun+http://127.0.0.1:{self._config.port}/proxy"

    @property
    def name(self) -> str:
        return "rerun"
