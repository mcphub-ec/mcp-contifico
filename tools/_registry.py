"""Data-driven tool registry + factory for the Contifico MCP server (issue #4).

Replaces ~37 hand-written ``@mcp.tool()`` shims with a declarative spec table
(:data:`tools.specs.SPECS`) plus this factory. Each :class:`ToolSpec` carries
the EXACT original Python signature text and docstring so FastMCP regenerates a
byte-identical ``inputSchema``/description, plus a structured behavior
descriptor that the runtime dispatcher replays to build the same method, path,
query params and request body the original hand-written tool produced.

Why exec a literal signature instead of ``inspect.Signature``?
  FastMCP derives each tool's JSON schema from the function's annotations via
  Pydantic. Reproducing every original annotation object (``str | None``,
  ``list[dict[str, Any]]``, bare ``dict``/``list``) by hand is error-prone; the
  schemas differ on subtle cases (e.g. ``list[dict]`` has no ``items`` but
  ``list[dict[str, Any]]`` does). Compiling the ORIGINAL signature source in a
  namespace that has the same ``Any`` / typing context guarantees the annotation
  objects — and therefore the schema — are identical. The generated body is a
  thin shim that captures its own arguments and hands them to the dispatcher, so
  the public interface (what the schema reflects) and the runtime behavior are
  defined in one place each.

Every generated tool resolves request helpers through the ``server`` module at
call time (``server._request`` / ``server._resolve_pos_token`` / ``server._json``
/ ``server._drop_none``), exactly as the hand-written tools did, so the test
suite's monkeypatching of ``server.*`` keeps working.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import server
from app import mcp


@dataclass(frozen=True)
class ToolSpec:
    """Declarative description of one Contifico endpoint exposed as an MCP tool.

    Interface (drives the generated schema — must match the original verbatim):
      name: the tool's ``__name__`` (and schema title prefix).
      sig: the exact original parameter list as source text, e.g.
           ``"id_integracion: str, page: str | None = None"`` (no parens).
      doc: the exact original docstring (without surrounding triple quotes).

    Behavior (drives the runtime request — replays the original body):
      method: HTTP method ("GET" / "POST" / "PUT").
      path: path template; ``{name}`` placeholders are filled from arguments.
      mode: which body/params construction the original used. One of:
        - "params":      GET with a fixed query-param dict (``query`` keys).
        - "params_pos_v1": GET, ``params = {"pos": pos_token} if pos_token else {}``.
        - "params_truthy": GET, build params from truthy values only, then pass
                            ``params if params else None`` (bancos movimientos).
        - "documentos_list": the listar_documentos page→result_page special case.
        - "body_literal": POST/PUT with a single-key body (``required`` first key).
        - "body":        POST/PUT with required body keys + drop-none optionals.
        - "inv_create":  crear_movimiento_inventario (if-not-None optionals).
        - "asiento_create": crear_asiento_contable (extra_data merge + v1 pos).
      query: ordered query-param argument names (mode="params"/"documentos_list").
      required: ordered required body-field names (POST/PUT body modes).
      optional: ordered optional (drop-none) body-field names.
      pos_arg: argument name holding the POS token, when the body needs
               ``server._resolve_pos_token`` (crear/actualizar persona/documento).
      pos_in_params: True when the resolved pos is sent as ``params={"pos": pos}``
                     (persona) rather than embedded in the body (documento).
    """

    name: str
    sig: str
    doc: str
    method: str
    path: str
    mode: str
    query: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    pos_arg: str | None = None
    pos_in_params: bool = False


async def _dispatch(spec: ToolSpec, args: dict[str, Any]) -> str:
    """Replay ``spec``'s original request from the captured call ``args``.

    ``args`` is the generated function's ``locals()`` — i.e. exactly the named
    parameters the caller supplied (after defaults). This rebuilds the same
    method/path/params/body the hand-written tool built and returns
    ``server._json`` of the result, preserving the original contract.
    """
    path = spec.path.format(**args) if "{" in spec.path else spec.path
    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None

    if spec.mode == "params":
        # No query keys -> the original passed no params kwarg at all (params
        # stays None); only build a params dict when there are keys to send.
        params = {k: args[k] for k in spec.query} if spec.query else None
    elif spec.mode == "params_pos_v1":
        pos_token = args.get("pos_token")
        params = {"pos": pos_token} if pos_token else {}
    elif spec.mode == "params_truthy":
        # bancos movimientos: only include truthy values; pass None if empty.
        built: dict[str, Any] = {}
        if args.get("fecha_inicial"):
            built["fecha_inicial"] = args["fecha_inicial"]
        if args.get("fecha_final"):
            built["fecha_final"] = args["fecha_final"]
        if args.get("pos_token"):
            built["pos"] = args["pos_token"]
        params = built if built else None
    elif spec.mode == "documentos_list":
        # 'page' is an alias for result_page when it is a digit string.
        result_page_val = args.get("result_page")
        page = args.get("page")
        if page is not None and str(page).isdigit():
            result_page_val = int(page)
        params = {
            "tipo_registro": args["tipo_registro"],
            "tipo": args["tipo"],
            "fecha_modificacion": args["fecha_modificacion"],
            "fecha_emision": args["fecha_emision"],
            "fecha_vencimiento": args["fecha_vencimiento"],
            "fecha_creacion": args["fecha_creacion"],
            "persona_identificacion": args["persona_identificacion"],
            "result_size": args["result_size"],
            "result_page": result_page_val,
            "fecha_inicial": args["fecha_inicial"],
            "fecha_final": args["fecha_final"],
            "persona_id": args["persona_id"],
            "bodega_id": args["bodega_id"],
        }
    elif spec.mode == "body_literal":
        key = spec.required[0]
        body = {key: args[key]}
    elif spec.mode == "body":
        body = {}
        if spec.pos_arg is not None:
            resolved = server._resolve_pos_token(args.get(spec.pos_arg) or "")
            if spec.pos_in_params:
                params = {"pos": resolved}
            else:
                body["pos"] = resolved
        for k in spec.required:
            body[k] = args[k]
        body.update(server._drop_none({k: args[k] for k in spec.optional}))
    elif spec.mode == "inv_create":
        body = {k: args[k] for k in spec.required}
        for k in spec.optional:
            if args.get(k) is not None:
                body[k] = args[k]
    elif spec.mode == "asiento_create":
        body = {k: args[k] for k in spec.required}
        if args.get("extra_data"):
            body.update(args["extra_data"])
        pos_token = args.get("pos_token")
        params = {"pos": pos_token} if pos_token else {}
    else:  # pragma: no cover - guards against an unknown mode in the table
        raise ValueError(f"Unknown tool mode: {spec.mode!r}")

    kwargs: dict[str, Any] = {}
    if params is not None:
        kwargs["params"] = params
    if body is not None:
        kwargs["body"] = body
    result = await server._request(spec.method, path, **kwargs)
    return server._json(result)


# Namespace the generated functions are compiled in. ``Any`` must resolve to the
# SAME object the originals used (typing.Any) so annotations like
# ``list[dict[str, Any]]`` reproduce the original schema exactly.
_EXEC_GLOBALS = {"Any": Any}


def build_tool(spec: ToolSpec):
    """Compile, register (via ``mcp.tool()``) and return one generated tool fn.

    The function is compiled from the spec's LITERAL original signature + the
    SAME ``Any``/typing context, so FastMCP regenerates the identical schema.
    Its body just captures the call's locals and defers to :func:`_dispatch`.
    """
    src = (
        f"async def {spec.name}({spec.sig}) -> str:\n"
        f"    {spec.doc!r}\n"
        f"    return await __dispatch(__spec, locals())\n"
    )
    ns = dict(_EXEC_GLOBALS)
    ns["__dispatch"] = _dispatch
    ns["__spec"] = spec
    exec(compile(src, f"<tool:{spec.name}>", "exec"), ns)  # noqa: S102 - trusted, static specs
    fn = ns[spec.name]
    # The docstring above is the repr of the original; restore the exact object
    # (repr round-trips for these plain strings, but assign to be unambiguous).
    fn.__doc__ = spec.doc
    fn.__module__ = "tools._registry"
    mcp.tool()(fn)
    return fn


def register_all(specs) -> dict[str, Any]:
    """Build + register every spec; return {name: fn} (also exposed as module globals)."""
    built: dict[str, Any] = {}
    for spec in specs:
        built[spec.name] = build_tool(spec)
    return built
