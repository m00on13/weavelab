"""
WeaveLab API — FastAPI application entry point.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes.generate import router as generate_router

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# ── App ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="WeaveLab API",
    description="String art generation engine — upload an image, get a nail sequence.",
    version="0.1.0",
)

# CORS — wide open for dev, tighten via CORS_ORIGINS env var in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────────
app.include_router(generate_router)


@app.get("/api/health", tags=["system"])
async def health():
    """Simple liveness check."""
    return {"status": "ok"}
