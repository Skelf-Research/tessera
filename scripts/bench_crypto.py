#!/usr/bin/env python3
"""
E1 — Cryptographic microbenchmark for Tessera.

Measures the per-operation cost and wire size of the cryptographic core that
gates every authenticated call:

  * ZK proof generation      (ZKProver.generate_proof  — Schnorr / Fiat-Shamir)
  * ZK proof verification    (ZKVerifier.verify_proof)
  * AES-256-GCM encrypt      (SecureEncryption.encrypt — proof routing)
  * AES-256-GCM decrypt      (SecureEncryption.decrypt)
  * Key generation           (CryptoUtils.generate_keypair)
  * ECDSA sign/verify        (reference baseline ~ STIR/SHAKEN-style signing)

Outputs:
  * a formatted table to stdout
  * a JSON results blob          (results/<name>.json)
  * a ready-to-\\input LaTeX table (results/<name>.tex)

By repo convention (see ../calldns-paper), this harness lives in tessera/ and
writes its artefacts into the sibling paper repo's results/ directory.

Usage:
  poetry run python scripts/bench_crypto.py
  poetry run python scripts/bench_crypto.py --iterations 20000 --out-dir /tmp
"""

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ecdsa
from ecdsa import SECP256k1

from tessera.crypto.crypto_utils import CryptoUtils, ZKProver, ZKVerifier, SecureEncryption


DEFAULT_OUT = Path(__file__).resolve().parents[2] / "calldns-paper" / "results"


def time_op(fn, iterations, warmup):
    """Run fn() warmup+iterations times; return (latencies_us, results[-1])."""
    for _ in range(warmup):
        fn()
    latencies = []
    last = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        last = fn()
        latencies.append((time.perf_counter() - t0) * 1e6)  # microseconds
    return latencies, last


def summarize(name, latencies):
    s = sorted(latencies)
    n = len(s)
    return {
        "op": name,
        "n": n,
        "mean_us": statistics.fmean(s),
        "median_us": statistics.median(s),
        "p50_us": s[int(0.50 * (n - 1))],
        "p99_us": s[int(0.99 * (n - 1))],
        "min_us": s[0],
        "max_us": s[-1],
        "stdev_us": statistics.pstdev(s) if n > 1 else 0.0,
        "throughput_ops_per_s": 1e6 / statistics.fmean(s),
    }


def proof_wire_sizes(proof):
    """Component + total on-wire byte sizes of a proof."""
    R = proof["R"]
    pk = proof["public_key"]
    s_bytes = 32  # s is an int mod q (256-bit) -> 32 bytes on the wire
    meta = proof.get("metadata") or ""
    meta_bytes = len(json.dumps(meta).encode()) if not isinstance(meta, str) else len(meta.encode())
    return {
        "R_bytes": len(R),
        "s_bytes": s_bytes,
        "public_key_bytes": len(pk),
        "metadata_bytes": meta_bytes,
        "total_bytes": len(R) + s_bytes + len(pk) + meta_bytes,
    }


