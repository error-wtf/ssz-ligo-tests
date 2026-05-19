# SSZ-LIGO Forward Model Test Suite

**Version:** 0.4.0 — 2026-05-19  
**Event:** GW240925 (O4b, GWOSC public release)  
**Status:** `PIPELINE_STATUS: PASS_EXPLORATORY` | `READY_FOR_REAL_LIGO_SSZ_CLAIM: NO`

---

> **Core methodological position:**
> We distinguish measured detector strain from model-conditioned inference products.
> Component masses, chirp mass, spins, and QNM parameters are not directly measured
> observables — they are outputs of a GR/CBC or Kerr-conditioned inference chain.
> Therefore they cannot serve as metric-neutral input for SSZ tests.
> **m₁ and m₂ do not exist as numbers anywhere in the detector.**

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

## Critical Open-Data and Methodology Position

### Summary

This repository does **not** claim that LIGO data are fake, manipulated, or useless.

It also does **not** claim that SSZ is confirmed or falsified by the current LIGO release data.

The central conclusion is narrower and more important:

> Public LIGO release products are useful for standard GR/CBC analyses and educational
> reproduction, but they are not sufficient, by themselves, for a fully independent,
> anti-circular test of alternative metric theories.

- LIGO measures detector strain. The strain is real measurement input.
- Many higher-level products — masses, spins, QNM frequencies, remnant parameters,
  posterior samples, Bayes factors — are **not raw observables**.
- They are outputs of model-dependent inference pipelines.
- If those outputs are used as independent proof of the same model assumptions
  that produced them, a circularity problem arises.

We call this: **model-bound self-confirmation**.

The data are not meaningless. But outside the official GR/CBC pipeline, their
independent evidential power is much smaller than public communication often suggests.

**Canonical methodological statement of this project:**

> We distinguish between detector measurements and model-conditioned inference
> products. The calibrated strain is measurement input; chirp mass, component
> masses, spins, and QNM parameters are GR/CBC-conditioned estimates — not
> metric-neutral observables.

And on the L1 anomaly:

> The anomaly may be detector- or pipeline-induced. Current public GWOSC
> products are insufficient to decide whether the 20–40 Hz structure is
> instrumental, environmental, line-related, or signal-like.

---

### 1. Strain Is Data; Posterior Products Are Interpretation

LIGO measures calibrated detector strain: `h(t)`. Everything above that level is inferred.

Quantities such as `m1`, `m2`, chirp mass, final spin, QNM frequency, Bayes factors, and
posterior samples are **not directly observed in the detector**. They are estimated from
strain using waveform models, priors, noise assumptions, calibration, DQ selections, and
GR/Kerr/CBC parameter-estimation pipelines. Such products are **not metric-neutral**.

For alternative metrics, the correct test is not:
`Does SSZ match the Kerr-derived posterior?`

But:
`Can h_SSZ(f) explain the calibrated strain without using GR/Kerr posteriors as truth?`

---

### 2. The Chirp Mass Is Not a Direct Measurement

The chirp mass is mathematically well-motivated (not arbitrary):

```text
M_chirp = (m1 * m2)^(3/5) / (m1 + m2)^(1/5)
```

It governs the GR inspiral rate: `df/dt ∝ M_chirp^(5/3) * f^(11/3)`.

However, `m1` and `m2` are **not directly measured object properties**. They are
model-inferred from Bayesian template matching.

| Layer | What it is | Status |
|-------|-----------|--------|
| `h(t)` — strain | Raw observable | Directly measured |
| `M_chirp`, `m1`, `m2`, `chi` | GR/CBC Bayesian posterior | Model-dependent |
| `f_QNM`, `tau_QNM` — ringdown | Inferred under Kerr assumption | Model-dependent |

**`m1` and `m2` do not exist as numbers anywhere in the detector.**

Correct: *"Under GR/CBC assumptions, the strain is consistent with a source having
this inferred chirp mass."*

Not valid: *"The detector directly measured this chirp mass as a metric-neutral fact."*

---

### 3. The Circularity Problem

```text
1. Assume GR/Kerr/CBC waveform models.
2. Search strain with GR/Kerr/CBC templates.
3. Estimate masses, spins, QNMs via GR/Kerr/CBC parameter estimation.
4. Publish those posterior products.
5. Treat them as independent evidence that GR/Kerr/CBC is correct.
```

This does not mean the experiment is fraudulent. It means the evidential scope must be
stated honestly. The pipeline shows: *"Data are consistent with GR/CBC."* It cannot
alone prove: *"All alternative metric models are excluded."* For that, alternative models
need their own strain-level forward models tested directly against calibrated strain.

