#!/usr/bin/env python3
"""
E3 — Traffic-analysis linkability simulation for Tessera cover traffic.

Validates the metadata-privacy guarantee of Workstream C
(see ../tessera-paper-msg/spec/metadata_privacy.md).

Adversary (worst case, the DP assumption): a global passive observer who knows every
other input and must decide a single bit — did the *target* user place a call into a
given bucket this round? It observes only the per-bucket message count C_b.

  world0: target did NOT call  -> observable  C = R + D
  world1: target DID call      -> observable  C = R + 1 + D
  (R = all other real proofs in the bucket; D = cover/dummy proofs)

Because R is identical in both worlds, it cancels from the optimal test, so the
adversary's distinguishing power depends entirely on the cover-traffic policy D:

  * none          D = 0                          -> deterministic +1 shift -> AUC = 1.0 (total break)
  * proportional  D = round(rho * R)             -> deterministic given R  -> AUC = 1.0 (total break)
  * dp            D = max(0, round(mu + Lap))    -> AUC bounded by epsilon

We report the optimal-test AUC (Mann-Whitney, tie-corrected), the bandwidth overhead,
and the DP AUC upper bound 1 - e^{-eps}/2 (area under the eps-DP-constrained ROC; delta
negligible) which no test may exceed.

Usage:
  poetry run python scripts/analysis/linkability_sim.py
  poetry run python scripts/analysis/linkability_sim.py --samples 50000 --plot
"""

import argparse
import csv
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from tessera.sdk.traffic_manager import DPCoverTraffic

PAPER = Path(__file__).resolve().parents[3] / "tessera-paper-msg"
DEFAULT_RESULTS = PAPER / "results"
DEFAULT_FIGURES = PAPER / "figures"


def auc_mann_whitney(world1, world0):
    """AUC = P(X1 > X0) + 0.5 P(X1 == X0), via tie-corrected average ranks."""
    n1, n0 = len(world1), len(world0)
    combined = [(v, 1) for v in world1] + [(v, 0) for v in world0]
    combined.sort(key=lambda t: t[0])
    # Assign average ranks (1-based), resolving ties.
    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # average of ranks i+1..j+1
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    sum_ranks_world1 = sum(r for r, (_, label) in zip(ranks, combined) if label == 1)
    u1 = sum_ranks_world1 - n1 * (n1 + 1) / 2.0
    return u1 / (n1 * n0)


def auc_upper_bound_eps(epsilon):
    """Largest AUC any test can achieve under epsilon-DP: area under the DP-constrained ROC.

    For pure epsilon-DP the ROC obeys TPR <= e^eps * FPR (and TPR <= 1); the area under
    min(e^eps*FPR, 1) is 1 - e^{-eps}/2. This is a valid (slightly loose) upper bound;
    no test, optimal or otherwise, can exceed it. delta=1e-6 contributes negligibly.
    """
    return 1.0 - math.exp(-epsilon) / 2.0


def simulate_dp(epsilon, delta, num_buckets, samples, rng):
    dp = DPCoverTraffic(epsilon=epsilon, delta=delta, num_buckets=num_buckets, rng=rng)
    # R cancels, so sample only the noise. world1 observable = 1 + D.
    world0 = [dp.dummy_count_for_bucket() for _ in range(samples)]
    world1 = [1 + dp.dummy_count_for_bucket() for _ in range(samples)]
    auc = auc_mann_whitney(world1, world0)
    return {
        "policy": "dp",
        "epsilon": epsilon,
        "delta": delta,
        "baseline_mu": dp.mu,
        "overhead_per_round": dp.expected_overhead_per_round(),
        "empirical_auc": auc,
        "auc_ceiling_from_eps": auc_upper_bound_eps(epsilon),
    }


