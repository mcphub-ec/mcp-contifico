"""Configuration, logging, and shared constants for the Contifico MCP server.

Split out of server.py (issue #1). load_dotenv() runs here before any config
constant is read, preserving the original load order.
"""

import os
import json
import logging
import re as _re

from dotenv import load_dotenv

load_dotenv()


class _JsonLogFormatter(logging.Formatter):
    """One well-formed JSON object per log line. json.dumps escapes the message,
    preventing log-injection / forged lines via crafted values."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "time": self.formatTime(record),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
            },
            ensure_ascii=False,
            default=str,
        )


_log_handler = logging.StreamHandler()
_log_handler.setFormatter(_JsonLogFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
logger = logging.getLogger("contifico-mcp")


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


CONTIFICO_BASE_URL = os.environ.get(
    "CONTIFICO_BASE_URL", "https://api.contifico.com/sistema"
)

HTTP_TIMEOUT = float(os.environ.get("CONTIFICO_HTTP_TIMEOUT", "30"))

# Security posture — safe by default:
#   ALLOW_ENV_KEY_FALLBACK (default false): when false, a request with no/invalid
#     Authorization header is REJECTED instead of silently using the server's
#     CONTIFICO_API_KEY (which would route one caller to another tenant's account).
#     Set true ONLY for local single-tenant dev.
#   CONTIFICO_READONLY (default true): when true, mutating HTTP methods
#     (POST/PUT/DELETE/PATCH) are blocked server-side. Flip to false only behind a
#     human-approval layer.
ALLOW_ENV_KEY_FALLBACK = _env_flag("ALLOW_ENV_KEY_FALLBACK", False)
CONTIFICO_READONLY = _env_flag("CONTIFICO_READONLY", True)

# Legit Contifico API paths are slash-delimited alphanumeric segments (letters,
# digits, '_' and '-'). Anything else (a '.', '?', '#', whitespace, '//') is
# rejected — blocks path traversal and query/fragment injection through any
# id value interpolated into the path.
_SAFE_PATH = _re.compile(r"^(?:/[A-Za-z0-9_-]+)+/?$")
