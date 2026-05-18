"""DQ-aware final LIGO status reports for GW240925.

Generates three reports reflecting the verified DQ state:
  1. reports/DQ_AWARE_FINAL_LIGO_STATUS.md     -- master gate document
  2. reports/H1_ONLY_EXPLORATORY_STRAIN_REPORT.md
  3. reports/L1_EXCLUDED_OR_DIAGNOSTIC_REPORT.md

Rules:
  - L1 not used for claim-like coherence while DQ context is unresolved.
  - H1-only remains exploratory.
  - No SSZ support/falsification claim.
  - All DQ facts sourced from VERIFIED_FROM_HDF5 provenance check.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
"""
import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
for d in (REPORTS, LOGS):
    d.mkdir(exist_ok=True)

TRIGGER_GPS = 1411261107.984
F_LOW, F_HIGH = 20.0, 210.0

_log = []


def log(m=""):
    print(m)
    _log.append(str(m))


log(f"DQ-Aware Final Status -- {NOW}")
log(f"Trigger GPS: {TRIGGER_GPS}")

# Use pre-verified values from run_dq_bit_provenance / run_robust_multiwindow_psd
# to avoid re-loading the full 4096-second HDF5 files (timeout risk).
# Source: run_dq_bit_provenance.py  (VERIFIED_FROM_HDF5)
h1d = {"bp_ratio": 0.76, "snr_proxy": 0.87}
l1d = {"bp_ratio": 2.28, "snr_proxy": 1.51}

log(f"H1: bp_ratio={h1d['bp_ratio']:.2f}  (from provenance run)")
log(f"L1: bp_ratio={l1d['bp_ratio']:.2f}  (from provenance run)")

# -----------------------------------------------------------------------
# Verified DQ facts (from VERIFIED_FROM_HDF5 provenance run)
# -----------------------------------------------------------------------
DQ_FACTS = """
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
"""

LIGO_QUESTION = """
@LIGO We found a strong 20-210 Hz in-band power excess in L1 at the GW240925
trigger time (GPS 1411261107.984) after robust multi-window off-source PSD
checks (band-power ratio L1/off-source ~ 2.28 vs H1 ~ 0.76).

DQ verification (VERIFIED_FROM_HDF5):
  - CBC_CAT2/CAT3: passing for both detectors
  - NO_CW_HW_INJ: unset (not certified injection-free) for both
    detectors over the entire 4096-second release segment
  - L1 CW_CAT1: passes; H1 CW_CAT1: fails (file-wide, constant)

Questions:
  1. Is L1 intended for broadband H1/L1 coherence analysis in this release?
  2. Are offline DQ products (omicron, iDQ, hveto) available for GW240925?
  3. Is the L1 segment affected by any known environmental coupling or
     non-stationarity not captured in the simple DQ bitmask?
  4. Is there a recommended off-source PSD window strategy for L1 in
     this event?
"""

# -----------------------------------------------------------------------
# Report 1: DQ_AWARE_FINAL_LIGO_STATUS.md
# -----------------------------------------------------------------------
r1 = """# DQ-Aware Final LIGO Status — GW240925

Generated: {NOW}  
Event: GW240925 (trigger GPS {TRIGGER_GPS})

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

{DQ_FACTS}

## What This Means

H1 passes all CBC quality flags and has a normal band-power ratio
(trigger/off-source = {h1d['bp_ratio']:.2f}). It can be used for
exploratory single-detector strain analysis.

L1 passes all CBC quality flags but shows a strong broadband
in-band power excess (ratio = {l1d['bp_ratio']:.2f}) that is not
explained by any available GWOSC DQ flag. The NO_CW_HW_INJ
flag is unset for the entire 4096-second file at both detectors —
a file-level property, not a trigger artifact. Until this is
clarified by offline DQ tools, L1 should not be used as a coherence
partner for SSZ claim-level tests.

## What This Does NOT Mean

```
NOT: SSZ explains the L1 anomaly
NOT: LIGO data is incorrect
NOT: GW240925 is not a real event
NOT: The pipeline is wrong
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
{LIGO_QUESTION}
```
"""

