# SSZ-LIGO Forward Model Test Suite v0.2

## Purpose

**Forward model from SSZ (Segmented Spacetime) to LIGO detector strain through radial scaling gauge and inspiral phase accumulation.**

This is NOT a posterior-parameter test.  
This is NOT a Kerr self-consistency test.  
This is NOT a claim engine.

This is a **physics-first** framework:
```
Strong Field Source → Radial Scaling Gauge → Phase Accounting → 
Weak Field Propagation → Interferometer Strain h(t)
```

## Core Architecture

### Three Levels

**A. Locked SSZ Core**
- Ξ(r), D(r), s(r) = 1/D(r)
- Weak/strong/blend regimes

**B. Forward-Derivable (NEW)**
- P_GW correction: D²/s²
- rdot correction: D²/s⁴
- Phase accumulation via RSG: dφ/dr = Ω/ṙ

**C. Blocked/Conflicting**
- Ringdown ε_220: **3% vs 31% vs 39% conflict**

## Key Formulas (Locked)

### SSZ Core
```python
D_SSZ(r) = 1/(1 + Ξ(r))
Ξ_weak(r) = r_s/(2r)
Ξ_strong(r) = min(1 - exp(-φr/r_s), Ξ_max)
s(r) = 1 + Ξ(r) = 1/D(r)
```

### Inspiral Forward Model
```python
# From SSZ Book Ch.31-32 (Lagrangian section)
P_GW^SSZ = P_GW^GR × D(r)² / s(r)²
ṙ_SSZ = ṙ_GR × D(r)² / s(r)⁴

# Phase accumulation
Ω(r) = √(GM/r³)
dφ/dr = Ω(r) / ṙ(r)
φ(r) = ∫ dφ/dr dr
```

### Phase to Frequency
```python
# Leading-order proxy
r(f) = (GM/(πf)²)^(1/3)
δΨ_SSZ(f) = Δφ(r(f))
```

## Anti-Circularity

**FORBIDDEN:**
- Posterior f,m,χ as observables
- Kerr as SSZ reference
- R_f = f_measured/f_Kerr (circular)

**REQUIRED:**
- Model lock before data
- Strain/residuals only
- Strong field → RSG → phase → weak field

## Ringdown Conflict ⚠️

**STATUS:** CONFLICTING_SSZ_SOURCES

| Source | Value | Origin |
|--------|-------|--------|
| A (text) | ~3% | Book Ch.30 "ca. 3%" |
| B (formula) | ~31% | Book Ch.30 "∝ D_min²" |
| C (photon sphere) | ~39% | qnm_spectrum.md |

**Resolution required before ringdown test.**

## Installation

```bash
cd E:\clone\ssz-ligo-tests
pip install -r requirements.txt
pip install -e .
```

## Running Tests

```bash
# All tests
pytest

# New architecture tests
pytest tests/unit/test_radial_scaling_core.py
pytest tests/integration/test_inspiral_phase_forward_model.py
pytest tests/integration/test_strong_to_weak_transition.py
pytest tests/validation/test_ringdown_conflict_detection.py

# Markers
pytest -m unit
pytest -m integration
pytest -m validation
```

## Status

| Component | Status |
|-----------|--------|
| Locked core | ✅ |
| Radial Scaling | ✅ |
| Inspiral phase | ✅ |
| δΨ_SSZ(f) | ✅ DRY RUN READY |
| Ringdown | ❌ BLOCKED (conflict) |
| LIGO comparison | ⏳ Pending δΨ validation |

## Documentation

- `docs/SSZ_EQUATION_REGISTRY.md`
- `docs/SSZ_LIGO_FORWARD_MODEL_SPEC.md`
- `docs/SSZ_LIGO_ANTI_CIRCULARITY_PROTOCOL.md`
- `docs/SSZ_LIGO_TEST_DESIGN.md`
- `reports/BUILD_REPORT.md`

## First Real Test

Not "SSZ true/false", but:
```
Can δΨ_SSZ(f) be reproducibly computed from locked SSZ formulas?
Is δΨ in LIGO band large or small?
Is δΨ near calibration/noise limits?
Is correction H1/L1 coherent?
```

## License

ANTI-CAPITALIST SOFTWARE LICENSE v1.4
