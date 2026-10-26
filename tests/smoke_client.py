"""No-LLM smoke test: start the server, do register -> find -> propose -> accept over MCP.

Run from the repo root: python -m tests.smoke_client
"""
import asyncio
import json

from mcp import Client

from gridpact import db, server
from gridpact.config import SERVER_URL


def out(result):
    """call_tool returns a CallToolResult; our dict is JSON text in content[0]."""
    return json.loads(result.content[0].text)


def show(name, result):
    out = globals()["out"](result)
    print(f"{name:20s} -> {json.dumps(out)[:160]}")
    assert out["ok"], out
    return out


async def main():
    async with Client(SERVER_URL) as c:
        buyer = show("register buyer", await c.call_tool("register_agent", {"agent_id": "COM_09", "role": "buyer"}))
        seller = show("register seller", await c.call_tool("register_agent", {"agent_id": "PVB_17", "role": "seller"}))
        found = show("find_counterparties", await c.call_tool("find_counterparties", {"token": buyer["token"]}))
        assert found["counterparties"][0]["agent_id"] == "PVB_17"
        offer = show("propose", await c.call_tool("propose", {
            "token": buyer["token"], "to": "PVB_17", "step_from": 68, "step_to": 79,
            "kwh_per_step": 1000, "price_usd_mwh": 45, "penalty_usd_mwh": 60}))
        too_big = (await c.call_tool("propose", {
            "token": buyer["token"], "to": "PVB_17", "step_from": 68, "step_to": 79,
            "kwh_per_step": 99999, "price_usd_mwh": 45, "penalty_usd_mwh": 60}))
        too_big = out(too_big)
        print(f"{'propose (over cap)':20s} -> {too_big}")
        assert not too_big["ok"]
        inbox = show("get_inbox", await c.call_tool("get_inbox", {"token": seller["token"]}))
        assert inbox["incoming"][0]["offer_id"] == offer["offer_id"]
        commit = show("respond accept", await c.call_tool("respond", {
            "token": seller["token"], "offer_id": offer["offer_id"], "action": "accept"}))
        assert commit["stake_usd"] == 60 * 1000 * 12 / 1000
        led = show("get_ledger", await c.call_tool("get_ledger", {"token": buyer["token"]}))
        actions = [e["action"] for e in led["entries"]]
        print("ledger actions:", actions)
        assert actions == ["register", "register", "propose", "commit"]


if __name__ == "__main__":
    db.reset()
    proc = server.launch()
    try:
        asyncio.run(main())
        print("SMOKE OK")
    finally:
        proc.terminate()
