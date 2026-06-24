FROM python:3.12-slim

# uv: fast, reproducible installs from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Compile to the image's system environment, no project venv layer needed.
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install runtime deps first (cached) from the lockfile, excluding dev tools.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