def run(iterations, warmup):
    prover = ZKProver()
    verifier = ZKVerifier()
    priv, pub, sk = CryptoUtils.generate_keypair()
    metadata = {"call_type": "voice", "ts": 1716800000, "region": "US"}

    results = {"ops": [], "sizes": {}, "params": {}}

    # --- Key generation ---
    lat, _ = time_op(lambda: CryptoUtils.generate_keypair(), iterations // 10 or 1, warmup)
    results["ops"].append(summarize("keygen", lat))

    # --- Proof generation ---
    lat, sample_proof = time_op(
        lambda: prover.generate_proof(priv, pub, metadata), iterations, warmup
    )
    results["ops"].append(summarize("zk_proof_gen", lat))

    # --- Proof verification ---
    proof = prover.generate_proof(priv, pub, metadata)
    lat, verify_ok = time_op(lambda: verifier.verify_proof(proof), iterations, warmup)
    results["ops"].append(summarize("zk_proof_verify", lat))
    assert verify_ok is True, "sanity: a freshly generated proof must verify"

    # --- AES-GCM encrypt / decrypt (proof routing) ---
    proof_json = json.dumps(
        {"R": proof["R"].hex(), "s": proof["s"], "public_key": proof["public_key"].hex(),
         "metadata": proof["metadata"]}
    ).encode()
    key = CryptoUtils.hash_data(b"routing-key-seed")
    lat, enc = time_op(lambda: SecureEncryption.encrypt(proof_json, key, b"aad"), iterations, warmup)
    results["ops"].append(summarize("aesgcm_encrypt", lat))
    lat, _ = time_op(lambda: SecureEncryption.decrypt(enc, key), iterations, warmup)
    results["ops"].append(summarize("aesgcm_decrypt", lat))

    # --- ECDSA baseline (reference for STIR/SHAKEN-style signing) ---
    msg = b"sip-identity-header-canonical-form"
    lat, sig = time_op(lambda: sk.sign(msg), iterations, warmup)
    results["ops"].append(summarize("ecdsa_sign_baseline", lat))
    vk = sk.get_verifying_key()
    lat, _ = time_op(lambda: vk.verify(sig, msg), iterations, warmup)
    results["ops"].append(summarize("ecdsa_verify_baseline", lat))

    # --- Sizes ---
    results["sizes"]["proof"] = proof_wire_sizes(sample_proof)
    results["sizes"]["aesgcm_overhead_bytes"] = {
        "plaintext_bytes": len(proof_json),
        "ciphertext_bytes": len(enc["ciphertext"]),
        "nonce_bytes": len(enc["nonce"]),
        "overhead_bytes": len(enc["ciphertext"]) - len(proof_json) + len(enc["nonce"]),
    }
    results["params"] = {
        "curve": "SECP256k1",
        "hash": "SHA-256",
        "iterations": iterations,
        "warmup": warmup,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
    }
    return results


def print_table(results):
    print("\nTessera cryptographic microbenchmark (E1)")
    print("=" * 78)
    print(f"{'operation':<24}{'mean us':>10}{'p50 us':>10}{'p99 us':>10}{'ops/sec':>14}")
    print("-" * 78)
    for o in results["ops"]:
        print(f"{o['op']:<24}{o['mean_us']:>10.2f}{o['p50_us']:>10.2f}"
              f"{o['p99_us']:>10.2f}{o['throughput_ops_per_s']:>14.0f}")
    print("-" * 78)
    p = results["sizes"]["proof"]
    print(f"\nProof wire size: {p['total_bytes']} B "
          f"(R={p['R_bytes']}, s={p['s_bytes']}, pubkey={p['public_key_bytes']}, "
          f"meta={p['metadata_bytes']})")
    a = results["sizes"]["aesgcm_overhead_bytes"]
    print(f"AES-GCM: {a['plaintext_bytes']} B -> {a['ciphertext_bytes']} B "
          f"+ {a['nonce_bytes']} B nonce (overhead {a['overhead_bytes']} B)")
    pr = results["params"]
    print(f"\n{pr['iterations']} iters, {pr['python']} on {pr['platform']}")


def latex_table(results):
    lines = [
        "% Auto-generated by scripts/bench_crypto.py — do not edit by hand.",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Tessera cryptographic cost (SECP256k1, single core).}",
        "\\label{tab:crypto-microbench}",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Operation & Mean ($\\mu$s) & p99 ($\\mu$s) & Throughput (op/s) \\\\",
        "\\midrule",
    ]
    pretty = {
        "keygen": "Key generation",
        "zk_proof_gen": "ZK proof gen",
        "zk_proof_verify": "ZK proof verify",
        "aesgcm_encrypt": "AES-GCM encrypt",
        "aesgcm_decrypt": "AES-GCM decrypt",
        "ecdsa_sign_baseline": "ECDSA sign (baseline)",
        "ecdsa_verify_baseline": "ECDSA verify (baseline)",
    }
    for o in results["ops"]:
        lines.append(
            f"{pretty.get(o['op'], o['op'])} & {o['mean_us']:.1f} & "
            f"{o['p99_us']:.1f} & {o['throughput_ops_per_s']:,.0f} \\\\"
        )
    p = results["sizes"]["proof"]
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        f"\\\\[2pt]\\footnotesize Proof wire size: {p['total_bytes']}\\,B.",
        "\\end{table}",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Tessera crypto microbenchmark (E1)")
    ap.add_argument("--iterations", type=int, default=10000)
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--name", default="e1_crypto_microbench")
    ap.add_argument("--no-write", action="store_true", help="print only, do not write files")
    args = ap.parse_args()

    results = run(args.iterations, args.warmup)
    print_table(results)

    if args.no_write:
        return
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"{args.name}.json"
    tex_path = args.out_dir / f"{args.name}.tex"
    json_path.write_text(json.dumps(results, indent=2))
    tex_path.write_text(latex_table(results))
    print(f"\nwrote {json_path}")
    print(f"wrote {tex_path}")


if __name__ == "__main__":
    main()
