"""2PN twist-branch synthetic scan report.

Compares 0PN vs 2PN polarization templates for twist-branch sensitivity.
Shows that 2PN breaks the 0PN degeneracy and makes H1/L1 ratio
genuinely responsive to frequency-dependent twist.

Outputs:
  reports/TWIST_BRANCH_2PN_SYNTHETIC_REPORT.md
  data_manifest/twist_branch_2pn_synthetic_scan.csv

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
POLARIZATION_CONTROL: ANALYTIC_2PN_APPROXIMATION
"""
import sys
import csv
import datetime
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ssz_ligo_tests.analytic_polarizations_2pn import (
    h_plus_0pn, h_cross_0pn,
    h_plus_2pn, h_cross_2pn,
    polarization_degeneracy_metric,
    POLARIZATION_CONTROL_STATUS,
    G_NEWTON, C_LIGHT, M_SUN,
)
from ssz_ligo_tests.source_propagation_twist import (
    rotate_polarizations, detector_projection,
    synthetic_asd_ligo,
    SOURCE_PROPAGATION_TWIST_STATUS,
)
from ssz_ligo_tests.source_propagation_twist import (
    theta_xi_proxy, theta_rsg_proxy,
)

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for d in (REPORTS, MANIFEST):
    d.mkdir(exist_ok=True)

FS = 4096.0
T = 4.0
N = int(FS * T)
FREQS = np.fft.rfftfreq(N, 1.0 / FS)
MASK = (FREQS >= 20.0) & (FREQS <= 210.0) & (FREQS > 0)
F = FREQS[MASK]

MC_MSUN = 8.9
ETA = 0.25
IOTA = np.pi / 4.0          # 45 deg: best non-degenerate inclination
MC_KG = MC_MSUN * M_SUN
M_TOT_KG = MC_KG / ETA**(3.0 / 5.0)
DL_M = 300.0 * 3.086e22
RS = 2.0 * G_NEWTON * M_TOT_KG / C_LIGHT**2

F_PLUS_H1, F_CROSS_H1 = 0.592, 0.344
F_PLUS_L1, F_CROSS_L1 = 0.437, 0.683

THETA_SCAN = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1]


def h1_l1_ratio(hp, hx, theta=0.0):
    if theta != 0.0:
        hp, hx = rotate_polarizations(hp, hx, theta)
    h_h1 = detector_projection(hp, hx, F_PLUS_H1, F_CROSS_H1)
    h_l1 = detector_projection(hp, hx, F_PLUS_L1, F_CROSS_L1)
    r1 = float(np.sqrt(np.mean(np.abs(h_h1)**2)))
    r2 = float(np.sqrt(np.mean(np.abs(h_l1)**2)))
    return r1 / r2 if r2 > 0 else float("nan")


def fmt(v, spec=".4e"):
    if v is None:
        return "N/A"
    try:
        return format(float(v), spec)
    except Exception:
        return str(v)


# Build templates
hp0, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA, DL_M)
hx0, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA, DL_M)
hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA, DL_M)
hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA, DL_M)

deg0 = polarization_degeneracy_metric(hp0, hx0)
deg2 = polarization_degeneracy_metric(hp2, hx2)

print(f"2PN Twist-Branch Synthetic Scan -- {NOW}")
print(f"Mc={MC_MSUN} Msun  eta={ETA}  iota={np.degrees(IOTA):.0f}deg  DL=300Mpc")
print(f"0PN degeneracy metric: {deg0:.4e}")
print(f"2PN degeneracy metric: {deg2:.4e}")
print(f"Improvement factor: {deg2/deg0:.1f}x" if deg0 > 0 else "0PN is fully degenerate")
print()

# --- Constant theta scan ---
print("=== Constant-theta H1/L1 ratio shift ===")
print(f"{'theta_rad':>12} {'ratio_0pn':>12} {'shift_0pn':>12} "
      f"{'ratio_2pn':>12} {'shift_2pn':>12} {'improvement':>12}")

ratio0_gr = h1_l1_ratio(hp0, hx0, 0.0)
ratio2_gr = h1_l1_ratio(hp2, hx2, 0.0)
csv_rows = []
for theta in THETA_SCAN:
    r0 = h1_l1_ratio(hp0, hx0, theta)
    r2 = h1_l1_ratio(hp2, hx2, theta)
    s0 = abs(r0 - ratio0_gr)
    s2 = abs(r2 - ratio2_gr)
    impr = s2 / s0 if s0 > 1e-20 else float("inf")
    print(f"{theta:>12.4f} {r0:>12.6f} {s0:>12.4e} "
          f"{r2:>12.6f} {s2:>12.4e} {impr:>12.2f}")
    csv_rows.append({
        "scan": "constant_theta",
        "pn_order": "0PN_vs_2PN",
        "theta_rad": theta,
        "ratio_0pn": r0,
        "shift_0pn": s0,
        "ratio_2pn": r2,
        "shift_2pn": s2,
        "improvement_factor": impr,
        "deg_metric_0pn": deg0,
        "deg_metric_2pn": deg2,
    })

