"""
Thread — represents a single colored thread in the string art.

Port of the JS ``Thread`` class from index.js.  Each thread maintains its
current nail, the ordered sequence of nails it has visited, and a set of
previously-used connections to avoid duplicates.
"""

from __future__ import annotations

import numpy as np

from .rasterize import bresenham_line


class Thread:
    """
    A single colored thread that greedily selects the next nail whose line
    would reduce the error between the current canvas and the target image
    the most.
    """

    def __init__(
        self,
        start_nail: int,
        color: tuple[int, int, int, int],
        fade: float,
    ):
        self.current_nail: int = start_nail
        self.color = np.array(color, dtype=np.float64)  # [R, G, B, A]
        self.fade: float = fade
        self.nail_order: list[int] = [start_nail]
        self.prev_connections: set[tuple[int, int]] = set()

        # Cached best-move state (invalidated after each move)
        self._next_nail: int | None = None
        self._next_score: float = float("inf")
        self._next_pixels: np.ndarray | None = None
        self._cache_valid: bool = False

    # ------------------------------------------------------------------
    # Core algorithm — direct port of JS get_line_diff + get_next_nail_weight
    # ------------------------------------------------------------------

    def evaluate_best_nail(
        self,
        nail_positions_px: np.ndarray,
        current_buffer: np.ndarray,
        target_buffer: np.ndarray,
        img_width: int,
        line_cache: dict[tuple[int, int], np.ndarray],
    ) -> float:
        """
        Scan every other nail and find the one whose line would improve the
        image the most.  Caches the result until ``apply_line`` is called.

        Returns the best score (lower / more negative = better).
        """
        if self._cache_valid:
            return self._next_score

        num_nails = len(nail_positions_px)
        best_score = float("inf")
        best_nail = self.current_nail
        best_pixels: np.ndarray | None = None

        src = nail_positions_px[self.current_nail]

        for i in range(num_nails):
            if i == self.current_nail:
                continue

            # Skip already-used connections
            key = (min(self.current_nail, i), max(self.current_nail, i))
            if key in self.prev_connections:
                continue

            # Get or compute pixels for this line
            if key in line_cache:
                pixels = line_cache[key]
            else:
                dst = nail_positions_px[i]
                pixels = bresenham_line(
                    int(src[0]), int(src[1]),
                    int(dst[0]), int(dst[1]),
                )
                line_cache[key] = pixels

            score = self._compute_line_diff(pixels, current_buffer, target_buffer, img_width)

            if score < best_score:
                best_score = score
                best_nail = i
                best_pixels = pixels

        # If no improvement is possible, mark as infinity
        if best_score >= 0:
            best_score = float("inf")

        self._next_nail = best_nail
        self._next_score = best_score
        self._next_pixels = best_pixels
        self._cache_valid = True
        return best_score

    def apply_line(
        self,
        current_buffer: np.ndarray,
        img_width: int,
    ) -> int:
        """
        Draw the cached best line into ``current_buffer`` and advance to the
        next nail.  Returns the nail index we moved to.

        Must be called after ``evaluate_best_nail``.
        """
        assert self._cache_valid, "Call evaluate_best_nail first"
        assert self._next_pixels is not None

        # Alpha-blend each pixel on the line into the current buffer
        pixels = self._next_pixels
        
        px = pixels[:, 0].astype(np.int32)
        py = pixels[:, 1].astype(np.int32)
        base_idx = (px + py * img_width) * 4
        
        valid_pixel_mask = (base_idx >= 0) & (base_idx + 3 < len(current_buffer))
        base_idx = base_idx[valid_pixel_mask]
        
        if len(base_idx) > 0:
            c_offsets = np.arange(4)
            indices = base_idx[:, None] + c_offsets  # shape (M, 4)
            curr_vals = current_buffer[indices]
            
            # Blend
            new_c = self.color * self.fade + curr_vals * (1 - self.fade)
            current_buffer[indices] = new_c

        # Record the connection
        key = (min(self.current_nail, self._next_nail), max(self.current_nail, self._next_nail))
        self.prev_connections.add(key)

        from_nail = self.current_nail
        self.current_nail = self._next_nail
        self.nail_order.append(self.current_nail)

        # Invalidate cache
        self._cache_valid = False
        self._next_pixels = None

        return self.current_nail

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _compute_line_diff(
        self,
        pixels: np.ndarray,
        current_buffer: np.ndarray,
        target_buffer: np.ndarray,
        img_width: int,
    ) -> float:
        """
        Compute how much drawing this line would change the error between
        the current canvas and the target image.

        Direct port of JS ``Line.get_line_diff``:
        - For each pixel on the line, compute the new blended value
        - Measure the change in absolute error vs target
        - Negative diffs (improvements) weighted 1×, positive (regressions) 1/5×
        - Result = (mean_weighted_diff)^3
        """
        if len(pixels) == 0:
            return float("inf")

        px = pixels[:, 0].astype(np.int32)
        py = pixels[:, 1].astype(np.int32)
        base_idx = (px + py * img_width) * 4
        
        valid_pixel_mask = (base_idx >= 0) & (base_idx + 3 < len(current_buffer))
        base_idx = base_idx[valid_pixel_mask]
        
        if len(base_idx) == 0:
            return float("inf")
            
        c_offsets = np.arange(4)
        indices = base_idx[:, None] + c_offsets # shape (M, 4)
        
        curr_vals = current_buffer[indices]
        targ_vals = target_buffer[indices]
        
        new_c = self.color * self.fade + curr_vals * (1 - self.fade)
        
        # Absolute differences
        diff = np.abs(targ_vals - new_c) - np.abs(curr_vals - targ_vals)
        
        # Sum over RGBA channels
        pixel_diff = diff.sum(axis=1)
        
        # Asymmetric weighting
        improvements = pixel_diff[pixel_diff < 0]
        regressions = pixel_diff[pixel_diff >= 0]
        
        total_diff = improvements.sum() + (regressions.sum() / 5.0)
        
        avg = total_diff / len(base_idx)
        return float(avg ** 3)
