"""Integration test: under streamable-http, the caller's per-request
`Authorization: Bearer <key>` header must reach `_resolve_api_key()` for the
tool invocation. This is THE load-bearing assumption of the multi-tenant fork.

Runs a real uvicorn server in a thread, connects with the MCP streamable-http
client carrying a Bearer header, calls a tool (with `_request` monkeypatched to
capture the resolved key instead of hitting Contifico), and asserts the key the
server resolved equals the header the client sent.
"""
import asyncio
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["ALLOW_ENV_KEY_FALLBACK"] = "false"
os.environ["CONTIFICO_API_KEY"] = "SERVER_ENV_KEY_SHOULD_NOT_BE_USED"

import server  # noqa: E402

CAPTURED: dict[str, str] = {}


async def _fake_request(method, path, **kw):
    # Capture what the server resolved for THIS request; no network.
    CAPTURED["key"] = server._resolve_api_key()
    return {"ok": True}


server._request = _fake_request  # tools resolve the module global at call time
server.ALLOW_ENV_KEY_FALLBACK = False
server.CONTIFICO_READONLY = True

PORT = 8765


def _serve():
    import uvicorn
    app = server.mcp.streamable_http_app()
    uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error")
    ).run()


async def _call_with_header(bearer: str) -> str | None:
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    url = f"http://127.0.0.1:{PORT}/mcp"
    async with streamablehttp_client(
        url, headers={"Authorization": f"Bearer {bearer}"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.call_tool("listar_personas", {})
    return CAPTURED.get("key")


def main() -> int:
    threading.Thread(target=_serve, daemon=True).start()
    time.sleep(2.0)
    resolved = asyncio.run(_call_with_header("TENANT_A_KEY"))
    print(f"resolved key under http_stream: {resolved!r}")
    if resolved == "TENANT_A_KEY":
        print("PASS: per-request Authorization header reaches _resolve_api_key under http_stream")
        return 0
    if resolved == "SERVER_ENV_KEY_SHOULD_NOT_BE_USED":
        print("FAIL: header did NOT propagate — fell back to server env key (cross-tenant risk)")
        return 1
    print(f"FAIL: unexpected resolved key {resolved!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
