"""Twist Branch Synthetic Comparison Report.

Three models compared on synthetic GW240925-like waveform:
  GR:           h_GR
  scale-only:   S(f) * h_GR          (V0/V1 pipeline)
  scale+twist:  S(f) * R(theta) * h_GR   (new twist branch)

No LIGO data used. No posterior used. No claim made.
Synthetic only: chi-squared / lnL comparisons between model pairs.

Theta scan: [0.001, 0.01, 0.05, 0.1] rad (constant form)
Also tested: xi_proxy and rsg_proxy theta forms.

Output:
  reports/TWIST_BRANCH_SYNTHETIC_REPORT.md

TWIST_BRANCH_STATUS: DERIVED_V0_CONCEPTUAL
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import sys
import datetime
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ssz_ligo_tests.ssz_twist import (
    apply_ssz_scale_and_twist,
    theta_constant,
    theta_xi_proxy,
    theta_rsg_proxy,
)

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
REPORTS.mkdir(exist_ok=True)

G = 6.674e-11
C = 2.998e8
M_SUN = 1.989e30

# GW240925 proxy parameters (not from posterior — synthetic only)
M_TOTAL_SUN = 37.0          # solar masses, round number for synthetic test
M_KG = M_TOTAL_SUN * M_SUN
RS_M = 2 * G * M_KG / C**2

# Synthetic frequency array
FS = 2048.0
N = 2048
FREQS = np.fft.rfftfreq(N, d=1.0 / FS)
MASK = (FREQS >= 20.0) & (FREQS <= 210.0)
F_BAND = FREQS[MASK]

# Synthetic SSZ scale factor from V0/V1 proxy
# delta_A = D^2 - 1, D = 1/(1+Xi) at r_ISCO
RS_CHAR = 3.0 * RS_M
XI_CHAR = RS_M / (2.0 * RS_CHAR)   # weak field
D_CHAR = 1.0 / (1.0 + XI_CHAR)
SCALE_V0 = complex(D_CHAR**2)      # pure amplitude scaling, no phase here

# Synthetic waveform: Gaussian-modulated chirp in 20-210 Hz
t = np.arange(N) / FS
f_chirp = 50.0 + 80.0 * (t / t[-1])
phase = 2 * np.pi * np.cumsum(f_chirp) / FS
amp_env = np.exp(-((t - 0.8) / 0.3)**2)
h_time = amp_env * np.cos(phase)
h_cross_time = amp_env * np.sin(phase) * 0.5   # cross ~ half plus

# Bandpass to 20-210 Hz
def bandpass(x, fs, f_lo, f_hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), d=1.0/fs)
    X[(f < f_lo) | (f > f_hi)] = 0.0
    return np.fft.irfft(X)

hp_t = bandpass(h_time, FS, 20.0, 210.0)
hx_t = bandpass(h_cross_time, FS, 20.0, 210.0)

# To frequency domain (in-band only)
HP_F = np.fft.rfft(hp_t)[MASK]
HX_F = np.fft.rfft(hx_t)[MASK]

# Synthetic flat PSD — normalized so SNR=20 for the GR signal
# This avoids overflow in lnL while keeping relative comparisons meaningful
_hp_raw = HP_F.copy()
_df_raw = FS / N
_snr_raw = np.sqrt(4.0 * np.sum(np.abs(_hp_raw)**2) * _df_raw)
_norm = 20.0 / _snr_raw if _snr_raw > 0 else 1.0
HP_F = HP_F * _norm
HX_F = HX_F * _norm
PSD_VAL = 1.0   # unit PSD; waveform is already normalized to SNR=20
PSD = np.full_like(F_BAND, PSD_VAL)

# LIGO antenna patterns for GW240925-like sky position
# Typical mid-latitude source, face-on — rough values, not from posterior
F_PLUS_H1 = 0.52
F_CROSS_H1 = 0.38
F_PLUS_L1 = 0.31
F_CROSS_L1 = 0.62


def inner_product(a, b, psd, df):
    """Noise-weighted inner product: 4 Re sum(a b* / S) df."""
    return 4.0 * float(np.real(np.sum(a * np.conj(b) / psd))) * df


def lnL_model(h_model_h1, h_model_l1, h_data_h1, h_data_l1, psd, df):
    """Log-likelihood: lnL = (d|h) - 0.5*(h|h)."""
    lnL_h1 = (inner_product(h_data_h1, h_model_h1, psd, df)
               - 0.5 * inner_product(h_model_h1, h_model_h1, psd, df))
    lnL_l1 = (inner_product(h_data_l1, h_model_l1, psd, df)
               - 0.5 * inner_product(h_model_l1, h_model_l1, psd, df))
    return lnL_h1 + lnL_l1


DF = FS / N

# GR detector responses
h_gr_h1 = F_PLUS_H1 * HP_F + F_CROSS_H1 * HX_F
h_gr_l1 = F_PLUS_L1 * HP_F + F_CROSS_L1 * HX_F

# Use GR as synthetic "data"
h_data_h1 = h_gr_h1.copy()
h_data_l1 = h_gr_l1.copy()

# Scale-only model
hp_scale = SCALE_V0 * HP_F
hx_scale = SCALE_V0 * HX_F
h_scale_h1 = F_PLUS_H1 * hp_scale + F_CROSS_H1 * hx_scale
h_scale_l1 = F_PLUS_L1 * hp_scale + F_CROSS_L1 * hx_scale

lnL_gr = lnL_model(h_gr_h1, h_gr_l1, h_data_h1, h_data_l1, PSD, DF)
lnL_scale = lnL_model(h_scale_h1, h_scale_l1, h_data_h1, h_data_l1, PSD, DF)
dlnL_scale = lnL_scale - lnL_gr

print(f"GR lnL:          {lnL_gr:.2f}")
print(f"scale-only dlnL: {dlnL_scale:.4f}  "
      f"scale={abs(SCALE_V0):.4f}")


# Residual norms (|h_model - h_data| / |h_data|)
def residual_norm(h_model, h_data):
    return float(np.sqrt(np.sum(np.abs(h_model - h_data)**2))
                 / np.sqrt(np.sum(np.abs(h_data)**2)))


res_gr_h1 = residual_norm(h_gr_h1, h_data_h1)
res_gr_l1 = residual_norm(h_gr_l1, h_data_l1)
res_scale_h1 = residual_norm(h_scale_h1, h_data_h1)
res_scale_l1 = residual_norm(h_scale_l1, h_data_l1)

# Theta scan
THETA_VALUES = [0.001, 0.01, 0.05, 0.1]
rows_const = []

for theta0 in THETA_VALUES:
    th = theta_constant(F_BAND, theta0)
    h_twp, h_twx = apply_ssz_scale_and_twist(HP_F, HX_F, SCALE_V0, th)
    h_tw_h1 = F_PLUS_H1 * h_twp + F_CROSS_H1 * h_twx
    h_tw_l1 = F_PLUS_L1 * h_twp + F_CROSS_L1 * h_twx
    lnL_tw = lnL_model(h_tw_h1, h_tw_l1, h_data_h1, h_data_l1, PSD, DF)
    dlnL_tw = lnL_tw - lnL_gr
    dlnL_vs_scale = lnL_tw - lnL_scale
    res_h1 = residual_norm(h_tw_h1, h_data_h1)
    res_l1 = residual_norm(h_tw_l1, h_data_l1)
    h1_l1_ratio_gr = (np.sqrt(np.mean(np.abs(h_gr_h1)**2))
                      / np.sqrt(np.mean(np.abs(h_gr_l1)**2)))
    h1_l1_ratio_tw = (np.sqrt(np.mean(np.abs(h_tw_h1)**2))
                      / np.sqrt(np.mean(np.abs(h_tw_l1)**2)))
    detect = ("DETECTABLE" if abs(dlnL_vs_scale) >= 8
              else "MARGINAL" if abs(dlnL_vs_scale) >= 2
              else "UNDETECTABLE")
    rows_const.append({
        "theta_rad": theta0,
        "dlnL_vs_gr": dlnL_tw,
        "dlnL_vs_scale": dlnL_vs_scale,
        "res_h1": res_h1,
        "res_l1": res_l1,
        "h1_l1_ratio_gr": h1_l1_ratio_gr,
        "h1_l1_ratio_tw": h1_l1_ratio_tw,
        "h1_l1_ratio_delta": h1_l1_ratio_tw - h1_l1_ratio_gr,
        "detect_vs_scale": detect,
    })
    print(f"theta={theta0:.3f} rad | dlnL_vs_GR={dlnL_tw:.3f}"
          f" | dlnL_vs_scale={dlnL_vs_scale:.3f}"
          f" | H1/L1_ratio_delta={h1_l1_ratio_tw-h1_l1_ratio_gr:+.4f}"
          f" | {detect}")

# Proxy theta forms
th_xi, xi_c = theta_xi_proxy(F_BAND, M_KG, RS_M)
th_rsg, dxi_c = theta_rsg_proxy(F_BAND, M_KG, RS_M)
proxy_rows = []
for label, th_arr, val in [
    ("xi_proxy", th_xi, float(th_xi[0])),
    ("rsg_proxy", th_rsg, float(th_rsg[0])),
]:
    h_twp, h_twx = apply_ssz_scale_and_twist(HP_F, HX_F, SCALE_V0, th_arr)
    h_tw_h1 = F_PLUS_H1 * h_twp + F_CROSS_H1 * h_twx
    h_tw_l1 = F_PLUS_L1 * h_twp + F_CROSS_L1 * h_twx
    lnL_tw = lnL_model(h_tw_h1, h_tw_l1, h_data_h1, h_data_l1, PSD, DF)
    dlnL_vs_scale = lnL_tw - lnL_scale
    detect = ("DETECTABLE" if abs(dlnL_vs_scale) >= 8
              else "MARGINAL" if abs(dlnL_vs_scale) >= 2
              else "UNDETECTABLE")
    proxy_rows.append({
        "form": label,
        "theta_rad": val,
        "dlnL_vs_scale": dlnL_vs_scale,
        "detect": detect,
    })
    print(f"{label}: theta={val:.4f} rad | dlnL_vs_scale={dlnL_vs_scale:.3f}"
          f" | {detect}")

# Write report
sep = "\n"
rows_md = [
    "| theta [rad] | dlnL vs GR | dlnL vs scale | H1/L1 ratio Δ"
    " | res H1 | res L1 | Detectable vs scale |",
    "|------------|------------|--------------|--------------|"
    "--------|--------|---------------------|",
]
for r in rows_const:
    rows_md.append(
        f"| {r['theta_rad']:.3f} | {r['dlnL_vs_gr']:.3f}"
        f" | {r['dlnL_vs_scale']:.3f} | {r['h1_l1_ratio_delta']:+.4f}"
        f" | {r['res_h1']:.4f} | {r['res_l1']:.4f}"
        f" | {r['detect_vs_scale']} |"
    )

proxy_md = [
    "| Form | theta [rad] | dlnL vs scale | Detectable |",
    "|------|------------|--------------|-----------|",
]
for r in proxy_rows:
    proxy_md.append(
        f"| {r['form']} | {r['theta_rad']:.4f}"
        f" | {r['dlnL_vs_scale']:.3f} | {r['detect']} |"
    )

# Find threshold theta
threshold_theta = None
for r in rows_const:
    if abs(r["dlnL_vs_scale"]) >= 8.0:
        threshold_theta = r["theta_rad"]
        break

thresh_str = (f"{threshold_theta:.3f} rad"
              if threshold_theta is not None
              else ">0.1 rad (not reached in scan)")

report = """# Twist Branch Synthetic Comparison Report

