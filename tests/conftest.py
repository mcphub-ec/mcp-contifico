"""conftest.py — pytest session setup for local development.

Fixes a test isolation issue: test_header_plumbing.py monkey-patches
server._request at MODULE LEVEL (not inside a function), so pytest importing
it during collection permanently replaces server._request with a fake that
returns {"ok": True}. This breaks test_security.py tests that call _request.

Fix: save the real _request before collection touches the module, and restore
it before each security test that needs the real implementation.

In CI, this is a no-op (test_header_plumbing is not collected without a
free TCP port, or the test runner runs files separately).
"""

import os
import sys

import pytest

# ── Clear security flag env-vars (local .env may set them) ───────────────────
for _var in ("CONTIFICO_READONLY", "ALLOW_ENV_KEY_FALLBACK"):
    os.environ.pop(_var, None)


# ── Save the real server._request BEFORE test_header_plumbing is imported ────
# We must import server here, before pytest collection triggers the import of
# test_header_plumbing.py which replaces server._request at module level.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server as _server  # noqa: E402

_REAL_REQUEST = _server._request


# ── Restore server._request before each test ─────────────────────────────────
@pytest.fixture(autouse=True)
def _restore_real_request():
    """Undo test_header_plumbing.py's module-level server._request replacement.

    test_header_plumbing.py does `server._request = _fake_request` at module
    level. When pytest collects the full tests/ directory it imports that module,
    permanently replacing _request. This fixture restores the real function before
    each test so test_security.py assertions are not silently running against
    the fake implementation.
    """
    _server._request = _REAL_REQUEST
    yield
    _server._request = _REAL_REQUEST
