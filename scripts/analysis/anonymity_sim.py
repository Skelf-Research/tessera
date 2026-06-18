#!/usr/bin/env python3
"""
E2 — Spatial-anonymity analysis of Tessera bucket + bloom routing.

Complements E3 (which covers temporal/count privacy). Here we quantify the *spatial*
anonymity provided by the routing layer in tessera/network/decentralized.py:

  Part A — Bucket k-anonymity.
    commitment -> bucket = int(SHA256(commitment)[:2]) mod B  (B = 64).
    A proof in bucket b is indistinguishable among all commitments in that bucket, so the
    bucket occupancy *is* the recipient anonymity set. We measure its distribution and the
    fraction of buckets that fall below a privacy threshold k.

  Part B — Bloom false-positive rate.
    Each subscription's bloom filter (m = 1024 bits, k = 3 hashes, n ~ 60 time-window
    fingerprints) is matched against proofs. A false positive makes a subscriber download an
    irrelevant proof (efficiency cost) and widens the recipient ambiguity (mild privacy gain).
    We compare the real BloomFilter implementation against the analytic FPR (1 - e^{-kn/m})^k.

Usage:
  poetry run python scripts/analysis/anonymity_sim.py
  poetry run python scripts/analysis/anonymity_sim.py --users 100000 --k-threshold 20
"""

import argparse
import csv
import hashlib
import json
import math
import secrets
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from tessera.network.decentralized import BloomFilter

PAPER = Path(__file__).resolve().parents[3] / "calldns-paper"
DEFAULT_RESULTS = PAPER / "results"


def bucket_of(commitment: bytes, num_buckets: int) -> int:
    """Mirror of Subscription._compute_bucket (decentralized.py)."""
    return int.from_bytes(hashlib.sha256(commitment).digest()[:2], "big") % num_buckets


def percentile(sorted_vals, q):
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1)))
    return sorted_vals[idx]


def bucket_anonymity(num_users, num_buckets, k_threshold):
    counts = Counter()
    for _ in range(num_users):
        counts[bucket_of(secrets.token_bytes(32), num_buckets)] += 1
    occ = sorted(counts.get(b, 0) for b in range(num_buckets))
    below = sum(1 for c in occ if c < k_threshold)
    return {
        "num_users": num_users,
        "num_buckets": num_buckets,
        "k_threshold": k_threshold,
        "expected_per_bucket": num_users / num_buckets,
        "min_anonymity_set": occ[0],
        "p5_anonymity_set": percentile(occ, 0.05),
        "median_anonymity_set": percentile(occ, 0.50),
        "max_anonymity_set": occ[-1],
        "buckets_below_threshold": below,
        "frac_buckets_below_threshold": below / num_buckets,
    }


def analytic_fpr(m_bits, k_hashes, n_items):
    return (1.0 - math.exp(-k_hashes * n_items / m_bits)) ** k_hashes


def bloom_fpr_empirical(m_bits, k_hashes, n_items, trials):
    bf = BloomFilter(size=m_bits, hash_count=k_hashes)
    for _ in range(n_items):
        bf.add(secrets.token_bytes(8))  # mirrors _compute_fingerprint output (8 bytes)
    fp = sum(1 for _ in range(trials) if bf.might_contain(secrets.token_bytes(8)))
    return fp / trials


def run(args):
    bucket_rows = [bucket_anonymity(n, args.num_buckets, args.k_threshold)
                   for n in args.user_sweep]

    # Real subscription params: m=1024 bits, k=3, n ~ time_window/10 = 60 fingerprints.
    real = {"m_bits": 1024, "k_hashes": 3, "n_items": 60}
    real["analytic_fpr"] = analytic_fpr(**{k: real[k] for k in ("m_bits", "k_hashes", "n_items")})
    real["empirical_fpr"] = bloom_fpr_empirical(real["m_bits"], real["k_hashes"],
                                                real["n_items"], args.fpr_trials)

    fpr_sweep = []
    for m in [512, 1024, 2048, 4096]:
        for n in [30, 60, 120]:
            fpr_sweep.append({
                "m_bits": m, "k_hashes": 3, "n_items": n,
                "analytic_fpr": analytic_fpr(m, 3, n),
                "empirical_fpr": bloom_fpr_empirical(m, 3, n, args.fpr_trials),
            })

    return {
        "experiment": "E2_anonymity",
        "params": {
            "num_buckets": args.num_buckets,
            "k_threshold": args.k_threshold,
            "fpr_trials": args.fpr_trials,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
        "bucket_anonymity": bucket_rows,
        "bloom_real_params": real,
        "bloom_fpr_sweep": fpr_sweep,
    }


def print_report(r):
    print("\nE2 — bucket k-anonymity (B = %d)" % r["params"]["num_buckets"])
    print("=" * 78)
    print(f"{'users':>9}{'E[/bucket]':>12}{'min':>7}{'p5':>7}{'median':>8}{'max':>7}"
          f"{'<k frac':>10}")
    print("-" * 78)
    for row in r["bucket_anonymity"]:
        print(f"{row['num_users']:>9}{row['expected_per_bucket']:>12.1f}"
              f"{row['min_anonymity_set']:>7}{row['p5_anonymity_set']:>7}"
              f"{row['median_anonymity_set']:>8}{row['max_anonymity_set']:>7}"
              f"{row['frac_buckets_below_threshold']:>10.2f}")
    print("-" * 78)
    rp = r["bloom_real_params"]
    print(f"\nBloom FPR @ real params (m={rp['m_bits']} bits, k={rp['k_hashes']}, "
          f"n={rp['n_items']}): analytic={rp['analytic_fpr']:.4f}, "
          f"empirical={rp['empirical_fpr']:.4f}")
    print("\nBloom FPR sweep (k=3):")
    print(f"{'m_bits':>8}{'n_items':>9}{'analytic':>11}{'empirical':>11}")
    for s in r["bloom_fpr_sweep"]:
        print(f"{s['m_bits']:>8}{s['n_items']:>9}{s['analytic_fpr']:>11.4f}"
              f"{s['empirical_fpr']:>11.4f}")


def write_outputs(r):
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    (DEFAULT_RESULTS / "e2_anonymity.json").write_text(json.dumps(r, indent=2))
    with (DEFAULT_RESULTS / "e2_bucket_anonymity.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["num_users", "expected_per_bucket", "min", "p5", "median", "max",
                    "frac_below_threshold"])
        for row in r["bucket_anonymity"]:
            w.writerow([row["num_users"], row["expected_per_bucket"], row["min_anonymity_set"],
                        row["p5_anonymity_set"], row["median_anonymity_set"],
                        row["max_anonymity_set"], row["frac_buckets_below_threshold"]])
    print(f"\nwrote {DEFAULT_RESULTS / 'e2_anonymity.json'}")


def main():
    ap = argparse.ArgumentParser(description="Tessera spatial-anonymity analysis (E2)")
    ap.add_argument("--num-buckets", type=int, default=64)
    ap.add_argument("--k-threshold", type=int, default=20)
    ap.add_argument("--user-sweep", type=int, nargs="+",
                    default=[1000, 10000, 50000, 100000])
    ap.add_argument("--fpr-trials", type=int, default=50000)
    args = ap.parse_args()

    r = run(args)
    print_report(r)
    write_outputs(r)


if __name__ == "__main__":
    main()
