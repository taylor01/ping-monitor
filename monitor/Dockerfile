FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir icmplib requests

# Copy application
COPY ping_monitor.py .

# Create directories for config and cache
RUN mkdir -p /config /data

# Run as non-root (icmplib supports unprivileged mode)
RUN useradd -m pingmon
RUN chown -R pingmon:pingmon /app /config /data
USER pingmon

CMD ["python", "-u", "ping_monitor.py"]
