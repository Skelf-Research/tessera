# Privacy Model

Tessera composes three independent privacy mechanisms. The formal guarantees
live in [`../research.md`](../research.md); this page is the engineer-facing summary.

## Adversaries we defend against

| Adversary | What they see | Defence |
|---|---|---|
| The recipient | The proof, `Y'`, the metadata | **Per-recipient blinded pseudonym** — recipient learns nothing about the sender beyond what enrolment already revealed. |
| Colluding recipients of the same sender | Each their own `Y'` | **Distinct shared seeds** → unrelated `Y'` distributions; without the seed, `Y'` is uniform. No cross-recipient linkage. |
| Global passive network observer | Per-bucket message counts per round | **(ε,δ)-DP cover traffic** — load-independent shifted-Laplace noise. |
| A coalition of compromised relays | Same as above (counts only) | Same: the DP bound holds against any party that only sees counts. |
| Replay attacker | A captured `(commit, π)` | **Per-delivery commitment freshness + receiver dedup**. |

Out of scope: a compromised endpoint (we assume the secret key is intact on
the sender's device and the recipient runs the verifier honestly).

## Mechanism 1 — sender authentication without witness leak

Schnorr / Fiat–Shamir in the ROM gives perfect honest-verifier zero-knowledge
on the witness `x` (Theorem 2 in [`../research.md`](../research.md)).
The proof `π = (R, s)` reveals nothing about `x` beyond the truth of
"`∃ x: Y = xG`", and `Y` itself is the per-recipient blinded pseudonym `Y'`,
not the long-term key.

## Mechanism 2 — per-recipient pseudonyms (cross-recipient unlinkability)

For each delivery the sender uses

```
t  = H(shared_seed ‖ session_id) mod q
Y' = Y + t·G
```

and proves knowledge of `x' = x + t`. The recipient holding `shared_seed`
recomputes `t` and accepts. **A party without `shared_seed` sees a uniform
`Y'` per delivery** — so two different recipients of the same sender cannot
correlate their `Y'`s, and a third-party observer cannot link any of them.
See [`authentication.md`](authentication.md) for the API and
`tests/test_blinding.py` for the cross-recipient-unlinkability test.

## Mechanism 3 — (ε,δ)-DP cover traffic on per-bucket counts

The protocol routes encrypted, fixed-size proofs into `B = 64` buckets; an
adversary observing the network sees, per bucket per 30 s round, only the
**count** `C_b = R_b + D_b` (real plus dummy).

The original design generated dummies *proportional* to real load, which made
`C_b` a deterministic function of `R_b` — zero metadata privacy.
`tessera/sdk/traffic_manager.py::DPCoverTraffic` instead draws dummies
**independently of the real load**:

```
D_b = max(0, round(μ + L)),    L ~ Laplace(0, 1/ε)
μ  ≥ (1/ε) · ln(1/(2δ))
```

The shifted-Laplace mechanism makes `C_b` `(ε,δ)`-differentially private with
respect to a single delivery event (sensitivity 1). The truncation at 0 is the
source of `δ` and is bounded by the chosen `μ`. Expected bandwidth cost ≈ `B·μ`
dummies per round, independent of real load.

**Empirically validated** by E3 (`scripts/analysis/linkability_sim.py`):
under a worst-case knows-all-other-inputs adversary, no-cover and proportional
cover both give linking AUC = 1.0; DP cover bounds AUC toward 0.5 as `ε → 0`
and stays under the `ε`-DP ceiling `1 − e^(−ε)/2` at every operating point.

## Spatial anonymity at the bucket layer

Each commitment maps to one of 64 buckets; a proof is indistinguishable among
the commitments sharing its bucket. With ≥10 k active commitments per window
every bucket holds ≥126 members. At low deployment scale (≲1 k commitments)
86 % of buckets fall below `k=20` — a known limitation; the design space for an
adaptive bucket count is noted in the paper.

## Replay resistance

`commit = H(Y' ‖ ephemeral_key ‖ session_id)` is fresh per delivery (the
ephemeral and session_id are freshly sampled). The receiver-side dedup in
`AsyncNodeStorage` rejects re-presented proofs; outside the matchable time
window the freshness check rejects regardless. See
[`commitment-registration.md`](commitment-registration.md) and Theorem 3 in the
paper.

## What the recipient *does* learn (the intended disclosure)

- That this delivery came from the contact whose `(Y, shared_seed)` record it
  holds.
- Anything in the delivery metadata (the recipient can read the message;
  Tessera doesn't replace content encryption).
- The arrival time at the recipient (intended; the recipient's own clock).

It does **not** learn the sender's long-term `Y`, the sender's interactions
with any other recipient, or the sender's deliveries that didn't reach it.

## What the network learns

Nothing actionable beyond (ε,δ)-DP-noised per-bucket counts: encrypted proofs
are padded to a constant size and shuffled within the 30 s round. Routing
keys are not visible without the per-call commitment; the only observable is
the bucket count.

## Comparative leakage

See E7 / `scripts/analysis/leakage_compare.py` and Table 2 in the paper:
signed-messaging baselines leak 12 unintended cells (the central server sees
the graph); metadata-private messaging hides the graph but has 3
authentication gaps (the recipient cannot identify the sender at all);
Tessera has 0 leaks and 0 gaps.

## Related

- [`authentication.md`](authentication.md) — the per-recipient pseudonym mechanism.
- [`commitment-registration.md`](commitment-registration.md) — replay defence.
- [`../research.md`](../research.md) — full DP proof.
