"""Rerun Python client implementation."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import click
import rerun as rr

from bench.backends.base import BaseClient, ClientConfig
from bench.data_generators import generate_data
from bench.metrics import ClientMetrics, save_client_metrics


class RerunPythonClient(BaseClient):
    """Rerun Python client implementation."""

    def start(
        self,
        config: ClientConfig,
        server_addr: str,
        metrics_file: Path,
        client_id: str,
    ) -> subprocess.Popen[bytes]:
        cmd = [
            sys.executable,
            "-m",
            "bench.backends.rerun.client_py",
            "--server",
            server_addr,
            "--type",
            config.data_type,
            "--size",
            str(config.data_size),
            "--frequency",
            str(config.frequency_hz),
            "--duration",
            str(config.duration_sec),
            "--metrics-file",
            str(metrics_file),
            "--client-id",
            client_id,
        ]

        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @property
    def language(self) -> str:
        return "python"


@click.command()
@click.option("--server", default="rerun+http://127.0.0.1:9876/proxy")
@click.option("--type", "data_type", type=click.Choice(["points3d", "image", "text", "mesh"]), required=True)
@click.option("--size", required=True)
@click.option("--frequency", type=float, default=30.0)
@click.option("--duration", type=float, default=10.0)
@click.option("--metrics-file", required=True, type=click.Path())
@click.option("--client-id", default="client_0")
def main(
    server: str,
    data_type: str,
    size: str,
    frequency: float,
    duration: float,
    metrics_file: str,
    client_id: str,
) -> None:
    """Rerun benchmark client - sends data and records latency."""
    parsed_size: int | str
    if data_type == "image" and "x" in size.lower():
        parsed_size = size
    else:
        parsed_size = int(size)

    metrics = ClientMetrics(
        client_id=client_id,
        data_type=data_type,
        data_size=parsed_size,
        frequency_hz=frequency,
    )

    try:
        rr.init(f"bench_{client_id}")
        rr.connect_grpc(server)

        time.sleep(0.5)

        interval = 1.0 / frequency

        log_count = 0
        latencies: list[float] = []

        regen_interval = 100
        current_data = generate_data(data_type, parsed_size, seed=0)

        start_time = time.time()
        end_time = start_time + duration
        metrics.start_time = start_time

        while time.time() < end_time:
            if log_count % regen_interval == 0 and log_count > 0:
                current_data = generate_data(data_type, parsed_size, seed=log_count)

            start_ns = time.perf_counter_ns()
            rr.log(f"bench/{data_type}", current_data)
            end_ns = time.perf_counter_ns()

            latency_ms = (end_ns - start_ns) / 1_000_000
            latencies.append(latency_ms)
            log_count += 1

            # Use absolute time to compensate accumulated errors
            next_time = start_time + log_count * interval
            sleep_time = next_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

        metrics.end_time = time.time()
        metrics.log_count = log_count
        metrics.latencies_ms = latencies

    except Exception as e:
        metrics.errors.append(str(e))
        metrics.end_time = time.time()

    finally:
        save_client_metrics(metrics, metrics_file)


if __name__ == "__main__":
    main()
