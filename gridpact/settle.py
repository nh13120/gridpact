"""Deterministic settlement and challenge adjudication. No LLM anywhere in this file.

Settlement, per commitment and 15-minute step:
    delivered = min(committed, what the seller's battery can physically add)
    shortfall = committed - delivered
    buyer pays the seller for delivered energy at the contract price,
    buyer gets shortfall x penalty from the seller's stake, and
    buyer buys the missing energy from the grid at real-time price + grid fee.
"What the battery can add" comes from the public registry (metadata nameplate): power x 0.25 h per
step, and total energy over the window. The recorded dispatch is not re-simulated (known limitation).

Adjudication: a declared envelope above the nameplate battery power (with 10% tolerance) is a false
claim. Valid -> bounty to the auditor from the seller's stake, reputation cut, cap reduced to the
real one. Invalid -> the auditor pays a bond.
"""
import math

from gridpact import ledger
from gridpact.config import GRID_FEE_USD_MWH, STEP_H

TOLERANCE = 1.10          # declared may exceed nameplate by 10% before it counts as a lie
BOUNTY_SHARE = 0.10       # of the commitment's stake
REPUTATION_CUT = 0.5
CHALLENGE_BOND_USD = 50.0


def settle_day(conn, day, trust=False, incremental=False):
    """Settle every active commitment against `day` (output of data.load_day). Returns rows written.

    trust=True is the benchmark's baseline: pay the seller for what it committed, as if every claim
    were true. No shortfall, no penalty, no grid top-up. The scorer computes the real shortfall.

    incremental=True (HW8, used by the operator tool) settles only commitments that have no settlement
    rows yet, starting each seller's battery pools from what earlier calls already delivered, so calling
    it again after new trades gives the same result as one call at the end of the day."""
    price_rt = day.groupby("step").price_usd_mwh.first()
    written = []
    power_left, energy_left = {}, {}   # per (seller, step) kWh and per seller kWh, shared by all its commitments
    if incremental:
        for r in conn.execute("SELECT c.seller, s.step, SUM(s.delivered_kwh) AS d FROM settlements s "
                              "JOIN commitments c USING (commitment_id) GROUP BY c.seller, s.step").fetchall():
            sl = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (r["seller"],)).fetchone()
            power_left[(r["seller"], r["step"])] = sl["bess_power_kw"] * STEP_H - r["d"]
            energy_left[r["seller"]] = energy_left.get(r["seller"], sl["bess_energy_kwh"]) - r["d"]
    # 'challenged' commitments still settle: a challenge adds a bounty, it does not cancel delivery duties.
    for c in conn.execute("SELECT * FROM commitments WHERE status IN ('active', 'challenged') "
                          "ORDER BY commitment_id").fetchall():
        if incremental and conn.execute("SELECT 1 FROM settlements WHERE commitment_id = ?",
                                        (c["commitment_id"],)).fetchone():
            continue
        seller = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (c["seller"],)).fetchone()
        sid = seller["agent_id"]
        energy_left.setdefault(sid, seller["bess_energy_kwh"])             # kWh over the whole day
        for step in range(c["step_from"], c["step_to"] + 1):
            power_left.setdefault((sid, step), seller["bess_power_kw"] * STEP_H)  # kWh in this step
            committed = c["kwh_per_step"]
            delivered = committed if trust else min(committed, power_left[(sid, step)], energy_left[sid])
            power_left[(sid, step)] -= delivered
            energy_left[sid] -= delivered
            shortfall = committed - delivered
            energy_usd = delivered / 1000 * c["price_usd_mwh"]
            stake_left = conn.execute("SELECT stake_locked_usd FROM agents WHERE agent_id = ?",
                                      (c["seller"],)).fetchone()[0]
            penalty_usd = min(shortfall / 1000 * c["penalty_usd_mwh"], stake_left)
            grid_usd = shortfall / 1000 * (float(price_rt[step]) + GRID_FEE_USD_MWH)
            conn.execute("INSERT INTO settlements (commitment_id, step, committed_kwh, delivered_kwh, "
                         "shortfall_kwh, energy_usd, penalty_usd, grid_usd) VALUES (?,?,?,?,?,?,?,?)",
                         (c["commitment_id"], step, committed, delivered, shortfall, energy_usd, penalty_usd, grid_usd))
            conn.execute("UPDATE agents SET balance_usd = balance_usd + ?, stake_locked_usd = stake_locked_usd - ? "
                         "WHERE agent_id = ?", (energy_usd - penalty_usd, penalty_usd, c["seller"]))
            conn.execute("UPDATE agents SET balance_usd = balance_usd - ? WHERE agent_id = ?",
                         (energy_usd + grid_usd - penalty_usd, c["buyer"]))
            row = {"commitment_id": c["commitment_id"], "step": step, "committed_kwh": committed,
                   "delivered_kwh": round(delivered, 3), "shortfall_kwh": round(shortfall, 3),
                   "energy_usd": round(energy_usd, 4), "penalty_usd": round(penalty_usd, 4),
                   "grid_usd": round(grid_usd, 4)}
            ledger.append(conn, "gridpact", "settle", row)
            written.append(row)
    conn.commit()
    return written


