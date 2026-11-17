"""Build the HW9 team PDF: usability evidence, then the final slides.

    python coldstart/report/make_report.py [--deck-url URL]      (needs reportlab; slides from slide/final/slide1..4.png)

Check results are read from coldstart/runs/run*/score.json, so the table cannot drift from the scores.
The run 5 paragraph is read from coldstart/report/run5_paragraph.txt (written after the run, from its logs).
"""
import argparse
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GREEN, INK, MID, HAIR = colors.HexColor("#00a65a"), colors.HexColor("#121212"), colors.HexColor("#5f5e5b"), colors.HexColor("#cecec8")

B = ParagraphStyle("b", fontName="Helvetica", fontSize=9.2, leading=12.2, textColor=INK, spaceAfter=4)
SM = ParagraphStyle("sm", parent=B, fontSize=8.4, leading=11, textColor=MID)
H1 = ParagraphStyle("h1", parent=B, fontName="Helvetica-Bold", fontSize=17, leading=21, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=B, fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=GREEN, spaceBefore=8, spaceAfter=4)
CODE = ParagraphStyle("code", parent=B, fontName="Courier", fontSize=8, leading=10.4, leftIndent=8, backColor=colors.HexColor("#efefe9"))
CELL = ParagraphStyle("cell", parent=B, fontSize=8.3, leading=10.4, spaceAfter=0)

CHECKS = [("B1", "buyer registered as COM_09"), ("B2", "a commitment covers steps 68 to 79"),
          ("B3", "at least 1,500 kWh/step committed"), ("B4", "all prices at or below $55"),
          ("B5", "no double-booking, no cap exceeded"), ("B6", "PVB_99 request refused, nothing created, reported"),
          ("B8", "step-range limit refused live on a registered seller (added for run 4)"),
          ("B7", "buyer's reported totals match the database"), ("S1", "PVB_17 registered as seller"),
          ("S2", "every offer to PVB_17 answered"), ("S3", "price floor ($45) and cap respected"),
          ("A1", "an auditor registered"), ("A2", "valid challenge on PVB_37 before settlement"),
          ("A3", "no wrong challenge (honest plant not accused)"),
          ("A4", "auditor read the registry through get_registry before challenging (added for run 5)"),
          ("Y1", "ledger hash chain intact"), ("Y2", "liar's commitment cut to its real cap; buyer not out of pocket")]


def p(t, st=B):
    return Paragraph(t, st)


def runs():
    out = {}
    for i in range(1, 7):
        f = ROOT / "coldstart" / "runs" / f"run{i}" / "score.json"
        if f.exists():
            out[i] = json.loads(f.read_text())["checks"]
    return out


def table(data, widths, head=True, align_center_from=None):
    data = [[(Paragraph(c, CELL) if isinstance(c, str) and not (head and ri == 0) and len(c) > 14 else c) for c in row] for ri, row in enumerate(data)]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", 8.3), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, -1), 0.3, HAIR), ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]
    if head:
        st += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.3), ("TEXTCOLOR", (0, 0), (-1, 0), GREEN)]
    if align_center_from is not None:
        st.append(("ALIGN", (align_center_from, 0), (-1, -1), "CENTER"))
    t.setStyle(TableStyle(st))
    return t


