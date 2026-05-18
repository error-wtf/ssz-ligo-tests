# SSZ-LIGO Test Suite Build Status

**Version:** 0.2.0
**Date:** 2026-05-14

## Build Status: PASS_FOR_FRAMEWORK_BUILD ✅

## Architecture

```
Strong Field → RSG Phase Accounting → Weak Field → δΨ(f) → h_SSZ(f) → Detector → Residual
```

## Modules Implemented

### Core
- `constants.py` - PHI, XI_MAX, D_MIN, G, C
- `ssz_core.py` - Ξ(r), D(r), s(r), regime detection

### RSG / Phase Accounting
- `radial_scaling.py` - ρ(r), dρ/dr, A(r), strong-to-weak blend

### Inspiral Forward Model
- `ssz_inspiral.py` - P_GW correction, ṙ correction, dφ/dr, accumulated phase
- `ssz_phase.py` - r(f) mapping, δΨ_SSZ(f)

### Detector / Likelihood
- `detector_response.py` - F⁺h₊ + Fˣhˣ
- `likelihood.py` - ln L, residuals

### Data / Anti-Circularity
- `ligo_data.py` - LIGO release scanner (read-only)
- `anti_circularity.py` - Forbidden/Allowed observables

### Registry / Status
- `equation_registry.py` - LOCKED vs MISSING vs EXPLORATORY
- `ssz_ringdown.py` - PARTIAL (3% V51, below single-event precision)

## Tests

| Test | Status |
|------|--------|
| test_radial_scaling_core.py | ✅ READY |
| test_inspiral_phase_forward_model.py | ✅ READY |
| test_strong_to_weak_transition.py | ✅ READY |
| test_ringdown_conflict_detection.py | ⚠️ PARTIAL |

## Readiness

| Capability | Status |
|------------|--------|
| Framework build | ✅ PASS |
| Synthetic dry-run | ✅ READY |
| Real LIGO numerical claim | ❌ BLOCKED |
| Ringdown numerical test | ⚠️ PARTIAL (3% exploratory) |
| Posterior R_f test | ❌ INVALID |

## Missing Before Real Claims

- δΨ_SSZ(f) full derivation (currently V0 proxy)
- δA_SSZ(f) formula
- ε_220 exact derivation (currently ~3% exploratory)
- Interferometer calibration coupling

## Next Steps

1. Run pytest suite
2. Validate δΨ magnitude on synthetic waveforms
3. Assess detectability in LIGO band
4. Resolve ringdown model branch
