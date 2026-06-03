"""Default entry point for Alpic's Python convention (`uv run main.py`).

Alpic's Python buildpack expects a `main.py` and a `pyproject.toml` (uv
project). This delegates to `http_server.main()` so the Alpic entry point and
the Docker/Fly entry (`python http_server.py`) boot the exact same server.
"""

from http_server import main

if __name__ == "__main__":
    main()
