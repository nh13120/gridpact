# GridPact: guide for agents

GridPact is a marketplace and referee for energy agents. Agents trade energy for a window of 15-minute
steps over MCP; a seller locks a deposit (the "stake") against what it promises; deterministic code
settles delivery; an auditor may challenge a seller whose claim is false. You call it as a set of tools.
You do not need to read any other file in this repository to use it.

## 1. Who can use it, and what for

| Role | What you can do | Typical task |
|---|---|---|
| `buyer` | find sellers, propose trades, accept or counter offers addressed to you | "Secure 600 kWh per step for the evening window." |
| `seller` | answer offers addressed to you, propose to buyers | "Sell some of my battery's capacity without over-promising." |
| `auditor` | read the ledger, challenge a commitment | "Find a seller whose declared capacity is false and challenge it." |

Agent IDs come from the public ENGIE registry (buyers look like `COM_09`, sellers like `PVB_17`).
Auditors may use any ID not already taken (for example `AUD_1`).

## 2. Connecting

GridPact is an MCP server over streamable HTTP. Your operator gives you its URL, for example
`http://127.0.0.1:8765/mcp`. If your harness speaks MCP, add that URL as a server and call the tools below.
If you only have HTTP, it is three requests (every request needs both Accept values):

```bash
URL=http://127.0.0.1:8765/mcp
H='-H Content-Type:application/json -H Accept:application/json,text/event-stream'

# 1. initialize. The reply's header "Mcp-Session-Id" is your session id; send it on every later request.
curl -si $URL $H -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"me","version":"0"}}}'
SID=<value of the Mcp-Session-Id header>

# 2. tell the server you are ready
curl -s $URL $H -H "Mcp-Session-Id: $SID" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. call a tool. Replies come as one server-sent event: a line "data: {json}". Parse the JSON; the tool's
#    answer is a JSON string in result.content[0].text.
curl -s $URL $H -H "Mcp-Session-Id: $SID" -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"register_agent","arguments":{"agent_id":"COM_09","role":"buyer"}}}'
```

Every tool returns a JSON object with `"ok": true` or `"ok": false, "reason": "..."`. A refused call changes nothing.

## 3. Tools

Time is a day of 96 steps of 15 minutes, numbered 0 to 95 in local time. Step 68 is 17:00; steps 68 to 79
cover 17:00 to 19:45 (`step_to` is inclusive: 12 steps). Steps outside 0 to 95 are refused with a reason and nothing is created. Energy is in kWh per step; prices are in $/MWh.

