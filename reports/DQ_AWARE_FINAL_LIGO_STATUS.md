# DQ-Aware Final LIGO Status — GW240925

Generated: 2026-05-18 23:49:58  
Event: GW240925 (trigger GPS 1411261107.984)

## Master Gate

```
H1_STATUS:                     USABLE_EXPLORATORY
L1_STATUS:                     DQ_FLAGGED_DIAGNOSTIC_ONLY
H1_L1_COHERENCE_STATUS:        BLOCKED_BY_L1_DQ
TWIST_REAL_DATA_STATUS:        BLOCKED_BY_L1_DQ
DQ_BIT_MAPPING_STATUS:         VERIFIED_FROM_HDF5
L1_DQ_INTERPRETATION:          NO_CBC_FLAG_CONFIRMED / CW_CONTEXT_UNRESOLVED
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
```

## Pipeline Status Summary

| Component | Status | Basis |
|-----------|--------|-------|
| Phase transport theory | FORMALIZED | 39 tests pass |
| Source propagation twist | SYNTHETIC_PASS | 42 tests pass |
| 2PN polarization control | BETTER_CONDITIONED | 26 tests pass |
| H1 exploratory strain | USABLE_EXPLORATORY | CBC DQ pass, H1 only |
| L1 coherence partner | DQ_FLAGGED_DIAGNOSTIC | CW context unresolved |
| H1/L1 twist real data | BLOCKED_BY_L1_DQ | Cannot interpret |
| Real LIGO SSZ claim | NO | Multiple blockers |

## Verified DQ Facts (VERIFIED_FROM_HDF5)


Source: run_dq_bit_provenance.py  —  DQ_BIT_MAPPING_STATUS: VERIFIED_FROM_HDF5
All names and descriptions read from HDF5 datasets DQShortnames / DQDescriptions
/ InjShortnames / InjDescriptions directly.

H1 DQ at trigger:
  DATA=1, CBC_CAT1=1, CBC_CAT2=1, CBC_CAT3=1
  BURST_CAT1=1, BURST_CAT2=1, BURST_CAT3=1, STOCH_CAT1=1
  CW_CAT1=0  (0% over entire 4096s file — constant, not trigger-specific)
  NO_CW_HW_INJ=0  (0% over entire 4096s file — constant)

L1 DQ at trigger:
  DATA=1, CBC_CAT1=1, CBC_CAT2=1, CBC_CAT3=1
  BURST_CAT1=1, BURST_CAT2=1, BURST_CAT3=1, STOCH_CAT1=1, CW_CAT1=1
  NO_CW_HW_INJ=0  (0% over entire 4096s file — constant)

Key interpretation:
  - L1 passes ALL CBC quality flags (CAT1/2/3) — no vetoed CBC glitch
  - H1 CW_CAT1=0 is file-wide, not trigger-specific
  - NO_CW_HW_INJ unset for both = "not certified injection-free for CW"
    over the entire segment; cannot explain broadband L1 excess
  - L1 broadband excess remains unexplained by GWOSC release DQ products


## What This Means

H1 passes all CBC quality flags and has a normal band-power ratio
(trigger/off-source = 0.76). It can be used for
exploratory single-detector strain analysis.

L1 passes all CBC quality flags but shows a strong broadband
in-band power excess (ratio = 2.28) that is not
explained by any available GWOSC DQ flag. The NO_CW_HW_INJ
flag is unset for the entire 4096-second file at both detectors —
a file-level property, not a trigger artifact. Until this is
clarified by offline DQ tools, L1 should not be used as a coherence
partner for SSZ claim-level tests.

## Data Context — Precise Interpretation

The GWOSC release products are calibrated, quality-classified products
intended for specific analysis classes (primarily CBC/GR detection).

```
CBC_CAT2/CAT3 clean means:
  For CBC/compact-binary analysis, no vetoed glitch by these criteria.

CBC_CAT2/CAT3 clean does NOT mean:
  This segment is neutral in every frequency band and for
  every alternative analysis metric.
```

The correct framing for our situation:

```
The released products are suitable for their intended CBC/GR
analysis context, but not sufficient for our anti-circular
non-GR forward-model test without additional DQ/line/injection
clarification for L1.
```

This is NOT:

```
NOT: LIGO data is wrong or manipulated
NOT: GW240925 is not a real event
NOT: SSZ explains the L1 anomaly
NOT: The pipeline is wrong
NOT: LIGO has misrepresented the data
```

## Path Forward

```
Option A: Other event(s)
  Run same pipeline on additional O4 events with clean H1 and L1.
  Multi-event consistent H1/L1 twist response would be meaningful.

Option B: H1-only exploratory
  Use H1 alone for scale/twist sensitivity studies.
  Cannot test H1/L1 differential response, but can validate pipeline.

Option C: LIGO question
  Submit the question below to LIGO/GWOSC.
  If offline DQ confirms L1 is clean, rerun coherence analysis.

Option D: Wait for offline DQ products
  If omicron/iDQ becomes available for this release, rerun.
```

## LIGO Question (ready to send)

```
@LIGO We do not claim the data are wrong. But for our non-GR forward-model
test (non-circular, source-propagation twist branch) we found that L1 has
a persistent 20-210 Hz band-power excess (ratio trigger/off-source ~ 2.28
vs H1 ~ 0.76), while CBC_CAT2/CAT3 are clean at both detectors.

Our state-vector check (bit names verified from HDF5 file directly):
  - CBC_CAT1/2/3: passing for both detectors
  - NO_CW_HW_INJ: unset for both detectors over full 4096-second segment
    (constant, not trigger-specific)
  - H1 CW_CAT1: 0 (file-wide); L1 CW_CAT1: 1 (file-wide)

We understand the release products are optimized for CBC/GR analyses.
For our specific use case (broadband H1/L1 coherence as a forward-model
differential test) we need additional context:

  1. Is L1 intended for broadband H1/L1 coherence tests in this release?
  2. Are offline DQ products (omicron, iDQ, hveto, line-noise) available
     for GW240925?
  3. Is the L1 segment affected by known non-stationarity or environmental
     coupling not captured in the simple DQ bitmask?
  4. Is there a recommended off-source PSD window strategy for L1 here?

Thank you.
```
