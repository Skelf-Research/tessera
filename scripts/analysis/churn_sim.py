#!/usr/bin/env python3
"""
E5 — Churn-resilience sweep for the CallDNS gossip network.

Measures end-to-end proof delivery while a fraction of nodes are offline, for two
topologies, using the real in-process multi-node cluster (calldns/deploy/cluster.py)
with real WebSocket gossip.

Per trial: register a subscriber on a random *live* node S, submit a matching proof to a
different random *live* node E, then fetch from S. Delivery succeeds iff the proof reached
S via gossip. We sweep the offline fraction and compare mesh vs ring connectivity.

Expectation: mesh degrades gracefully (1-hop gossip — delivery holds until the subscriber's
own node is down), while ring segments once >1 node is offline (a down node breaks the path),
motivating richer connectivity / replication.

Usage:
  poetry run python scripts/analysis/churn_sim.py --nodes 8 --trials 30
"""

import argparse
import asyncio
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import websockets

from calldns.deploy.cluster import LocalCluster
from calldns.network.decentralized import Subscription, make_routing_fields

PAPER = Path(__file__).resolve().parents[3] / "calldns-paper"
DEFAULT_RESULTS = PAPER / "results"


async def _rt(uri, msg):
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(msg))
        return json.loads(await ws.recv())


async def _trial(cluster, live_names, commitment) -> bool:
    """Register a subscriber on one live node, submit a proof to another, fetch back."""
    if len(live_names) >= 2:
        s_name, e_name = random.sample(live_names, 2)
    else:
        s_name = e_name = live_names[0]
    uris = cluster.uris()
    sub_id = f"sub-{commitment.hex()[:8]}"
    await _rt(uris[s_name], {"type": "subscribe", "subscriber_id": sub_id,
                             "subscription": Subscription(commitment, ["org"]).to_dict()})
    await _rt(uris[e_name], {"type": "proof",
                             "proof": {**make_routing_fields(commitment), "org_hint": "org"}})
    resp = await _rt(uris[s_name], {"type": "fetch", "subscriber_id": sub_id})
    return len(resp["proofs"]) >= 1


async def sweep_config(topology, n, offline_frac, trials):
    cluster = LocalCluster(n=n, topology=topology)
    await cluster.start()
    try:
        names = [f"node-{i}" for i in range(n)]
        k = int(offline_frac * n)
        # Keep at least 2 nodes live so gossip is exercised.
        k = min(k, max(0, n - 2))
        offline = random.sample(names, k)
        for name in offline:
            await cluster.stop_node(name)
        live = [nm for nm in names if nm not in offline]

        successes = 0
        for t in range(trials):
            commitment = random.randbytes(32)
            if await _trial(cluster, live, commitment):
                successes += 1
        return {
            "topology": topology, "nodes": n, "offline_frac": offline_frac,
            "offline_count": k, "trials": trials,
            "delivery_rate": successes / trials,
        }
    finally:
        await cluster.stop()


async def run(args):
    rows = []
    for topology in ("mesh", "ring"):
        for frac in args.offline_fracs:
            row = await sweep_config(topology, args.nodes, frac, args.trials)
            rows.append(row)
            print(f"{topology:<5} offline={frac:<4} ({row['offline_count']}/{args.nodes}) "
                  f"-> delivery {row['delivery_rate']*100:5.1f}%")
    return {
        "experiment": "E5_churn",
        "params": {"nodes": args.nodes, "trials": args.trials,
                   "offline_fracs": args.offline_fracs,
                   "timestamp_utc": datetime.now(timezone.utc).isoformat()},
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description="CallDNS churn-resilience sweep (E5)")
    ap.add_argument("--nodes", type=int, default=8)
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--offline-fracs", type=float, nargs="+", default=[0.0, 0.125, 0.25, 0.5])
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    print("E5 — churn-resilience sweep")
    print("=" * 50)
    results = asyncio.run(run(args))

    if not args.no_write:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out = args.out_dir / "e5_churn.json"
        out.write_text(json.dumps(results, indent=2))
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
