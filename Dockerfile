FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the application source (avoid shipping anything extraneous)
COPY server.py stdio_server.py ./

# Run as a non-root user
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

# Default MCP port (streamable-http transport); actual port via MCP_PORT at runtime
EXPOSE 8000

# Healthcheck to ensure the container is running and responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import socket, os; s=socket.create_connection(('localhost', int(os.getenv('MCP_PORT', '8000'))), 5); s.close()" || exit 1

# Run the FastMCP server (transport from MCP_TRANSPORT_MODE, default http_stream)
CMD ["python", "server.py"]
