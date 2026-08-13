# Atelier Lens Backend

Phase 0 FastAPI backend scaffold.

## Setup

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```
