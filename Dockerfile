# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code (see .dockerignore)
COPY . .

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Expose port (Cloud Run defaults to 8080)
EXPOSE 8080

# Run the FastAPI app using uvicorn
CMD exec uvicorn src.app.main:app --host 0.0.0.0 --port ${PORT:-8080}
