# Residual and Log-Likelihood Report
Generated: 2026-05-18 18:52:44

## Computation
- FFT length: 16384 samples
- df: 0.250000 Hz
- Band: 20.0–800.0 Hz

## Log-Likelihood (noise-weighted inner product)
| Model | lnL | MF-SNR | Residual RMS |
|-------|-----|--------|--------------|
| GR control (0PN) | -3.2372e+07 | 39.92 | 8.502e-22 |
| SSZ V0-proxy     | -3.2372e+07 | 40.27 | 8.502e-22 |

**delta_lnL (SSZ - GR) = -4.4703e-08**

## Interpretation
- |delta_lnL| < 1: INDISTINGUISHABLE
- GR control is 0PN only (GR_CONTROL_TEMPLATE_LIMITED)
- SSZ uses V0 proxy (SSZ_FORWARD_V0_PROXY)
- Neither result constitutes a physics claim

## Mandatory Statements
```
READY_FOR_REAL_SSZ_CLAIM:      NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
POSTERIOR_RF_TEST:             INVALID_FOR_SSZ
```

## Status
**PASS_NUMERICAL** — residuals and lnL computed without error
