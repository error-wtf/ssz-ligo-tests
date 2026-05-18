# SSZ Forward Model Application Report
Generated: 2026-05-18 18:52:44

## LABEL: SSZ_FORWARD_V0_PROXY

## Warning
The delta_psi(f) formula used here is a V0 proxy.
Exact derivation from SSZ Book Ch.31 (RSG phase integral) is MISSING.
This result CANNOT be used for any physics claim.

## Formula Applied
```
r(f)    = (G*M / (pi*f)^2)^(1/3)   [Kepler 3rd law]
xi(r)   = xi_weak(r, rs)             [weak field: rs/(2r)]
dPsi(f) = kappa * (1 - D(xi(r)))    [kappa=1.0, locked]
h_SSZ   = h_GR * exp(i * dPsi(f))
```

## Parameters
- Total mass: 20.45 Msun
- Schwarzschild radius: 60.40 km
- kappa_phase: 1.0 (exploratory, not derived)
- Regime: weak field (r >> rs in LIGO band)

## delta_psi Statistics [20–800 Hz]
- max:  0.2858 rad
- min:  0.0331 rad
- mean: 0.1919 rad

## Blocked Items
- BLOCKED_MISSING_EQUATION: exact delta_psi from SSZ Ch.31
- BLOCKED_MISSING_EQUATION: epsilon_220 ringdown (CONFLICTING 3%/31%/39%)

## Status
**SSZ_FORWARD_V0_PROXY** — technical application only, no physics claim
