# SSZ-LIGO Forward Model Test Suite

**Version:** 0.3.0 — 2026-05-18  
**Status:** EXPLORATORY PIPELINE PASS | READY_FOR_REAL_LIGO_SSZ_CLAIM: **NO**

---

## What This Is

A **physics-first forward model** from SSZ (Segmented Spacetime) theory to LIGO detector strain,
tested against real GWOSC data (GW240925, O4b).

**NOT** a posterior-parameter test.  
**NOT** a Kerr self-consistency test.  
**NOT** a claim engine.

Pipeline:
```
SSZ Core (Ξ,D,s) → rdot/P_GW correction → Phase accumulation (RSG)
→ δΨ_SSZ(f), δA_SSZ(f) → h_SSZ(f) → H1/L1 strain → Residuals + lnL
```

---

## Data Source

Real LIGO strain data from the **GWOSC O4b public release**:

> **GW240925 + GW250207 — O4b Data Release**  
> Zenodo: [https://zenodo.org/records/18600070](https://zenodo.org/records/18600070)  
> DOI: 10.5281/zenodo.18600070

Files used (read-only, no posterior):
- `H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5`
- `L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5`
- PSD estimated from off-source Welch (−500 s window, 256 s duration)
- **No posterior samples used. No PE output used.**

---

## Core SSZ Formulas

```python
# Regime-dependent Xi
Xi_weak(r)   = r_s / (2r)                          # r/r_s > 10
Xi_strong(r) = min(1 - exp(-phi * r/r_s), Xi_max)  # r/r_s < 1.8  [CANONICAL]
Xi_blend(r)  = Hermite C2 interpolation             # 1.8 < r/r_s < 2.2

# Metric functions
D(r) = 1 / (1 + Xi(r))
s(r) = 1 + Xi(r) = 1/D(r)

# Inspiral corrections  [SSZ Book Ch.31-32, LOCKED]
rdot_SSZ  = rdot_GR  * D(r)^2 / s(r)^4
P_GW_SSZ  = P_GW_GR  * D(r)^2 / s(r)^2

# Frequency-domain observables
delta_psi_SSZ(f) = [Omega(r(f)) / |rdot_GR(r(f))|] * [(1+Xi)^6 - 1] * |dr/df|
delta_a_SSZ(f)   = D(r(f))^2 - 1
h_SSZ(f)         = h_GR(f) * (1 + delta_a) * exp(i * delta_psi)
```

**Key values:**  `phi = 1.6180...` (golden ratio) | `Xi_max = 0.8017` | `D_min = 0.5550`

---

## Formula Status

| Formula | Status | Source |
|---------|--------|--------|
| Xi_weak, Xi_strong, D, s | LOCKED | SSZ Book, formula_compendium.md |
| rdot_SSZ = rdot_GR·D²/s⁴ | LOCKED | SSZ Book Ch.31 |
| delta_psi_SSZ(f) | **DERIVED_V1_INSPIRAL_0PN_LOCKED** | algebraically exact given rdot |
| delta_a_SSZ(f) | DERIVED_V0_PROXY | D²−1 from P_GW ratio |
| h_SSZ(f) | DERIVED_V0_PROXY | V0 waveform construction |
| epsilon_220 (ringdown) | **BLOCKED_BRANCH_CONFLICT** | 3% vs 31% vs 39% — different observables |

**The 39% QNM value is a source-frame strong-field ratio, not a LIGO strain observable.**

---

## Pipeline Results (GW240925, H1, 20–210 Hz)

| Model | lnL | MF-SNR |
|-------|-----|--------|
| GR control (0PN TaylorF2) | −3.24×10⁷ | 44.2 |
| SSZ V1 inspiral (0PN) | −3.24×10⁷ | 5.98 |

```
delta_lnL (H1) = +5.3e-06   [indistinguishable at 0PN]
delta_lnL (L1) = −4.4e-05   [L1 anomalous noise floor — pipeline diagnostic]
```

**Calibration sensitivity scan:**  
`SSZ_EFFECT_ABOVE_CALIBRATION: YES` — delta_lnL (6.3e-06) > cal spread (7.1e-08)  
(The effect is internally stable against ±5% amp and ±0.05 rad phase calibration errors,
but the absolute magnitude is far below noise.)

**F_HIGH capped at 210 Hz** (below f_ISCO ~ 215 Hz for M~20 M☉ — 0PN regime validity).

---

## Anti-Circularity

| Rule | Status |
|------|--------|
| No posterior f,m,χ used | ✅ ENFORCED |
| No pSEOBNR / PE output | ✅ ENFORCED |
| GR control = analytic 0PN only | ✅ ENFORCED |
| PSD from off-source Welch | ✅ ENFORCED |
| No ringdown epsilon claim | ✅ ENFORCED |
| SSZ_SUPPORT_CLAIM_MADE | **NO** |
| SSZ_FALSIFICATION_CLAIM_MADE | **NO** |

---

## Code/Docs Consistency Audit (2026-05-18)

`reports/DERIVED_FORMULAS_CODE_CONSISTENCY_AUDIT.md`

| Check | Result |
|-------|--------|
| delta_psi code matches derivation doc | ✅ YES |
| delta_a code matches derivation doc | ✅ YES |
| h_SSZ code matches derivation doc | ✅ YES |
| Xi_strong = saturation (CANONICAL) | ✅ YES |
| epsilon_220 blocked | ✅ YES |
| Posterior firewall | ✅ CLEAR |

---

## H1/L1 Coherence + Calibration (2026-05-18)

`reports/H1_L1_COHERENCE_PIPELINE_REPORT.md`  
`reports/CALIBRATION_PSD_SENSITIVITY_REPORT.md`

- Both detectors processed independently with same anti-circular pipeline
- L1 shows anomalous noise (~6× H1 RMS) in trigger window — documented diagnostic
- Frequency-domain coherence test pending (time-domain xcorr normalisation failed)
- Calibration scan complete: SSZ V1 effect stable across ±5% amp, ±0.05 rad phase, Welch variants

---

## Repository Structure

```
src/ssz_ligo_tests/
  ssz_core.py              — Xi, D, s, regime detection
  constants.py             — PHI, XI_MAX, D_MIN, G, C
  derived_phase.py         — delta_psi_ssz_v0 (V1 0PN locked)
  derived_amplitude.py     — delta_a_ssz_v0
  derived_waveform.py      — h_SSZ(f) construction
  epsilon_220_registry.py  — 3 branches, all BLOCKED
  anti_circularity.py      — observable classifier
  likelihood.py            — lnL, MF-SNR
  ligo_data.py             — read-only GWOSC adapter

tests/
  test_derived_delta_psi_v0.py
  test_derived_delta_a_v0.py
  test_h_ssz_v0_waveform_application.py
  test_epsilon_220_branch_registry.py
  test_xi_strong_branch_lock.py
  test_08_anti_circularity.py

scripts/
  run_h1_l1_coherence_pipeline.py     — B1: H1+L1 strain pipeline
  run_calibration_psd_sensitivity.py  — B2: cal/PSD sensitivity scan
  run_derived_v0_pipeline.py          — original V0 strain pipeline
  run_strain_pipeline.py              — full strain pipeline

docs/
  DELTA_PSI_DERIVATION.md             — delta_psi formula derivation
  DELTA_PSI_V1_LOCK_ATTEMPT.md        — V1 lock attempt (0PN locked)
  DELTA_A_DERIVATION.md               — delta_a formula derivation
  H_SSZ_V0_DERIVATION.md             — h_SSZ construction
  EPSILON_220_DERIVATION_STATUS.md    — 3-branch conflict status
  EPSILON_220_BRANCH_LOCK.md          — branch classification
  QNM_OBSERVABLE_RENAMING.md          — 39%/31%/3% disambiguation
  FORMULA_BRANCH_LOCK.md              — Xi branch lock
  XI_STRONG_BRANCH_LOCK.md            — Xi_strong canonical form
  REGIME_BOUNDARY_LOCK.md             — r/rs regime boundaries
  MISSING_FORMULAS_DEVELOPMENT_REPORT.md

reports/
  DERIVED_FORMULAS_CODE_CONSISTENCY_AUDIT.md  — code/docs audit
  H1_L1_COHERENCE_PIPELINE_REPORT.md          — H1/L1 run
  CALIBRATION_PSD_SENSITIVITY_REPORT.md        — cal/PSD scan
  FINAL_INTERPRETATION_LOCK.md                 — locked interpretation
  ANTI_CIRCULARITY_FINAL_GATE.md               — anti-circ gate
  DERIVED_V0_STRAIN_PIPELINE_REPORT.md         — V0 pipeline run
  NEXT_PHYSICS_DERIVATION_TASKS.md             — open tasks
```

---

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

Requirements: `numpy`, `scipy`, `h5py`, `pytest`

## Running Tests

```bash
pytest                                           # all tests
pytest tests/test_derived_delta_psi_v0.py        # delta_psi formula
pytest tests/test_xi_strong_branch_lock.py       # Xi branch lock
pytest tests/test_epsilon_220_branch_registry.py # epsilon_220 blocked
```

## Running Pipelines

```bash
# H1+L1 coherence pipeline (needs GWOSC data at path in script)
python scripts/run_h1_l1_coherence_pipeline.py

# Calibration/PSD sensitivity scan
python scripts/run_calibration_psd_sensitivity.py
```

---

## Open Blockers Before Any Real Claim

```
1. delta_psi: upgrade from 0PN to 3.5PN r(f) mapping
2. delta_a:   scope lock (inspiral only, no merger)
3. epsilon_220: resolve 3% vs 31% vs 39% (different observables — need author)
4. L1 noise floor: check stationarity in trigger window
5. Coherence: implement frequency-domain coherence (time-domain xcorr failed)
6. GR control: use matched 3.5PN TaylorF2 instead of 0PN
7. Detector propagation: RSG phase not yet included

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
```

---

## License

ANTI-CAPITALIST SOFTWARE LICENSE v1.4

---

*Part of the SSZ (Segmented Spacetime) research project.*  
*Related repositories: [ssz-complete-documentation](https://github.com/error-wtf/ssz-complete-documentation) | [ssz-all-tests](https://github.com/error-wtf/ssz-all-tests)*
