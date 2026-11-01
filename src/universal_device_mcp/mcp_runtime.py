"""Select the official MCP SDK when installed, with a stdlib stdio fallback.

The fallback implements the MCP JSON-RPC methods used by this server. It is kept
small so a base installation can still start when optional dependencies are not
available; installing ``mcp`` uses the official SDK instead.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import sys
import types
import typing
from typing import Any, get_args, get_origin, get_type_hints

_FALLBACK_PROTOCOL_VERSION = "2024-11-05"

if os.environ.get("UDMCP_FORCE_STDIO_FALLBACK", "").lower() == "true":
    USING_OFFICIAL_SDK = False
else:
    try:
        from mcp.server import MCPServer as FastMCP
        USING_OFFICIAL_SDK = True
    except ImportError:
        try:
            from mcp.server.fastmcp import FastMCP as FastMCP
            USING_OFFICIAL_SDK = True
        except ImportError:
            USING_OFFICIAL_SDK = False

if not USING_OFFICIAL_SDK:
    class FastMCP:  # noqa: N801 - mirrors the public SDK server class
        def __init__(self, name: str, instructions: str = "") -> None:
            self.name = name
            self.instructions = instructions
            self._tools: dict[str, Any] = {}
            self._resources: dict[str, tuple[Any, dict[str, Any]]] = {}

        def tool(self, *args: Any, **kwargs: Any):
            def register(func):
                func._mcp_annotations = kwargs.get("annotations")
                self._tools[func.__name__] = func
                return func
            if args and callable(args[0]):
                return register(args[0])
            return register

        def resource(self, uri: str, **metadata: Any):
            def register(func):
                self._resources[uri] = (func, metadata)
                return func
            return register

        def _schema(self, func: Any) -> dict[str, Any]:
            hints = get_type_hints(func)
            properties: dict[str, Any] = {}
            required: list[str] = []
            for parameter in inspect.signature(func).parameters.values():
                annotation = hints.get(parameter.name, Any)
                properties[parameter.name] = self._json_schema(annotation)
                if parameter.default is inspect.Parameter.empty:
                    required.append(parameter.name)
            schema: dict[str, Any] = {"type": "object", "properties": properties}
            if required:
                schema["required"] = required
            return schema

        @classmethod
        def _matches_type(cls, value: Any, annotation: Any) -> bool:
            if annotation is Any:
                return True
            origin = get_origin(annotation)
            args = get_args(annotation)
            if origin in (typing.Union, types.UnionType):
                return any(cls._matches_type(value, item) for item in args)
            if origin is list:
                return isinstance(value, list) and all(
                    cls._matches_type(item, args[0]) for item in value
                )
            if origin is dict:
                if len(args) < 2:
                    return isinstance(value, dict)
                return isinstance(value, dict) and all(
                    cls._matches_type(key, args[0]) and cls._matches_type(item, args[1])
                    for key, item in value.items()
                )
            if annotation is bool:
                return isinstance(value, bool)
            if annotation is int:
                return isinstance(value, int) and not isinstance(value, bool)
            if annotation is float:
                return isinstance(value, int | float) and not isinstance(value, bool)
            return isinstance(value, annotation) if isinstance(annotation, type) else True

        @classmethod
        def _validate_arguments(cls, func: Any, arguments: Any) -> dict[str, Any]:
            if not isinstance(arguments, dict):
                raise TypeError("Tool arguments must be a JSON object")
            signature = inspect.signature(func)
            hints = get_type_hints(func)
            accepted = {key for key, parameter in signature.parameters.items()
                        if parameter.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                                  inspect.Parameter.VAR_KEYWORD)}
            unknown = set(arguments) - accepted
            if unknown:
                raise TypeError(f"Unexpected tool arguments: {', '.join(sorted(unknown))}")
            for name, parameter in signature.parameters.items():
                if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue
                if name not in arguments:
                    if parameter.default is inspect.Parameter.empty:
                        raise TypeError(f"Missing required tool argument: {name}")
                    continue
                annotation = hints.get(name, Any)
                if not cls._matches_type(arguments[name], annotation):
                    expected = getattr(annotation, "__name__", str(annotation))
                    raise TypeError(f"Tool argument {name!r} must match {expected}")
            return arguments

        @classmethod
        def _json_schema(cls, annotation: Any) -> dict[str, Any]:
            origin = get_origin(annotation)
            args = get_args(annotation)
            if origin is list:
                return {"type": "array", "items": cls._json_schema(args[0] if args else Any)}
            if origin is dict:
                return {"type": "object", "additionalProperties": True}
            if origin is not None and args:
                non_none = [arg for arg in args if arg is not type(None)]
                if len(non_none) == 1:
                    return cls._json_schema(non_none[0])
                return {"anyOf": [cls._json_schema(arg) for arg in non_none]}
            types = {str: "string", int: "integer", float: "number", bool: "boolean"}
            return {"type": types[annotation]} if annotation in types else {}

        @staticmethod
        def _text(value: Any) -> str:
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)

        def _dispatch(self, request: dict[str, Any]) -> dict[str, Any] | None:
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}
            if method == "notifications/initialized" or method == "notifications/cancelled":
                return None
            if method == "initialize":
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                    "protocolVersion": _FALLBACK_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False},
                                     **({"resources": {"listChanged": False}}
                                        if self._resources else {})},
                    "serverInfo": {"name": self.name, "version": "0.1.0"},
                    "instructions": self.instructions}}
            if method == "ping":
                return {"jsonrpc": "2.0", "id": request_id, "result": {}}
            if method == "tools/list":
                tools = [{"name": name, "description": inspect.getdoc(func) or "",
                          "inputSchema": self._schema(func),
                          **({"annotations": func._mcp_annotations}
                             if getattr(func, "_mcp_annotations", None) else {})}
                         for name, func in self._tools.items()]
                return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
            if method == "resources/list":
                resources = [{"uri": uri, "name": metadata.get("name", uri),
                              "description": metadata.get("description", ""),
                              "mimeType": metadata.get("mime_type", "text/plain")}
                             for uri, (_, metadata) in self._resources.items()
                             if "{" not in uri]
                return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": resources}}
            if method == "resources/read":
                uri = params.get("uri", "")
                for template, (func, metadata) in self._resources.items():
                    names = re.findall(r"\{([^{}]+)\}", template)
                    pattern = re.escape(template)
                    for name in names:
                        pattern = pattern.replace(re.escape("{" + name + "}"), f"(?P<{name}>[^/]+)")
                    match = re.fullmatch(pattern, uri)
                    if match:
                        try:
                            value = func(**match.groupdict()) if names else func()
                            mime_type = metadata.get("mime_type", "text/plain")
                            content = value if isinstance(value, str) else json.dumps(
                                value, ensure_ascii=False, default=str)
                            return {"jsonrpc": "2.0", "id": request_id, "result": {
                                "contents": [{"uri": uri, "mimeType": mime_type, "text": content}]}}
                        except Exception as exc:
                            return {"jsonrpc": "2.0", "id": request_id,
                                    "error": {"code": -32603,
                                              "message": f"Could not read resource {uri}: {exc}"}}
                return {"jsonrpc": "2.0", "id": request_id,
                        "error": {"code": -32602, "message": f"Unknown resource: {uri}"}}
            if method == "resources/templates/list":
                templates = [{"uriTemplate": uri, "name": metadata.get("name", uri),
                              "description": metadata.get("description", ""),
                              "mimeType": metadata.get("mime_type", "text/plain")}
                             for uri, (_, metadata) in self._resources.items() if "{" in uri]
                return {"jsonrpc": "2.0", "id": request_id, "result": {"resourceTemplates": templates}}
            if method == "tools/call":
                name = params.get("name")
                func = self._tools.get(name)
                if func is None:
                    result = {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
                else:
                    try:
                        arguments = self._validate_arguments(func, params.get("arguments", {}))
                        value = func(**arguments)
                        result = {"content": [{"type": "text", "text": self._text(value)}]}
                    except Exception as exc:
                        result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
                return {"jsonrpc": "2.0", "id": request_id, "result": result}
            return {"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}}

        def run(self, transport: str = "stdio") -> None:
            if transport != "stdio":
                raise ValueError("The dependency-free MCP runtime supports stdio only")
            for line in sys.stdin.buffer:
                try:
                    request = json.loads(line)
                except Exception as exc:
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": str(exc)}}) + "\n")
                    sys.stdout.flush()
                    continue
                try:
                    response = self._dispatch(request)
                except Exception as exc:
                    request_id = request.get("id") if isinstance(request, dict) else None
                    response = {"jsonrpc": "2.0", "id": request_id,
                                "error": {"code": -32603, "message": str(exc)}}
                if response is not None:
                    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                    sys.stdout.flush()

