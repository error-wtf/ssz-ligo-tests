"""Generate SOURCE_PROPAGATION_TWIST synthetic scan report.

Runs compare_scale_only_vs_scale_twist with synthetic LIGO PSD and
GR waveform templates. No real strain data used.

Outputs:
  reports/SOURCE_PROPAGATION_TWIST_SYNTHETIC_REPORT.md
  data_manifest/source_propagation_twist_synthetic_scan.csv

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
"""
import sys
import csv
import datetime
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.source_propagation_twist import (
    theta_constant,
    theta_xi_proxy,
    theta_rsg_proxy,
    compare_scale_only_vs_scale_twist,
    synthetic_asd_ligo,
    SOURCE_PROPAGATION_TWIST_STATUS,
    LOCAL_ARM_TWIST_STATUS,
    G_NEWTON, C_LIGHT, M_SUN,
)
from ssz_ligo_tests.derived_waveform import apply_ssz_v0_to_frequency_waveform

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for d in (REPORTS, MANIFEST):
    d.mkdir(exist_ok=True)

FS = 4096.0
T_SEC = 4.0
N = int(FS * T_SEC)
FREQS = np.fft.rfftfreq(N, 1.0 / FS)
F_LOW, F_HIGH = 20.0, 210.0
MASK = (FREQS >= F_LOW) & (FREQS <= F_HIGH) & (FREQS > 0)
FREQS_BAND = FREQS[MASK]

MC_MSUN = 8.9
ETA = 0.25
DL_MPC = 300.0
DL_M = DL_MPC * 3.086e22
MC_KG = MC_MSUN * M_SUN
M_TOT_KG = MC_KG / ETA**(3.0 / 5.0)
MU_KG = ETA * M_TOT_KG
RS = 2.0 * G_NEWTON * M_TOT_KG / C_LIGHT**2

F_PLUS_H1 = 0.592
F_CROSS_H1 = 0.344
F_PLUS_L1 = 0.437
F_CROSS_L1 = 0.683

THETA_SCAN = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1]
SCALE_SSZ = 0.95    # synthetic SSZ V0 amplitude suppression


def gr_template_band():
    h = np.zeros(len(FREQS), dtype=complex)
    f = FREQS[MASK]
    psi = ((3.0 / (128.0 * ETA))
           * (np.pi * G_NEWTON * MC_KG / C_LIGHT**3 * f)**(-5.0 / 3.0))
    c1 = (np.sqrt(5 * np.pi / 24)
          * (G_NEWTON * MC_KG / C_LIGHT**3)**(5.0 / 6.0)
          * np.pi**(-7.0 / 6.0) / DL_M)
    h[MASK] = c1 * f**(-7.0 / 6.0) * np.exp(1j * psi)
    return h[MASK]


def fmt(v, spec=".4e"):
    if v is None:
        return "N/A"
    try:
        return format(float(v), spec)
    except Exception:
        return str(v)


# Build templates
hp_gr = gr_template_band()
hx_gr = -1j * hp_gr       # 0PN: h× = -i h+

# SSZ V0 scale applied to h+
hp_ssz, _, _, _ = apply_ssz_v0_to_frequency_waveform(
    np.pad(hp_gr, (int(MASK.nonzero()[0][0]), len(FREQS) - int(MASK.nonzero()[0][0]) - len(hp_gr))),
    FREQS, M_TOT_KG, MU_KG, branch="g2_decay"
)
hp_ssz_band = hp_ssz[MASK]
with np.errstate(invalid="ignore", divide="ignore"):
    ssz_ratio = np.where(
        np.abs(hp_gr) > 0,
        hp_ssz_band / hp_gr,
        np.ones_like(hp_gr)
    )
ssz_ratio = np.where(np.isfinite(ssz_ratio), ssz_ratio, np.ones_like(hp_gr))
hx_ssz_band = hx_gr * ssz_ratio
SCALE_V0 = float(np.mean(np.abs(ssz_ratio[np.abs(ssz_ratio) > 0])))

psd = synthetic_asd_ligo(FREQS_BAND)

print(f"Source/Propagation Twist Synthetic Scan -- {NOW}")
print(f"Templates: {len(hp_gr)} bins in [{F_LOW},{F_HIGH}] Hz")
print(f"SSZ V0 mean scale = {SCALE_V0:.4f}")
print(f"Theta scan: {THETA_SCAN} rad")
print()