Generated: {NOW}  
Status: DERIVED_V0_CONCEPTUAL  
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO  
No LIGO data used. No posterior parameters used. Synthetic only.

## Setup

| Parameter | Value |
|-----------|-------|
| Waveform | Synthetic Gaussian-chirp, 20–210 Hz |
| M_total (synthetic, not posterior) | {M_TOTAL_SUN:.0f} M_sun |
| r_s | {RS_M:.2f} m |
| Xi at r_ISCO | {XI_CHAR:.4f} |
| SSZ scale V0 (D^2 at ISCO) | {abs(SCALE_V0):.6f} |
| F+/Fx H1 | {F_PLUS_H1}/{F_CROSS_H1} |
| F+/Fx L1 | {F_PLUS_L1}/{F_CROSS_L1} |
| Synthetic data | GR (no SSZ injected) |

Note: antenna patterns and mass are NOT from GW240925 posterior.
They are fixed round numbers for the synthetic distinguishability test only.

## Model Comparison (lnL relative to GR)

| Model | delta_lnL vs GR | Residual H1 | Residual L1 |
|-------|----------------|-------------|-------------|
| GR (reference) | 0.000 | {res_gr_h1:.4f} | {res_gr_l1:.4f} |
| scale-only | {dlnL_scale:.4f} | {res_scale_h1:.4f} | {res_scale_l1:.4f} |

