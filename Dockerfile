FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source (all modules server.py imports after the #1 split)
COPY app.py config.py _http.py server.py stdio_server.py http_server.py ./
COPY tools/ ./tools/

# Run as a non-root user
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

# Default MCP port (streamable-http transport); actual port via MCP_PORT at runtime
EXPOSE 8000

# Healthcheck: TCP-connect to the bound port (dynamic via $PORT/$MCP_PORT). A
# liveness check, not an HTTP GET — the streamable-http app has no plain-200
# route (every /mcp call needs a session), so an HTTP probe would false-fail.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT') or os.getenv('MCP_PORT') or '8000')), 5)" || exit 1

# Run the FastMCP server via the HTTP entry point (transport from
# MCP_TRANSPORT_MODE, default http_stream; port from $PORT, falls back to 8000).
CMD ["python", "http_server.py"]
