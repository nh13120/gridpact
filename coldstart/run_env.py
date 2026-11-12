"""The test bed for the cold-start run (HW9). Starts a fresh GridPact server on the synthetic registry, one logging
proxy per client agent, registers the over-declaring seller PVB_37 (its owner's act, part of the setup) and runs a
small responder for it that accepts any offer addressed to it. Prints a JSON line with the URLs, then runs until killed.

    python -m coldstart.run_env --out coldstart/runs/<name>

The client agents see only their own proxy URL. They are never told who else is registered or who lies.
"""
import argparse
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parent.parent
SERVER_PORT, PROXY_PORTS = 8830, {"buyer": 8841, "seller": 8842, "auditor": 8843}
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


class Mcp:
    def __init__(self, url):
        self.url, self.n, self.sid = url, 0, None
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "liar-bot", "version": "0"}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _h(self):
        return {**H, **({"Mcp-Session-Id": self.sid, "MCP-Protocol-Version": "2025-06-18"} if self.sid else {})}

    def _rpc(self, method, params):
        self.n += 1
        text, headers = self._post({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        self.sid = headers.get("mcp-session-id", self.sid)
        body = next((ln[5:].strip() for ln in text.splitlines() if ln.startswith("data:")), text)
        return json.loads(body)["result"]

    def _post(self, payload):
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=self._h(), method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode(), {k.lower(): v for k, v in r.getheaders()}

    def call(self, name, **a):
        return json.loads(self._rpc("tools/call", {"name": name, "arguments": a})["content"][0]["text"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(8)
    env = {**os.environ, "GRIDPACT_DATA_DIR": str(ROOT / "fixtures" / "synthetic"), "GRIDPACT_DB": str(out / "gridpact.db"),
           "GRIDPACT_PORT": str(SERVER_PORT), "GRIDPACT_OPERATOR_KEY": key}
    (out / "gridpact.db").unlink(missing_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "gridpact.server"], cwd=ROOT, env=env,
                              stdout=open(out / "server.log", "w"), stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{SERVER_PORT}/mcp"
    for _ in range(60):
        try:
            Mcp(url); break
        except Exception:
            time.sleep(0.5)
    sys.path.insert(0, str(ROOT))
    from coldstart.log_proxy import make_server
    for role, port in PROXY_PORTS.items():
        threading.Thread(target=make_server(port, url, out / f"{role}.jsonl").serve_forever, daemon=True).start()
    bot = Mcp(url)                                         # setup: the liar's owner registers its seller
    liar = bot.call("register_agent", agent_id="PVB_37", role="seller", declared_flex_kw=5000.0)
    assert liar["ok"], liar
    info = {"server": url, "operator_key": key, "db": str(out / "gridpact.db"),
            "proxies": {r: f"http://127.0.0.1:{p}/mcp" for r, p in PROXY_PORTS.items()}}
    (out / "env.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info), flush=True)
    answered = set()
    try:
        while True:                                        # responder for PVB_37: accepts whatever is offered to it
            inbox = bot.call("get_inbox", token=liar["token"])
            for o in inbox.get("incoming", []):
                if o["offer_id"] not in answered:
                    answered.add(o["offer_id"])
                    r = bot.call("respond", token=liar["token"], offer_id=o["offer_id"], action="accept")
                    (out / "liar_bot.jsonl").open("a").write(json.dumps({"offer": o["offer_id"], "result": r}) + "\n")
            time.sleep(2)
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