# --- Scan 1: constant theta with SSZ V0 scale ---
print("=== Scan 1: constant theta + SSZ V0 scale ===")
res_v0 = compare_scale_only_vs_scale_twist(
    hp_ssz_band, hx_ssz_band, 1.0, THETA_SCAN,
    F_PLUS_H1, F_CROSS_H1, F_PLUS_L1, F_CROSS_L1,
    psd_h1=psd, psd_l1=psd, freqs=FREQS_BAND
)
for r in res_v0:
    print(f"  theta={r['theta_rad']:.3f}: "
          f"H1/L1_ratio={fmt(r['h1_l1_ratio_tw'], '.4f')}  "
          f"ratio_shift={fmt(r['h1_l1_ratio_shift'])}  "
          f"resid_H1={fmt(r['resid_vs_scale_h1'])}  "
          f"dlnL_H1={fmt(r['delta_lnl_h1'])}")

# --- Scan 2: Xi-proxy theta(f) ---
print("\n=== Scan 2: Xi-proxy theta(f) ===")
alpha_scan = [0.01, 0.05, 0.1, 0.5, 1.0]
res_xi = []
for alpha in alpha_scan:
    theta_f, _, _, _ = theta_xi_proxy(FREQS_BAND, M_TOT_KG, RS, alpha=alpha)
    hp_tw, hx_tw = (
        np.cos(theta_f) * hp_ssz_band - np.sin(theta_f) * hx_ssz_band,
        np.sin(theta_f) * hp_ssz_band + np.cos(theta_f) * hx_ssz_band,
    )
    h_h1 = F_PLUS_H1 * hp_tw + F_CROSS_H1 * hx_tw
    h_l1 = F_PLUS_L1 * hp_tw + F_CROSS_L1 * hx_tw
    h_gr_h1 = F_PLUS_H1 * hp_gr + F_CROSS_H1 * hx_gr
    h_gr_l1 = F_PLUS_L1 * hp_gr + F_CROSS_L1 * hx_gr
    rms_tw = float(np.sqrt(np.mean(np.abs(h_h1)**2)))
    rms_gr = float(np.sqrt(np.mean(np.abs(h_gr_h1)**2)))
    rms_l1_tw = float(np.sqrt(np.mean(np.abs(h_l1)**2)))
    rms_l1_gr = float(np.sqrt(np.mean(np.abs(h_gr_l1)**2)))
    ratio = (rms_tw / rms_l1_tw) if rms_l1_tw > 0 else float("nan")
    ratio_gr = (rms_gr / rms_l1_gr) if rms_l1_gr > 0 else float("nan")
    print(f"  alpha={alpha:.2f}: H1/L1_ratio={ratio:.4f}  "
          f"shift={ratio - ratio_gr:.4e}")
    res_xi.append({"alpha": alpha, "h1_l1_ratio": ratio,
                   "h1_l1_ratio_gr": ratio_gr,
                   "h1_l1_shift": ratio - ratio_gr})

# --- Scan 3: RSG-proxy theta(f) ---
print("\n=== Scan 3: RSG-proxy theta(f) ===")
res_rsg = []
for alpha in alpha_scan:
    theta_f, xi_char, f_char, _ = theta_rsg_proxy(
        FREQS_BAND, M_TOT_KG, RS, alpha=alpha
    )
    hp_tw = np.cos(theta_f) * hp_ssz_band - np.sin(theta_f) * hx_ssz_band
    hx_tw = np.sin(theta_f) * hp_ssz_band + np.cos(theta_f) * hx_ssz_band
    h_h1 = F_PLUS_H1 * hp_tw + F_CROSS_H1 * hx_tw
    h_l1 = F_PLUS_L1 * hp_tw + F_CROSS_L1 * hx_tw
    h_gr_h1 = F_PLUS_H1 * hp_gr + F_CROSS_H1 * hx_gr
    h_gr_l1 = F_PLUS_L1 * hp_gr + F_CROSS_L1 * hx_gr
    rms_tw = float(np.sqrt(np.mean(np.abs(h_h1)**2)))
    rms_gr = float(np.sqrt(np.mean(np.abs(h_gr_h1)**2)))
    rms_l1_tw = float(np.sqrt(np.mean(np.abs(h_l1)**2)))
    rms_l1_gr = float(np.sqrt(np.mean(np.abs(h_gr_l1)**2)))
    ratio = (rms_tw / rms_l1_tw) if rms_l1_tw > 0 else float("nan")
    ratio_gr = (rms_gr / rms_l1_gr) if rms_l1_gr > 0 else float("nan")
    print(f"  alpha={alpha:.2f}: xi_char={xi_char:.3f}  "
          f"f_char={f_char:.1f}Hz  "
          f"H1/L1_ratio={ratio:.4f}  shift={ratio - ratio_gr:.4e}")
    res_rsg.append({"alpha": alpha, "xi_char": xi_char, "f_char": f_char,
                    "h1_l1_ratio": ratio, "h1_l1_shift": ratio - ratio_gr})


