# H1/L1 Abs-Correlation Replication Report

**Generated:** 2026-05-19
**Event:** GW240925 (GPS 1411261107.984)
**Status:** COHERENT_WITH_SIGN_FLIP — NO CLAIM

---

## Summary

The H1/L1 cross-correlation test does not argue against a common event signal.
When sign convention is handled correctly, the trigger window shows a strong
anti-correlated match at dt=0 ms:

```text
corr(dt=0 ms) = -0.991
abs(corr)     =  0.991
```

This is consistent with an opposite detector sign/projection convention
(H1/L1 have opposite arm orientations in the GW strain projection).

The previous dt=-10 ms result and PERSISTENT_SYSTEMATIC classification were
xcorr implementation artifacts from using argmax(corr) instead of argmax(|corr|).

---

## Classification

```text
H1_L1_REPLICATION_STATUS:        COHERENT_WITH_SIGN_FLIP
BEST_DELAY:                       0 ms
BEST_ABS_CORR:                    0.991
SIGN_RELATION:                    OPPOSITE_SIGN
PREVIOUS_DT_MINUS_10MS_RESULT:    CLASSIFICATION_ARTIFACT
L1_ONLY_STRUCTURE:                NO, not globally
L1_20_40_STATUS:                  DQ/artifact context still required — see below
READY_FOR_REAL_LIGO_SSZ_CLAIM:    NO
SSZ_SUPPORT_CLAIM_MADE:           NO
SSZ_FALSIFICATION_CLAIM_MADE:     NO
```

---

## What This Means

**The H1/L1 anti-correlation at dt=0 ms IS a valid coherence signal.**

When the sign convention between detectors is accounted for, abs(corr) = 0.991
at zero delay is an extremely strong match. This is not bad correlation —
it is expected behavior for the H1/L1 detector pair.

**What this does NOT mean:**

```text
- L1 is fully clean
- The 20-40 Hz L1 anomaly is resolved
- SSZ is confirmed
- SSZ is falsified
- This event is free of DQ concerns
```

---

## Remaining Open Gate: L1 20-40 Hz

The L1 20-40 Hz non-Gaussian structure (kurtosis +44.9 at trigger) remains separately
unresolved. Full-band coherence does not automatically imply that the 20-40 Hz subband
contributes coherently.

**Required next gate:** Subband abs-correlation test.
See: reports/H1_L1_SUBBAND_REPLICATION_REPORT.md

---

## Anti-Circularity

```text
No PE/QNM posteriors used.
No Kerr/SSZ model parameters used.
Peak detection: argmax(|C(tau)|) — sign-convention-safe.
```