def adjudicate(conn, commitment, auditor, claim, evidence):
    """Decide a challenge against `commitment` (a commitments row). Writes the verdict; caller commits."""
    seller = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (commitment["seller"],)).fetchone()
    already = conn.execute("SELECT 1 FROM challenges WHERE commitment_id = ? AND verdict = 'valid'",
                           (commitment["commitment_id"],)).fetchone()
    if already:
        return {"verdict": "duplicate", "reason": "this commitment was already successfully challenged"}
    valid = seller["declared_flex_kw"] > TOLERANCE * seller["bess_power_kw"]
    bounty = 0.0
    if valid:
        bounty = min(BOUNTY_SHARE * commitment["stake_usd"], seller["stake_locked_usd"])
        real_cap = math.floor(seller["bess_power_kw"] * STEP_H)
        # The bounty leaves the seller's locked stake AND its balance (like a settlement penalty does),
        # so the auditor's gain below is matched by the seller's loss and money is conserved.
        conn.execute("UPDATE agents SET stake_locked_usd = stake_locked_usd - ?, balance_usd = balance_usd - ?, "
                     "reputation = MAX(0, reputation - ?), trade_cap_kwh = MIN(trade_cap_kwh, ?) WHERE agent_id = ?",
                     (bounty, bounty, REPUTATION_CUT, real_cap, seller["agent_id"]))
        conn.execute("UPDATE agents SET balance_usd = balance_usd + ? WHERE agent_id = ?", (bounty, auditor))
        conn.execute("UPDATE commitments SET status = 'challenged' WHERE commitment_id = ?",
                     (commitment["commitment_id"],))
        trim_to_real_cap(conn, seller["agent_id"], real_cap)
    else:
        conn.execute("UPDATE agents SET balance_usd = balance_usd - ? WHERE agent_id = ?",
                     (CHALLENGE_BOND_USD, auditor))
    verdict = "valid" if valid else "invalid"
    conn.execute("INSERT INTO challenges (commitment_id, auditor, claim, evidence, verdict, bounty_usd) "
                 "VALUES (?,?,?,?,?,?)", (commitment["commitment_id"], auditor, claim, evidence, verdict, bounty))
    payload = {"commitment_id": commitment["commitment_id"], "seller": seller["agent_id"], "claim": claim,
               "evidence": evidence, "verdict": verdict, "declared_flex_kw": seller["declared_flex_kw"],
               "nameplate_kw": seller["bess_power_kw"], "bounty_usd": round(bounty, 2),
               "bond_usd": 0 if valid else CHALLENGE_BOND_USD}
    seq = ledger.append(conn, auditor, "challenge", payload)["seq"]
    return {**payload, "ledger_seq": seq}


def trim_to_real_cap(conn, seller_id, real_cap):
    """v2 (benchmark Phase 4): after a valid challenge, cut the seller's not-yet-settled commitments, in
    commitment order, so their kWh/step fits the real cap. The cut volume is released back to the market
    (the buyer can re-source it) and the stake locked on it is released. Settled commitments stand."""
    room = {}                                                   # step -> kWh/step still allowed
    rows = conn.execute("SELECT * FROM commitments WHERE seller = ? AND status IN ('active', 'challenged') "
                        "ORDER BY commitment_id", (seller_id,)).fetchall()
    for c in rows:
        steps = range(c["step_from"], c["step_to"] + 1)
        allowed = min(room.setdefault(s, real_cap) for s in steps)
        new_kwh = min(c["kwh_per_step"], allowed)
        for s in steps:
            room[s] -= new_kwh
        settled = conn.execute("SELECT 1 FROM settlements WHERE commitment_id = ?", (c["commitment_id"],)).fetchone()
        if new_kwh >= c["kwh_per_step"] or settled:
            continue
        n_steps = len(steps)
        new_stake = c["penalty_usd_mwh"] * new_kwh * n_steps / 1000
        released = c["stake_usd"] - new_stake
        conn.execute("UPDATE commitments SET kwh_per_step = ?, stake_usd = ?, trimmed_from_kwh = ? WHERE commitment_id = ?",
                     (new_kwh, new_stake, c["kwh_per_step"], c["commitment_id"]))
        conn.execute("UPDATE agents SET stake_locked_usd = MAX(0, stake_locked_usd - ?) WHERE agent_id = ?",
                     (released, seller_id))
        for who in (c["buyer"], seller_id):       # tell both parties on their next call: nothing else is pushed to agents
            conn.execute("INSERT INTO notices (agent_id, text) VALUES (?, ?)",
                         (who, f"commitment #{c['commitment_id']} between {c['buyer']} (buyer) and {seller_id} (seller) was cut from "
                               f"{c['kwh_per_step']:.0f} to {new_kwh:.0f} kWh/step by a valid challenge; the stake locked on the cut part "
                               f"(${released:.2f}) was released. Call get_commitments for the current position."))
        ledger.append(conn, "gridpact", "trim", {"commitment_id": c["commitment_id"], "seller": seller_id,
                                                 "buyer": c["buyer"], "from_kwh": c["kwh_per_step"], "to_kwh": new_kwh,
                                                 "released_stake_usd": round(released, 2)})