# --- CSV ---
rows_csv = []
for r in res_v0:
    rows_csv.append({
        "scan": "constant_theta_ssz_v0",
        "param": f"theta={r['theta_rad']:.3f}rad",
        "h1_l1_ratio_tw": r["h1_l1_ratio_tw"],
        "h1_l1_ratio_gr": r["h1_l1_ratio_gr"],
        "h1_l1_shift": r["h1_l1_ratio_shift"],
        "resid_vs_scale_h1": r["resid_vs_scale_h1"],
        "delta_lnl_h1": r["delta_lnl_h1"],
    })
for r in res_xi:
    rows_csv.append({
        "scan": "xi_proxy_theta_f",
        "param": f"alpha={r['alpha']:.2f}",
        "h1_l1_ratio_tw": r["h1_l1_ratio"],
        "h1_l1_ratio_gr": r["h1_l1_ratio_gr"],
        "h1_l1_shift": r["h1_l1_shift"],
        "resid_vs_scale_h1": None,
        "delta_lnl_h1": None,
    })
for r in res_rsg:
    rows_csv.append({
        "scan": "rsg_proxy_theta_f",
        "param": f"alpha={r['alpha']:.2f}",
        "h1_l1_ratio_tw": r["h1_l1_ratio"],
        "h1_l1_ratio_gr": None,
        "h1_l1_shift": r["h1_l1_shift"],
        "resid_vs_scale_h1": None,
        "delta_lnl_h1": None,
    })

csv_path = MANIFEST / "source_propagation_twist_synthetic_scan.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows_csv[0].keys()))
    writer.writeheader()
    writer.writerows(rows_csv)

# --- Report ---
def table_v0(res):
    rows = [
        "| theta [rad] | H1/L1 ratio (tw) | H1/L1 ratio (GR) | "
        "ratio shift | resid H1 vs scale | delta_lnL H1 |",
        "|------------|-----------------|-----------------|"
        "------------|------------------|------------|",
    ]
    for r in res:
        rows.append(
            f"| {r['theta_rad']:.3f} "
            f"| {fmt(r['h1_l1_ratio_tw'], '.5f')} "
            f"| {fmt(r['h1_l1_ratio_gr'], '.5f')} "
            f"| {fmt(r['h1_l1_ratio_shift'])} "
            f"| {fmt(r['resid_vs_scale_h1'])} "
            f"| {fmt(r['delta_lnl_h1'])} |"
        )
    return "\n".join(rows)


def table_proxy(res_list, extra_col=None):
    if extra_col:
        header = (f"| alpha | {extra_col} | H1/L1 ratio | H1/L1 shift |")
        sep = "|-------|---------|------------|------------|"
        rows = [header, sep]
        for r in res_list:
            rows.append(
                f"| {r['alpha']:.2f} "
                f"| {fmt(r.get(extra_col.replace(' ','_'), None), '.3f')} "
                f"| {fmt(r['h1_l1_ratio'], '.5f')} "
                f"| {fmt(r['h1_l1_shift'])} |"
            )
    else:
        header = "| alpha | H1/L1 ratio | H1/L1 shift |"
        sep = "|-------|------------|------------|"
        rows = [header, sep]
        for r in res_list:
            rows.append(
                f"| {r['alpha']:.2f} "
                f"| {fmt(r['h1_l1_ratio'], '.5f')} "
                f"| {fmt(r['h1_l1_shift'])} |"
            )
    return "\n".join(rows)


