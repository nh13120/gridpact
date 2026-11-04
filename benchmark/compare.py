"""Phase 4: before/after table, v1 (before the change) vs v2 (after), gridpact condition, same seeds.

    python -m benchmark.compare   -> benchmark/results/compare_v1_v2.md

Tuning and held-out are reported separately: the change was chosen on tuning evidence, so only
the held-out rows say whether it generalises. The baseline is unchanged between versions and is
shown once for reference.
"""
from pathlib import Path

import pandas as pd

from benchmark.analyze import load, table

HERE = Path(__file__).resolve().parent
COLS = ["recall", "false_challenge_rate", "fraud_loss_usd", "liar_gain_usd", "honest_completion",
        "coverage", "released_kwh_per_step", "resourced_kwh_per_step", "cost_usd", "wall_s"]


def prep(version):
    df = load(version)
    df["coverage"] = df.true_delivered_kwh / 12 / df.need_kwh_per_step
    df["set"] = df.set.replace({"stress": "tuning (stress)"})
    return df


def main():
    v1, v2 = prep("v1"), prep("v2")
    g1 = v1[v1.condition == "gridpact"].groupby(["set", "scenario"])[COLS].mean()
    g2 = v2[v2.condition == "gridpact"].groupby(["set", "scenario"])[COLS].mean()
    bl = v1[v1.condition == "baseline"].groupby(["set", "scenario"])[COLS].mean()
    md = ["# Before / after: v1 vs v2 (gridpact, mean over 5 seeds)", "",
          "v2 = a valid challenge trims the liar's commitment to its real cap and the released volume is "
          "re-sourced in one extra round. Baseline (unchanged) shown for reference.", ""]
    for s in ("tuning", "tuning (stress)", "heldout"):
        rows = []
        for sc in g2.loc[s].index if s in g2.index.get_level_values(0) else []:
            a, b, c = g1.loc[(s, sc)], g2.loc[(s, sc)], bl.loc[(s, sc)]
            rows.append({"scenario": sc,
                         "coverage v1 -> v2": f"{a.coverage:.2f} -> {b.coverage:.2f} (baseline {c.coverage:.2f})",
                         "honest completion v1 -> v2": f"{a.honest_completion:.2f} -> {b.honest_completion:.2f} (baseline {c.honest_completion:.2f})",
                         "fraud loss $ v1 -> v2": f"{a.fraud_loss_usd:.0f} -> {b.fraud_loss_usd:.0f}",
                         "liar gain $ v1 -> v2": f"{a.liar_gain_usd:.0f} -> {b.liar_gain_usd:.0f}",
                         "recall v1 -> v2": f"{a.recall:.2f} -> {b.recall:.2f}",
                         "released / re-sourced kWh/step (v2)": f"{b.released_kwh_per_step:.0f} / {b.resourced_kwh_per_step:.0f}",
                         "cost $ v1 -> v2": f"{a.cost_usd:.4f} -> {b.cost_usd:.4f}"})
        if rows:
            md += [f"## {s}", "", table(pd.DataFrame(rows).set_index("scenario")), ""]
    # pooled numbers per set
    pooled = []
    for s in ("tuning", "tuning (stress)", "heldout"):
        for name, d in (("v1", v1), ("v2", v2)):
            x = d[(d.condition == "gridpact") & (d.set == s) & d.scenario.isin(g2.loc[s].index if s in g2.index.get_level_values(0) else [])]
            if len(x):
                pooled.append({"set": s, "version": name, "runs": len(x), "coverage": round(x.coverage.mean(), 3),
                               "honest_completion": round(x.honest_completion.mean(), 3),
                               "recall": round(x[x.n_catchable > 0].n_caught.sum() / max(1, x[x.n_catchable > 0].n_catchable.sum()), 3),
                               "false_challenge_rate": round(x.n_honest_challenged.sum() / max(1, x.n_honest.sum()), 3),
                               "fraud_loss_usd": round(x.fraud_loss_usd.mean(), 0), "liar_gain_usd": round(x.liar_gain_usd.mean(), 0),
                               "cost_usd": round(x.cost_usd.mean(), 4)})
    md += ["## Pooled over the rerun scenarios", "", table(pd.DataFrame(pooled).set_index(["set", "version"])), ""]
    text = "\n".join(md)
    (HERE / "results" / "compare_v1_v2.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
