"""Benchmark runner - coordinates server and clients."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from bench.backends import get_backend
from bench.backends.base import ClientConfig, ServerConfig
from bench.config import BenchmarkConfig, load_config
from bench.data_generators import get_data_type_description
from bench.metrics import (
    BenchmarkResult,
    load_client_metrics,
)

console = Console()


def run_benchmark(config: BenchmarkConfig, keep_tmpdir: bool = False) -> BenchmarkResult:
    """Run a complete benchmark based on the configuration.
    
    Args:
        config: Benchmark configuration.
        keep_tmpdir: If True, keep the temporary directory after benchmark completes.
    """
    backend = get_backend(config.backend.type)

    result = BenchmarkResult(
        name=config.name,
        description=config.description,
        backend_type=config.backend.type,
        config_snapshot=config.model_dump(),
    )

    tmpdir = tempfile.mkdtemp()

    try:
        tmpdir_path = Path(tmpdir)

        server_config = ServerConfig.from_config(config.backend, config.metrics)

        console.print(f"[bold blue]Starting {backend.name} server on port {server_config.port}...[/]")
        server = backend.create_server()
        server.start(server_config, tmpdir_path)

        try:
            time.sleep(1.0)

            if not server.is_running():
                raise RuntimeError("Server failed to start")

            server_addr = server.get_address()
            console.print(f"[green]Server started at {server_addr}[/]")

            client_procs: list[tuple[subprocess.Popen[bytes], Path, str]] = []
            client_idx = 0

            for client_group in config.clients:
                if client_group.language not in backend.supported_languages():
                    console.print(
                        f"[yellow]Warning: Language '{client_group.language}' "
                        f"not supported for {backend.name}, skipping[/]"
                    )
                    continue

                client = backend.create_client(client_group.language)
                client_config = ClientConfig.from_config(client_group, config.duration_sec)

                for i in range(client_group.count):
                    client_id = f"client_{client_idx}"
                    metrics_file = tmpdir_path / f"{client_id}_metrics.json"

                    console.print(
                        f"[blue]Starting {client_id} "
                        f"({client_group.data.type}, "
                        f"{get_data_type_description(client_group.data.type, client_group.data.size)}, "
                        f"{client_group.frequency_hz}Hz)...[/]"
                    )

                    proc = client.start(
                        client_config,
                        server_addr,
                        metrics_file,
                        client_id,
                    )
                    client_procs.append((proc, metrics_file, client_id))
                    client_idx += 1

            if not client_procs:
                raise RuntimeError("No clients started")

            console.print(f"[green]Started {len(client_procs)} client(s)[/]")
            console.print("[bold]Waiting for clients to complete...[/]")

            for proc, _, client_id in client_procs:
                proc.wait()
                console.print(f"[dim]{client_id} finished[/]")

            console.print("[green]All clients completed[/]")

        finally:
            console.print("[bold blue]Stopping server...[/]")
            server.stop()

        console.print("[bold]Collecting metrics...[/]")

        result.server_metrics = server.get_metrics()

        for _, metrics_file, _ in client_procs:
            if metrics_file.exists():
                client_metrics = load_client_metrics(metrics_file)
                result.client_metrics.append(client_metrics)

    finally:
        if keep_tmpdir:
            console.print(f"[yellow]Temporary directory kept: {tmpdir}[/]")
        else:
            shutil.rmtree(tmpdir, ignore_errors=True)

    return result


def print_result(result: BenchmarkResult) -> None:
    """Print benchmark results to console."""
    console.print()
    console.rule(f"[bold]Benchmark: {result.name}[/]")
    console.print()

    console.print(f"[bold]Backend:[/] {result.backend_type}")
    console.print(f"[bold]Description:[/] {result.description}")
    console.print()

    console.print("[bold underline]Server Metrics[/]")
    server = result.server_metrics
    console.print(f"  Memory Peak: {server.memory_peak_mb:.1f} MB")
    console.print(f"  Memory Avg: {server.memory_avg_mb:.1f} MB")
    console.print(f"  RRD File Size: {server.rrd_file_size_mb:.2f} MB")
    console.print(f"  Duration: {server.duration_sec:.1f}s")
    console.print()

    if result.client_metrics:
        console.print("[bold underline]Client Metrics[/]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Client")
        table.add_column("Type")
        table.add_column("Logs")
        table.add_column("Throughput")
        table.add_column("Latency (mean)")
        table.add_column("Latency (p99)")

        for client in result.client_metrics:
            table.add_row(
                client.client_id,
                client.data_type,
                str(client.log_count),
                f"{client.throughput:.1f}/s",
                f"{client.latency_mean_ms:.2f}ms",
                f"{client.latency_p99_ms:.2f}ms",
            )

        console.print(table)
        console.print()

        agg = result.aggregated_client_metrics
        console.print("[bold underline]Aggregated Client Metrics[/]")
        console.print(f"  Total Logs: {agg.total_log_count}")
        console.print(f"  Total Throughput: {agg.total_throughput:.1f} logs/s")
        console.print(f"  Latency Mean: {agg.latency_mean_ms:.2f} ms")
        console.print(f"  Latency P50: {agg.latency_p50_ms:.2f} ms")
        console.print(f"  Latency P99: {agg.latency_p99_ms:.2f} ms")
        console.print(f"  Latency Max: {agg.latency_max_ms:.2f} ms")

    console.print()


@click.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--keep", "keep_tmpdir", is_flag=True, default=False, help="Keep temporary directory after benchmark")
def main(
    config_path: str | None,
    keep_tmpdir: bool,
) -> None:
    """Run benchmark with the specified configuration."""

    if config_path is None:
        console.print("[red]Error: --config is required[/]")
        raise SystemExit(1)

    console.print(f"[bold]Loading config from {config_path}...[/]")
    config = load_config(config_path)

    result = run_benchmark(config, keep_tmpdir=keep_tmpdir)

    print_result(result)

    output_path = result.save(config.metrics.output_dir)
    console.print(f"[green]Results saved to: {output_path}[/]")


if __name__ == "__main__":
    main()