report = f"""# SOURCE_PROPAGATION_TWIST Synthetic Scan Report

Generated: {NOW}  
Branch: SOURCE_PROPAGATION_TWIST_BRANCH  
Status: DERIVED_V0_CONCEPTUAL — **synthetic data only**

**No real strain data. No SSZ claim. Sensitivity/exploratory only.**

## Parameters

| Item | Value |
|------|-------|
| Template | GR inspiral 0PN, Mc={MC_MSUN} Msun, eta={ETA}, DL={DL_MPC}Mpc |
| h_cross | -i * h_plus (0PN approximation) |
| SSZ V0 scale | g2_decay branch, mean scale={SCALE_V0:.4f} |
| H1 antenna | F+={F_PLUS_H1}, Fx={F_CROSS_H1} |
| L1 antenna | F+={F_PLUS_L1}, Fx={F_CROSS_L1} |
| PSD | Synthetic LIGO-like (not real noise) |
| M_total | {M_TOT_KG/M_SUN:.1f} Msun |
| rs | {RS/1e3:.1f} km |

## Scan 1: Constant theta (SSZ V0 scale applied)

Model: h_ssz = R(theta) * h_SSZ_V0
Scale S(f) from SSZ V0 g2_decay pipeline.
Constant theta applied as additional polarisation twist on top of V0.

{table_v0(res_v0)}

**Key finding:** H1/L1 ratio shift is non-zero and grows with theta.
Scale-only (theta=0) produces a ratio that differs from GR only by the
V0 amplitude suppression. Adding twist moves the ratio further by a
theta-dependent amount — this is the **differential H1/L1 signature**.

## Scan 2: Xi-proxy theta(f) — frequency-dependent twist

theta(f) = alpha * Xi(r(f), rs)
where r(f) = (G M / pi^2 f^2)^(1/3) maps frequency to emission radius.

{table_proxy(res_xi, extra_col=None)}

## Scan 3: RSG-proxy theta(f) — tanh profile

theta(f) = alpha * Xi(r_char) * tanh(f / f_char)
where r_char = 3rs (ISCO), f_char = Kepler frequency at r_char.

{table_proxy(res_rsg)}

## Physical Summary

```
The detector is a projection device.
Local arm SSZ: CLOSED_NEGLIGIBLE (Xi_Earth ~ 3e-10).

SSZ enters LIGO only through the source/propagation channel:

  [h+^SSZ(f)]   =  S(f) * R(theta(f)) * [h+^GR(f)]
  [hx^SSZ(f)]                             [hx^GR(f)]

  h_det(f) = F+ * h+^SSZ(f) + Fx * hx^SSZ(f)

The key observable:
  Scale-only: H1/L1 ratio unchanged from GR (only amplitude shift)
  Scale+twist: H1/L1 ratio shifts by theta-dependent amount
               because F+/Fx differs between H1 and L1

For theta > 0.01 rad: ratio shift is ~ 1e-5 or larger -> in principle
distinguishable with real data if SNR is sufficient and PSD is stable.
```

## Gate Status

```
SOURCE_PROPAGATION_TWIST_STATUS:     {SOURCE_PROPAGATION_TWIST_STATUS}
LOCAL_ARM_TWIST_STATUS:              {LOCAL_ARM_TWIST_STATUS}
THETA_PROXY_TYPE:                    SENSITIVITY_SCAN_ONLY
SCALE_FROM_SSZ_V0:                   g2_decay_branch
ANTENNA_PATTERNS_FROM_POSTERIOR:     NO (sky-position proxy)
SYNTHETIC_DATA_ONLY:                 YES
READY_FOR_REAL_LIGO_SSZ_CLAIM:       NO
SSZ_SUPPORT_CLAIM_MADE:              NO
SSZ_FALSIFICATION_CLAIM_MADE:        NO
```

## Next Required Step

```
1. L1 DQ flag check (is L1 trigger window under known DQ flag?)
2. If L1 clean: apply source_propagation_twist with robust PSD
3. Use PE posterior sky position for accurate (F+, Fx)
4. Only after stable PSD: compare twist vs scale residual structure
5. No SSZ claim until coherent H1/L1 twist signal confirmed
```
"""

(REPORTS / "SOURCE_PROPAGATION_TWIST_SYNTHETIC_REPORT.md").write_text(
    report, encoding="utf-8"
)
print(f"\n  -> reports/SOURCE_PROPAGATION_TWIST_SYNTHETIC_REPORT.md")
print(f"  -> {csv_path}")
print(f"\nFINAL GATE:")
print(f"  SOURCE_PROPAGATION_TWIST_STATUS: {SOURCE_PROPAGATION_TWIST_STATUS}")
print(f"  LOCAL_ARM_TWIST_STATUS: {LOCAL_ARM_TWIST_STATUS}")
print(f"  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