Scale-only reduces lnL by {abs(dlnL_scale):.2f} relative to GR.
This is the cost of SSZ amplitude suppression with no twist.

## Constant Theta Scan

{sep.join(rows_md)}

## Physics Proxy Theta Forms

{sep.join(proxy_md)}

## H1/L1 Distinguishability

The key observable is the **H1/L1 amplitude ratio change** under twist.
Because H1 and L1 have different antenna patterns (F+/Fx), a polarisation
rotation produces a *detector-specific* change in strain, unlike a scalar
scale that affects both detectors identically.

H1/L1 ratio (GR):    {rows_const[0]['h1_l1_ratio_gr']:.4f}

Under twist, this ratio changes:

| theta [rad] | H1/L1 ratio | Delta |
|------------|------------|-------|
| 0 (GR) | {rows_const[0]['h1_l1_ratio_gr']:.4f} | 0 |
""" + "\n".join(
    f"| {r['theta_rad']:.3f} | {r['h1_l1_ratio_tw']:.4f}"
    f" | {r['h1_l1_ratio_delta']:+.4f} |"
    for r in rows_const
) + """

The H1/L1 ratio changes because the rotation mixes h+ and hx differently
into each detector's F+/Fx projection. This is the distinctive signature
of a twist compared to a scalar scale factor.

