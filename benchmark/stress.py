"""Phase 3: the stress sweep over the number of sellers (PREREGISTRATION.md section 7).

    python -m benchmark.stress [--version v1]
        -> benchmark/results/stress_<version>.md and stress_<version>.png

Levels: n=2 is liar2x_of_2, n=4 is liar2x_of_4, then stress_n6 / n8 / n12 / n16. Tuning buyer and
day only. Also grades the four hypotheses H1-H4 against the per-run columns, so the diagnosis is
read off the logs rather than assumed.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from benchmark.analyze import table

HERE = Path(__file__).resolve().parent
LEVELS = {"liar2x_of_2": 2, "liar2x_of_4": 4, "stress_n6": 6, "stress_n8": 8, "stress_n12": 12, "stress_n16": 16}
COLS = ["recall", "false_challenge_rate", "fraud_loss_usd", "liar_gain_usd", "honest_completion",
        "committed_kwh_per_step", "true_delivered_kwh", "n_sellers_offered", "ledger_entries",
        "auditor_tool_calls", "auditor_hit_max_turns", "buyer_hit_max_turns", "cost_usd", "wall_s"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    args = ap.parse_args()
    df = pd.read_csv(HERE / "results" / f"results_{args.version}.csv")
    df = df[df.scenario.isin(LEVELS) & df.condition.isin(["gridpact", "baseline"])].copy()
    df["n"] = df.scenario.map(LEVELS)
    df["coverage"] = df.true_delivered_kwh / 12 / df.need_kwh_per_step      # share of the buyer's need really delivered
    g = df.groupby(["n", "condition"])
    summary = g[COLS + ["coverage"]].mean().round(3)
    summary.insert(0, "runs", g.size())

    md = [f"# Stress sweep {args.version}: sellers 2 -> 16, 25% liars at x2.0", "",
          "Mean over 5 seeds. coverage = kWh really delivered / kWh the buyer needed.", "", table(summary), ""]
    gp = df[df.condition == "gridpact"]
    h = []
    h.append(f"H1 buyer turn cap: buyers hit max_turns in {int(df.buyer_hit_max_turns.sum())}/{len(df)} runs; "
             f"sellers that received an offer, by n: {df.groupby('n').n_sellers_offered.mean().round(1).to_dict()}")
    h.append(f"H2 auditor turn cap: auditor hit max_turns in {int(gp.auditor_hit_max_turns.sum())}/{len(gp)} runs; "
             f"tool calls by n: {gp.groupby('n').auditor_tool_calls.mean().round(1).to_dict()}; "
             f"recall by n: {gp.groupby('n').recall.mean().round(2).to_dict()}")
    h.append(f"H3 ledger page: ledger entries by n: {gp.groupby('n').ledger_entries.mean().round(0).to_dict()}; "
             f"auditor's get_ledger limit (min per run) by n: {gp.groupby('n').auditor_ledger_limit.min().to_dict()}")
    h.append(f"H4 crowding out: honest completion by n: {df.groupby('n').honest_completion.mean().round(2).to_dict()}; "
             f"coverage by n: {df.groupby('n').coverage.mean().round(2).to_dict()}; "
             f"committed kWh/step vs need {df.need_kwh_per_step.iloc[0]:.0f}: {df.groupby('n').committed_kwh_per_step.mean().round(0).to_dict()}")
    md += ["## Hypotheses (section 7)", ""] + [f"- {x}" for x in h] + [""]
    text = "\n".join(md)
    (HERE / "results" / f"stress_{args.version}.md").write_text(text)
    print(text)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (col, title) in zip(axes.flat, [("recall", "recall (gridpact)"), ("fraud_loss_usd", "buyer loss to fraud, $"),
                                            ("honest_completion", "honest sellers with a trade"), ("coverage", "share of need delivered")]):
        for cond, m in (("gridpact", "o-"), ("baseline", "s--")):
            d = df[df.condition == cond].groupby("n")[col]
            if col == "recall" and cond == "baseline":
                continue
            ax.errorbar(d.mean().index, d.mean(), yerr=d.std().fillna(0), fmt=m, capsize=3, label=cond)
        ax.set_title(title); ax.set_xlabel("sellers"); ax.set_xticks(list(LEVELS.values())); ax.grid(alpha=.3); ax.legend()
    fig.suptitle(f"GridPact stress sweep ({args.version}): 25% of sellers over-declare x2, 5 seeds, Haiku 5.5")
    fig.tight_layout()
    fig.savefig(HERE / "results" / f"stress_{args.version}.png", dpi=130)
    print("plot ->", HERE / "results" / f"stress_{args.version}.png")


if __name__ == "__main__":
    main()