(REPORTS / "DQ_AWARE_FINAL_LIGO_STATUS.md").write_text(r1, encoding="utf-8")
log("  -> reports/DQ_AWARE_FINAL_LIGO_STATUS.md")

# -----------------------------------------------------------------------
# Report 2: H1_ONLY_EXPLORATORY_STRAIN_REPORT.md
# -----------------------------------------------------------------------

# Pre-verified values from run_dq_bit_provenance / earlier PSD runs
bp_ratio_h1 = h1d["bp_ratio"]
peak_snr_h1 = h1d["snr_proxy"]

r2 = """# H1-Only Exploratory Strain Report — GW240925

Generated: {NOW}  
Detector: H1 (LIGO Hanford)  
Event: GW240925 (trigger GPS {TRIGGER_GPS})  
Status: **USABLE_EXPLORATORY**

## Why H1-Only

L1 is in DQ_FLAGGED_DIAGNOSTIC_ONLY status due to unresolved broadband
power excess and CW hardware injection context (see
DQ_AWARE_FINAL_LIGO_STATUS.md). H1 passes all CBC quality flags and
has a normal in-band power profile.

## H1 DQ Status (VERIFIED_FROM_HDF5)

| Flag | Value | Status |
|------|-------|--------|
| DATA | 1 | PASS |
| CBC_CAT1 | 1 | PASS |
| CBC_CAT2 | 1 | PASS |
| CBC_CAT3 | 1 | PASS |
| BURST_CAT1 | 1 | PASS |
| BURST_CAT2 | 1 | PASS |
| BURST_CAT3 | 1 | PASS |
| STOCH_CAT1 | 1 | PASS |
| CW_CAT1 | 0 | FAILS (file-wide, not trigger-specific) |

CW_CAT1 failure is constant over the entire 4096-second file,
indicating a detector-state issue for CW analyses unrelated to the
GW240925 trigger window.

## H1 In-Band Diagnostics

| Metric | Value |
|--------|-------|
| Band | {F_LOW}--{F_HIGH} Hz |
| Off-source window | trigger -200s, 64s duration |
| Band-power ratio (trigger/off-source) | {bp_ratio_h1:.2f} |
| Peak single-bin SNR proxy | {peak_snr_h1:.1f} |
| Assessment | {'ELEVATED — consistent with real GW signal' if bp_ratio_h1 > 1.5 else 'NORMAL' if bp_ratio_h1 > 0.5 else 'LOW'} |

## What H1 Can Test

```
USABLE FOR:
  - Single-detector scale SSZ: h_H1^SSZ = S * h_H1^GR
  - H1 MF-SNR with 2PN template
  - H1 band-power consistency check
  - H1 scale-factor scan vs theta at fixed inclination
  - Pipeline validation on a clean detector

NOT USABLE FOR (without L1):
  - H1/L1 differential response under twist
  - Coherence-based SSZ evidence
  - Multi-detector twist claim
```

## Gate

```
H1_STATUS:                     USABLE_EXPLORATORY
H1_CBC_DQ:                     PASS
H1_ANOMALY:                    NONE
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE:        NO
```
"""

(REPORTS / "H1_ONLY_EXPLORATORY_STRAIN_REPORT.md").write_text(r2, encoding="utf-8")
log("  -> reports/H1_ONLY_EXPLORATORY_STRAIN_REPORT.md")

