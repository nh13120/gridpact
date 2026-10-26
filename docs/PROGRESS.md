# Progress

Check the phase's "done when" command before ticking it. Details in `PLAN.md`.

- [x] Phase 0 - repo setup + data inspection. Check: `python -m gridpact.data`
- [x] Phase 1 - SQLite state + hash-chained ledger. Check: `pytest tests/test_ledger.py`
- [x] Phase 2 - MCP server with 7 tools. Check: `python -m tests.smoke_client`
- [x] Phase 3 - LLM agents + orchestration. Check: `python orchestrate.py --demo` (needs ANTHROPIC_API_KEY; ~$0.01)
- [x] Phase 4 - settlement + challenge adjudication. Check: `python orchestrate.py --demo` (liar: shortfall, valid challenge, reputation 0.5)
- [ ] Phase 5 - independent `verify.py` + `python orchestrate.py --demo`
- [ ] Phase 6 - README complete, fresh-clone test, GitHub

## What's next
Phase 5: `verify.py` (independent checks 1-5, no imports from gridpact/), `--demo` runs it at the end.
