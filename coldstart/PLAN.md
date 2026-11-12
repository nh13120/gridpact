# Cold-start test plan (HW9). Written and committed BEFORE the run.

## What is tested
Can a fresh agent that has only `docs/AGENT_GUIDE.md`, a URL and a task use GridPact to do a real job? Three fresh
Claude sessions run at the same time, each a role in one trading day on the synthetic registry (no ENGIE files):

| Client | Role | Authorised access |
|---|---|---|
| `buyer` | community `COM_09` | its own GridPact URL; the guide; Bash for HTTP |
| `seller` | honest plant `PVB_17` | its own GridPact URL; the guide; Bash for HTTP |
| `auditor` | `AUD_1` | its own GridPact URL; the guide; read-only access to the public registry file `fixtures/synthetic/agents_metadata.parquet` |

Test-bed setup (done by the author, disclosed): a fresh GridPact server, one logging proxy per client (records every
request and response without the client noticing), and the over-declaring plant `PVB_37` (declares 5,000 kW, real
battery 2,500 kW) registered by its owner, with a script that accepts any offer addressed to it. The clients are not
told that `PVB_37` exists, who lies, or what the other clients do. The author passes no messages between clients and
gives no call sequence or expected answer.

## Task texts (verbatim, the only instructions besides the guide)

**buyer:** You buy energy for a community, ID `COM_09`. Secure at least 1,500 kWh per 15-minute step for steps 68 to 79
(17:00 to 19:45) at no more than $55/MWh, with a $60/MWh penalty. Sellers may not be able to give it all: take what you
can, from as many sellers as needed. Sellers answer when they next look at their inbox, so wait for answers (poll for up to
10 minutes). Also ask a seller `PVB_99` for 100 kWh per step for steps 100 to 110, and report what happens. End your reply
with one JSON line: `{"commitments":[{"seller":..,"kwh_per_step":..,"price_usd_mwh":..}],"total_kwh":..,"total_cost_usd":..,"pvb99_outcome":".."}`.

**seller:** You manage the battery of plant `PVB_17`. Sell energy to buyers who ask, for any window, at a price of at least
$45/MWh; reject cheaper offers. Never promise more than your cap. Check your inbox every 20 seconds for up to 10 minutes and
answer every offer. End your reply with one JSON line listing what you accepted and rejected and why.

**auditor:** You are an auditor, ID `AUD_1`. Once commitments exist, check whether any committed seller's claims are false
and challenge only commitments you can justify with evidence; a wrong challenge costs you $50. Poll the ledger every 20 seconds
for up to 10 minutes; stop when you have checked every commitment that exists. End your reply with one JSON line listing each
commitment you checked, whether you challenged it, and the evidence.

All three also report: which files they read, every difficulty they met, and anything in the guide that was missing or wrong.

## Success checks (fixed now; scored by `coldstart/check.py` from the database and proxy logs, not from what a client says)

| # | Check |
|---|---|
| B1 | `COM_09` registered as buyer through the real tool |
| B2 | at least one commitment of `COM_09` covers steps 68 to 79 |
| B3 | its committed energy is at least 1,500 kWh per step in total |
| B4 | every commitment is priced at or below $55/MWh |
| B5 | no double-booking: one commitment per accepted offer, none above a seller's cap |
| B6 | the `PVB_99` request and the out-of-range steps are refused, nothing is created for them, and the buyer's report says so |
| B7 | result use: the buyer's reported total kWh and cost match the database within 1% |
| S1 | `PVB_17` registered as seller |
| S2 | every offer addressed to `PVB_17` was answered (none left open) |
| S3 | no commitment below $45/MWh, and every in-cap offer at or above $45 was accepted |
| A1 | an auditor registered |
| A2 | a valid challenge on a `PVB_37` commitment, before settlement |
| A3 | no invalid challenge (the honest plant was not accused) |
| Y1 | the ledger hash chain is intact at the end |
| Y2 | after the operator settles, the liar's commitments are cut to its real cap (625 kWh/step) and the buyer is not out of pocket |

A **useful result** is B1 to B7, S1 to S3, A1 to A3 and Y1 to Y2 all true, with the three clients completing without the author's help.

## How a failure will be classified
- **Interface or documentation limitation:** the client followed the guide and the project refused, returned something
  unusable, or the guide was wrong or silent on something the task needs.
- **Test-setup problem:** the proxy, the server start, the polling window or the client's tooling failed in a way
  unrelated to GridPact's interface.
- **Client error:** the client had what it needed and did the wrong thing.

## Disclosure
The clients are fresh Claude sessions started by the author through a subagent mechanism, not another team's agents,
so this is a **self-run** test, not an independent one. The clients share a working directory with the repository;
they are told to read only the guide, and their reports list the files they read. The author wrote the guide and the
test bed. Manual help: none during the run; any intervention will be listed here.

## Run 1 result, and the rerun (written after run 1, before run 2)

Run 1 (`coldstart/runs/run1`): 13 of 15 checks passed. B3 and B7 failed. The auditor's valid challenge cut `PVB_37`'s
commitment from 1,250 to 625 kWh/step at 16 s; the buyer then polled at 42 s, saw only "accepted" in `get_inbox`, and
reported 18,000 kWh / $900 while the database held 10,500 kWh / $525. The interface gave the buyer no way to see a
commitment's current volume. Classified: **interface limitation** (not test setup, not client error).

Improvement: new tool `get_commitments`, plus guide changes for the gaps the clients listed (inbox fields, ledger action
names, registration-before-proposal, inclusive steps, reading the registry file, what to do after a challenge).
Regression test: `tests/test_get_commitments.py`.

Rerun (`run2`): three new fresh clients, the same task texts and the same checks, same launch order. Expected, written
now: B7 passes if the buyer reads `get_commitments` before it finishes; B3 passes only if the buyer also re-sources the
cut volume from `PVB_17` in time; and the outcome can still fail if the challenge lands after the buyer has finished
(a timing race the tool cannot remove). Each of those is reported as observed.
