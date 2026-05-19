"""
String art generator — the main orchestrator.

Port of the JS ``graph.setup()`` + ``graph.parse_image()`` loop.

Accepts a PIL Image and generation parameters, runs the greedy multi-thread
optimization, and returns the ordered step sequence plus nail positions.
"""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field
from io import BytesIO

import numpy as np
from PIL import Image

from .frames import FRAME_GENERATORS
from .thread import Thread
from .schemas import (
    GenerateRequest,
    GenerateResponse,
    ThreadStep,
    NailPosition,
)
from ..config import settings

logger = logging.getLogger(__name__)


# ── Default thread palette (CMYKW) ──────────────────────────────────────
# Fixed from the original JS which had a Color(r, g, b, a) constructor
# that accidentally swapped g and b fields.  These are the correct RGBA
# values for each ink:
#   Cyan    = (0,   255, 255, 255)
#   Magenta = (255, 0,   255, 255)
#   Yellow  = (255, 255, 0,   255)
#   Black   = (0,   0,   0,   255)
#   White   = (255, 255, 255, 255)

DEFAULT_THREAD_COLORS: list[tuple[int, int, int, int]] = [
    (0, 255, 255, 255),    # Cyan
    (255, 0, 255, 255),    # Magenta
    (255, 255, 0, 255),    # Yellow
    (0, 0, 0, 255),        # Black
    (255, 255, 255, 255),  # White
]


# ── In-memory job store (swap for Redis/DB later) ────────────────────────

@dataclass
class Job:
    """Tracks a running or completed generation job."""

    job_id: str
    status: str = "pending"            # pending | running | completed | failed
    progress: float = 0.0
    error: str | None = None
    result: GenerateResponse | None = None
    steps: list[ThreadStep] = field(default_factory=list)
    nail_positions: list[NailPosition] = field(default_factory=list)


# Simple dict store — fine for single-process; swap for Redis when scaling
_jobs: dict[str, Job] = {}


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


# ── Image preprocessing ─────────────────────────────────────────────────

