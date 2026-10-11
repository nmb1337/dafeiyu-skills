#!/usr/bin/env python3
"""Probe any streamable-HTTP MCP server directly, without Hermes in the loop.

Use it to separate "the server is broken" from "the Hermes wiring is broken",
and to make one real tool call when verifying a newly added server.

Usage:
    python probe-mcp-http.py <url>                          # tools/list
    python probe-mcp-http.py <url> <tool> '{"k": "v"}'     # tools/call
    python probe-mcp-http.py                                # url from MCP_URL env

Exit code 0 on a JSON-RPC result, 1 on a transport/protocol failure, so it can
gate a script. Reads the SSE `data:` line that streamable-HTTP servers return.
"""
import json
import os
import sys
import urllib.request


def post(url, payload, sid=None, timeout=25):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if sid:
        req.add_header("Mcp-Session-Id", sid)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.headers.get("Mcp-Session-Id"), resp.read().decode("utf-8", "replace")


def rpc(url, method, params, sid=None, rid=1):
    sid, body = post(url, {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}, sid)
    for line in body.splitlines():
        if line.startswith("data: "):
            return sid, json.loads(line[6:])
    return sid, {"raw": body}


def main():
    args = sys.argv[1:]
    url = args.pop(0) if args else os.environ.get("MCP_URL", "")
    if not url:
        print(__doc__)
        return 1

    try:
        sid, _ = post(url, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "hermes-probe", "version": "1"}},
        })
        post(url, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, sid)

        if args:
            tool = args.pop(0)
            tool_args = json.loads(args[0]) if args else {}
            _, out = rpc(url, "tools/call", {"name": tool, "arguments": tool_args}, sid, 2)
        else:
            _, out = rpc(url, "tools/list", {}, sid, 2)
            tools = out.get("result", {}).get("tools", []) if isinstance(out, dict) else []
            out = {"tool_count": len(tools), "tools": [t.get("name") for t in tools]}
    except Exception as exc:  # transport/protocol failure
        print(f"PROBE FAILED: {type(exc).__name__}: {exc}")
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
