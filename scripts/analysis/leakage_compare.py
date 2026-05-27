#!/usr/bin/env python3
"""
E7 — Comparative metadata-leakage analysis.

Encodes, for each scheme and each observer, which pieces of call metadata are exposed.
Produces a JSON matrix + a LaTeX comparison table for the paper (§related-work / §evaluation).
This is the SoK-style table that makes the privacy contribution legible against deployed and
academic alternatives; the per-cell rationale is in the `notes` field.

Schemes:   STIR/SHAKEN (FCC), AuthentiCall (USENIX'17), CallDNS (this work).
Observers: Central authority (carrier/CA/enrolment server), Network eavesdropper,
           The callee, Colluding other callees.
Leaked items (per observer): caller identity, callee identity, caller<->callee link,
           call timing, cross-call linkability of a caller.

A cell is "leak" (1) / "no leak" (0) / "intended" (disclosure that is the point of the
system, counted separately). Lower total leakage = stronger metadata privacy.

Usage:  poetry run python scripts/analysis/leakage_compare.py
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

PAPER = Path(__file__).resolve().parents[3] / "calldns-paper"
DEFAULT_RESULTS = PAPER / "results"

ITEMS = ["caller_id", "callee_id", "caller_callee_link", "call_timing", "cross_call_link"]

# value: "leak" | "none" | "intended" | "n/a"
MATRIX = {
    "STIR/SHAKEN": {
        "central_authority": {  # carriers + certificate authorities mediate every call
            "caller_id": "leak", "callee_id": "leak", "caller_callee_link": "leak",
            "call_timing": "leak", "cross_call_link": "leak",
            "_note": "Carriers/CAs sign & verify every call; full call-graph visibility.",
        },
        "network": {  # SS7/SIP signaling frequently in clear
            "caller_id": "leak", "callee_id": "leak", "caller_callee_link": "leak",
            "call_timing": "leak", "cross_call_link": "leak",
            "_note": "Signaling metadata commonly observable on-path.",
        },
        "callee": {
            "caller_id": "intended", "callee_id": "n/a", "caller_callee_link": "intended",
            "call_timing": "leak", "cross_call_link": "leak",
            "_note": "Stable caller number -> callee links all calls from a caller.",
        },
        "colluding_callees": {
            "caller_id": "leak", "callee_id": "leak", "caller_callee_link": "leak",
            "call_timing": "leak", "cross_call_link": "leak",
            "_note": "Shared global caller number links a caller across callees.",
        },
    },
    "AuthentiCall": {
        "central_authority": {  # central enrolment + handshake service
            "caller_id": "leak", "callee_id": "leak", "caller_callee_link": "leak",
            "call_timing": "leak", "cross_call_link": "leak",
            "_note": "Central enrolment/handshake server sees who authenticates to whom.",
        },
        "network": {
            "caller_id": "none", "callee_id": "none", "caller_callee_link": "none",
            "call_timing": "leak", "cross_call_link": "none",
            "_note": "Handshake over an encrypted data channel; timing still observable.",
        },
        "callee": {
            "caller_id": "intended", "callee_id": "n/a", "caller_callee_link": "intended",
            "call_timing": "leak", "cross_call_link": "leak",
            "_note": "Enrolled long-term identity -> cross-call linkage.",
        },
        "colluding_callees": {
            "caller_id": "leak", "callee_id": "leak", "caller_callee_link": "leak",
            "call_timing": "leak", "cross_call_link": "leak",
            "_note": "Enrolled identity is global -> linkable across callees.",
        },
    },
    "CallDNS": {
        "central_authority": {  # there is none: pairwise local enrolment
            "caller_id": "n/a", "callee_id": "n/a", "caller_callee_link": "n/a",
            "call_timing": "n/a", "cross_call_link": "n/a",
            "_note": "No central party exists; bindings are pairwise/local.",
        },
        "network": {  # encrypted proofs + DP cover traffic in buckets
            "caller_id": "none", "callee_id": "none", "caller_callee_link": "none",
            "call_timing": "none", "cross_call_link": "none",
            "_note": "Proofs encrypted; (eps,delta)-DP bucket counts; blinded keys.",
        },
        "callee": {
            "caller_id": "intended", "callee_id": "n/a", "caller_callee_link": "intended",
            "call_timing": "intended", "cross_call_link": "intended",
            "_note": "Callee authenticates its own contact (the point); nothing more.",
        },
        "colluding_callees": {
            "caller_id": "none", "callee_id": "none", "caller_callee_link": "none",
            "call_timing": "none", "cross_call_link": "none",
            "_note": "Per-callee blinded pseudonym Y' -> no cross-callee linkage.",
        },
    },
}

COMPLIANCE = {
    "note": "Minimising caller<->callee metadata supports GDPR data-minimisation (Art. 5(1)(c)) "
            "and reduces the call-detail-record footprint relevant to PSD2 SCA and FCA Consumer "
            "Duty obligations; CallDNS keeps verification logs without a central communication graph.",
}


def leak_score(cells: dict) -> int:
    """Count of unintended leaks (excludes 'intended', 'none', 'n/a')."""
    return sum(1 for k in ITEMS if cells.get(k) == "leak")


def summarize():
    summary = {}
    for scheme, observers in MATRIX.items():
        total = sum(leak_score(cells) for cells in observers.values())
        summary[scheme] = total
    return summary


# Base-LaTeX math symbols (no extra packages needed).
SYMBOL = {"leak": "$\\bullet$", "none": "$\\circ$", "intended": "$\\odot$", "n/a": "--"}


def latex_table():
    obs_order = ["central_authority", "network", "callee", "colluding_callees"]
    obs_label = {"central_authority": "Central auth.", "network": "Network",
                 "callee": "Callee", "colluding_callees": "Colluding callees"}
    lines = [
        "% Auto-generated by scripts/analysis/leakage_compare.py (E7).",
        "% legend: $\\bullet$ leaked, $\\odot$ intended disclosure, $\\circ$ not leaked, -- n/a",
        "\\begin{table}[t]\\centering",
        "\\caption{Caller$\\leftrightarrow$callee metadata leakage by observer. "
        "Lower is more private.}",
        "\\label{tab:leakage}",
        "\\begin{tabular}{ll" + "c" * len(ITEMS) + "}",
        "\\toprule",
        "Scheme & Observer & " + " & ".join(
            ["caller", "callee", "link", "timing", "x-call"]) + " \\\\",
        "\\midrule",
    ]
    for scheme, observers in MATRIX.items():
        for j, obs in enumerate(obs_order):
            cells = observers[obs]
            row = [SYMBOL[cells[i]] for i in ITEMS]
            prefix = f"{scheme}" if j == 0 else ""
            lines.append(f"{prefix} & {obs_label[obs]} & " + " & ".join(row) + " \\\\")
        lines.append("\\midrule")
    lines[-1] = "\\bottomrule"
    lines += ["\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)


def print_report():
    print("E7 — comparative metadata leakage (unintended leaks per scheme)")
    print("=" * 60)
    for scheme, score in summarize().items():
        print(f"  {scheme:<14} total unintended-leak cells: {score}")
    print("\n(lower = more private; 'intended' callee disclosure excluded)")


def main():
    ap = argparse.ArgumentParser(description="CallDNS comparative leakage (E7)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    print_report()
    if not args.no_write:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        payload = {"experiment": "E7_leakage", "items": ITEMS, "matrix": MATRIX,
                   "summary_unintended_leaks": summarize(), "compliance": COMPLIANCE,
                   "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        (args.out_dir / "e7_leakage.json").write_text(json.dumps(payload, indent=2))
        (args.out_dir / "e7_leakage.tex").write_text(latex_table())
        print(f"\nwrote {args.out_dir / 'e7_leakage.json'}")
        print(f"wrote {args.out_dir / 'e7_leakage.tex'}")


if __name__ == "__main__":
    main()