---

### 4. Open Data vs. Open Reproducibility

The public GWOSC releases are open in a formal sense — calibrated strain, some metadata,
some DQ bits, posterior products, tutorials. But this is **not** the same as full open
reproducibility.

For a fully independent non-GR test, one also needs:

```text
Omicron triggers      iDQ products          offline DQ reports
auxiliary channels    line lists            known instrumental couplings
calibration details   state-vector context  detector-characterization decisions
```

Without these, external groups cannot independently decide whether an anomaly is a signal,
a known glitch, an unvetoed transient, a line, a calibration feature, a whitening artifact,
or a seismic coupling.

We distinguish **formal open data** from **full open reproducibility**.

---

### 5. Why Public LIGO Products Are Not Enough for SSZ

SSZ is an alternative metric framework. A valid SSZ-LIGO test **cannot** use GR/Kerr
posterior parameters as neutral input.

Circular inputs:

```text
Kerr QNM posteriors     GR remnant mass/spin posteriors
pSEOBNR samples         PE-derived QNM frequencies as ground truth
```

Valid inputs start at strain level:

```text
calibrated H1/L1 strain     independent PSD + whitening
independent artifact gates  SSZ forward model h_SSZ(f)
direct residual / likelihood comparison
```

This is the **anti-circular principle** of this project.

---

### 6. GW240925 — What the Pipeline Found

The pipeline built and tested: PSD estimation, H1/L1 diagnostics, Gaussianity, line/notch,
STFT/Omicron-lite, phase-randomization, DQ-bit provenance, H1-only exploratory,
synthetic SSZ branches, source-propagation twist, and phase-transport formalism.

Key empirical finding:

```text
L1 non-Gaussianity concentrated in 20-40 Hz sub-band.
Trigger excess kurtosis:  +44.9  vs. off-source -500s: +1.1
Delta = +43.7 -- trigger-specific, not chronic broadband.
```

Classification:

```text
H1: USABLE_EXPLORATORY      L1: DIAGNOSTIC_ONLY
H1/L1 coherence: BLOCKED    SSZ claim: NO    SSZ falsification: NO
```

Public products are insufficient to decide whether the L1 behavior is caused by
low-frequency detector noise, seismic coupling, suspension/control system, unvetoed
transient, line contamination, or filtering artifacts. Offline Omicron/iDQ/AUX needed.

---

### 7. What the L1 Anomaly Does and Does Not Mean

Does **not** mean:
`LIGO data are fake` / `GW240925 is not real` / `SSZ is confirmed or falsified` / `LIGO manipulated data`

Does mean:
`The released public data are not sufficient for a broadband non-GR H1/L1 coherence test.`

> The L1 behavior is technically reproducible but not sufficiently explained by public
> release DQ products. Without offline Omicron/iDQ/line/AUX context, L1 cannot be used
> for a claim-level broadband non-GR coherence test.

---

### 8. Detector Strain Is Not a Telescope Observable

For telescope SSZ tests, one may compare redshift, emission lines, or lensing. LIGO is
different — it measures local interferometer strain: laser phase differences, arm
projections, detector response, noise-weighted strain.

A valid SSZ-LIGO model must describe how SSZ affects source-frame emission, propagation,
phase transport, polarization/twist, detector projection, and calibrated strain.
The relevant target is `h_SSZ(f)`, not a Kerr-derived posterior table.

---

### 9. Phase Transport and Co-Scaling

If the detector, arms, optics, and local rulers co-scale, a pure local scale factor is
not directly observable. What is observable is the relative phase accumulated by photons:
`DeltaPhi = Phi_x - Phi_y`. Therefore SSZ-LIGO must be formulated as a phase-transport /
relative-holonomy problem. The local arm-length correction was found to be negligible.

The relevant signal chain:

```text
source / strong-field geometry
  -> SSZ scale and twist
  -> propagation
  -> polarization / phase transport
  -> detector projection
  -> strain residual
```

---

### 10. Source-Propagation Twist Branch

```text
[h_plus_SSZ, h_cross_SSZ]^T  =  S(f) * R(theta) * [h_plus_GR, h_cross_GR]^T
```

where `S(f)` = scale contribution, `R(theta)` = polarization/phase/frame twist.

```text
SOURCE_PROPAGATION_TWIST: synthetic pass
REAL_TWIST_SIGNAL:        not extractable from current GW240925 run
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
```

---

