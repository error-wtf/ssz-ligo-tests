# SSZ-LIGO Forward Model Test Suite

**Version:** 0.4.0 — 2026-05-19  
**Event:** GW240925 (O4b, GWOSC public release)  
**Status:** `PIPELINE_STATUS: PASS_EXPLORATORY` | `READY_FOR_REAL_LIGO_SSZ_CLAIM: NO`

---

## What This Is

A **physics-first, anti-circular forward model** from SSZ (Segmented Spacetime)
theory to LIGO detector strain, tested against real public GWOSC data (GW240925, O4b).

This is **not** a posterior-parameter test.  
This is **not** a Kerr self-consistency test.  
This is **not** a claim engine.

The pipeline computes a fully analytic SSZ waveform from first principles,
applies it to real strain, and reports likelihood differences — without using
any LIGO parameter estimation output.

```
SSZ Core (Xi, D, s)
  → rdot/P_GW correction (Ch.31, LOCKED)
  → Phase accumulation (0PN inspiral, RSG)
  → delta_psi_SSZ(f), delta_a_SSZ(f)
  → h_SSZ(f) = h_GR(f) * (1 + delta_a) * exp(i * delta_psi)
  → H1 / L1 strain comparison
  → Residuals + lnL + MF-SNR
```

---

## Contributors

| Name | Role |
|------|------|
| **Carmen Wrede** | Theory Development — SSZ framework, formula derivation, physics interpretation |
| **Lino Casu** | Programming & Testing — pipeline implementation, test suite, data analysis |

---

## Data Source

Real LIGO strain data from the **GWOSC O4b public release**:

