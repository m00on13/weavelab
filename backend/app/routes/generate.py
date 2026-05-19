"""
API routes for string art generation.
"""

from __future__ import annotations

import threading
import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from ..engine.schemas import (
    GenerateRequest,
    GenerateResponse,
    JobStatusResponse,
)
from ..engine.generator import create_job, get_job, run_generation
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generate"])


@router.post(
    "/generate",
    response_model=JobStatusResponse,
    summary="Submit a string art generation job",
    description=(
        "Upload an image and generation parameters. Returns a job_id that "
        "can be polled via GET /api/jobs/{job_id} until the result is ready."
    ),
)
async def generate(
    image: UploadFile = File(..., description="Source image (JPEG or PNG)"),
    params: str = Form(
        '{}',
        description="JSON string of GenerateRequest parameters",
    ),
):
    """
    Accept an image upload + JSON params, kick off generation in a
    background thread, and return immediately with a job_id.
    """
    import json

    # Validate file type
    if image.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {image.content_type}. Use JPEG or PNG.",
        )

    # Read image bytes
    image_bytes = await image.read()
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds {settings.max_image_size_mb} MB limit.",
        )

    # Parse parameters
    try:
        parsed = json.loads(params)
        gen_params = GenerateRequest(**parsed)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid parameters: {e}")

    # Create job and run in background thread
    job = create_job()
    logger.info("Created job %s — starting background generation", job.job_id)

    thread = threading.Thread(
        target=run_generation,
        args=(image_bytes, gen_params, job),
        daemon=True,
    )
    thread.start()

    return JobStatusResponse(
        job_id=job.job_id,
        status="running",
        progress=0.0,
    )


@router.get(
    "/jobs/{job_id}",
    summary="Poll job status",
    description="Check the status of a generation job. Returns progress, and the full result once completed.",
)
async def get_job_status(job_id: str):
    """Return the current status/result of a generation job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status == "completed" and job.result is not None:
        return job.result

    if job.status == "failed":
        return JobStatusResponse(
            job_id=job.job_id,
            status="failed",
            progress=job.progress,
            error=job.error,
        )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        steps=job.steps,
        nail_positions=job.nail_positions,
    )
