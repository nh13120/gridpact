# Progress

Check the phase's "done when" command before ticking it. Details in `PLAN.md`.

- [x] Phase 0 - repo setup + data inspection. Check: `python -m gridpact.data`
- [x] Phase 1 - SQLite state + hash-chained ledger. Check: `pytest tests/test_ledger.py`
- [x] Phase 2 - MCP server with 7 tools. Check: `python -m tests.smoke_client`
- [ ] Phase 3 - LLM agents + orchestration. Check: `python orchestrate.py`
- [ ] Phase 4 - settlement + challenge adjudication
- [ ] Phase 5 - independent `verify.py` + `python orchestrate.py --demo`
- [ ] Phase 6 - README complete, fresh-clone test, GitHub

## What's next
Phase 3: `agents/prompts/*.md`, `agents/run_agent.py`, `orchestrate.py` (Claude Agent SDK + Haiku).
