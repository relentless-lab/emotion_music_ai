FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (pymysql, audio/image helpers, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# Keep pip lean
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

# Runtime dirs (mounted as volumes in compose)
RUN mkdir -p /app/static /app/uploads

EXPOSE 8000

# Run migrations then start API
CMD ["bash", "-lc", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]