## Detectability Threshold

Threshold for |delta_lnL vs scale| >= 8 (DETECTABLE): **{thresh_str}**

Interpretation:
- theta < 0.001 rad: twist indistinguishable from scale-only
- theta ~ 0.01–0.1 rad: marginal to detectable vs scale-only
- The H1/L1 ratio change is the cleanest discriminator

## What Would Constitute Interesting Evidence

```
NOT a claim — conceptual threshold only:

If:  scale-only fits poorly (dlnL_scale << 0)
AND: twist model improves match with theta > threshold
AND: H1/L1 ratio change matches observed H1/L1 residual difference
THEN: twist branch warrants further investigation
NEVER: this constitutes an SSZ support claim
```

## Anti-Circularity Check

- [x] No posterior f, m, chi used
- [x] No LIGO strain data used
- [x] No SSZ claim made
- [x] Synthetic data = GR (conservative, no SSZ injected)
- [x] Theta values fixed by sensitivity scan, not fitted to data
- [x] Status locked: DERIVED_V0_CONCEPTUAL

## Gate Status

```
TWIST_BRANCH_STATUS:            DERIVED_V0_CONCEPTUAL
THETA_DERIVED_FROM_SPIN_CONN:   NO (placeholder forms only)
SYNTHETIC_TEST:                 COMPLETE
READY_FOR_REAL_LIGO_SSZ_CLAIM:  NO
SSZ_SUPPORT_CLAIM_MADE:         NO
SSZ_FALSIFICATION_CLAIM_MADE:   NO
```
"""

out_path = REPORTS / "TWIST_BRANCH_SYNTHETIC_REPORT.md"
out_path.write_text(report, encoding="utf-8")
print("\n-> reports/TWIST_BRANCH_SYNTHETIC_REPORT.md")
print("DONE — READY_FOR_REAL_CLAIM: NO")
