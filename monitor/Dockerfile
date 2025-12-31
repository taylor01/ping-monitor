FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application package
COPY ping_monitor/ ./ping_monitor/

# Create directories for config and cache
RUN mkdir -p /config /data

# Run as non-root (but we need privileged mode for ICMP)
# User will be set to root via docker-compose for NET_RAW capability
RUN useradd -m -u 1000 pingmon
RUN chown -R pingmon:pingmon /app /config /data

# Note: USER is set to root in docker-compose.yml for NET_RAW capability
# Docker Compose will override this with user: root

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "ping_monitor.main"]
