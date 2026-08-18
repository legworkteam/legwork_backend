# Atelier Lens backend image.
#
# Note: paddleocr/paddlepaddle make this a heavy image (~2GB+) and a slow
# first build — that's inherent to bundling PaddleOCR, not something this
# Dockerfile can avoid. requirements.txt (not pyproject.toml's version
# ranges) is the source of truth here so the image matches exactly what
# passed the test suite locally.
FROM python:3.12-slim

# Runtime libs paddlepaddle / opencv need on a slim base image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so app-code-only changes don't invalidate this
# (multi-minute) layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FILE_ROOT=/data

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fs http://localhost:8000/api/v1/health || exit 1

# Apply migrations then start the API. A single-container demo deploy;
# split this into a separate migrate step first if you ever run >1 replica.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
