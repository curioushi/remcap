# remcap-bench

Extensible benchmark framework for log servers (Rerun, Foxglove). Used to measure performance, resource usage, and stability of log server implementations under realistic robotics workloads.

## Quick Start

```bash
cd bench

# Install dependencies
uv sync

# Run benchmark with typical workload
uv run python -m bench.runner --config configs/typical.json
```

## Configuration

See `configs/typical.json` for a basic configuration example.

### Supported Data Types

- `points3d`: 3D point cloud (size = number of points)
- `image`: RGB image (size = "WIDTHxHEIGHT", e.g., "1920x1080")
- `text`: Text log (size = character count)
- `mesh`: 3D mesh (size = number of vertices)

### Supported Backends

- `rerun`: Rerun visualization server (gRPC)
- `foxglove`: Foxglove Studio (planned)

