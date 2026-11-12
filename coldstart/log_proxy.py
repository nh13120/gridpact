"""A logging pass-through proxy for MCP-over-HTTP. One instance per client agent, so every request and response
of that agent is recorded without the agent doing anything or knowing. Used by coldstart/run_env.py.

    python -m coldstart.log_proxy --listen 8841 --upstream http://127.0.0.1:8830/mcp --log coldstart/runs/x/buyer.jsonl

GET (the optional server-push stream) is answered 405, which the MCP transport allows, so a request never hangs.
"""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import urllib.error
import urllib.request

HOP = {"host", "content-length", "connection", "transfer-encoding", "accept-encoding"}


def make_server(listen: int, upstream: str, log_path: Path) -> ThreadingHTTPServer:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    def forward(method, headers, body):
        req = urllib.request.Request(upstream, data=body or None, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, dict((k.lower(), v) for k, v in r.getheaders()), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict((k.lower(), v) for k, v in e.headers.items()), e.read()

    def log(rec):
        with lock, open(log_path, "a") as f:
            f.write(json.dumps(rec) + "\n")

    class H(BaseHTTPRequestHandler):
        def _do(self):
            n = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(n) if n else b""
            t0 = time.time()
            if self.command == "GET":
                log({"t": t0, "method": "GET", "status": 405, "req": "", "resp": "GET stream not offered"})
                self.send_response(405); self.send_header("Content-Length", "0"); self.end_headers(); return
            hdrs = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
            status, rh, content = forward(self.command, hdrs, body)
            log({"t": t0, "ms": round((time.time() - t0) * 1000), "method": self.command, "status": status,
                 "session": rh.get("mcp-session-id") or self.headers.get("mcp-session-id"),
                 "req": body.decode("utf-8", "replace"), "resp": content.decode("utf-8", "replace")[:50000]})
            self.send_response(status)
            for k in ("content-type", "mcp-session-id"):
                if k in rh:
                    self.send_header(k, rh[k])
            self.send_header("Content-Length", str(len(content))); self.end_headers(); self.wfile.write(content)

        do_POST = do_DELETE = do_GET = _do

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer(("127.0.0.1", listen), H)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int, required=True); ap.add_argument("--upstream", required=True)
    ap.add_argument("--log", required=True); a = ap.parse_args()
    make_server(a.listen, a.upstream, Path(a.log)).serve_forever()
