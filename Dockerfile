# syntax=docker/dockerfile:1
FROM python:3.12-slim

# uv: fast, reproducible installs from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Runtime deps install first (layer-cached until the lockfile changes). They all
# ship as manylinux wheels, so no compiler toolchain is needed. The cache mount
# lets repeat builds reuse already-downloaded wheels instead of refetching.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .

EXPOSE 8000

# Start the venv's uvicorn directly — avoids a per-start uv sync/network check.
CMD ["/app/.venv/bin/uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
