"""Metrics definitions and result serialization."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MemorySample:
    """A single memory measurement sample."""

    timestamp: float
    memory_mb: float


@dataclass
class ServerMetrics:
    """Metrics collected from the server."""

    memory_samples: list[MemorySample] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    rrd_file_size_mb: float = 0.0

    @property
    def memory_peak_mb(self) -> float:
        if not self.memory_samples:
            return 0.0
        return max(s.memory_mb for s in self.memory_samples)

    @property
    def memory_avg_mb(self) -> float:
        if not self.memory_samples:
            return 0.0
        return statistics.mean(s.memory_mb for s in self.memory_samples)

    @property
    def duration_sec(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_samples": [
                {"timestamp": s.timestamp, "memory_mb": s.memory_mb}
                for s in self.memory_samples
            ],
            "memory_peak_mb": self.memory_peak_mb,
            "memory_avg_mb": self.memory_avg_mb,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_sec": self.duration_sec,
            "rrd_file_size_mb": self.rrd_file_size_mb,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerMetrics:
        metrics = cls(
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 0.0),
            rrd_file_size_mb=data.get("rrd_file_size_mb", 0.0),
        )
        for sample in data.get("memory_samples", []):
            metrics.memory_samples.append(
                MemorySample(
                    timestamp=sample["timestamp"],
                    memory_mb=sample["memory_mb"],
                )
            )
        return metrics


@dataclass
class ClientMetrics:
    """Metrics collected from a single client."""

    client_id: str = ""
    data_type: str = ""
    data_size: int | str = 0
    frequency_hz: float = 0.0
    log_count: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def latency_mean_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.mean(self.latencies_ms)

    @property
    def latency_p50_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.median(self.latencies_ms)

    @property
    def latency_p99_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def latency_max_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return max(self.latencies_ms)

    @property
    def latency_min_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return min(self.latencies_ms)

    @property
    def duration_sec(self) -> float:
        return self.end_time - self.start_time

    @property
    def throughput(self) -> float:
        if self.duration_sec <= 0:
            return 0.0
        return self.log_count / self.duration_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "data_type": self.data_type,
            "data_size": self.data_size,
            "frequency_hz": self.frequency_hz,
            "log_count": self.log_count,
            "latencies_ms": self.latencies_ms,
            "latency_mean_ms": self.latency_mean_ms,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "latency_max_ms": self.latency_max_ms,
            "latency_min_ms": self.latency_min_ms,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_sec": self.duration_sec,
            "throughput": self.throughput,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClientMetrics:
        return cls(
            client_id=data.get("client_id", ""),
            data_type=data.get("data_type", ""),
            data_size=data.get("data_size", 0),
            frequency_hz=data.get("frequency_hz", 0.0),
            log_count=data.get("log_count", 0),
            latencies_ms=data.get("latencies_ms", []),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 0.0),
            errors=data.get("errors", []),
        )


@dataclass
class AggregatedClientMetrics:
    """Aggregated metrics from all clients."""

    total_log_count: int = 0
    total_throughput: float = 0.0
    latency_mean_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_min_ms: float = 0.0
    client_count: int = 0

    @classmethod
    def from_clients(cls, clients: list[ClientMetrics]) -> AggregatedClientMetrics:
        if not clients:
            return cls()

        all_latencies = []
        total_log_count = 0
        total_throughput = 0.0

        for client in clients:
            all_latencies.extend(client.latencies_ms)
            total_log_count += client.log_count
            total_throughput += client.throughput

        result = cls(
            total_log_count=total_log_count,
            total_throughput=total_throughput,
            client_count=len(clients),
        )

        if all_latencies:
            result.latency_mean_ms = statistics.mean(all_latencies)
            result.latency_p50_ms = statistics.median(all_latencies)
            sorted_latencies = sorted(all_latencies)
            idx = int(len(sorted_latencies) * 0.99)
            result.latency_p99_ms = sorted_latencies[min(idx, len(sorted_latencies) - 1)]
            result.latency_max_ms = max(all_latencies)
            result.latency_min_ms = min(all_latencies)

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_log_count": self.total_log_count,
            "total_throughput": self.total_throughput,
            "latency_mean_ms": self.latency_mean_ms,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "latency_max_ms": self.latency_max_ms,
            "latency_min_ms": self.latency_min_ms,
            "client_count": self.client_count,
        }


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""

    name: str
    description: str
    backend_type: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    server_metrics: ServerMetrics = field(default_factory=ServerMetrics)
    client_metrics: list[ClientMetrics] = field(default_factory=list)
    config_snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def aggregated_client_metrics(self) -> AggregatedClientMetrics:
        return AggregatedClientMetrics.from_clients(self.client_metrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "backend_type": self.backend_type,
            "timestamp": self.timestamp,
            "server_metrics": self.server_metrics.to_dict(),
            "client_metrics": [c.to_dict() for c in self.client_metrics],
            "aggregated_client_metrics": self.aggregated_client_metrics.to_dict(),
            "config_snapshot": self.config_snapshot,
        }

    def save(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{ts}.json"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        return filepath

    @classmethod
    def load(cls, path: str | Path) -> BenchmarkResult:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            backend_type=data["backend_type"],
            timestamp=data["timestamp"],
            server_metrics=ServerMetrics.from_dict(data.get("server_metrics", {})),
            client_metrics=[
                ClientMetrics.from_dict(c) for c in data.get("client_metrics", [])
            ],
            config_snapshot=data.get("config_snapshot", {}),
        )


def save_client_metrics(metrics: ClientMetrics, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2)


def load_client_metrics(path: str | Path) -> ClientMetrics:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ClientMetrics.from_dict(data)


def save_server_metrics(metrics: ServerMetrics, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2)


def load_server_metrics(path: str | Path) -> ServerMetrics:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ServerMetrics.from_dict(data)
