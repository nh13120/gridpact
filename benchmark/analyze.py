"""Regenerate every table from the scored CSV, and grade the preregistered checks P1-P6.

    python -m benchmark.analyze [--version v1]   -> benchmark/results/summary_<version>.md (and stdout)

Failure scenarios (lazy_auditor, colluding_auditor) are reported but excluded from P1, as
PREREGISTRATION.md section 5 says.
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FAILURE = {"lazy_auditor", "colluding_auditor"}
COLS = ["recall", "false_challenge_rate", "fraud_loss_usd", "liar_gain_usd", "honest_completion",
        "buyer_paid_usd", "wall_s", "tokens_in", "tokens_out", "cost_usd", "cost_per_commitment"]


def table(df):
    """DataFrame -> markdown table (avoids the tabulate dependency)."""
    df = df.reset_index()
    rows = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    rows += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)


def mean_sd(df, cols):
    """One row per group: 'mean ± sd' strings, plus n runs."""
    g = df.groupby(["condition", "set"])
    def fmt(m, s):
        s = 0 if pd.isna(s) else s
        return f"{m:.3f} ± {s:.3f}" if abs(m) < 10 else f"{m:,.0f} ± {s:,.0f}"
    out = pd.DataFrame({c: [fmt(m, s) for m, s in zip(g[c].mean(), g[c].std())] for c in cols}, index=g.size().index)
    out.insert(0, "runs", g.size())
    return out


def checks(df):
    gp, bl = df[df.condition == "gridpact"], df[df.condition == "baseline"]
    std = gp[~gp.scenario.isin(FAILURE)]
    lines = []

    def p(name, ok, detail):
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")

    for s in ("tuning", "heldout"):
        d = std[(std.set == s) & (std.n_catchable > 0)]
        r = d.n_caught.sum() / d.n_catchable.sum() if len(d) else float("nan")
        p(f"P1 recall {s} >= 0.90", r >= 0.90, f"{d.n_caught.sum()}/{d.n_catchable.sum()} catchable liars caught = {r:.3f}")
    d = std[std.n_honest > 0]
    fcr = d.n_honest_challenged.sum() / d.n_honest.sum()
    p("P2 false challenges <= 0.05", fcr <= 0.05, f"{d.n_honest_challenged.sum()}/{d.n_honest.sum()} honest sellers challenged = {fcr:.3f}")
    gl, bll = gp[gp.lie_bit], bl[bl.lie_bit]
    p("P3 fraud loss: gridpact <= 0 every run where the lie bit", (gl.fraud_loss_usd <= 0.005).all(),
      f"{(gl.fraud_loss_usd <= 0.005).sum()}/{len(gl)} runs; mean ${gl.fraud_loss_usd.mean():.0f}")
    p("P3 fraud loss: baseline > 0 every run where the lie bit", (bll.fraud_loss_usd > 0).all(),
      f"{(bll.fraud_loss_usd > 0).sum()}/{len(bll)} runs; mean ${bll.fraud_loss_usd.mean():.0f}")
    p("P4 liar gain: gridpact < 0 every run where the lie bit", (gl.liar_gain_usd < 0).all(),
      f"{(gl.liar_gain_usd < 0).sum()}/{len(gl)} runs; mean ${gl.liar_gain_usd.mean():.0f}")
    p("P4 liar gain: baseline >= 0 every run where the lie bit", (bll.liar_gain_usd >= 0).all(),
      f"{(bll.liar_gain_usd >= 0).sum()}/{len(bll)} runs; mean ${bll.liar_gain_usd.mean():.0f}")
    gap = abs(gp.honest_completion.mean() - bl.honest_completion.mean())
    p("P5 honest completion gap <= 0.10", gap <= 0.10, f"gridpact {gp.honest_completion.mean():.3f} vs baseline {bl.honest_completion.mean():.3f}")
    ratio = gp.cost_per_commitment.mean() / bl.cost_per_commitment.mean()
    p("P6 $ per settled commitment <= 2x", ratio <= 2, f"gridpact ${gp.cost_per_commitment.mean():.4f} vs baseline ${bl.cost_per_commitment.mean():.4f} = {ratio:.2f}x")
    lie_no_bite = gp[(gp.n_liars > 0) & ~gp.lie_bit]
    integrity = f"ledger ok {df.ledger_ok.all()}, settlement = truth {gp.settle_matches_truth.all()}, audit before settlement {gp.audit_before_settlement.all()}, dropout ok {df.dropout_ok.all()}"
    return lines, integrity, len(lie_no_bite)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    args = ap.parse_args()
    df = pd.read_csv(HERE / "results" / f"results_{args.version}.csv")
    df = df[df.set != "stress"]          # the stress sweep has its own report: benchmark/stress.py
    md = [f"# Results {args.version}", "", f"{df[df.condition != 'stake_only'].shape[0]} real runs "
          f"({df[df.condition == 'gridpact'].shape[0]} gridpact, {df[df.condition == 'baseline'].shape[0]} baseline); "
          f"stake_only is derived from the gridpact runs. Model {df.get('model', pd.Series(['claude-haiku-5-5'])).iloc[0] if 'model' in df else 'claude-haiku-5-5'}.", ""]
    md += ["## Per condition and set (mean ± sd over scenarios x seeds)", "", mean_sd(df, COLS).pipe(table), ""]
    per = df.groupby(["scenario", "condition"])[["recall", "false_challenge_rate", "fraud_loss_usd", "liar_gain_usd",
                                                   "honest_completion", "n_commitments", "cost_usd"]].mean().round(3)
    md += ["## Per scenario (mean over seeds)", "", per.pipe(table), ""]
    lines, integrity, n_no_bite = checks(df)
    md += ["## Preregistered checks", "", "| check | result | numbers |", "|---|---|---|"] + lines + [""]
    md += [f"Integrity: {integrity}. Gridpact runs with a liar whose lie never bit (committed <= real capacity): {n_no_bite}.", ""]
    sub = df[(df.condition == "gridpact") & (df.n_sub_tolerance > 0)]
    if len(sub):
        md += [f"Sub-tolerance liars (factor <= 1.10): {len(sub)} runs, challenged in {int(sub.sub_tolerance_challenged.sum())} "
               f"(ruled invalid by design), shortfall still penalised by settlement in all.", ""]
    fail = df[(df.condition == "gridpact") & df.scenario.isin(FAILURE)]
    if len(fail):
        md += ["## Failure scenarios (excluded from P1)", "", fail.groupby("scenario")[["recall", "n_caught", "n_catchable", "false_challenge_rate", "cost_usd"]].mean().round(3).pipe(table), ""]
    text = "\n".join(md)
    (HERE / "results" / f"summary_{args.version}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