### 11. What the Current Data Can and Cannot Be Used For

**Can be used for:**
`pipeline construction` / `PSD estimation` / `H1/L1 diagnostics` / `Gaussianity tests`
`line/notch analysis` / `STFT/Omicron-lite` / `background estimates`
`H1-only exploratory tests` / `synthetic SSZ validation` / `methodological demonstrations`

**Cannot currently be used for:**
`a final SSZ claim` / `a final SSZ falsification` / `a metric-neutral QNM test`
`a claim-level H1/L1 non-GR coherence test without offline DQ/Omicron/iDQ`

---

### 12. What We Need from LIGO

```text
Omicron triggers for the relevant GPS windows
iDQ information and offline DQ reports
line lists and known instrumental couplings
auxiliary-channel context
calibration uncertainty context
state-vector interpretation
detector-characterization notes for the 20-40 Hz band
```

Concise question to LIGO:

> We cannot treat current PE/QNM posterior products as metric-neutral for our
> non-GR forward-model test. H1 is usable for exploratory validation, but L1 shows
> unresolved low-frequency DQ context in the 20-40 Hz band (excess kurtosis +44.9
> at trigger vs. +1.1 off-source). Are offline DQ/iDQ/Omicron/line products
> available, or should L1 be treated as diagnostic-only for broadband non-GR tests?

---

### 13. Public Petition / Transparency Context

A public petition questioning aspects of the LIGO experiment is not, by itself, scientific
proof that LIGO is wrong. However, it is relevant as a transparency signal.

```text
petition = transparency and trust signal
not:
petition = physical disproof of LIGO
```

This project does not use any petition as evidence against LIGO. It uses the existence
of public scrutiny as evidence that reproducibility limits deserve serious attention.

---

### 14. Political / Funding-Relevant Interpretation

For policymakers: the key issue is not whether LIGO is fake. The key issue is whether
publicly funded large-scale science should provide enough data and context for independent
verification outside the collaboration's preferred model family.

Current situation:

```text
Open data:                       yes, in a limited formal sense
Open reproducibility:            only partially
Open alternative-model testing:  strongly limited
```

If public money funds the experiment, then public releases should clearly state: what the
data can prove, what they cannot prove, which products are model-dependent, and which
detector-characterization products are missing. Without that clarity, "open data" can
create an impression of complete openness while leaving decisive non-standard checks
impossible. That is not strong open science.

**Sharpest fair summary:**

> This is not full open science; it is partial open-data access around a largely
> collaboration-controlled inference context.

Or in the language of the data layers:

```text
Open enough to reproduce their story.
Not open enough to independently challenge the story.
```

---

### 15. Final Position

```text
LIGO strain is real measurement input.
LIGO posterior products are model-dependent outputs.
The public releases are useful but incomplete for anti-circular non-GR tests.
GW240925 is useful for pipeline and artifact-gate development.
GW240925 is not sufficient for a final SSZ test.
L1 remains diagnostic-only without offline DQ/Omicron/iDQ clarification.
No SSZ support claim is made.
No SSZ falsification claim is made.
```

The strongest fair criticism:

> The public LIGO releases are formally open, but not fully open in the sense required
> for independent alternative-metric reproducibility. They allow standard analyses to be
> reproduced, but they do not always provide enough detector-characterization context for
> external groups to independently test non-GR forward models at claim level.

This is the central methodological result of this project.

---

### 16. What We Can and Cannot Say — Precisely

This section separates claims by evidential strength.

**What we can say with confidence:**

```text
1. We built and ran a reproducible, anti-circular LIGO strain pipeline.
2. It uses real H1 GWOSC strain, off-source PSD, an analytic GR control
   template, and an SSZ V0/V1 forward proxy.
3. It does NOT use PE posteriors, PE-derived PSD, or Kerr self-tests.
4. PE/QNM posterior-based R_f tests are methodologically invalid for SSZ
   because posterior products are model-dependent.
5. The anti-circularity gate explicitly marks posterior samples, PE-PSD,
   and pSEOBNR products as invalid inputs; strain, off-source PSD, and
   the SSZ V0 proxy were used instead.
6. Formal open data is not the same as full open reproducibility.
```

**What we can say about SSZ/LIGO:**

```text
The current V0/V1 strain pipeline produces no measurable deviation
from the GR control template in the tested range:

  delta_lnL ~= 0
  |delta_lnL| < 1  ->  indistinguishable

This does NOT mean SSZ is confirmed.
This does NOT mean SSZ is falsified.
It means:
  With the current V0/V1 inspiral forward proxy and the limited
  0PN GR control, SSZ is indistinguishable in this setup.
```

