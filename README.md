# Atelier Lens Backend

Atelier Lens FastAPI backend for the hackathon submission.

Implemented scope:

- Backend A
  - Auth / User / Social Login
  - GuestSession
  - Product / Variant / Image / Tag
  - Recent Product
  - Cart
  - Order / MockPayment
  - RegisteredProduct
  - Care Guide
  - Store / Campaign / QR
- Backend B
  - FileMetadata / Local Storage / Private File
  - Job / BackgroundTasks
  - OCR / PaddleOCR
  - Avatar
  - Mock Try-on / Photo Try-on
  - Rule-based Recommendation
  - SavedCoordi
  - Diagnosis / Damage / MockDiagnosisProvider
  - RepairReservation
  - CleanupService

## Requirements

- Python 3.12
- Docker Desktop
- PostgreSQL via Docker Compose

## Environment

Create `.env` from `.env.example`.

Required values:

- `BACKEND_CORS_ORIGINS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`

Notes:

- `JWT_SECRET_KEY` should be at least 32 bytes.
- `FILE_ROOT` defaults to `./data`.
- `BACKEND_CORS_ORIGINS` is a comma-separated origin list for browser access.

## Install

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Start PostgreSQL

```powershell
docker compose up -d
docker compose ps
```

Expected service:

- `atelier-lens-postgres`

## Apply migrations

```powershell
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Seed demo data

```powershell
.\.venv\Scripts\python.exe -m scripts.seed
```

Seeded demo catalog uses `DEMO-*` product codes. These are demo identifiers, not real MCM product codes.

## Run API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Health / Swagger

- Health: `http://127.0.0.1:8000/api/v1/health`
- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

## Docker (Postgres + API together)

For a production-like run instead of `## Start PostgreSQL` + local `uvicorn`:

```powershell
docker compose up -d --build
docker compose ps
curl http://localhost:8000/api/v1/health
```

Notes:

- Requires `.env` (same as local dev). Inside the compose network the API reaches
  Postgres by service name, so `docker-compose.yml` overrides `DATABASE_URL` to
  `postgresql+asyncpg://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB`
  regardless of what `.env` has (`.env`'s value stays correct for local/non-Docker runs).
- The `app` container runs `alembic upgrade head` on every start, then `uvicorn`.
- First build is slow (multiple minutes, ~2.4GB image) — `paddleocr`/`paddlepaddle`
  are heavy and unavoidable given the OCR feature.
- `requirements.txt` (not `pyproject.toml`'s version ranges) is what the image
  installs from, so it must stay in sync with the dev venv. Regenerate with
  `pip freeze > requirements.txt` after changing dependencies, and check there's
  no stray self-referencing `-e git+https://...#egg=atelier_lens_backend` line
  (happens if it was generated from an editable install) before committing.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## OCR demo image

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_ocr_test_images
```

Generated file:

- `data/temporary/ocr-demo-DEMO-BAG-001.png`

## Cleanup one-shot

```powershell
.\.venv\Scripts\python.exe -m scripts.cleanup_once
```

Removes expired:

- private files with TTL
- unsaved try-on rows/files
- orphan jobs
- guest sessions

## Frontend handoff

See [docs/frontend_handoff.md](docs/frontend_handoff.md).
