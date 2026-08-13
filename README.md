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

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`

Notes:

- `JWT_SECRET_KEY` should be at least 32 bytes.
- `FILE_ROOT` defaults to `./data`.

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
