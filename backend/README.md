# WeaveLab Backend

Python + FastAPI backend for the WeaveLab string art generator engine.

## Setup

```bash
# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env

# Run the dev server
uv run uvicorn app.main:app --reload --port 8000
```

## API

### POST /api/generate

Upload an image and generation parameters. Returns a `job_id` for polling.

```bash
curl -X POST http://localhost:8000/api/generate \
  -F "image=@photo.jpg" \
  -F 'params={"num_nails": 300, "max_connections": 5000, "frame_shape": "circle"}'
```

### GET /api/jobs/{job_id}

Poll for job status. Returns progress while running, full result when complete.

### GET /api/health

Liveness check.

## Testing

```bash
uv run pytest tests/ -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── config.py         # Settings via pydantic-settings
│   ├── engine/
│   │   ├── frames.py     # Nail position generators (circle, square, rect, polygon, heart)
│   │   ├── rasterize.py  # Bresenham line rasterization
│   │   ├── thread.py     # Thread class — greedy nail selection
│   │   ├── generator.py  # Orchestrator — preprocessing, main loop, result assembly
│   │   └── schemas.py    # Pydantic request/response models
│   └── routes/
│       └── generate.py   # API endpoints
├── tests/
├── requirements.txt
├── pyproject.toml
└── .env.example
```
