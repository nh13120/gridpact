"""Run one agent turn with the Claude Agent SDK, talking to GridPact over MCP.

Pattern note: `query()` starts a Claude Code process, lets the model call tools until it is
done, and streams back messages. We only give it our MCP server (no file or shell tools),
cap the turns and the spend, and write every tool call to a transcript file.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock,
                              ToolResultBlock, ToolUseBlock, UserMessage, query)

from gridpact.config import ROOT, SERVER_URL

MODEL = "claude-haiku-5-5"
PROMPTS = ROOT / "agents" / "prompts"
RUN_DIR = ROOT / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S")


def log(record):
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    with open(RUN_DIR / "transcript.jsonl", "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _short(x, n=140):
    s = x if isinstance(x, str) else json.dumps(x, default=str)
    return s if len(s) <= n else s[:n] + "..."


async def run_turn(name, role_file, task, max_turns=8):
    """One agent turn. Returns (final_text, cost_usd). Prints each tool call as it happens."""
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=(PROMPTS / role_file).read_text(),
        mcp_servers={"gridpact": {"type": "http", "url": SERVER_URL}},
        allowed_tools=["mcp__gridpact__*"],   # auto-approve our tools...
        tools=[],                             # ...and give the agent no built-in ones
        setting_sources=[],                   # ignore ~/.claude settings and CLAUDE.md files
        max_turns=max_turns,
        max_budget_usd=2.0,
        stderr=lambda line: log({"agent": name, "event": "stderr", "text": line}),
    )
    print(f"\n=== {name} ===")
    log({"agent": name, "event": "task", "text": task})
    final, cost = "", 0.0
    async for msg in query(prompt=task, options=options):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    tool = b.name.replace("mcp__gridpact__", "")
                    args = {k: v for k, v in b.input.items() if k != "token"}
                    print(f"  {name} -> {tool}({_short(args, 110)})")
                    log({"agent": name, "event": "tool_call", "tool": tool, "args": args})
                elif isinstance(b, TextBlock) and b.text.strip():
                    final = b.text.strip()
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    text = b.content if isinstance(b.content, str) else " ".join(
                        c.get("text", "") for c in (b.content or []) if isinstance(c, dict))
                    print(f"     <- {_short(text.replace(chr(10), ' '), 120)}")
                    log({"agent": name, "event": "tool_result", "text": text})
        elif isinstance(msg, ResultMessage):
            cost = msg.total_cost_usd or 0.0
            log({"agent": name, "event": "result", "subtype": msg.subtype, "cost_usd": cost, "text": final})
    print(f"  {name}: {final}  (${cost:.3f})")
    return final, cost


def run(name, role_file, task, max_turns=8):
    return asyncio.run(run_turn(name, role_file, task, max_turns))
