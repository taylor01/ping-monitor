FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash nc

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY nc/ ./nc/
COPY config.yml .

# Create data directory
RUN mkdir -p /app/data && chown -R nc:nc /app

# Switch to non-root user
USER nc

# Environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "nc.main"]
