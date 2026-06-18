# Tessera Node Dockerfile
# Multi-stage build for minimal image size

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (no dev dependencies)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 tessera

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY tessera/ ./tessera/

# Create data directory
RUN mkdir -p /data && chown -R tessera:tessera /data /app

# Switch to non-root user
USER tessera

# Environment variables
ENV CALLDNS_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost', int('$PORT' or 8100))); s.close()" || exit 1

# Default command (can be overridden)
ENTRYPOINT ["python", "-m", "tessera.cli.node"]
CMD ["start", "--type", "core", "--id", "node-1", "--port", "8100", "--host", "0.0.0.0"]
