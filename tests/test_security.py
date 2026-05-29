"""Security unit tests for the per-request multi-tenant hardening.

Runnable without pytest: `python tests/test_security.py` (exits non-zero on failure).
Covers: fail-closed key resolution, log redaction, path validation, read-only
write-gate. These exercise the load-bearing security logic added in the
feat/per-request-key hardening.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402  (deps must be installed)


def test_resolve_api_key_fail_closed():
    """No Authorization header + fallback off -> empty (rejected), never env key."""
    server.ALLOW_ENV_KEY_FALLBACK = False
    os.environ["CONTIFICO_API_KEY"] = "ENVKEY"
    assert server._resolve_api_key() == ""


def test_resolve_api_key_dev_fallback():
    """Fallback explicitly enabled (dev) -> env key is used."""
    server.ALLOW_ENV_KEY_FALLBACK = True
    os.environ["CONTIFICO_API_KEY"] = "ENVKEY"
    try:
        assert server._resolve_api_key() == "ENVKEY"
    finally:
        server.ALLOW_ENV_KEY_FALLBACK = False


def test_build_headers_raises_when_no_key():
    server.ALLOW_ENV_KEY_FALLBACK = False
    os.environ["CONTIFICO_API_KEY"] = ""
    try:
        server._build_headers()
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_safe_params_redacts_sensitive():
    out = server._safe_params(
        {"pos": "secret", "Authorization": "tok", "api_key": "k", "search": "ok"}
    )
    assert out["pos"] == "***"
    assert out["Authorization"] == "***"
    assert out["api_key"] == "***"
    assert out["search"] == "ok"


def test_safe_path_accepts_legit():
    assert server._SAFE_PATH.match("/api/v2/persona/123/")
    assert server._SAFE_PATH.match("/api/v2/producto/abc-1/stock/")
    assert server._SAFE_PATH.match("/api/v1/rrhh/rol/")


def test_safe_path_rejects_injection():
    assert not server._SAFE_PATH.match("/api/v2/persona/../../v1/x/")
    assert not server._SAFE_PATH.match("/api/v2/persona/1?pos=evil")
    assert not server._SAFE_PATH.match("/api/v2/persona/1#frag")
    assert not server._SAFE_PATH.match("/api/v2/p/ x")


def test_readonly_blocks_writes():
    server.CONTIFICO_READONLY = True
    res = asyncio.run(server._request("POST", "/api/v2/persona/", body={}))
    assert isinstance(res, dict) and res.get("status_code") == 403


def test_path_validation_raises_before_network():
    """A malicious path is rejected before any HTTP call (even for GET)."""
    server.CONTIFICO_READONLY = False
    try:
        asyncio.run(server._request("GET", "/api/v2/x/../../y/"))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    finally:
        server.CONTIFICO_READONLY = True


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