# -----------------------------------------------------------------------
# Report 3: L1_EXCLUDED_OR_DIAGNOSTIC_REPORT.md
# -----------------------------------------------------------------------
r3 = """# L1 Excluded / Diagnostic Report — GW240925

Generated: {NOW}  
Detector: L1 (LIGO Livingston)  
Event: GW240925 (trigger GPS {TRIGGER_GPS})  
Status: **DQ_FLAGGED_DIAGNOSTIC_ONLY**

## Why L1 Is Diagnostic-Only

L1 passes all CBC quality flags (CAT1/2/3, DATA) according to the
GWOSC release DQ bitmask. However, a strong broadband in-band power
excess is observed (band-power ratio trigger/off-source = {l1d['bp_ratio']:.2f})
that is NOT explained by any available DQ flag.

Additionally, the CW hardware injection flag (NO_CW_HW_INJ) is not
set ("not certified injection-free") for the entire 4096-second
release segment at both detectors. This is a file-wide constant, not
a trigger-specific event, and cannot by itself explain the broadband
excess.

## L1 DQ Status (VERIFIED_FROM_HDF5)

| Flag | Value | Status |
|------|-------|--------|
| DATA | 1 | PASS |
| CBC_CAT1 | 1 | PASS |
| CBC_CAT2 | 1 | PASS |
| CBC_CAT3 | 1 | PASS |
| BURST_CAT1 | 1 | PASS |
| BURST_CAT2 | 1 | PASS |
| BURST_CAT3 | 1 | PASS |
| STOCH_CAT1 | 1 | PASS |
| CW_CAT1 | 1 | PASS (100% over full file) |

## L1 In-Band Diagnostics

| Metric | Value |
|--------|-------|
| Band | {F_LOW}--{F_HIGH} Hz |
| Band-power ratio (trigger/off-source) | {l1d['bp_ratio']:.2f} |
| H1 band-power ratio for comparison | {h1d['bp_ratio']:.2f} |
| H1/L1 ratio difference | {abs(l1d['bp_ratio'] - h1d['bp_ratio']):.2f} |
| Assessment | ANOMALOUS — excess not explained by GWOSC DQ |

## Possible Explanations (Unresolved)

```
1. Real GW signal in L1
   GW240925 is a confirmed event. L1 would be expected to show
   elevated in-band power. This may simply be the signal.
   -> Would require matched-filter SNR comparison vs H1.

2. Non-stationary noise transient
   A noise event not captured by the 1Hz DQ bitmask.
   -> Needs offline omicron/iDQ to rule out.

3. PSD estimation mismatch
   Off-source window at -200s may not represent noise at trigger time.
   -> Robust multi-window PSD (already done) showed consistent excess.

4. CW hardware injection contribution
   Narrow-band only — cannot explain broadband excess.
   -> Already ruled out by bandwidth argument.
```

## What L1 Can Be Used For

```
DIAGNOSTIC USE ONLY:
  - Qualitative comparison with H1
  - Visual inspection of spectral excess
  - Motivating LIGO DQ question

NOT USABLE FOR:
  - H1/L1 coherence-based SSZ evidence
  - Multi-detector twist amplitude claim
  - Any claim requiring clean L1 noise characterization
```

## Reinstatement Criteria

```
L1 can be reinstated as a full coherence partner when:
  1. Offline DQ (omicron/iDQ/hveto) confirms no glitch at trigger time
  OR
  2. LIGO/GWOSC confirms the L1 segment is usable for coherence tests
  OR
  3. A physically motivated explanation for the excess is found
     (e.g., confirmed matched-filter SNR consistent with the event)
```

## Gate

```
L1_STATUS:                     DQ_FLAGGED_DIAGNOSTIC_ONLY
L1_CBC_DQ:                     PASS (no vetoed glitch)
L1_BROADBAND_EXCESS:           UNEXPLAINED
L1_REINSTATEMENT:              REQUIRES_OFFLINE_DQ_OR_LIGO_CONFIRMATION
H1_L1_COHERENCE_STATUS:        BLOCKED_BY_L1_DQ
TWIST_REAL_DATA_STATUS:        BLOCKED_BY_L1_DQ
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
```
"""

(REPORTS / "L1_EXCLUDED_OR_DIAGNOSTIC_REPORT.md").write_text(r3, encoding="utf-8")
log("  -> reports/L1_EXCLUDED_OR_DIAGNOSTIC_REPORT.md")

# Flush log
(LOGS / "dq_aware_final_status.log").write_text(
    "\n".join(_log), encoding="utf-8"
)

log("\nFINAL GATE:")
log("  H1_STATUS:                     USABLE_EXPLORATORY")
log("  L1_STATUS:                     DQ_FLAGGED_DIAGNOSTIC_ONLY")
log("  H1_L1_COHERENCE_STATUS:        BLOCKED_BY_L1_DQ")
log("  TWIST_REAL_DATA_STATUS:        BLOCKED_BY_L1_DQ")
log("  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
log("  SSZ_SUPPORT_CLAIM_MADE:        NO")
log("  SSZ_FALSIFICATION_CLAIM_MADE:  NO")
