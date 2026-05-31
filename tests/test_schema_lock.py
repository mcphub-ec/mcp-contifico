"""Schema-lock test: the exposed MCP tool contract must not drift silently.

Runnable without pytest: `python tests/test_schema_lock.py` (exits non-zero on failure).

Asserts the live tool schema (names + descriptions + inputSchema) exactly
matches the committed baseline in `tests/schemas_baseline.json`. This is the
regression guard for the behavior-preserving refactor: any future edit to a
tool, spec, or factory either keeps the contract byte-identical or must
explicitly regenerate the baseline (a reviewable diff), so drift can never
slip in unnoticed.

To intentionally change the contract, regenerate the baseline:
    python tests/test_schema_lock.py --update
and review the resulting diff in `tests/schemas_baseline.json`.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402,F401  (import registers all @mcp.tool definitions)
from app import mcp  # noqa: E402

BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas_baseline.json")


def _live_schema() -> dict:
    """Dump the live tool contract as {name: {description, inputSchema}}."""
    tools = asyncio.run(mcp.list_tools())
    return {t.name: {"description": t.description, "inputSchema": t.inputSchema} for t in tools}


def _load_baseline() -> dict:
    with open(BASELINE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_schema_matches_baseline():
    """Live tool schema is identical to the committed baseline."""
    live = _live_schema()
    base = _load_baseline()

    live_names, base_names = set(live), set(base)
    added = sorted(live_names - base_names)
    removed = sorted(base_names - live_names)
    changed = sorted(
        n for n in (live_names & base_names)
        if live[n] != base[n]
    )

    problems = []
    if added:
        problems.append(f"tools ADDED (not in baseline): {added}")
    if removed:
        problems.append(f"tools REMOVED (in baseline, now gone): {removed}")
    for n in changed:
        what = []
        if live[n].get("description") != base[n].get("description"):
            what.append("description")
        if live[n].get("inputSchema") != base[n].get("inputSchema"):
            what.append("inputSchema")
        problems.append(f"tool CHANGED: {n} ({', '.join(what)})")

    assert not problems, (
        "MCP tool contract drifted from tests/schemas_baseline.json:\n  "
        + "\n  ".join(problems)
        + "\n\nIf this change is intentional, regenerate the baseline with "
        "`python tests/test_schema_lock.py --update` and review the diff."
    )


def test_baseline_tool_count():
    """Guard against accidental wholesale loss/gain of tools."""
    base = _load_baseline()
    assert len(base) == 37, f"baseline has {len(base)} tools, expected 37"


def _update_baseline():
    live = _live_schema()
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(live, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(f"Updated {BASELINE_PATH} — {len(live)} tools")


if __name__ == "__main__":
    if "--update" in sys.argv:
        _update_baseline()
        sys.exit(0)
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
