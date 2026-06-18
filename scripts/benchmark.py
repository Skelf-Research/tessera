#!/usr/bin/env python3
"""
Tessera Load Testing Benchmark.
Tests proof broadcasting, routing, and subscription performance.
"""

import asyncio
import time
import json
import base64
import secrets
import hashlib
import argparse
import statistics
from typing import List, Dict
from dataclasses import dataclass, field

import websockets

from tessera.network.decentralized import Subscription, make_routing_fields


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    name: str
    total_operations: int
    successful: int
    failed: int
    duration_seconds: float
    latencies_ms: List[float] = field(default_factory=list)

    @property
    def ops_per_second(self) -> float:
        if self.duration_seconds > 0:
            return self.total_operations / self.duration_seconds
        return 0

    @property
    def success_rate(self) -> float:
        if self.total_operations > 0:
            return self.successful / self.total_operations * 100
        return 0

    @property
    def p50_ms(self) -> float:
        if self.latencies_ms:
            return statistics.median(self.latencies_ms)
        return 0

    @property
    def p99_ms(self) -> float:
        if len(self.latencies_ms) >= 100:
            sorted_latencies = sorted(self.latencies_ms)
            idx = int(len(sorted_latencies) * 0.99)
            return sorted_latencies[idx]
        return max(self.latencies_ms) if self.latencies_ms else 0

    def print_report(self):
        print(f"\n{'='*50}")
        print(f"Benchmark: {self.name}")
        print(f"{'='*50}")
        print(f"Total operations: {self.total_operations}")
        print(f"Successful: {self.successful}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {self.success_rate:.1f}%")
        print(f"Duration: {self.duration_seconds:.2f}s")
        print(f"Throughput: {self.ops_per_second:.1f} ops/s")
        if self.latencies_ms:
            print(f"Latency P50: {self.p50_ms:.2f}ms")
            print(f"Latency P99: {self.p99_ms:.2f}ms")
            print(f"Latency avg: {statistics.mean(self.latencies_ms):.2f}ms")


def generate_commitment(value: str) -> bytes:
    """Generate a test commitment."""
    return hashlib.sha256(value.encode()).digest()


def generate_proof(commitment: bytes, org_hint: str = "benchmark-org") -> dict:
    """Generate a test proof with canonical routing fields (so routing actually matches)."""
    return {
        **make_routing_fields(commitment),
        "ciphertext": base64.b64encode(secrets.token_bytes(128)).decode(),
        "nonce": base64.b64encode(secrets.token_bytes(12)).decode(),
        "org_hint": org_hint,
    }


def generate_subscription(commitment: bytes, org_hint: str = "benchmark-org") -> dict:
    """Generate a subscription consistent with generate_proof's routing fields."""
    return Subscription(commitment, linked_orgs=[org_hint]).to_dict()


async def benchmark_proof_broadcast(
    node_uri: str,
    num_proofs: int,
    concurrency: int
) -> BenchmarkResult:
    """Benchmark proof broadcasting throughput."""
    latencies = []
    successful = 0
    failed = 0

    semaphore = asyncio.Semaphore(concurrency)

    async def send_proof(i: int):
        nonlocal successful, failed

        async with semaphore:
            commitment = generate_commitment(f"benchmark-{i}")
            proof = generate_proof(commitment)

            try:
                async with websockets.connect(node_uri) as ws:
                    start = time.time()
                    await ws.send(json.dumps({
                        "type": "proof",
                        "proof": proof
                    }))
                    latency = (time.time() - start) * 1000
                    latencies.append(latency)
                    successful += 1
            except Exception as e:
                failed += 1

    start_time = time.time()
    tasks = [send_proof(i) for i in range(num_proofs)]
    await asyncio.gather(*tasks)
    duration = time.time() - start_time

    return BenchmarkResult(
        name="Proof Broadcast",
        total_operations=num_proofs,
        successful=successful,
        failed=failed,
        duration_seconds=duration,
        latencies_ms=latencies
    )


async def benchmark_subscription_registration(
    node_uri: str,
    num_subscriptions: int,
    concurrency: int
) -> BenchmarkResult:
    """Benchmark subscription registration throughput."""
    latencies = []
    successful = 0
    failed = 0

    semaphore = asyncio.Semaphore(concurrency)

    async def register_subscription(i: int):
        nonlocal successful, failed

        async with semaphore:
            commitment = generate_commitment(f"subscriber-{i}")
            subscription = generate_subscription(commitment)

            try:
                async with websockets.connect(node_uri) as ws:
                    start = time.time()
                    await ws.send(json.dumps({
                        "type": "subscribe",
                        "subscriber_id": f"sub-{i}",
                        "subscription": subscription
                    }))
                    latency = (time.time() - start) * 1000
                    latencies.append(latency)
                    successful += 1
            except Exception as e:
                failed += 1

    start_time = time.time()
    tasks = [register_subscription(i) for i in range(num_subscriptions)]
    await asyncio.gather(*tasks)
    duration = time.time() - start_time

    return BenchmarkResult(
        name="Subscription Registration",
        total_operations=num_subscriptions,
        successful=successful,
        failed=failed,
        duration_seconds=duration,
        latencies_ms=latencies
    )