**What we can say about GW240925:**

```text
H1: USABLE_EXPLORATORY
L1: DIAGNOSTIC_ONLY
  -> reproducible 20-40 Hz non-Gaussianity
  -> trigger excess kurtosis: +44.9  vs. off-source: +1.1
  -> trigger-specific, not chronic broadband
  -> without Omicron/iDQ/offline DQ: not claimable

GW240925 tests the method. It does not adjudicate SSZ.
```

**What we must NOT say:**

```text
SSZ is confirmed by LIGO.
SSZ is falsified by LIGO.
LIGO data are fake.
LIGO manipulated the results.
The 39% branch is refuted.
L1 shows SSZ.
```

**Best public short statement:**

> We built an anti-circular strain-level pipeline for SSZ-like non-GR
> forward models. PE/QNM posteriors are not used as metric-neutral
> observables. For GW240925, H1 is usable exploratorily; L1 remains
> diagnostic-only due to reproducible 20-40 Hz non-Gaussianity without
> offline Omicron/iDQ/DQ context. The current V0/V1 SSZ pipeline is
> technically operational but not at claim level.

---

### 17. Paper-Ready Status Statement

> GW240925 supports method validation, not physical adjudication of SSZ.
> The strain-level pipeline is reproducible and anti-circular, but the
> event is DQ-limited for H1/L1 non-GR coherence tests, and the SSZ
> interferometer forward model remains V0/V1, not LOCKED_FINAL.

This is the most defensible single-sentence summary of the project's current state.

**The data access hierarchy:**

| Level | What it is | Publicly available | Sufficient for non-GR test |
|-------|-----------|--------------------|--------------------------|
| Level 1: Strain `h(t)` | Calibrated interferometer output | Yes (GWOSC) | Partially |
| Level 2: DQ bits CAT1-3 | Standardized quality flags | Yes (GWOSC) | Partially |
| Level 3: Omicron / iDQ | Glitch triggers, glitch probability | No (internal / AR only) | Yes, critical |
| Level 4: Aux channels | Environmental/control monitors | Very limited | Often needed |
| Level 5: Posteriors, QNM | GR/Kerr model-inferred parameters | Yes (GWOSC) | **NOT metric-neutral** |

The public LIGO release is strong at Level 1-2 and 5, but weak at Level 3-4.
For standard GR/CBC: Level 1-2 is sufficient.
For anti-circular non-GR tests: Level 3-4 is often decisive, and Level 5 is methodologically invalid as input.

---

### 18. Petition / Public Criticism Context

**Reference:** LIGO official Mastodon post (scicomm.xyz):
[https://chaos.social/deck/@LIGO@scicomm.xyz/116569194588841654](https://chaos.social/deck/@LIGO@scicomm.xyz/116569194588841654)

A public petition signed by ~3000 people questioning aspects of the LIGO
experiment (including researchers) is not, by itself, scientific proof that
LIGO is wrong. It is a **transparency and trust signal**.

```text
petition = transparency and trust signal
not:
petition = physical disproof of LIGO
```

The right way to evaluate it:

```text
Which technical questions does it raise?
Which are already answered by official LIGO/GWOSC documentation?
Which reflect misunderstandings?
Which point to real reproducibility gaps?
Which require unavailable Omicron/iDQ/Aux/Offline-DQ products to answer?
```

This project does not use the petition as evidence against LIGO. It uses the
existence of organized public scrutiny as evidence that:

> The boundaries between what LIGO data can prove and what requires
> collaboration-internal context deserve clearer public communication.

For policymakers and funders, the issue is not whether LIGO is fraudulent.
The issue is whether a publicly funded experiment provides enough material
for independent verification outside its preferred model family.

**The epistemic asymmetry:**

```text
Formal openness:  strain + some metadata + posterior products available.
Actual openness:  decisive non-standard checks require Omicron/iDQ/
                  Aux/Line/Offline-DQ context not in the public release.
```

This creates an impression of complete openness while leaving specific
non-standard analyses incomplete. That is a legitimate open-science concern
— not a fraud accusation.

Strongest fair single sentence:

> The public LIGO releases are formally open but epistemically asymmetric:
> strain and derived products are available, yet central detector
> characterization, Omicron/iDQ, auxiliary channels, and offline DQ
> context are typically missing as a complete reproducibility package,
> meaning external groups can reproduce standard analyses but can only
> partially verify non-GR forward models independently.

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