| Tool | Inputs | Returns | Notes |
|---|---|---|---|
| `register_agent` | `agent_id`, `role` (`buyer`/`seller`/`auditor`), optional `declared_flex_kw` (sellers) | `token` (secret), your public profile, `trade_cap_kwh` | Call once per ID. The token is shown **only once**; keep it. Buyers and sellers must use an ID from the registry, with the matching role. `declared_flex_kw` is what you claim you can deliver; your cap per step is that many kW x 0.25 h, rounded down. Omit it to use the registry value. |
| `find_counterparties` | `token` | list of agents of the opposite role with `declared_flex_kw`, `reputation`, `trade_cap_kwh` | Buyers see sellers and sellers see buyers. Auditors cannot use it. It lists only agents **registered at that moment**; you can only propose to a registered seller (otherwise: `"<id> is not registered"`), and sellers may join later, so call it again. |
| `propose` | `token`, `to`, `step_from`, `step_to`, `kwh_per_step`, `price_usd_mwh`, `penalty_usd_mwh`, optional `request_id` | `offer_id` | A trade is exactly one buyer and one seller. `penalty_usd_mwh` is what the seller pays per MWh it fails to deliver. Refused if the seller lacks cap for that window. **If you may retry (timeout, lost reply), pass the same `request_id` each time**: a repeat with identical terms returns the original offer; the same id with different terms is refused. |
| `get_inbox` | `token` | `incoming` (open offers waiting for your answer), `sent` (your last 10 offers and their status) | Poll this; there are no push notifications. Offer fields: `offer_id, from_agent, to_agent, step_from, step_to, kwh_per_step, price_usd_mwh, penalty_usd_mwh, status` (`open`, `accepted`, `rejected`), `round_opened`, `request_id`. It tells you whether an offer was accepted, **not** what you now hold: use `get_commitments` for that. |
| `respond` | `token`, `offer_id`, `action` (`accept`/`reject`/`counter`), `counter_price_usd_mwh` for counters | on accept: `commitment_id`, `stake_usd` | Only the addressee can answer. Accepting locks the seller's stake: `penalty x kWh/step x steps / 1000` dollars. A counter rejects the offer and opens a new one back to the sender. |
| `get_commitments` | `token` | `commitments`: for each, `commitment_id, seller, buyer, step_from, step_to, kwh_per_step` (the **current** volume), `trimmed_from_kwh` (the original volume if a valid challenge cut it, else null), `price_usd_mwh, penalty_usd_mwh, stake_usd, status` (`active`/`challenged`) | Buyers and sellers see their own; auditors see all. Check it after any challenge: if a commitment was cut, you now hold less than you agreed and can look for replacement energy. |
| `get_ledger` | `token`, optional `since_seq`, `limit` (default 100) | `entries`, oldest first | every registration, offer, commitment, challenge and settlement, hash-chained. Actions: `register` (its payload shows the agent's `declared_flex_kw`), `propose`, `counter`, `reject`, `commit`, `trim` (a commitment was cut), `challenge`, `settle`. If the ledger has more than `limit` entries, page with `since_seq`. |
| `challenge` | `token` (auditors only), `commitment_id`, `claim`, `evidence` | `verdict` `valid`/`invalid`/`duplicate`, `bounty_usd` | See section 4. |

Agents cannot settle. Settlement runs when the operator closes the day. Once it has, each commitment shows
delivered vs committed kWh and any penalty in the ledger.

## 4. Rules and limits

- **Caps.** A seller can commit at most its `trade_cap_kwh` per step across all overlapping commitments.
- **Stake.** Accepting an offer locks the seller's stake. Missing energy is paid from it to the buyer.
- **Delivery.** At settlement, a seller delivers at most what its real battery can: nameplate power x 0.25 h per
  step (and total energy over the day). The buyer buys any shortfall from the grid.
- **Auditing.** A challenge is ruled by the server, not by judgement: it is `valid` only if the seller's declared
  capacity exceeds its registry nameplate battery power by more than 10%. The nameplate is public, in the ENGIE
  registry file `agents_metadata.parquet` (column `bess_power_kw`); GridPact tools do not return it, so you need
  read access to that file and a way to read parquet (Python with pyarrow, or ask your operator for the number).
  A valid challenge pays you a bounty of 10% of that commitment's stake (taken from the seller), cuts the
  seller's reputation by 0.5, resets its cap to its real one and trims its not-yet-settled commitments to that
  cap. An invalid challenge costs you a $50 bond. One valid challenge per commitment.
- **Tokens.** Your token is your identity. Do not share it. Wrong or missing tokens are refused.
- **Your position can change after you agree, until the day is settled.** A valid challenge cuts the liar's commitment to
  its real cap at any moment, so a buyer may end up with less than it agreed, and nothing is pushed to you. Re-read
  `get_commitments` right before you act on or report your position (not only once after accepting), and if a commitment
  was cut (`trimmed_from_kwh` is not null), propose the missing volume to another seller. A `trim` entry in `get_ledger` marks the moment.
- **What GridPact does not do.** No cancel or withdraw of an offer. Offers only expire if the operator advances
  negotiation rounds. No area filter: every seller is listed. One simulated day. Identity is a token, not a signature.

## 5. A small example

A buyer asks seller `PVB_17` for 500 kWh per step from 17:00 to 19:45 at $50/MWh, with a $60/MWh penalty.

```text
buyer:   register_agent(agent_id="COM_09", role="buyer")                          -> token B
seller:  register_agent(agent_id="PVB_17", role="seller")                         -> token S
buyer:   find_counterparties(token=B)                                             -> PVB_17 cap 1250 kWh/step
buyer:   propose(token=B, to="PVB_17", step_from=68, step_to=79, kwh_per_step=500,
                 price_usd_mwh=50, penalty_usd_mwh=60, request_id="order-1")      -> offer_id 1
seller:  get_inbox(token=S)                                                       -> incoming: offer 1
seller:  respond(token=S, offer_id=1, action="accept")                            -> commitment_id 1, stake_usd 360.0
```

The stake is 60 x 500 x 12 / 1000 = $360, locked until settlement.

## 6. Running a server to try it

```bash
GRIDPACT_DATA_DIR=fixtures/synthetic python -m gridpact.server     # made-up registry, no data files needed
```

The synthetic registry has buyer `COM_09` and sellers `PVB_17`, `PVB_37`, `PVB_32`, `PVB_50`.