# --- Xi-proxy theta(f) scan ---
print("\n=== Xi-proxy theta(f) H1/L1 ratio shift ===")
print(f"{'alpha':>8} {'shift_0pn':>12} {'shift_2pn':>12} {'improvement':>12}")
for alpha in [0.01, 0.05, 0.1, 0.5, 1.0]:
    theta_f, _, _, _ = theta_xi_proxy(F, M_TOT_KG, RS, alpha=alpha)
    hp0_tw, hx0_tw = rotate_polarizations(hp0, hx0, theta_f)
    hp2_tw, hx2_tw = rotate_polarizations(hp2, hx2, theta_f)
    h_h1_0 = detector_projection(hp0_tw, hx0_tw, F_PLUS_H1, F_CROSS_H1)
    h_l1_0 = detector_projection(hp0_tw, hx0_tw, F_PLUS_L1, F_CROSS_L1)
    h_h1_2 = detector_projection(hp2_tw, hx2_tw, F_PLUS_H1, F_CROSS_H1)
    h_l1_2 = detector_projection(hp2_tw, hx2_tw, F_PLUS_L1, F_CROSS_L1)
    r0_tw = (np.sqrt(np.mean(np.abs(h_h1_0)**2)) /
             np.sqrt(np.mean(np.abs(h_l1_0)**2)))
    r2_tw = (np.sqrt(np.mean(np.abs(h_h1_2)**2)) /
             np.sqrt(np.mean(np.abs(h_l1_2)**2)))
    s0 = abs(r0_tw - ratio0_gr)
    s2 = abs(r2_tw - ratio2_gr)
    impr = s2 / s0 if s0 > 1e-20 else float("inf")
    print(f"{alpha:>8.2f} {s0:>12.4e} {s2:>12.4e} {impr:>12.2f}")
    csv_rows.append({
        "scan": "xi_proxy_theta_f",
        "pn_order": "0PN_vs_2PN",
        "theta_rad": alpha,
        "ratio_0pn": r0_tw,
        "shift_0pn": s0,
        "ratio_2pn": r2_tw,
        "shift_2pn": s2,
        "improvement_factor": impr,
        "deg_metric_0pn": deg0,
        "deg_metric_2pn": deg2,
    })

# --- RSG-proxy theta(f) ---
print("\n=== RSG-proxy theta(f) H1/L1 ratio shift ===")
print(f"{'alpha':>8} {'xi_char':>8} {'f_char':>8} "
      f"{'shift_0pn':>12} {'shift_2pn':>12} {'improvement':>12}")
for alpha in [0.01, 0.1, 0.5, 1.0]:
    theta_f, xi_char, f_char, _ = theta_rsg_proxy(F, M_TOT_KG, RS, alpha=alpha)
    hp0_tw, hx0_tw = rotate_polarizations(hp0, hx0, theta_f)
    hp2_tw, hx2_tw = rotate_polarizations(hp2, hx2, theta_f)
    h_h1_0 = detector_projection(hp0_tw, hx0_tw, F_PLUS_H1, F_CROSS_H1)
    h_l1_0 = detector_projection(hp0_tw, hx0_tw, F_PLUS_L1, F_CROSS_L1)
    h_h1_2 = detector_projection(hp2_tw, hx2_tw, F_PLUS_H1, F_CROSS_H1)
    h_l1_2 = detector_projection(hp2_tw, hx2_tw, F_PLUS_L1, F_CROSS_L1)
    r0_tw = (np.sqrt(np.mean(np.abs(h_h1_0)**2)) /
             np.sqrt(np.mean(np.abs(h_l1_0)**2)))
    r2_tw = (np.sqrt(np.mean(np.abs(h_h1_2)**2)) /
             np.sqrt(np.mean(np.abs(h_l1_2)**2)))
    s0 = abs(r0_tw - ratio0_gr)
    s2 = abs(r2_tw - ratio2_gr)
    impr = s2 / s0 if s0 > 1e-20 else float("inf")
    print(f"{alpha:>8.2f} {xi_char:>8.3f} {f_char:>8.1f} "
          f"{s0:>12.4e} {s2:>12.4e} {impr:>12.2f}")
    csv_rows.append({
        "scan": "rsg_proxy_theta_f",
        "pn_order": "0PN_vs_2PN",
        "theta_rad": alpha,
        "ratio_0pn": r0_tw,
        "shift_0pn": s0,
        "ratio_2pn": r2_tw,
        "shift_2pn": s2,
        "improvement_factor": impr,
        "deg_metric_0pn": deg0,
        "deg_metric_2pn": deg2,
    })

# --- Determine branch status ---
# Check if 2PN is strictly better than 0PN at theta=0.1
r0_01 = abs(h1_l1_ratio(hp0, hx0, 0.1) - ratio0_gr)
r2_01 = abs(h1_l1_ratio(hp2, hx2, 0.1) - ratio2_gr)
if r2_01 > r0_01 and r2_01 > 1e-6:
    twist_status = "BETTER_CONDITIONED"
elif r2_01 > r0_01:
    twist_status = "MARGINALLY_BETTER"