def run(args):
    rng = random.Random(args.seed)
    rows = []

    # Baselines (deterministic under a knows-R adversary -> total break).
    rows.append({"policy": "none", "epsilon": None, "empirical_auc": 1.0,
                 "overhead_per_round": 0.0})
    rows.append({"policy": "proportional", "epsilon": None, "rho": args.rho,
                 "empirical_auc": 1.0,
                 "overhead_per_round": args.rho * args.background_load * args.num_buckets,
                 "note": "deterministic given R -> no privacy"})

    for eps in args.epsilons:
        rows.append(simulate_dp(eps, args.delta, args.num_buckets, args.samples, rng))

    return {
        "experiment": "E3_linkability",
        "params": {
            "num_buckets": args.num_buckets,
            "delta": args.delta,
            "samples_per_world": args.samples,
            "rho_proportional_baseline": args.rho,
            "background_load_per_bucket": args.background_load,
            "seed": args.seed,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
        "rows": rows,
    }


def print_table(results):
    print("\nE3 — adversary linking power vs cover-traffic policy")
    print("=" * 74)
    print(f"{'policy':<14}{'epsilon':>9}{'AUC':>10}{'AUC ceil':>10}{'overhead/round':>18}")
    print("-" * 74)
    for r in results["rows"]:
        eps = "" if r.get("epsilon") is None else f"{r['epsilon']:.2f}"
        ceil = r.get("auc_ceiling_from_eps")
        ceil_s = "" if ceil is None else f"{ceil:.3f}"
        print(f"{r['policy']:<14}{eps:>9}{r['empirical_auc']:>10.3f}{ceil_s:>10}"
              f"{r['overhead_per_round']:>18.1f}")
    print("-" * 74)
    print("AUC 0.5 = adversary has no advantage (ideal); 1.0 = perfect linking (total break).")


def write_outputs(results, args):
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    (DEFAULT_RESULTS / "e3_linkability.json").write_text(json.dumps(results, indent=2))
    csv_path = DEFAULT_RESULTS / "e3_linkability.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["policy", "epsilon", "empirical_auc", "auc_ceiling", "overhead_per_round"])
        for r in results["rows"]:
            w.writerow([r["policy"], r.get("epsilon", ""), r["empirical_auc"],
                        r.get("auc_ceiling_from_eps", ""), r.get("overhead_per_round", "")])
    print(f"\nwrote {DEFAULT_RESULTS / 'e3_linkability.json'}")
    print(f"wrote {csv_path}")
    if args.plot:
        _maybe_plot(results)


def _maybe_plot(results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot (CSV written for external plotting).")
        return
    dp = [r for r in results["rows"] if r["policy"] == "dp"]
    overhead = [r["overhead_per_round"] for r in dp]
    auc = [r["empirical_auc"] for r in dp]
    DEFAULT_FIGURES.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(5, 3.2))
    plt.plot(overhead, auc, "o-", label="DP cover traffic")
    plt.axhline(0.5, ls="--", color="gray", label="no advantage")
    plt.axhline(1.0, ls=":", color="red", label="no/proportional cover (total break)")
    plt.xlabel("Bandwidth overhead (dummy proofs / round)")
    plt.ylabel("Adversary linking AUC")
    plt.title("Privacy vs overhead (E3)")
    plt.legend(fontsize=8)
    plt.tight_layout()
    out = DEFAULT_FIGURES / "e3_privacy_overhead.pdf"
    plt.savefig(out)
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser(description="Tessera linkability simulation (E3)")
    ap.add_argument("--samples", type=int, default=20000, help="samples per world")
    ap.add_argument("--num-buckets", type=int, default=64)
    ap.add_argument("--delta", type=float, default=1e-6)
    ap.add_argument("--epsilons", type=float, nargs="+",
                    default=[0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0])
    ap.add_argument("--rho", type=float, default=0.3, help="proportional-baseline cover ratio")
    ap.add_argument("--background-load", type=float, default=10.0,
                    help="assumed real proofs/bucket (only for baseline overhead reporting)")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    results = run(args)
    print_table(results)
    write_outputs(results, args)


if __name__ == "__main__":
    main()
