# SSZ-LIGO Test Suite — Current Status

**Version:** 0.3.0  
**Date:** 2026-05-18  
**Data:** GW240925 O4b — GWOSC [https://zenodo.org/records/18600070](https://zenodo.org/records/18600070)

---

## Overall Status

```
PIPELINE_STATUS:               PASS_EXPLORATORY
CODE_DOC_CONSISTENCY:          PASS (5/5)
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
```

---

## Formula Status

| Formula | Status | Since |
|---------|--------|-------|
| Xi_weak, Xi_strong, D, s | LOCKED | 2026-05-14 |
| rdot_SSZ = rdot_GR·D²/s⁴ | LOCKED (Ch.31) | 2026-05-14 |
| delta_psi_SSZ(f) | DERIVED_V1_INSPIRAL_0PN_LOCKED | 2026-05-18 |
| delta_a_SSZ(f) | DERIVED_V0_PROXY | 2026-05-18 |
| h_SSZ(f) | DERIVED_V0_PROXY | 2026-05-18 |
| epsilon_220 | BLOCKED_BRANCH_CONFLICT | 2026-05-14 |

---

## Pipeline Run Results (H1, 20–210 Hz, GW240925)

| Metric | Value |
|--------|-------|
| lnL_GR | −3.24×10⁷ |
| lnL_SSZ | −3.24×10⁷ |
| delta_lnL | +5.3×10⁻⁶ |
| MF-SNR GR | 44.2 |
| SSZ_EFFECT_ABOVE_CALIBRATION | YES (6.3e-06 > cal_spread 7.1e-08) |

---

## Test Coverage

| Test file | Status |
|-----------|--------|
| test_derived_delta_psi_v0.py | ✅ PASS |
| test_derived_delta_a_v0.py | ✅ PASS |
| test_h_ssz_v0_waveform_application.py | ✅ PASS |
| test_epsilon_220_branch_registry.py | ✅ PASS |
| test_xi_strong_branch_lock.py | ✅ PASS |
| test_08_anti_circularity.py | ✅ PASS |

---

## Open Blockers

1. **delta_psi**: 0PN only → need 3.5PN r(f) for real claim
2. **L1 noise**: anomalous SNR=647 in trigger window → check stationarity
3. **Coherence**: xcorr>1 (normalisation failure) → frequency-domain coherence needed
4. **epsilon_220**: 3 conflicting branches, all different observables — needs author resolution
5. **GR control**: 0PN only → needs matched 3.5PN
6. **Detector propagation**: RSG phase not included

---

## Reports

| Report | Date |
|--------|------|
| DERIVED_FORMULAS_CODE_CONSISTENCY_AUDIT.md | 2026-05-18 |
| H1_L1_COHERENCE_PIPELINE_REPORT.md | 2026-05-18 |
| CALIBRATION_PSD_SENSITIVITY_REPORT.md | 2026-05-18 |
| FINAL_INTERPRETATION_LOCK.md | 2026-05-18 |
| ANTI_CIRCULARITY_FINAL_GATE.md | 2026-05-18 |
