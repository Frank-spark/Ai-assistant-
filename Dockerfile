# Multi-stage build for Reflex Executive AI Assistant
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install build && \
    pip install -e .

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN groupadd -r reflex && useradd -r -g reflex reflex

# Create application directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./
COPY README.md ./

# Install application
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs /app/data && \
    chown -R reflex:reflex /app

# Switch to non-root user
USER reflex

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"] 