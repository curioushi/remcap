"""Data generators for different data types."""

from __future__ import annotations

from typing import Any

import numpy as np
import rerun as rr


def generate_points3d(num_points: int, seed: int | None = None) -> Any:
    """Generate random 3D point cloud data."""
    if seed is not None:
        np.random.seed(seed)

    positions = np.random.uniform(-10, 10, (num_points, 3)).astype(np.float32)
    colors = np.random.randint(0, 255, (num_points, 3), dtype=np.uint8)

    return rr.Points3D(positions, colors=colors)


def generate_image(width: int, height: int, seed: int | None = None) -> Any:
    """Generate random RGB image data."""
    if seed is not None:
        np.random.seed(seed)

    data = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

    return rr.Image(data)


def generate_text(length: int, seed: int | None = None) -> Any:
    """Generate random text log data."""
    if seed is not None:
        np.random.seed(seed)

    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
    indices = np.random.randint(0, len(chars), length)
    text = "".join(chars[i] for i in indices)

    return rr.TextLog(text)


def generate_mesh(num_vertices: int, seed: int | None = None) -> Any:
    """Generate random 3D mesh data."""
    if seed is not None:
        np.random.seed(seed)

    if num_vertices < 3:
        num_vertices = 3

    vertices = np.random.uniform(-10, 10, (num_vertices, 3)).astype(np.float32)

    num_triangles = max(1, num_vertices - 2)
    indices = []
    for i in range(num_triangles):
        indices.extend([i, i + 1, i + 2])
    triangle_indices = np.array(indices, dtype=np.uint32).reshape(-1, 3)

    colors = np.random.randint(0, 255, (num_vertices, 3), dtype=np.uint8)

    return rr.Mesh3D(
        vertex_positions=vertices,
        triangle_indices=triangle_indices,
        vertex_colors=colors,
    )


def generate_data(
    data_type: str,
    size: int | str,
    seed: int | None = None,
) -> Any:
    """Generate data of the specified type and size."""
    if data_type == "points3d":
        if isinstance(size, str):
            size = int(size)
        return generate_points3d(size, seed)

    elif data_type == "image":
        if isinstance(size, str):
            parts = size.lower().split("x")
            width, height = int(parts[0]), int(parts[1])
        else:
            width = height = size
        return generate_image(width, height, seed)

    elif data_type == "text":
        if isinstance(size, str):
            size = int(size)
        return generate_text(size, seed)

    elif data_type == "mesh":
        if isinstance(size, str):
            size = int(size)
        return generate_mesh(size, seed)

    else:
        raise ValueError(f"Unknown data type: {data_type}")


def get_data_type_description(data_type: str, size: int | str) -> str:
    """Get a human-readable description of the data type and size."""
    if data_type == "points3d":
        return f"{size} points"
    elif data_type == "image":
        if isinstance(size, str):
            return f"{size} pixels"
        return f"{size}x{size} pixels"
    elif data_type == "text":
        return f"{size} chars"
    elif data_type == "mesh":
        return f"{size} vertices"
    else:
        return f"{size}"