def _preprocess_image(
    image_bytes: bytes,
    target_width: int,
    target_height: int,
    downscale: int,
) -> tuple[np.ndarray, int, int]:
    """
    Load an image, center-crop to fill the target aspect ratio, resize to
    the working resolution, and return a flat RGBA uint8 buffer.

    Port of the JS ``img.onload`` handler that computes canvas dimensions
    from the frame bounding box and downscale factor.
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")

    # Working resolution
    canvas_w = max(1, target_width // downscale)
    canvas_h = max(1, target_height // downscale)

    frame_ar = canvas_w / canvas_h
    img_ar = img.width / img.height

    # Scale to fill (center-crop)
    if frame_ar >= img_ar:
        new_w = canvas_w
        new_h = max(1, int(canvas_w / img_ar))
    else:
        new_h = canvas_h
        new_w = max(1, int(canvas_h * img_ar))

    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Center-crop to canvas size
    left = (new_w - canvas_w) // 2
    top = (new_h - canvas_h) // 2
    img_cropped = img_resized.crop((left, top, left + canvas_w, top + canvas_h))

    # Flat RGBA buffer (matches JS ImageData.data layout)
    buf = np.array(img_cropped, dtype=np.float64).reshape(-1)
    return buf, canvas_w, canvas_h


# ── Nail coordinate mapping ─────────────────────────────────────────────

def _map_nails_to_pixels(
    nails_frame: np.ndarray,
    frame_bbox: tuple[float, float, float, float],
    img_w: int,
    img_h: int,
) -> np.ndarray:
    """
    Convert nail positions from frame (SVG) coordinates to pixel coordinates.

    Port of JS ``Image.get_image_point()``.

    Parameters
    ----------
    nails_frame : (N, 2) frame-space positions
    frame_bbox  : (x_min, y_min, width, height) of the frame
    img_w, img_h: pixel dimensions of the working image
    """
    bx, by, bw, bh = frame_bbox
    px = np.floor(((nails_frame[:, 0] - bx) / bw) * (img_w - 1)).astype(np.int32)
    py = np.floor(((nails_frame[:, 1] - by) / bh) * (img_h - 1)).astype(np.int32)
    px = np.clip(px, 0, img_w - 1)
    py = np.clip(py, 0, img_h - 1)
    return np.column_stack((px, py))


# ── Main generation ─────────────────────────────────────────────────────

def run_generation(
    image_bytes: bytes,
    params: GenerateRequest,
    job: Job,
) -> GenerateResponse:
    """
    Execute the full string art generation algorithm.

    This is designed to be called in a background thread so the API
    endpoint can return immediately with a job_id.
    """
    job.status = "running"
    downscale = settings.default_downscale_factor

    try:
        # ── 1. Generate nail positions ───────────────────────────────
        shape = params.frame_shape
        gen_fn = FRAME_GENERATORS[shape]

        if shape == "circle":
            radius = min(params.frame_width, params.frame_height) / 2
            nails_frame = gen_fn(params.num_nails, radius=radius)
        elif shape == "square":
            nails_frame = gen_fn(params.num_nails, side=params.frame_width)
        elif shape == "rectangle":
            nails_frame = gen_fn(params.num_nails, width=params.frame_width, height=params.frame_height)
        elif shape == "polygon":
            sides = params.polygon_sides or 6
            radius = min(params.frame_width, params.frame_height) / 2
            nails_frame = gen_fn(params.num_nails, sides=sides, radius=radius)
        elif shape == "heart":
            scale = min(params.frame_width, params.frame_height) / 2
            nails_frame = gen_fn(params.num_nails, scale=scale)
        else:
            raise ValueError(f"Unknown frame shape: {shape}")

        # Frame bounding box
        x_min, y_min = nails_frame.min(axis=0)
        x_max, y_max = nails_frame.max(axis=0)
        bbox_w = x_max - x_min or 1.0
        bbox_h = y_max - y_min or 1.0
        frame_bbox = (x_min, y_min, bbox_w, bbox_h)

        # ── 2. Preprocess image ──────────────────────────────────────
        # Working resolution derived from frame bbox (mirrors JS logic)
        thread_diam = 0.01
        target_w = int((bbox_w / thread_diam) / 2)
        target_h = int((bbox_h / thread_diam) / 2)

        target_buffer, img_w, img_h = _preprocess_image(
            image_bytes, target_w, target_h, downscale
        )

        # Current canvas — starts as grey (128,128,128,255), matches JS
        current_buffer = np.empty_like(target_buffer)
        for i in range(0, len(current_buffer), 4):
            current_buffer[i] = 128.0      # R
            current_buffer[i + 1] = 128.0  # G
            current_buffer[i + 2] = 128.0  # B
            current_buffer[i + 3] = 255.0  # A

        # ── 3. Map nails to pixel coordinates ────────────────────────
        nails_px = _map_nails_to_pixels(nails_frame, frame_bbox, img_w, img_h)

        # Populate job.nail_positions for early streaming
        job.nail_positions = [
            NailPosition(index=i, x=float(nails_frame[i, 0]), y=float(nails_frame[i, 1]))
            for i in range(params.num_nails)
        ]

        # ── 4. Initialize threads ────────────────────────────────────
        # A very small fade ensures the algorithm draws many overlapping lines 
        # to achieve darkness, resulting in a dense, highly detailed string art.
        fade = 0.05
        threads = [
            Thread(start_nail=0, color=color, fade=fade)
            for color in DEFAULT_THREAD_COLORS
        ]

        # ── 5. Main greedy loop ──────────────────────────────────────
        line_cache: dict[tuple[int, int], np.ndarray] = {}
        max_iter = params.max_connections

        logger.info(
            "Starting generation: %d nails, %d max connections, %s frame",
            params.num_nails, max_iter, shape,
        )

        for iteration in range(max_iter):
            # Evaluate all threads
            best_thread_idx = -1
            best_score = float("inf")

            for t_idx, thread in enumerate(threads):
                score = thread.evaluate_best_nail(
                    nails_px, current_buffer, target_buffer, img_w, line_cache,
                )
                if score < best_score:
                    best_score = score
                    best_thread_idx = t_idx

            # Early stop — no thread can improve the image
            if best_score == float("inf"):
                logger.info("Early stop at iteration %d — no improvement possible", iteration)
                break

            # Move the winning thread
            winning_thread = threads[best_thread_idx]
            from_nail = winning_thread.current_nail
            to_nail = winning_thread.apply_line(current_buffer, img_w)

            step = ThreadStep(
                thread_index=best_thread_idx,
                color=list(int(c) for c in DEFAULT_THREAD_COLORS[best_thread_idx]),
                from_nail=from_nail,
                to_nail=to_nail,
            )
            job.steps.append(step)

            # Update progress
            job.progress = (iteration + 1) / max_iter

            # Invalidate all other threads' caches since the buffer changed
            for t_idx, thread in enumerate(threads):
                if t_idx != best_thread_idx:
                    thread._cache_valid = False

        # ── 6. Assemble response ─────────────────────────────────────
        result = GenerateResponse(
            job_id=job.job_id,
            status="completed",
            nail_positions=job.nail_positions,
            steps=job.steps,
            total_connections=len(job.steps),
            frame_shape=shape,
        )

        job.status = "completed"
        job.progress = 1.0
        job.result = result
        logger.info("Generation complete: %d connections", len(job.steps))
        return result

    except Exception as e:
        logger.exception("Generation failed")
        job.status = "failed"
        job.error = str(e)
        raise


def create_job() -> Job:
    """Create a new job entry and return it."""
    job_id = uuid.uuid4().hex[:12]
    job = Job(job_id=job_id)
    _jobs[job_id] = job
    return job