> **GW240925 + GW250207 — O4b Data Release**  
> Zenodo: [https://zenodo.org/records/18600070](https://zenodo.org/records/18600070)  
> DOI: 10.5281/zenodo.18600070

Files used (read-only, no posterior):

- `H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5`
- `L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5`

PSD estimated from off-source Welch (−500 s window, 64 s duration).  
**No posterior samples used. No PE output used. No matched-filter templates from LIGO PE.**

---

## Core SSZ Formulas

```python
# Regime-dependent Xi
Xi_weak(r)   = r_s / (2r)                           # r/r_s > 10
Xi_strong(r) = min(1 - exp(-phi * r/r_s), Xi_max)   # r/r_s < 1.8  [CANONICAL]
Xi_blend(r)  = Hermite C2 interpolation              # 1.8 < r/r_s < 2.2

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

**Key constants:** `phi = 1.6180...` (golden ratio) | `Xi_max = 0.8017` | `D_min = 0.5550`

---

## Formula Lock Status

| Formula | Status | Source |
|---------|--------|--------|
| Xi_weak, Xi_strong, D, s | **LOCKED** | SSZ Book, formula_compendium.md |
| rdot_SSZ = rdot_GR·D²/s⁴ | **LOCKED** | SSZ Book Ch.31 |
| P_GW_SSZ = P_GW_GR·D²/s² | **LOCKED** | SSZ Book Ch.31 |
| delta_psi_SSZ(f) | **DERIVED_V1_INSPIRAL_0PN_LOCKED** | algebraically exact from rdot |
| delta_a_SSZ(f) | DERIVED_V0_PROXY | D²−1 from P_GW ratio |
| h_SSZ(f) | DERIVED_V0_PROXY | V0 waveform construction |
| epsilon_220 (ringdown) | **BLOCKED_BRANCH_CONFLICT** | 3% vs 31% vs 39% — different observables |

> The 39% QNM value is a source-frame strong-field frequency ratio, not a LIGO strain observable.

---

## Pipeline Results (GW240925, H1, 20–210 Hz)

| Metric | Value | Note |
|--------|-------|------|
| lnL GR control | −3.24×10⁷ | TaylorF2 0PN analytic |
| lnL SSZ V1 | −3.24×10⁷ | V1 inspiral correction |
| delta_lnL (H1) | +5.3×10⁻⁶ | indistinguishable at 0PN |
| delta_lnL (L1) | −4.4×10⁻⁵ | L1 diagnostic only |
| MF-SNR GR | 44.2 | |
| MF-SNR SSZ (with deltaA) | 14.2 | amplitude deformation reduces template match |
| SSZ_EFFECT_ABOVE_CALIBRATION | YES | 6.3e-06 > cal spread 7.1e-08 |

**F_HIGH capped at 210 Hz** (below f_ISCO ~ 215 Hz for M~20 M☉ — within 0PN regime).

> **Note:** MF-SNR 14.2 vs 44.2 reflects that an amplitude-deformed SSZ signal
> matches poorly against an undeformed GR template. This is not a physical result —
> it shows that a proper SSZ test would require an SSZ template bank.

---

## L1 Diagnostic Results (2026-05-19)

L1 shows a reproducible bandpower excess in the trigger window.
Three independent diagnostic tests have been run:

### 1. Stationarity / Glitch / DQ
- L1 20–210 Hz bandpower ratio (trigger/off-source): **~2.28×** (H1: 0.76×)
- CBC_CAT2/CAT3 flags: **CLEAN** (no vetoed CBC glitch)
- L1_CW_CAT1: file-wide constant, not trigger-specific
- Public DQ products: **INSUFFICIENT** to fully explain the excess
- `L1_STATUS: DQ_FLAGGED_DIAGNOSTIC_ONLY`

### 2. Harmonic Oscillator / Resonance Test
- L1 trigger peaks: 26, 36, 41, 53, **60**, 120 Hz
- **60 Hz + 120 Hz** = US mains frequency + 1st harmonic → persistent spectral line
- 41 Hz and 60 Hz peaks also present **500 s before the trigger** (off-source)
- H1 trigger peaks (22, 28, 40 Hz): **zero overlap** with L1
- `STATUS: RESONANCE_IN_OFF_SOURCE_TOO` — instrumental, not astrophysical

### 3. Gaussianity Artifact Gate
Whitened strain tested for 4 windows (trigger, −100s, −300s, −500s), fullband and 20–210 Hz.

| Window | L1 ex_kurtosis (bp) | H1 ex_kurtosis (bp) |
|--------|--------------------|--------------------|
| TRIGGER | +4.58 | +2.61 |
| OFF −500s | +2.86 | +6.37 |
| OFF −300s | +4.56 | +6.33 |
| OFF −100s | +4.52 | — |

- L1 trigger (4.58) ≈ L1 OFF−300s (4.56) ≈ L1 OFF−100s (4.52): **difference < 0.06**
- Non-Gaussianity is **chronic and stationarity-consistent**, not trigger-specific
- `GAUSSIANITY_ARTIFACT_GATE: FAIL_L1_NON_GAUSSIAN`
- `L1_EXCESS_CLASS: INCONCLUSIVE` (persistent detector noise, not transient)

### L1 Summary
```
L1_BROADBAND_EXCESS_EXPLAINED:    NO (open)
L1_INJECTION_CONFIRMED:           NO
L1_HARMONIC_STRUCTURE:            RESONANCE_IN_OFF_SOURCE_TOO (mains lines)
L1_GAUSSIANITY:                   STRONGLY_NON_GAUSSIAN (chronic, all windows)
L1_GAUSSIANITY_ARTIFACT_GATE:     FAIL_L1_NON_GAUSSIAN
H1_L1_COHERENCE_STATUS:           BLOCKED_BY_L1_DQ
```

---

## Anti-Circularity Protocol

| Rule | Status |
|------|--------|
| No posterior f, m, χ used | ✅ ENFORCED |
| No pSEOBNR / PE output | ✅ ENFORCED |
| GR control = analytic 0PN only | ✅ ENFORCED |
| PSD from off-source Welch | ✅ ENFORCED |
| No ringdown epsilon claim | ✅ ENFORCED |
| No QNM posterior | ✅ ENFORCED |
| SSZ_SUPPORT_CLAIM_MADE | **NO** |
| SSZ_FALSIFICATION_CLAIM_MADE | **NO** |

---

## Test Suite

```
497 PASS  |  1 xfail (expected: epsilon_220 branch conflict)  |  0 fail
```

| Test file | Status |
|-----------|--------|
| test_derived_delta_psi_v0.py | ✅ PASS |
| test_derived_delta_a_v0.py | ✅ PASS |
| test_h_ssz_v0_waveform_application.py | ✅ PASS |
| test_epsilon_220_branch_registry.py | ✅ PASS |
| test_xi_strong_branch_lock.py | ✅ PASS |
| test_08_anti_circularity.py | ✅ PASS |
| test_analytic_2pn_polarizations.py | ✅ PASS |
| test_geometric_algebra_interferometer.py | ✅ PASS |
| test_phase_transport_principle.py | ✅ PASS |
| tests/unit/ (all) | ✅ PASS |
| tests/validation/ (all) | ✅ PASS |
| tests/integration/ (all) | ✅ PASS |

---

## Repository Structure

```
src/
  ssz_ligo_tests/
    ssz_core.py              — Xi, D, s, regime detection
    constants.py             — PHI, XI_MAX, D_MIN, G, C, M_SUN
    derived_phase.py         — delta_psi_ssz (V1 0PN locked)
    derived_amplitude.py     — delta_a_ssz (V0 proxy)
    derived_waveform.py      — h_SSZ(f) construction
    ssz_inspiral.py          — rdot_SSZ, P_GW_SSZ (Ch.31 locked)
    ssz_phase.py             — phase accumulation
    ssz_ringdown.py          — QNM (BLOCKED_BRANCH_CONFLICT)
    epsilon_220_registry.py  — 3 branches, all BLOCKED
    anti_circularity.py      — observable classifier
    likelihood.py            — lnL, MF-SNR
    ligo_data.py             — read-only GWOSC HDF5 adapter
    forward_model.py         — full SSZ forward model
    equation_registry.py     — formula provenance registry
    provenance.py            — audit trail
    analytic_polarizations_2pn.py — 2PN h+/hx
    geometric_algebra_interferometer.py — GA detector model
    phase_transport.py       — photon phase transport
    source_propagation_twist.py — twist branch

  _legacy_ssz_ligo/          — archived legacy code (reference only)

tests/
  test_*.py                  — core formula tests
  unit/                      — unit tests
  validation/                — anti-circularity, book-value checks
  integration/               — forward model, inspiral-phase integration

scripts/
  run_strain_pipeline.py               — full H1+L1 strain pipeline
  run_h1_l1_coherence_pipeline.py      — H1/L1 coherence check
  run_calibration_psd_sensitivity.py   — calibration/PSD sensitivity scan
  run_derived_v0_pipeline.py           — V0 strain pipeline
  run_robust_multiwindow_psd.py        — multi-window Welch PSD
  run_l1_anomaly_diagnostic.py         — L1 stationarity/DQ diagnostic
  run_l1_glitch_stationarity.py        — L1 glitch / bandpower scan
  run_l1_dq_flag_check.py              — L1 DQ bit provenance
  run_l1_harmonic_oscillator_test.py   — harmonic/resonance structure test
  run_l1_gaussianity_test.py           — whitened Gaussianity stats
  run_gaussianity_artifact_gate.py     — full artifact gate (H1+L1)
  run_dq_aware_final_status.py         — master DQ-aware status report
  run_qnm_ringdown_injection_sensitivity.py — QNM injection sensitivity
  run_twist_branch_synthetic.py        — synthetic twist branch
  run_twist_branch_2pn_synthetic.py    — 2PN twist branch
  run_ga_interferometer_synthetic.py   — GA interferometer model
  run_source_propagation_twist_synthetic.py — source propagation twist
  verify_real_ligo_tests.py            — quick verification runner
  forced_verify.py                     — forced verification suite

docs/
  DELTA_PSI_DERIVATION.md              — delta_psi formula derivation
  DELTA_PSI_V1_LOCK_ATTEMPT.md         — V1 lock attempt (0PN locked)
  DELTA_A_DERIVATION.md                — delta_a formula derivation
  H_SSZ_V0_DERIVATION.md              — h_SSZ construction
  EPSILON_220_DERIVATION_STATUS.md     — 3-branch conflict status
  EPSILON_220_BRANCH_LOCK.md           — branch classification
  QNM_OBSERVABLE_RENAMING.md           — 39%/31%/3% disambiguation
  FORMULA_BRANCH_LOCK.md               — Xi branch lock
  XI_STRONG_BRANCH_LOCK.md             — Xi_strong canonical form
  REGIME_BOUNDARY_LOCK.md              — r/rs regime boundaries
  MODEL_HISTORY.md                     — model version history
  SSZ_LIGO_OBSERVABLE_BRANCH_MATRIX.md — full observable branch matrix
  SSZ_LIGO_PHASE_TRANSPORT_PRINCIPLE.md — phase transport derivation
  SSZ_GEOMETRIC_ALGEBRA_INTERFEROMETER_MODEL.md — GA detector model
  SSZ_TWIST_ANHOLONOMY_BRANCH.md       — twist/anholonomy branch
  ANALYTIC_2PN_POLARIZATION_CONTROL.md — 2PN polarization control

reports/
  FINAL_INTERPRETATION_LOCK.md         — locked interpretation (2026-05-18)
  DQ_AWARE_FINAL_LIGO_STATUS.md        — master DQ gate
  DERIVED_FORMULAS_CODE_CONSISTENCY_AUDIT.md
  H1_L1_COHERENCE_PIPELINE_REPORT.md
  CALIBRATION_PSD_SENSITIVITY_REPORT.md
  ANTI_CIRCULARITY_FINAL_GATE.md
  L1_ANOMALY_DIAGNOSTIC_REPORT.md
  L1_20_210HZ_GLITCH_STATIONARITY_REPORT.md
  L1_DQ_FLAG_CHECK_REPORT.md
  L1_HARMONIC_OSCILLATOR_TEST.md       — harmonic/resonance test (2026-05-19)
  L1_GAUSSIANITY_TEST.md               — gaussianity stats (2026-05-19)
  GAUSSIANITY_ARTIFACT_GATE_REPORT.md  — artifact gate (2026-05-19)
  ROBUST_MULTIWINDOW_PSD_REPORT.md
  QNM_3PCT_SENSITIVITY_FINAL_REPORT.md
  OBSERVABLE_BRANCH_TEST_READINESS.md
  NEXT_PHYSICS_DERIVATION_TASKS.md     — open physics agenda

data_manifest/
  gaussianity_summary_stats.csv        — per-window Gaussianity statistics
  gaussianity_test_windows.csv         — window manifest
```

---

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
pip install -e .
```

**Requirements:** `numpy`, `scipy`, `h5py`, `pytest`  
Optional (plots): `matplotlib`

---

## Running Tests

```bash
pytest                                            # full suite (497 pass, 1 xfail)
pytest tests/unit/                                # unit tests only
pytest tests/validation/                          # anti-circularity + book checks
pytest tests/test_xi_strong_branch_lock.py        # Xi branch lock
pytest tests/test_epsilon_220_branch_registry.py  # epsilon_220 blocked (xfail)
```

---

## Running Diagnostic Scripts

All scripts require the GWOSC HDF5 data files at the path configured inside each script.

```bash
# Full strain pipeline (H1 + L1)
python scripts/run_strain_pipeline.py

# L1 harmonic oscillator / resonance structure test
python scripts/run_l1_harmonic_oscillator_test.py

# L1 + H1 Gaussianity artifact gate
python scripts/run_gaussianity_artifact_gate.py

# L1 stationarity / glitch / bandpower diagnostic
python scripts/run_l1_glitch_stationarity.py

# DQ-aware master status report
python scripts/run_dq_aware_final_status.py
```

---

## Open Blockers Before Any Real Claim

```
PHYSICS BLOCKERS:
1. delta_psi: upgrade from 0PN to 3.5PN r(f) mapping (RSG integral, Ch.31)
2. delta_a:   scope lock — inspiral only, no merger/ringdown
3. epsilon_220: resolve 3% vs 31% vs 39% — three different observables, needs author
4. GR control: replace 0PN with matched 3.5PN TaylorF2
5. RSG detector propagation phase: not yet included

DATA QUALITY BLOCKERS:
6. L1 broadband excess: not explained — offline DQ (Omicron/iDQ/hveto) required
7. L1 harmonic structure: 60/120 Hz mains lines confirmed persistent
8. L1 Gaussianity gate: FAIL_L1_NON_GAUSSIAN (chronic, not trigger-specific)
9. H1/L1 coherence: frequency-domain coherence test needed

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
```

---

## Physical Interpretation of Current Results

The delta_lnL ~ 0 result admits three open interpretations:

- **Option A:** SSZ correction is intrinsically small in the LIGO band (weak field, r/rs >> 1 → SSZ → GR limit). This is physically expected.
- **Option B:** The V0 proxy formula for delta_psi is too coarse (kappa=1.0 exploratory, not derived from Ch.31).
- **Option C:** The true SSZ-LIGO forward term (RSG phase integral from Ch.31) has not yet been fully implemented.

None of these options has been eliminated. No claim is permitted until all physics blockers are resolved and L1 passes the artifact gate.

---

## Code Quality

```bash
flake8 src/ tests/ scripts/ --select=F401,F541,F811,F841,E722,E712
# Exit code: 0  (all critical errors resolved, 2026-05-19)
```

---

## License

ANTI-CAPITALIST SOFTWARE LICENSE v1.4

---

## Related Repositories

- [ssz-complete-documentation](https://github.com/error-wtf/ssz-complete-documentation)
- [ssz-all-tests](https://github.com/error-wtf/ssz-all-tests)
- [ssz-metric-pure](https://github.com/error-wtf/ssz-metric-pure)
- [ssz-qubits](https://github.com/error-wtf/ssz-qubits)

---

*Part of the SSZ (Segmented Spacetime) research project.*
