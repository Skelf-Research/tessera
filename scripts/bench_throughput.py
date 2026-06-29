#!/usr/bin/env python3
"""
E4 (proper) — throughput/latency of a live Tessera node over persistent connections.

Unlike scripts/benchmark.py (which opens a fresh WebSocket per operation and is therefore
connection-bound), this driver holds ``--connections`` persistent connections and pipelines
``--ops-per-conn`` requests on each, measuring true server-side throughput and latency.

Operations:
  * subscribe : register N subscriptions (canonical Subscription serialization)
  * route     : submit proofs for matching commitments (the hot path)
  * fetch     : drain pending proofs for subscribers

Usage (start a node first):
  poetry run python -m tessera.network.ws_server --port 8100 &
  poetry run python scripts/bench_throughput.py --node ws://127.0.0.1:8100 --op route \
      --connections 16 --ops-per-conn 500
"""

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets

from tessera.network.decentralized import Subscription, make_routing_fields

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
DEFAULT_RESULTS = RESULTS_DIR


def commitment_for(i: int) -> bytes:
    import hashlib

    return hashlib.sha256(f"bench-commit-{i}".encode()).digest()


def build_message(op: str, i: int) -> dict:
    if op == "subscribe":
        c = commitment_for(i)
        return {
            "type": "subscribe",
            "subscriber_id": f"sub-{i}",
            "subscription": Subscription(c, linked_orgs=["bench"]).to_dict(),
        }
    if op == "route":
        c = commitment_for(i)
        return {
            "type": "proof",
            "proof": {**make_routing_fields(c), "org_hint": "bench"},
        }
    if op == "fetch":
        return {"type": "fetch", "subscriber_id": f"sub-{i}"}
    raise ValueError(op)


async def prepare(uri: str, op: str, total: int, connections: int = 16):
    """For 'route'/'fetch' we want subscribers to exist so routing actually matches.

    Registration is spread across ``connections`` concurrent sockets so prep does not
    dominate the run.
    """
    if op == "subscribe":
        return

    async def reg(ids):
        async with websockets.connect(uri) as ws:
            for i in ids:
                await ws.send(json.dumps(build_message("subscribe", i)))
                await ws.recv()

    chunks = [range(c, total, connections) for c in range(connections)]
    await asyncio.gather(*(reg(ch) for ch in chunks))


async def worker(uri: str, op: str, ids, latencies):
    async with websockets.connect(uri) as ws:
        for i in ids:
            t0 = time.perf_counter()
            await ws.send(json.dumps(build_message(op, i)))
            await ws.recv()
            latencies.append((time.perf_counter() - t0) * 1000.0)


async def run(args):
    total = args.connections * args.ops_per_conn
    if args.op in ("route", "fetch"):
        await prepare(args.node, args.op, total, args.connections)

    latencies = []
    # Partition the id space across connections.
    chunks = [range(c, total, args.connections) for c in range(args.connections)]

    start = time.perf_counter()
    await asyncio.gather(*(worker(args.node, args.op, ch, latencies) for ch in chunks))
    duration = time.perf_counter() - start

    s = sorted(latencies)
    n = len(s)
    return {
        "experiment": "E4_throughput",
        "op": args.op,
        "connections": args.connections,
        "ops_per_conn": args.ops_per_conn,
        "total_ops": total,
        "duration_s": duration,
        "throughput_ops_per_s": total / duration if duration else 0,
        "latency_ms": {
            "p50": s[int(0.50 * (n - 1))],
            "p99": s[int(0.99 * (n - 1))],
            "mean": statistics.fmean(s),
            "max": s[-1],
        },
        "node": args.node,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def print_report(r):
    print(
        f"\nE4 throughput — op={r['op']}, {r['connections']} conns x {r['ops_per_conn']} ops"
    )
    print("=" * 60)
    print(f"total ops   : {r['total_ops']}")
    print(f"duration    : {r['duration_s']:.2f} s")
    print(f"throughput  : {r['throughput_ops_per_s']:.0f} ops/s")
    lat = r["latency_ms"]
    print(
        f"latency ms  : p50={lat['p50']:.2f}  p99={lat['p99']:.2f}  "
        f"mean={lat['mean']:.2f}  max={lat['max']:.2f}"
    )


def main():
    ap = argparse.ArgumentParser(description="Tessera throughput driver (E4)")
    ap.add_argument("--node", default="ws://127.0.0.1:8100")
    ap.add_argument("--op", default="route", choices=["subscribe", "route", "fetch"])
    ap.add_argument("--connections", type=int, default=16)
    ap.add_argument("--ops-per-conn", type=int, default=500)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    r = asyncio.run(run(args))
    print_report(r)
    if not args.no_write:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out = args.out_dir / f"e4_throughput_{args.op}.json"
        out.write_text(json.dumps(r, indent=2))
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
