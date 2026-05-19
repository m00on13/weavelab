"""
Bresenham line rasterization — returns the pixel coordinates a line
passes through on a discrete grid.

This is the hot path of the algorithm; keeping it in NumPy avoids
per-pixel Python overhead.
"""

from __future__ import annotations

import numpy as np


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    """
    Compute all pixel coordinates along the line from (x0, y0) to (x1, y1)
    using Bresenham's algorithm.

    Returns an ndarray of shape (N, 2) with columns [x, y].

    Mirrors the JS ``Line.compute_pixel_overlap()`` implementation exactly.
    """
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    # Pre-allocate with a generous upper bound, then trim
    max_steps = dx + dy + 1
    pixels = np.empty((max_steps, 2), dtype=np.int32)
    idx = 0

    cx, cy = x0, y0
    while True:
        pixels[idx, 0] = cx
        pixels[idx, 1] = cy
        idx += 1

        if cx == x1 and cy == y1:
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy

    return pixels[:idx]
