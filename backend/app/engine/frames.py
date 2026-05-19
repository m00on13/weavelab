"""
Nail position generators for each supported frame shape.

Every function returns an np.ndarray of shape (num_nails, 2) containing
(x, y) positions in a coordinate system centered at (0, 0).
"""

from __future__ import annotations

import math
import numpy as np


def circle_nails(num_nails: int, radius: float = 5.0) -> np.ndarray:
    """Evenly spaced nails around a circle — matches the original JS behavior."""
    angles = np.linspace(0, 2 * math.pi, num_nails, endpoint=False)
    x = radius * np.cos(angles)
    y = radius * np.sin(angles)
    return np.column_stack((x, y))


def square_nails(num_nails: int, side: float = 10.0) -> np.ndarray:
    """Nails distributed evenly across 4 equal sides of a square."""
    half = side / 2
    perimeter = 4 * side
    positions = []
    for i in range(num_nails):
        d = (i / num_nails) * perimeter
        if d < side:
            positions.append((-half + d, -half))
        elif d < 2 * side:
            positions.append((half, -half + (d - side)))
        elif d < 3 * side:
            positions.append((half - (d - 2 * side), half))
        else:
            positions.append((-half, half - (d - 3 * side)))
    return np.array(positions, dtype=np.float64)


def rectangle_nails(num_nails: int, width: float = 10.0, height: float = 8.0) -> np.ndarray:
    """Nails distributed proportionally around a rectangle."""
    hw, hh = width / 2, height / 2
    perimeter = 2 * (width + height)
    positions = []
    for i in range(num_nails):
        d = (i / num_nails) * perimeter
        if d < width:
            positions.append((-hw + d, -hh))
        elif d < width + height:
            positions.append((hw, -hh + (d - width)))
        elif d < 2 * width + height:
            positions.append((hw - (d - width - height), hh))
        else:
            positions.append((-hw, hh - (d - 2 * width - height)))
    return np.array(positions, dtype=np.float64)


def polygon_nails(num_nails: int, sides: int = 6, radius: float = 5.0) -> np.ndarray:
    """Nails distributed evenly along the edges of a regular polygon."""
    # Compute polygon vertices
    vertices = []
    for s in range(sides):
        angle = 2 * math.pi * s / sides - math.pi / 2  # start from top
        vertices.append((radius * math.cos(angle), radius * math.sin(angle)))
    vertices.append(vertices[0])  # close the polygon

    # Compute side lengths
    side_lengths = []
    for s in range(sides):
        dx = vertices[s + 1][0] - vertices[s][0]
        dy = vertices[s + 1][1] - vertices[s][1]
        side_lengths.append(math.sqrt(dx * dx + dy * dy))
    perimeter = sum(side_lengths)

    # Place nails proportionally
    positions = []
    for i in range(num_nails):
        d = (i / num_nails) * perimeter
        cumulative = 0.0
        for s in range(sides):
            if cumulative + side_lengths[s] > d or s == sides - 1:
                t = (d - cumulative) / side_lengths[s]
                x = vertices[s][0] + t * (vertices[s + 1][0] - vertices[s][0])
                y = vertices[s][1] + t * (vertices[s + 1][1] - vertices[s][1])
                positions.append((x, y))
                break
            cumulative += side_lengths[s]
    return np.array(positions, dtype=np.float64)


def heart_nails(num_nails: int, scale: float = 5.0) -> np.ndarray:
    """Nails along a parametric heart curve, evenly spaced by arc length."""
    # Over-sample the heart parametric curve
    n_samples = num_nails * 100
    t = np.linspace(0, 2 * math.pi, n_samples, endpoint=False)
    x = scale * 0.3 * 16 * np.sin(t) ** 3
    y = -scale * 0.3 * (
        13 * np.cos(t)
        - 5 * np.cos(2 * t)
        - 2 * np.cos(3 * t)
        - np.cos(4 * t)
    )

    # Compute cumulative arc length
    dx = np.diff(x)
    dy = np.diff(y)
    segment_lengths = np.sqrt(dx ** 2 + dy ** 2)
    cumulative = np.concatenate(([0], np.cumsum(segment_lengths)))
    total_length = cumulative[-1]

    # Resample at equal arc-length intervals
    target_distances = np.linspace(0, total_length, num_nails, endpoint=False)
    indices = np.searchsorted(cumulative, target_distances, side="right") - 1
    indices = np.clip(indices, 0, n_samples - 2)

    # Interpolate
    frac = (target_distances - cumulative[indices]) / np.maximum(
        segment_lengths[indices], 1e-12
    )
    nail_x = x[indices] + frac * dx[indices]
    nail_y = y[indices] + frac * dy[indices]
    return np.column_stack((nail_x, nail_y))


# Lookup for use by the generator
FRAME_GENERATORS = {
    "circle": circle_nails,
    "square": square_nails,
    "rectangle": rectangle_nails,
    "polygon": polygon_nails,
    "heart": heart_nails,
}