async def benchmark_proof_routing(
    node_uri: str,
    num_subscribers: int,
    num_proofs: int
) -> BenchmarkResult:
    """Benchmark proof routing to subscribers."""
    # First, register subscribers
    print(f"Registering {num_subscribers} subscribers...")

    commitments = []
    for i in range(num_subscribers):
        commitment = generate_commitment(f"routing-sub-{i}")
        commitments.append(commitment)
        subscription = generate_subscription(commitment)

        try:
            async with websockets.connect(node_uri) as ws:
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "subscriber_id": f"routing-sub-{i}",
                    "subscription": subscription
                }))
        except Exception as e:
            print(f"Failed to register subscriber {i}: {e}")

    # Now broadcast proofs
    print(f"Broadcasting {num_proofs} proofs...")
    latencies = []
    successful = 0
    failed = 0

    start_time = time.time()

    for i in range(num_proofs):
        # Pick a random commitment to match
        commitment = commitments[i % len(commitments)]
        proof = generate_proof(commitment)

        try:
            async with websockets.connect(node_uri) as ws:
                start = time.time()
                await ws.send(json.dumps({
                    "type": "proof",
                    "proof": proof
                }))
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                successful += 1
        except Exception as e:
            failed += 1

    duration = time.time() - start_time

    return BenchmarkResult(
        name="Proof Routing",
        total_operations=num_proofs,
        successful=successful,
        failed=failed,
        duration_seconds=duration,
        latencies_ms=latencies
    )


async def benchmark_proof_fetch(
    node_uri: str,
    num_subscribers: int,
    fetches_per_subscriber: int
) -> BenchmarkResult:
    """Benchmark fetching pending proofs."""
    latencies = []
    successful = 0
    failed = 0

    start_time = time.time()

    for sub_idx in range(num_subscribers):
        subscriber_id = f"fetch-sub-{sub_idx}"

        for _ in range(fetches_per_subscriber):
            try:
                async with websockets.connect(node_uri) as ws:
                    start = time.time()
                    await ws.send(json.dumps({
                        "type": "get_proofs",
                        "subscriber_id": subscriber_id
                    }))
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    latency = (time.time() - start) * 1000
                    latencies.append(latency)
                    successful += 1
            except Exception as e:
                failed += 1

    duration = time.time() - start_time
    total_ops = num_subscribers * fetches_per_subscriber

    return BenchmarkResult(
        name="Proof Fetch",
        total_operations=total_ops,
        successful=successful,
        failed=failed,
        duration_seconds=duration,
        latencies_ms=latencies
    )


async def run_full_benchmark(node_uri: str, scale: str = "small"):
    """Run full benchmark suite."""
    scales = {
        "small": {
            "proofs": 100,
            "subscriptions": 50,
            "routing_subs": 20,
            "routing_proofs": 100,
            "fetch_subs": 10,
            "fetch_per_sub": 5,
            "concurrency": 10
        },
        "medium": {
            "proofs": 1000,
            "subscriptions": 500,
            "routing_subs": 100,
            "routing_proofs": 500,
            "fetch_subs": 50,
            "fetch_per_sub": 10,
            "concurrency": 50
        },
        "large": {
            "proofs": 5000,
            "subscriptions": 2000,
            "routing_subs": 500,
            "routing_proofs": 2000,
            "fetch_subs": 200,
            "fetch_per_sub": 20,
            "concurrency": 100
        }
    }

    params = scales.get(scale, scales["small"])

    print(f"\nTessera Benchmark Suite - {scale.upper()} scale")
    print(f"Target node: {node_uri}")
    print("="*50)

    results = []

    # Proof broadcast benchmark
    print("\n[1/4] Running proof broadcast benchmark...")
    result = await benchmark_proof_broadcast(
        node_uri,
        params["proofs"],
        params["concurrency"]
    )
    results.append(result)
    result.print_report()

    # Subscription registration benchmark
    print("\n[2/4] Running subscription registration benchmark...")
    result = await benchmark_subscription_registration(
        node_uri,
        params["subscriptions"],
        params["concurrency"]
    )
    results.append(result)
    result.print_report()

    # Proof routing benchmark
    print("\n[3/4] Running proof routing benchmark...")
    result = await benchmark_proof_routing(
        node_uri,
        params["routing_subs"],
        params["routing_proofs"]
    )
    results.append(result)
    result.print_report()

    # Proof fetch benchmark
    print("\n[4/4] Running proof fetch benchmark...")
    result = await benchmark_proof_fetch(
        node_uri,
        params["fetch_subs"],
        params["fetch_per_sub"]
    )
    results.append(result)
    result.print_report()

    # Summary
    print("\n" + "="*50)
    print("BENCHMARK SUMMARY")
    print("="*50)
    total_ops = sum(r.total_operations for r in results)
    total_success = sum(r.successful for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    print(f"Total operations: {total_ops}")
    print(f"Total successful: {total_success}")
    print(f"Overall success rate: {total_success/total_ops*100:.1f}%")
    print(f"Total duration: {total_duration:.2f}s")
    print(f"Overall throughput: {total_ops/total_duration:.1f} ops/s")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Tessera Load Testing Benchmark"
    )
    parser.add_argument(
        "--node", "-n",
        default="ws://localhost:8100",
        help="Node WebSocket URI (default: ws://localhost:8100)"
    )
    parser.add_argument(
        "--scale", "-s",
        choices=["small", "medium", "large"],
        default="small",
        help="Benchmark scale (default: small)"
    )
    parser.add_argument(
        "--test", "-t",
        choices=["all", "broadcast", "subscribe", "routing", "fetch"],
        default="all",
        help="Specific test to run (default: all)"
    )

    args = parser.parse_args()

    print("Tessera Load Testing Benchmark")
    print("==============================")

    asyncio.run(run_full_benchmark(args.node, args.scale))


if __name__ == "__main__":
    main()