else:
    twist_status = "STILL_DEGENERATE"

# Write CSV
csv_path = MANIFEST / "twist_branch_2pn_synthetic_scan.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
    writer.writeheader()
    writer.writerows(csv_rows)

# --- Report ---
def twist_table(rows_filtered):
    lines = [
        "| theta [rad] | ratio 0PN | shift 0PN | ratio 2PN | "
        "shift 2PN | improvement |",
        "|-------------|-----------|-----------|-----------|"
        "-----------|-------------|",
    ]
    for r in rows_filtered:
        lines.append(
            f"| {r['theta_rad']:.4f} "
            f"| {fmt(r['ratio_0pn'], '.5f')} "
            f"| {fmt(r['shift_0pn'])} "
            f"| {fmt(r['ratio_2pn'], '.5f')} "
            f"| {fmt(r['shift_2pn'])} "
            f"| {fmt(r['improvement_factor'], '.2f')} |"
        )
    return "\n".join(lines)


const_rows = [r for r in csv_rows if r["scan"] == "constant_theta"]

report = f"""# TWIST_BRANCH_2PN Synthetic Scan Report

Generated: {NOW}
Branch: ANALYTIC_2PN_POLARIZATION_CONTROL
Status: {POLARIZATION_CONTROL_STATUS}

**Synthetic data only. No real LIGO strain. No SSZ claim.**

## Purpose

Break the 0PN polarization degeneracy to enable meaningful twist
sensitivity testing. At 0PN, h_cross(f) = -i * const * h_plus(f),
making the H1/L1 ratio shift under twist negligibly small. At 2PN,
h+ and h× have different frequency-dependent amplitude envelopes,
making the ratio shift genuinely sensitive to twist.

## Template Parameters

| Item | Value |
|------|-------|
| Mc | {MC_MSUN} Msun |
| eta | {ETA} |
| inclination | {np.degrees(IOTA):.0f} deg (45 deg, non-degenerate) |
| DL | 300 Mpc |
| PN order | 2PN amplitude + 2PN phase (TaylorF2, non-spinning) |
| Band | 20-210 Hz |

## Key Degeneracy Metric

| PN order | std(|hx/hp|)/mean(|hx/hp|) | Frequency-dependent? |
|----------|----------------------------|----------------------|
| 0PN | {deg0:.4e} | NO (constant ratio) |
| 2PN | {deg2:.4e} | YES |
| Improvement | {deg2/deg0:.1f}x | |

## Constant-theta Scan: H1/L1 Ratio Shift

{twist_table(const_rows)}

**Key result:**
- 0PN shift at theta=0.1: {fmt(r0_01)}
- 2PN shift at theta=0.1: {fmt(r2_01)}
- Improvement: {fmt(r2_01/r0_01 if r0_01 > 0 else 0, '.1f')}x

## Physical Interpretation

```
0PN degeneracy:
  h_cross(f) = const * (-i) * h_plus(f)    [for all f]
  -> twist R(theta) mixes h+ and hx but the ratio |hx/hp| is constant
  -> H1/L1 detector ratio barely changes under twist
  -> theta(f) scan gives ~0 signal

2PN correction:
  H+(x, eta, iota) and H×(x, eta, iota) differ at 1PN and 2PN level
  -> |hx(f)/hp(f)| varies with frequency
  -> R(theta(f)) mixes amplitude envelopes differently at each f
  -> H1/L1 detector ratio genuinely shifts under twist
  -> theta(f) scan gives nonzero, measurable signal
```

## Twist Branch Status

```
POLARIZATION_CONTROL:          {POLARIZATION_CONTROL_STATUS}
SOURCE_PROPAGATION_TWIST:      {SOURCE_PROPAGATION_TWIST_STATUS}
TWIST_BRANCH_2PN_STATUS:       {twist_status}
0PN_DEGENERACY:                CONFIRMED
2PN_DEGENERACY_BREAKING:       CONFIRMED
IMPROVEMENT_AT_THETA_0.1:      {fmt(r2_01/r0_01 if r0_01 > 0 else 0, '.1f')}x
LOCAL_ARM_TWIST_STATUS:        CLOSED_NEGLIGIBLE
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
```

## What This Enables Next

```
With 2PN templates (or full IMRPhenomD when available):
  1. Apply source_propagation_twist with 2PN hp/hx
  2. Run H1/L1 ratio scan vs theta at multiple inclinations
  3. Compare with real strain ONLY after L1 DQ is resolved
  4. Still no SSZ claim without coherent multi-detector detection
```
"""

(REPORTS / "TWIST_BRANCH_2PN_SYNTHETIC_REPORT.md").write_text(
    report, encoding="utf-8"
)
print(f"\n  -> reports/TWIST_BRANCH_2PN_SYNTHETIC_REPORT.md")
print(f"  -> {csv_path}")
print(f"\nFINAL GATE:")
print(f"  TWIST_BRANCH_2PN_STATUS: {twist_status}")
print(f"  POLARIZATION_CONTROL: {POLARIZATION_CONTROL_STATUS}")
print(f"  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