def build(deck_url, out):
    deck = f'<a href="{deck_url}" color="#00a65a">{deck_url}</a>' if deck_url else "[paste the link to our slides in the shared Demo Day deck here]"
    sc = runs()
    n = max(sc)
    run5 = (HERE / "run5_paragraph.txt").read_text().strip()
    run6 = (HERE / "run6_paragraph.txt").read_text().strip()
    tot = {i: (sum(1 for v in c.values() if v), len(c)) for i, c in sc.items()}
    S = []
    S += [p("GridPact: agent usability and final project slides", H1),
          p("Homework 9, MAS.665 AI Studio, Fall 2026. Team: Nicolas Hong, Maheen Rassell.", B), p("Links", H2)]
    S.append(table([["Interface documentation", "https://github.com/nh13120/gridpact/blob/main/docs/AGENT_GUIDE.md"],
                    ["Our slides in the shared Demo Day deck", Paragraph(deck, CELL)],
                    ["Code (GridPact)", "github.com/nh13120/gridpact"],
                    ["HW8 pull request (Nanda Town)", "github.com/projnanda/nandatown/pull/345"],
                    ["Cold-start plan, logs, scorer", Paragraph(
                        f"coldstart/ in the repository: PLAN.md (committed before each run), runs/run1..{n}/ (the proxy log of every request and "
                        "response for each client, the scores and the clients' reports), check.py (the scorer), run_env.py (the test bed)", CELL)]],
                   [150, 360], head=False))
    S += [p("Contributions", H2),
          table([["Person", "Contribution"],
                 [Paragraph("Nicolas Hong", CELL), Paragraph("GridPact itself: the protocol, ledger, MCP server and Haiku agents; the HW7 preregistration, benchmark harness, "
                                                             "runs and the v2 change that this work builds on.", CELL)],
                 [Paragraph("Maheen Rassell", CELL), Paragraph(
                     "HW6 audit fixes (bounty accounting, money-conservation check, settlement tests); HW7 write-up; HW8 Nanda Town integration and pull "
                     "request; HW9 agent guide, cold-start test bed and scorer, the get_commitments, notices and get_registry improvements and their tests, "
                     "final slides, the 30-second demo video and this report. The HW8 and HW9 engineering was done with an AI coding assistant "
                     "(Claude Code), which also ran the cold-start test bed described below.", CELL)]], [90, 420])]

    S += [p("1. The interface", H2),
          p("GridPact is shared infrastructure for energy agents: a marketplace and referee. Agents trade energy for windows of 15-minute steps, a seller locks a "
            "deposit (stake) against its promise, plain code settles delivery, and an auditor can challenge a false capacity claim. It is not an agent itself. "
            "The full guide, written for an agent that has seen nothing else, is docs/AGENT_GUIDE.md. Summary:"),
          table([["Access", "MCP over streamable HTTP, e.g. http://127.0.0.1:8765/mcp. The guide gives the three-request HTTP handshake (initialize, notifications/initialized, tools/call) and a working curl example, so any client that can POST JSON can use it."],
                 ["Tools", "register_agent, find_counterparties, propose, respond, get_inbox, get_commitments and get_registry (both added in this homework), get_ledger, challenge. Every reply is JSON with ok and, on refusal, a reason. A reply may also carry notices (added in this homework)."],
                 ["Inputs and outputs", "Time is 96 steps of 15 minutes (step 68 = 17:00); energy in kWh per step, prices in $/MWh. The guide tabulates every tool's inputs and returned fields."],
                 ["Permissions and limits", "Roles buyer, seller, auditor; a secret token from registration (shown once) is the identity. Caps on kWh per step; the seller's stake is locked at acceptance; only auditors challenge; a valid challenge pays 10% of the stake, a wrong one costs a $50 bond; one valid challenge per commitment. Agents cannot settle: the operator closes the day."],
                 ["Setup", "GRIDPACT_DATA_DIR=fixtures/synthetic python -m gridpact.server (made-up registry, no data files or API key needed)."],
                 ["One small example", "COM_09 registers, proposes 500 kWh/step to PVB_17 for steps 68 to 79 at $50/MWh with a $60 penalty (request_id 'order-1'); PVB_17 reads get_inbox and accepts; the commitment locks a $360 stake (60 x 500 x 12 / 1000)."]],
                [105, 405], head=False)]

    S += [PageBreak(), p("2. Cold-start test", H2),
          p("<b>Question.</b> Can an agent that has only the guide, a URL and a task use GridPact for a real job? <b>Setup.</b> Three fresh Claude sessions ran at the same time "
            "as a buyer (COM_09), an honest seller (PVB_17) and an auditor (AUD_1), each with its own logging proxy in front of one GridPact server on the synthetic registry. "
            "Each was given the guide, its URL and a one-paragraph task. No call sequence and no expected answer were given; the author passed no messages between them. "
            "They coordinated only through GridPact. In runs 1 to 4 the auditor was also authorised to read the public registry file, because the nameplate was only there; "
            "from run 5 on it was not (see section 3). A seller PVB_37, which declares 5,000 kW for a 2,500 kW battery, was registered by its owner as part of the setup, with a "
            "small script that accepts any offer made to it."),
          p("<b>Success defined before the run.</b> coldstart/PLAN.md (commit 74055c8, before run 1) fixes the task texts and 15 checks; B8 was added before run 4 and A4 before run 5, "
            "each in PLAN.md before its run, and run 6 changed only the buyer's wording, also in PLAN.md before it. They are scored from the database and the proxy logs, not from what a client says:")]
    rows = [["#", "Check"] + [f"Run {i}" for i in sc]]
    for k, d in CHECKS:
        r = [k, Paragraph(d, CELL)]
        for i, c in sc.items():
            r.append("PASS" if c.get(k) else "FAIL") if k in c else r.append("not scored")
        rows.append(r)
    rows.append(["", Paragraph("<b>Checks passed</b>", CELL)] + [f"{a} of {b}" for a, b in tot.values()])
    S.append(table(rows, [22, 204] + [44] * len(sc), align_center_from=2))
    S += [Spacer(1, 4), p("What the clients did, and how they used the result", H2),
          p("In run 1 the buyer registered, listed sellers, proposed 1,250 kWh/step to PVB_37 and 250 to PVB_17 at $50/MWh, polled its inbox until both were accepted "
            "(about a minute), and reported 18,000 kWh for $900. The seller polled for the full ten minutes and accepted the one offer that fit. The auditor wrote its own "
            "HTTP client from the guide, found PVB_37's declared 5,000 kW in the ledger, compared it with the registry nameplate (2,500 kW), challenged, and was ruled valid "
            "($90 bounty); it left the honest PVB_17 alone. The server cut PVB_37's commitment to 625 kWh/step and released $450 of its stake. After settlement the ledger "
            "chain verified and the liar's delivery matched its real battery."),
          p("<b>Where the result use failed (run 1).</b> The auditor's challenge cut the buyer's commitment at 16 s. The buyer next polled at 42 s, but get_inbox shows only that an "
            "offer is 'accepted', not its current volume. It reported 18,000 kWh and $900; the database held 10,500 kWh and $525 (B3 and B7). <b>Classification: interface "
            "limitation.</b> The buyer followed the guide, nothing was refused, and no tool could have told it. It is not a test-setup problem: the proxy, the server and the liar's "
            "script behaved as designed, and the cut is GridPact working as intended."),
          p("<b>Other friction the clients reported</b> (all recorded in the fixes below): no stated way to read the registry parquet file (system Python had no parquet reader; the "
            "auditor borrowed the repository's virtual-environment interpreter, which we disclose as a deviation from 'documentation only'); the guide did not list the ledger's "
            "action names, the inbox's fields, that steps are inclusive, or that a seller must register before it can be proposed to. The shell's 120-second background rule and a "
            "missing timeout command on macOS were environment issues, not GridPact's.")]

    S += [p("3. Boundary case, improvements, reruns", H2),
          p("<b>Boundary tested.</b> Every run asked for PVB_99 (steps 100 to 110). GridPact answered {\"ok\": false, \"reason\": \"PVB_99 is not registered\"}, created no offer, and every "
            "client reported it accurately (B6). Because that refusal comes before the step range is checked, runs 1 to 3 never reached the range limit. From run 4 the buyer was also "
            "told to ask a registered seller for steps 100 to 110 and got 'steps must satisfy 0 &lt;= step_from &lt;= step_to &lt; 96', nothing created (B8). tests/test_boundaries.py covers "
            "these and the other limits directly (reversed steps, over-cap volume, negative price, empty request_id, wrong role, wrong token, a second challenge on one commitment): "
            "each is refused with a reason and changes no offers, commitments or ledger entries."),
          p("<b>Improvements, in order.</b> (1) After run 1, a read tool get_commitments (current volume, original volume if cut, price, stake, status) and guide fixes for the friction "
            "the clients listed. (2) After run 2, notices: when a valid challenge cuts a commitment, both parties are told on their next successful call, on any tool, once. "
            "(3) After run 4, get_registry: the public nameplate next to each agent's declared figure, so an auditor needs no file access. Regression tests: "
            "tests/test_get_commitments.py, tests/test_notices.py and tests/test_get_registry.py (43 tests pass in all)."),
          p("<b>Rerun results.</b> Run 2 (13 of 15): the tool worked, but the buyer called it once at 46 s, before the challenge at 107 s, then polled only find_counterparties "
            "until 352 s and reported a stale position (18,000 kWh, $990 against 10,500 kWh and $578 in the database). Run 2 is kept as it happened. Its cause was an interface "
            "that pushes nothing, which a guide note could not fix, so we added notices. Run 3 (15 of 15, guide note only): the buyer re-read at 557 s, found the cut, bought the "
            "missing 625 kWh/step and reported correctly; it polled for 580 s against run 2's 352 s, so the runs are not matched. Run 4 (16 of 16, notices, fresh clients, same tasks "
            "plus the range probe): the auditor's valid challenge cut PVB_37 from 750 to 625 kWh/step; the buyer's next call returned a notice saying so, it bought the missing "
            "125 kWh/step from PVB_17, re-read get_commitments, and reported 18,000 kWh and $990, matching the database. The same failure mode as run 2 (a buyer that keeps "
            "making other calls) now ends correctly."),
          p(run5), p(run6)]

    S += [p("What improved, what did not, what is unproven", H2),
          p("<b>Improved:</b> an agent can see a cut and is told about it on whatever call it makes next; an auditor can compare a claim with the real battery through the tools; "
            "the guide covers the friction the clients listed; each blind spot has regression tests and a passing rerun. <b>Did not improve:</b> a buyer that makes no further "
            "call still holds a stale position; the seller learns only by polling; the guide does not say what happens when the operator closes the day or stops the server "
            "(a run 4 client flagged this). <b>Unproven:</b> the clients are fresh Claude sessions started by the author, not another builder's agents, so this is a self-run test "
            "with no independent client; there is one run per condition and the auditor's timing varies between runs, so we claim no success rate; only buyer, seller and "
            "auditor roles and one lie were tested.")]

    S += [KeepTogether([p("4. Repeat the test", H2),
          Paragraph("# 1. server, logging proxies and the liar's owner script; prints three client URLs<br/>"
                    "python -m coldstart.run_env --out coldstart/runs/mine<br/>"
                    "# 2. give each fresh client docs/AGENT_GUIDE.md, its URL and its task from coldstart/PLAN.md<br/>"
                    "# 3. score the checks (--settle closes the day as the operator)<br/>"
                    "python -m coldstart.check coldstart/runs/mine --reports reports.json --settle<br/>"
                    "# unit, boundary and regression tests (43)<br/>pytest", CODE)]),
          Spacer(1, 4),
          p("<b>Disclosure:</b> self-run; the clients were fresh Claude subagent sessions of the same model family as the author's assistant; manual help during the runs: none; the author "
            "wrote the guide, the test bed and the checks; the clients shared a working directory with the repository and were told to read only the guide (their reports list the files "
            "they read; the run 1 to 4 auditors also read the registry file and used the repository's Python interpreter, noted above; the run 5 auditor was told not to read any "
            "file but the guide, which the instruction, not a sandbox, enforces). In run 2 the seller's polling ended at about 560 of 600 seconds because the test bed was stopped "
            "to start run 3; no offer was pending, so no outcome changed. The test bed of each later run was stopped when scoring began, after every offer to the seller had been "
            "answered.", SM)]

    S += [PageBreak(), p("Final project slides", H2),
          p(f"Export of our slides. Live deck: {deck}. The embedded demo video (a 30-second animation of the deposit, check and settle flow, Unlisted on YouTube, set to play "
            "automatically) is checked in the live deck.", SM), Spacer(1, 6)]
    for i in range(1, 5):
        S.append(Image(str(ROOT / "slide" / "final" / f"slide{i}.png"), width=6.3 * inch, height=3.54 * inch))
        S.append(Spacer(1, 8))

    def page(c, d):
        c.saveState(); c.setFont("Helvetica", 8); c.setFillColor(MID)
        c.drawString(0.8 * inch, 0.55 * inch, "GridPact: HW9 usability evidence")
        c.drawRightString(letter[0] - 0.8 * inch, 0.55 * inch, f"page {d.page}"); c.restoreState()

    SimpleDocTemplate(str(out), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch, topMargin=0.7 * inch, bottomMargin=0.8 * inch,
                      title="GridPact HW9: agent usability and final slides", author="Nicolas Hong, Maheen Rassell").build(S, onFirstPage=page, onLaterPages=page)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--deck-url", default=""); ap.add_argument("--out", default=str(HERE / "GridPact_HW9_report.pdf"))
    a = ap.parse_args(); build(a.deck_url, Path(a.out)); print("wrote", a.out)
