"""TWIST_BRANCH: Exploratory theta scan on real H1/L1 strain (GW240925).

Uses robust multi-window PSD (median of available off-source windows).
Compares GR, scale-only SSZ, and scale+twist SSZ for each detector.

Rules:
  - No fitting theta to data for a claim
  - Theta scan is SENSITIVITY/EXPLORATORY only
  - Best theta reported as EXPLORATORY_DIAGNOSTIC, not a detection
  - No SSZ support/falsification claim
  - READY_FOR_REAL_LIGO_SSZ_CLAIM: NO

Outputs:
  reports/TWIST_BRANCH_REAL_H1_L1_EXPLORATORY_REPORT.md
  data_manifest/twist_branch_theta_scan.csv
  logs/twist_branch_real_h1_l1.log
"""
import sys
import csv
import datetime
import numpy as np
import h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.derived_waveform import apply_ssz_v0_to_frequency_waveform

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
LOGS = Path(__file__).parent.parent / "logs"
for d in (REPORTS, MANIFEST, LOGS):
    d.mkdir(exist_ok=True)

_B = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_PATH = _B / "H1/1410334720/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
L1_PATH = _B / "L1/1410334720/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"

G = 6.674e-11
C = 2.998e8
M_SUN = 1.989e30

TRIGGER_GPS = 1411261107.984
MC_MSUN = 8.9
ETA = 0.25
DL_MPC = 300.0
DL_M = DL_MPC * 3.086e22
MC_KG = MC_MSUN * M_SUN
M_TOT_KG = MC_KG / ETA**(3.0 / 5.0)
MU_KG = ETA * M_TOT_KG

WIN_S = 4.0
F_LOW = 20.0
F_HIGH = 210.0
NPERSEG = 4096
WIN_DUR_S = 64.0

# Antenna patterns for GW240925 sky location (approximate, not from posterior)
# H1 Hanford, L1 Livingston — using sky-averaged values as proxy
# F+ and Fx from public sky-position estimate (not from PE posterior)
# alpha~2.73h, delta~-3.3deg (from alert notice, not PE)
# These are APPROXIMATE — for exploratory use only
F_PLUS_H1 = 0.592
F_CROSS_H1 = 0.344
F_PLUS_L1 = 0.437
F_CROSS_L1 = 0.683

OFF_OFFSETS = [
    ("minus500", -500.0),
    ("minus300", -300.0),
    ("minus100", -100.0),
    ("plus100",  +100.0),
    ("plus300",  +300.0),
]

THETA_SCAN = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1]

_log = []


def log(m=""):
    print(m)
    _log.append(m)


