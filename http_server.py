"""HTTP entry point for the Contifico MCP server.

Run with `python http_server.py` (the Docker CMD / Alpic start command).

This lives in its own module — like `stdio_server.py` — rather than as a
`__main__` block in `server.py`, because `_http.py` does `import server` to
read the mutable config flags at call time. Running `server.py` directly would
make it the `__main__` module, so that `import server` would load a *second*
copy and blow up with a circular import. Importing `server` from here loads it
once, under its real name, so the cycle resolves cleanly.

Defaults to streamable-http: it carries the caller's `Authorization` header per
tool call, which the per-request multi-tenant key model depends on.
"""

import os

import uvicorn

from server import mcp


def main() -> None:
    # Bind the platform-provided port (Alpic/Fly inject $PORT); fall back to
    # MCP_PORT for back-compat, then 8000.
    port = int(os.getenv("PORT") or os.getenv("MCP_PORT") or "8000")
    if port <= 0:
        raise ValueError(f"Invalid port {port!r} — set $PORT/$MCP_PORT to a positive integer")
    transport_mode = os.getenv("MCP_TRANSPORT_MODE", "http_stream").lower()
    print(f"Starting Contifico MCP server on http://0.0.0.0:{port}/mcp ({transport_mode})")
    if transport_mode == "sse":
        app = mcp.sse_app()
    elif transport_mode == "http_stream":
        app = mcp.streamable_http_app()
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
