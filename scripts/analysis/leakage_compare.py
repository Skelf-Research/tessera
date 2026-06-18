#!/usr/bin/env python3
"""
E7 — Comparative metadata-leakage analysis (messaging framing, Paper A).

Encodes, for each scheme and each observer, which pieces of sender<->recipient metadata are
exposed, plus an explicit indicator of whether the system *authenticates* the sender at all.
Produces a JSON matrix + a LaTeX comparison table for the paper.

Schemes:   Signed messaging (Signal-style), Metadata-private messaging (Vuvuzela/Stadium/Talek),
           Tessera (this work).
Observers: Routing platform / mix-servers, Network eavesdropper, The recipient,
           Colluding other recipients.
Cell values per (scheme, observer, item):
  leak     — observer learns this metadata (unintended exposure)
  none     — observer does not learn this metadata
  intended — disclosure that is the point of the scheme (excluded from leak count)
  missing  — the system fundamentally cannot provide this (sender authentication gap)
  n/a      — observer does not exist in this scheme (e.g. central party in Tessera)

The headline is: signed messaging authenticates but leaks the graph; metadata-private messaging
hides the graph but cannot authenticate; Tessera does both.

Usage:  poetry run python scripts/analysis/leakage_compare.py
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

PAPER = Path(__file__).resolve().parents[3] / "tessera-paper-msg"
DEFAULT_RESULTS = PAPER / "results"

ITEMS = ["sender_id", "recipient_id", "sender_recipient_link", "delivery_timing", "cross_recipient_link"]

MATRIX = {
    "Signed messaging (Signal-style)": {
        "routing_platform": {  # central server / push platform routing every message
            "sender_id": "leak", "recipient_id": "leak", "sender_recipient_link": "leak",
            "delivery_timing": "leak", "cross_recipient_link": "leak",
            "_note": "Central server routes by sender/recipient identifiers; full graph visibility.",
        },
        "network": {  # TLS encrypts content; timing remains observable
            "sender_id": "none", "recipient_id": "none", "sender_recipient_link": "none",
            "delivery_timing": "leak", "cross_recipient_link": "none",
            "_note": "TLS encrypts content+identities on the wire; message timing observable.",
        },
        "recipient": {  # the recipient itself
            "sender_id": "intended", "recipient_id": "n/a", "sender_recipient_link": "intended",
            "delivery_timing": "intended", "cross_recipient_link": "leak",
            "_note": "Long-term sender identity key links the sender's prior deliveries to me.",
        },
        "colluding_recipients": {  # multiple recipients compare notes
            "sender_id": "leak", "recipient_id": "leak", "sender_recipient_link": "leak",
            "delivery_timing": "leak", "cross_recipient_link": "leak",
            "_note": "Shared long-term identity key links the sender across all their recipients.",
        },
    },
    "Metadata-private messaging (Vuvuzela-style)": {
        "routing_platform": {  # mix servers + DP cover traffic
            "sender_id": "none", "recipient_id": "none", "sender_recipient_link": "none",
            "delivery_timing": "none", "cross_recipient_link": "none",
            "_note": "Mix servers + (eps,delta)-DP cover traffic hide the graph by design.",
        },
        "network": {
            "sender_id": "none", "recipient_id": "none", "sender_recipient_link": "none",
            "delivery_timing": "none", "cross_recipient_link": "none",
            "_note": "Encrypted, padded, shuffled traffic between mix servers.",
        },
        "recipient": {
            "sender_id": "missing", "recipient_id": "n/a", "sender_recipient_link": "missing",
            "delivery_timing": "intended", "cross_recipient_link": "missing",
            "_note": "No sender authentication: recipient cannot tell which contact sent the message.",
        },
        "colluding_recipients": {
            "sender_id": "none", "recipient_id": "none", "sender_recipient_link": "none",
            "delivery_timing": "none", "cross_recipient_link": "none",
            "_note": "Cover traffic + per-mailbox PIR hides links between recipients.",
        },
    },
    "Tessera": {
        "routing_platform": {  # there is none: pairwise local enrolment, peered relays
            "sender_id": "n/a", "recipient_id": "n/a", "sender_recipient_link": "n/a",
            "delivery_timing": "n/a", "cross_recipient_link": "n/a",
            "_note": "No central routing operator; bindings are pairwise/local; relays are peers.",
        },
        "network": {  # encrypted proofs + DP cover traffic in buckets
            "sender_id": "none", "recipient_id": "none", "sender_recipient_link": "none",
            "delivery_timing": "none", "cross_recipient_link": "none",
            "_note": "Encrypted proofs; (eps,delta)-DP bucket counts; blinded pseudonyms.",
        },
        "recipient": {
            "sender_id": "intended", "recipient_id": "n/a", "sender_recipient_link": "intended",
            "delivery_timing": "intended", "cross_recipient_link": "intended",
            "_note": "Recipient authenticates its own contact (the point); nothing more.",
        },
        "colluding_recipients": {
            "sender_id": "none", "recipient_id": "none", "sender_recipient_link": "none",
            "delivery_timing": "none", "cross_recipient_link": "none",
            "_note": "Per-recipient blinded pseudonym Y' -> no cross-recipient linkage.",
        },
    },
}


def leak_score(cells: dict) -> int:
    """Count of unintended leaks (excludes 'intended', 'none', 'n/a', 'missing')."""
    return sum(1 for k in ITEMS if cells.get(k) == "leak")


def auth_gap_score(cells: dict) -> int:
    """Count of cells where the system fundamentally cannot provide authentication."""
    return sum(1 for k in ITEMS if cells.get(k) == "missing")


def summarize():
    leaks, gaps = {}, {}
    for scheme, observers in MATRIX.items():
        leaks[scheme] = sum(leak_score(c) for c in observers.values())
        gaps[scheme] = sum(auth_gap_score(c) for c in observers.values())
    return leaks, gaps


SYMBOL = {
    "leak": "$\\bullet$",
    "none": "$\\circ$",
    "intended": "$\\odot$",
    "missing": "$\\diamond$",
    "n/a": "--",
}


def latex_table():
    obs_order = ["routing_platform", "network", "recipient", "colluding_recipients"]
    obs_label = {
        "routing_platform": "Routing platform",
        "network": "Network",
        "recipient": "Recipient",
        "colluding_recipients": "Colluding recipients",
    }
    item_label = ["sender", "recip.", "link", "timing", "x-recip"]
    lines = [
        "% Auto-generated by scripts/analysis/leakage_compare.py (E7, messaging framing).",
        "% legend: $\\bullet$ leaked, $\\odot$ intended, $\\circ$ not leaked,",
        "%         $\\diamond$ authentication gap (system cannot provide), -- n/a",
        "\\begin{table}[t]\\centering",
        "\\caption{Sender$\\leftrightarrow$recipient metadata leakage by observer. "
        "Lower is more private; $\\diamond$ marks gaps where the scheme cannot authenticate the sender.}",
        "\\label{tab:leakage}",
        "\\begin{tabular}{ll" + "c" * len(ITEMS) + "}",
        "\\toprule",
        "Scheme & Observer & " + " & ".join(item_label) + " \\\\",
        "\\midrule",
    ]
    for scheme, observers in MATRIX.items():
        for j, obs in enumerate(obs_order):
            cells = observers[obs]
            row = [SYMBOL[cells[i]] for i in ITEMS]
            prefix = scheme if j == 0 else ""
            lines.append(f"{prefix} & {obs_label[obs]} & " + " & ".join(row) + " \\\\")
        lines.append("\\midrule")
    lines[-1] = "\\bottomrule"
    lines += ["\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)


def print_report():
    leaks, gaps = summarize()
    print("E7 — comparative metadata leakage (messaging framing)")
    print("=" * 72)
    print(f"{'scheme':<46}{'unintended leaks':>18}{'auth gaps':>11}")
    for scheme in MATRIX:
        print(f"  {scheme:<44}{leaks[scheme]:>18}{gaps[scheme]:>11}")
    print("\n(lower leaks = more private; auth gaps = recipient cannot authenticate sender)")


def main():
    ap = argparse.ArgumentParser(description="Tessera comparative leakage (E7)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    print_report()
    if not args.no_write:
        leaks, gaps = summarize()
        args.out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "experiment": "E7_leakage_messaging",
            "items": ITEMS,
            "matrix": MATRIX,
            "summary_unintended_leaks": leaks,
            "summary_authentication_gaps": gaps,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        (args.out_dir / "e7_leakage.json").write_text(json.dumps(payload, indent=2))
        (args.out_dir / "e7_leakage.tex").write_text(latex_table())
        print(f"\nwrote {args.out_dir / 'e7_leakage.json'}")
        print(f"wrote {args.out_dir / 'e7_leakage.tex'}")


if __name__ == "__main__":
    main()
