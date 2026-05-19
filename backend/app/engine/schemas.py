"""
Pydantic models for API requests and responses.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """Parameters for string art generation (sent as form field JSON)."""

    num_nails: int = Field(300, ge=10, le=2000, description="Number of nails around the frame")
    max_connections: int = Field(10000, ge=100, le=15000, description="Maximum thread connections")
    frame_shape: Literal["circle", "square", "rectangle", "polygon", "heart"] = Field(
        "circle", description="Shape of the nail frame"
    )
    polygon_sides: int | None = Field(None, ge=3, le=20, description="Sides for polygon frame")
    frame_width: float = Field(10.0, gt=0, description="Frame width")
    frame_height: float = Field(10.0, gt=0, description="Frame height")


# ── Response ─────────────────────────────────────────────────────────────

class ThreadStep(BaseModel):
    """A single step in the generation sequence."""

    thread_index: int
    color: list[int]   # [R, G, B, A]
    from_nail: int
    to_nail: int


class NailPosition(BaseModel):
    """Position of a nail in frame coordinates."""

    index: int
    x: float
    y: float


class GenerateResponse(BaseModel):
    """Full result of a string art generation job."""

    job_id: str
    status: str  # "completed" | "running" | "failed"
    nail_positions: list[NailPosition]
    steps: list[ThreadStep]
    total_connections: int
    frame_shape: str


class JobStatusResponse(BaseModel):
    """Lightweight polling response for a running job."""

    job_id: str
    status: str
    progress: float  # 0.0 — 1.0
    total_connections: int | None = None
    error: str | None = None
    nail_positions: list[NailPosition] = Field(default_factory=list)
    steps: list[ThreadStep] = Field(default_factory=list, description="Steps generated so far")
