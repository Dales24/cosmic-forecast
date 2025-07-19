# Use official Python image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install dev tools
RUN pip install pre-commit black flake8 pytest tox

# Copy project
COPY . .

# Expose port (change if your app uses a different port)
EXPOSE 8000

# Default command (change main.py to your app's entrypoint if needed)
CMD ["python", "predictions.py"] 