def flush_log():
    (LOGS / "twist_branch_real_h1_l1.log").write_text(
        "\n".join(_log), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_trigger(path):
    with h5py.File(str(path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur = float(f["meta/Duration"][()])
        n = f["strain/Strain"].shape[0]
        fs = int(n / dur)
        t_ev = TRIGGER_GPS - gps0
        half = WIN_S / 2.0
        i0 = max(0, int((t_ev - half) * fs))
        i1 = min(n, int((t_ev + half) * fs))
        strain = f["strain/Strain"][i0:i1].copy()
    return strain, fs, gps0


def load_off(path, gps0, fs, offset_s, dur_s):
    with h5py.File(str(path), "r") as f:
        n = f["strain/Strain"].shape[0]
        t_ev = TRIGGER_GPS - gps0
        centre = t_ev + offset_s
        j0 = max(0, int((centre - dur_s / 2.0) * fs))
        j1 = min(n, j0 + int(dur_s * fs))
        if j1 <= j0 or (j1 - j0) < NPERSEG * 2:
            return None
        arr = f["strain/Strain"][j0:j1].copy()
    return arr


def robust_psd(path, gps0, fs):
    """Median PSD from all available off-source windows."""
    psds = {}
    for lbl, offset in OFF_OFFSETS:
        arr = load_off(path, gps0, fs, offset, WIN_DUR_S)
        if arr is None:
            continue
        fp, psd = signal.welch(
            arr, fs=fs, nperseg=NPERSEG,
            window="hann", noverlap=NPERSEG // 2
        )
        if not np.any(np.isnan(psd)):
            psds[lbl] = (fp, psd)
    if not psds:
        return None, None
    all_fp = list(psds.values())[0][0]
    stack = np.array([v[1] for v in psds.values()])
    psd_med = np.nanmedian(stack, axis=0)
    return all_fp, psd_med


# ---------------------------------------------------------------------------
# Template and inner products
# ---------------------------------------------------------------------------

def gr_template(ffd):
    h = np.zeros(len(ffd), dtype=complex)
    mask = (ffd >= F_LOW) & (ffd <= F_HIGH) & (ffd > 0)
    f = ffd[mask]
    psi = (3.0 / (128.0 * ETA)) * (np.pi * G * MC_KG / C**3 * f)**(-5.0 / 3.0)
    c1 = (np.sqrt(5 * np.pi / 24)
          * (G * MC_KG / C**3)**(5.0 / 6.0)
          * np.pi**(-7.0 / 6.0) / DL_M)
    h[mask] = c1 * f**(-7.0 / 6.0) * np.exp(1j * psi)
    return h


def make_pi(ffd, fp, psd_arr):
    pi = np.interp(ffd, fp, psd_arr,
                   left=psd_arr[1], right=psd_arr[-1])
    pos = pi[(pi > 0) & np.isfinite(pi)]
    floor = float(pos.min()) if len(pos) > 0 else 1e-50
    return np.where((pi <= 0) | ~np.isfinite(pi), floor, pi)


def nwip(a, b, pi, df):
    return 4.0 * np.real(np.sum(a * np.conj(b) / pi)) * df


def mf_snr(dfd, h, pi, df):
    nn = nwip(h, h, pi, df)
    return abs(nwip(dfd, h, pi, df)) / np.sqrt(nn) if nn > 0 else 0.0


def lnl(dfd, h, pi, df):
    r = dfd - h
    return -0.5 * nwip(r, r, pi, df)


def residual_rms(dfd, h, mask):
    return float(np.sqrt(np.mean(np.abs((dfd - h)[mask])**2)))


# ---------------------------------------------------------------------------
# Apply antenna pattern projection + twist in frequency domain
# ---------------------------------------------------------------------------

def apply_detector_response(h_plus_f, h_cross_f, F_plus, F_cross,
                             scale, theta):
    """Project h+/hx onto detector with scale+twist in frequency domain.

    h_det(f) = F+ * h+^SSZ(f) + Fx * hx^SSZ(f)
    where:
      h+^SSZ = scale * (cos θ * h+^GR - sin θ * hx^GR)
      hx^SSZ = scale * (sin θ * h+^GR + cos θ * hx^GR)
    """
    c, s = np.cos(theta), np.sin(theta)
    h_plus_ssz = scale * (c * h_plus_f - s * h_cross_f)
    h_cross_ssz = scale * (s * h_plus_f + c * h_cross_f)
    return F_plus * h_plus_ssz + F_cross * h_cross_ssz


# ---------------------------------------------------------------------------
# Per-detector processing
# ---------------------------------------------------------------------------

def process_detector(label, path, F_plus, F_cross):
    log(f"\n{'='*60}")
    log(f"  DETECTOR: {label}")
    log(f"{'='*60}")

    if not path.exists():
        log("  BLOCKED: file not found")
        return None

    strain, fs, gps0 = load_trigger(path)
    if not np.all(np.isfinite(strain)) or len(strain) == 0:
        log("  BLOCKED: trigger window invalid")
        return None

    fp_rob, psd_rob = robust_psd(path, gps0, fs)
    if fp_rob is None:
        log("  BLOCKED: no usable off-source windows")
        return None

    band_med = float(np.median(psd_rob[(fp_rob >= F_LOW) & (fp_rob <= F_HIGH)]))
    log(f"  Robust PSD band_median = {band_med:.4e}")

    ffd = np.fft.rfftfreq(len(strain), 1.0 / fs)
    df = float(fs) / len(strain)
    dfd = np.fft.rfft(strain) / fs
    mask = (ffd >= F_LOW) & (ffd <= F_HIGH) & (ffd > 0)
    pi = make_pi(ffd, fp_rob, psd_rob)

    # GR template (+ polarisation; cross is 90-deg phase-shifted +)
    h_gr_plus = gr_template(ffd)
    h_gr_cross = -1j * h_gr_plus    # π/2 phase: approximate h× from h+

    # Detector-projected GR
    h_gr_det = F_plus * h_gr_plus + F_cross * h_gr_cross

    snr_gr = mf_snr(dfd, h_gr_det, pi, df)
    lnl_gr = lnl(dfd, h_gr_det, pi, df)
    rms_gr = residual_rms(dfd, h_gr_det, mask)
    log(f"  GR: SNR={snr_gr:.2f}  lnL={lnl_gr:.4e}  resid_rms={rms_gr:.3e}")

    # Scale-only SSZ
    h_ssz_base, _, _, _ = apply_ssz_v0_to_frequency_waveform(
        h_gr_plus, ffd, M_TOT_KG, MU_KG, branch="g2_decay"
    )
    # Get the amplitude+phase modification relative to h_gr_plus
    with np.errstate(invalid='ignore', divide='ignore'):
        raw_ratio = np.where(
            np.abs(h_gr_plus) > 0,
            h_ssz_base / h_gr_plus,
            np.ones(len(h_gr_plus), dtype=complex)
        )
    ssz_ratio = np.where(np.isfinite(raw_ratio), raw_ratio,
                         np.ones(len(h_gr_plus), dtype=complex))
    # Apply same ratio to cross polarisation
    h_ssz_cross = h_gr_cross * ssz_ratio

    h_scale_det = F_plus * h_ssz_base + F_cross * h_ssz_cross
    snr_sc = mf_snr(dfd, h_scale_det, pi, df)
    lnl_sc = lnl(dfd, h_scale_det, pi, df)
    rms_sc = residual_rms(dfd, h_scale_det, mask)
    log(f"  Scale-only: SNR={snr_sc:.2f}  lnL={lnl_sc:.4e}  "
        f"delta_lnL={lnl_sc-lnl_gr:.4e}  resid_rms={rms_sc:.3e}")

    # Twist scan
    theta_rows = []
    for theta in THETA_SCAN:
        h_tw_det = apply_detector_response(
            h_ssz_base, h_ssz_cross, F_plus, F_cross,
            scale=1.0, theta=theta
        )
        snr_tw = mf_snr(dfd, h_tw_det, pi, df)
        lnl_tw = lnl(dfd, h_tw_det, pi, df)
        rms_tw = residual_rms(dfd, h_tw_det, mask)
        dlnl_vs_gr = lnl_tw - lnl_gr
        dlnl_vs_sc = lnl_tw - lnl_sc
        log(f"  theta={theta:.3f}: SNR={snr_tw:.2f}  "
            f"lnL={lnl_tw:.4e}  "
            f"d_vs_GR={dlnl_vs_gr:.3e}  "
            f"d_vs_scale={dlnl_vs_sc:.3e}  "
            f"resid={rms_tw:.3e}")
        theta_rows.append({
            "detector": label,
            "theta_rad": theta,
            "snr_gr": snr_gr,
            "snr_scale": snr_sc,
            "snr_twist": snr_tw,
            "lnl_gr": lnl_gr,
            "lnl_scale": lnl_sc,
            "lnl_twist": lnl_tw,
            "delta_lnl_vs_gr": dlnl_vs_gr,
            "delta_lnl_vs_scale": dlnl_vs_sc,
            "resid_rms_gr": rms_gr,
            "resid_rms_scale": rms_sc,
            "resid_rms_twist": rms_tw,
        })

    # Best theta by lnL (exploratory diagnostic only — NOT a fit)
    best_idx = max(range(len(theta_rows)),
                   key=lambda i: theta_rows[i]["lnl_twist"])
    best_theta = theta_rows[best_idx]["theta_rad"]
    best_dlnl = theta_rows[best_idx]["delta_lnl_vs_scale"]
    log(f"  EXPLORATORY_BEST_THETA (lnL scan): {best_theta:.3f} rad  "
        f"d_vs_scale={best_dlnl:.3e}  [NOT A FIT — DIAGNOSTIC ONLY]")

    return {
        "label": label,
        "snr_gr": snr_gr,
        "lnl_gr": lnl_gr,
        "rms_gr": rms_gr,
        "snr_sc": snr_sc,
        "lnl_sc": lnl_sc,
        "rms_sc": rms_sc,
        "band_med_psd": band_med,
        "best_theta": best_theta,
        "best_dlnl": best_dlnl,
        "theta_rows": theta_rows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

log(f"Twist Branch Real H1/L1 Exploratory — {NOW}")
log(f"Trigger GPS: {TRIGGER_GPS}")
log(f"Theta scan: {THETA_SCAN} rad")
log(f"Antenna patterns - H1: F+={F_PLUS_H1} Fx={F_CROSS_H1}  "
    f"L1: F+={F_PLUS_L1} Fx={F_CROSS_L1}")
log("NOTE: Antenna patterns are approximate sky-position proxies, "
    "not from PE posterior.")

h1 = process_detector("H1", H1_PATH, F_PLUS_H1, F_CROSS_H1)
l1 = process_detector("L1", L1_PATH, F_PLUS_L1, F_CROSS_L1)

# --- H1/L1 coherence: lnL and residual ratio ---
log(f"\n{'='*60}")
log("  H1/L1 COHERENCE (twist scan)")
log(f"{'='*60}")

coherence_status = "BLOCKED"
if h1 and l1:
    log(f"  {'theta':>8}  {'H1_dlnL_vs_GR':>15}  {'L1_dlnL_vs_GR':>15}"
        f"  {'H1_dlnL_vs_sc':>15}  {'L1_dlnL_vs_sc':>15}")
    for i, theta in enumerate(THETA_SCAN):
        h1r = h1["theta_rows"][i]
        l1r = l1["theta_rows"][i]
        log(f"  {theta:8.3f}  {h1r['delta_lnl_vs_gr']:15.3e}  "
            f"{l1r['delta_lnl_vs_gr']:15.3e}  "
            f"{h1r['delta_lnl_vs_scale']:15.3e}  "
            f"{l1r['delta_lnl_vs_scale']:15.3e}")

    # Coherence: both detectors should prefer same theta range
    h1_best = h1["best_theta"]
    l1_best = l1["best_theta"]
    log(f"\n  H1 exploratory best theta: {h1_best:.3f} rad")
    log(f"  L1 exploratory best theta: {l1_best:.3f} rad")
    theta_agree = abs(h1_best - l1_best) < 0.05
    log(f"  Best-theta agreement (< 0.05 rad): {theta_agree}")

    h1_snr_ok = h1["snr_gr"] < 200
    l1_snr_ok = l1["snr_gr"] < 200

    if h1_snr_ok and l1_snr_ok and theta_agree:
        coherence_status = "TWIST_EXPLORATORY_PASS"
    elif h1_snr_ok and not l1_snr_ok:
        coherence_status = "TWIST_PARTIAL_L1_SNR_ANOMALY"
    elif not h1_snr_ok and not l1_snr_ok:
        coherence_status = "TWIST_BLOCKED_SNR_ANOMALY_BOTH"
    else:
        coherence_status = "TWIST_PARTIAL"

log(f"\n  COHERENCE_STATUS: {coherence_status}")

# --- Write CSV ---
all_rows = []
for res in [h1, l1]:
    if res:
        all_rows.extend(res["theta_rows"])

csv_path = MANIFEST / "twist_branch_theta_scan.csv"
if all_rows:
    fields = list(all_rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)
    log(f"\n  -> {csv_path}")


def fmt(v, spec=".4e"):
    if v is None:
        return "N/A"
    try:
        return format(float(v), spec)
    except Exception:
        return str(v)


def theta_table(res, label):
    if not res:
        return f"BLOCKED ({label} file not found)"
    rows = ["| theta [rad] | SNR_twist | lnL_twist | Δ_vs_GR | Δ_vs_scale |",
            "|------------|-----------|-----------|---------|------------|"]
    for r in res["theta_rows"]:
        rows.append(
            f"| {r['theta_rad']:.3f} | {fmt(r['snr_twist'], '.2f')} "
            f"| {fmt(r['lnl_twist'])} | {fmt(r['delta_lnl_vs_gr'])} "
            f"| {fmt(r['delta_lnl_vs_scale'])} |"
        )
    return "\n".join(rows)


report = """# TWIST_BRANCH Real H1/L1 Exploratory Report

Generated: {NOW}  
Event: GW240925 (trigger GPS {TRIGGER_GPS})  
Branch: TWIST_BRANCH / SOURCE_PROPAGATION  
Status: EXPLORATORY_DIAGNOSTIC — no claim

**No fitting. No claim. Theta scan is a sensitivity/exploratory diagnostic.**

## Model

```
h_det(f) = F+ h+^SSZ(f) + Fx hx^SSZ(f)

h+^SSZ = S(f) * [cos θ * h+^GR - sin θ * hx^GR]
hx^SSZ = S(f) * [sin θ * h+^GR + cos θ * hx^GR]

S(f): SSZ V0 amplitude+phase (g2_decay branch)
θ:    constant polarisation twist [rad] — sensitivity scan
```

Antenna patterns (approximate, sky-position proxy only, not PE posterior):
- H1: F+ = {F_PLUS_H1}, Fx = {F_CROSS_H1}
- L1: F+ = {F_PLUS_L1}, Fx = {F_CROSS_L1}

## H1 Results

GR baseline: SNR = {fmt(h1['snr_gr'] if h1 else None, '.2f')}  
Scale-only:  SNR = {fmt(h1['snr_sc'] if h1 else None, '.2f')}, ΔlnL vs GR = {fmt((h1['lnl_sc']-h1['lnl_gr']) if h1 else None)}  
Robust PSD band_median: {fmt(h1['band_med_psd'] if h1 else None)}

{theta_table(h1, 'H1')}

Exploratory best theta (lnL scan): {fmt(h1['best_theta'] if h1 else None, '.3f')} rad — **DIAGNOSTIC ONLY**

## L1 Results

GR baseline: SNR = {fmt(l1['snr_gr'] if l1 else None, '.2f')}  
Scale-only:  SNR = {fmt(l1['snr_sc'] if l1 else None, '.2f')}, ΔlnL vs GR = {fmt((l1['lnl_sc']-l1['lnl_gr']) if l1 else None)}  
Robust PSD band_median: {fmt(l1['band_med_psd'] if l1 else None)}

{theta_table(l1, 'L1')}

Exploratory best theta (lnL scan): {fmt(l1['best_theta'] if l1 else None, '.3f')} rad — **DIAGNOSTIC ONLY**

## H1/L1 Coherence

| Quantity | Value |
|---------|-------|
| H1 best theta (exploratory) | {fmt(h1['best_theta'] if h1 else None, '.3f')} rad |
| L1 best theta (exploratory) | {fmt(l1['best_theta'] if l1 else None, '.3f')} rad |
| H1 SNR GR | {fmt(h1['snr_gr'] if h1 else None, '.2f')} |
| L1 SNR GR | {fmt(l1['snr_gr'] if l1 else None, '.2f')} |
| COHERENCE_STATUS | {coherence_status} |

## Physical Interpretation

The twist branch adds an SO(2) rotation of (h+, hx) before projection:

- If θ = 0: reduces to scale-only model
- If θ > 0: h+ leaks into hx and vice versa; different (F+, Fx) at H1 vs L1
  means the two detectors see DIFFERENT amounts of twist
- This is the key observable: scale-only modifies both equally;
  twist produces a differential F+/Fx projection shift

If L1 has SNR anomaly (known from robust PSD recheck), its lnL values
are not reliable. H1 results are the primary diagnostic in that case.

The exploratory best theta is NOT a measurement. It is the theta value
that maximises lnL in the scan. Without proper null-hypothesis testing
and confidence intervals, this cannot be interpreted as a detection.

## Next Required Step

```
1. L1 DQ flag check (is L1 trigger window under known DQ flag?)
2. If L1 is flagged: H1-only analysis becomes primary
3. If L1 is clean: repeat with longer off-source window (1000s+ pre-merger)
4. Only after stable PSD: compare twist vs scale-only residual structure
```

## Gate Status

```
TWIST_REAL_DATA_STATUS:         {coherence_status}
H1_SNR_ANOMALY:                 {'YES' if h1 and h1['snr_gr'] >= 200 else 'NO'}
L1_SNR_ANOMALY:                 {'YES' if l1 and l1['snr_gr'] >= 200 else 'NO'}
ANTENNA_PATTERNS_FROM_POSTERIOR: NO (approximate sky-position proxy)
THETA_FIT_TO_DATA:              NO (scan only)
EXPLORATORY_DIAGNOSTIC_ONLY:    YES
READY_FOR_REAL_LIGO_SSZ_CLAIM:  NO
SSZ_SUPPORT_CLAIM_MADE:         NO
SSZ_FALSIFICATION_CLAIM_MADE:   NO
```
"""

(REPORTS / "TWIST_BRANCH_REAL_H1_L1_EXPLORATORY_REPORT.md").write_text(
    report, encoding="utf-8"
)
log("  -> reports/TWIST_BRANCH_REAL_H1_L1_EXPLORATORY_REPORT.md")

flush_log()
log("  -> logs/twist_branch_real_h1_l1.log")
log(f"\nFINAL GATE: {coherence_status}")
log("READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
