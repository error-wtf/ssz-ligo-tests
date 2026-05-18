"""Robust Multi-Window PSD Re-check for GW240925 H1 and L1.

Problem diagnosed:
  The -500s off-source window appears too quiet for L1, making
  PSD-normalised quantities (MF-SNR, bandpower ratio, lnL) artificially
  large. This script addresses that by computing a *median* PSD across
  multiple off-source windows and re-evaluating all coherence metrics.

Windows tried (offsets from trigger GPS):
  -500s, -300s, -100s, +100s, +300s  (each 64 s Welch segment)

Outputs:
  reports/ROBUST_MULTIWINDOW_PSD_REPORT.md
  reports/H1_L1_COHERENCE_RECHECK_ROBUST_PSD.md
  data_manifest/robust_psd_windows_used.csv
  logs/robust_psd_recheck.log

No LIGO claim. No posterior. No SSZ support/falsification.
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
M_TOT_KG = MC_KG / ETA**(3.0/5.0)
MU_KG = ETA * M_TOT_KG

WIN_S = 4.0
F_LOW = 20.0
F_HIGH = 210.0
NPERSEG = 4096
WIN_DUR_S = 64.0   # duration of each off-source window for Welch

# Off-source window offsets (centre of window relative to trigger)
OFF_OFFSETS = [
    ("minus500", -500.0),
    ("minus300", -300.0),
    ("minus100", -100.0),
    ("plus100",  +100.0),
    ("plus300",  +300.0),
]

_log = []


def log(m=""):
    print(m)
    _log.append(m)


def flush_log():
    (LOGS / "robust_psd_recheck.log").write_text(
        "\n".join(_log), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def load_trigger_window(path):
    """Load trigger-window strain from HDF5."""
    with h5py.File(str(path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur = float(f["meta/Duration"][()])
        n = f["strain/Strain"].shape[0]
        fs = int(n / dur)
        t_ev = TRIGGER_GPS - gps0
        half = WIN_S / 2.0
        i0 = max(0, int((t_ev - half) * fs))
        i1 = min(n, int((t_ev + half) * fs))
        strain = f["strain/Strain"][i0:i1]
    return strain.copy(), fs, gps0


def load_off_window(path, gps0, fs, offset_s, dur_s):
    """Load one off-source window centred at trigger + offset_s."""
    with h5py.File(str(path), "r") as f:
        n = f["strain/Strain"].shape[0]
        t_ev = TRIGGER_GPS - gps0
        centre = t_ev + offset_s
        j0 = max(0, int((centre - dur_s / 2.0) * fs))
        j1 = min(n, j0 + int(dur_s * fs))
        if j1 <= j0 or (j1 - j0) < NPERSEG * 2:
            return None
        arr = f["strain/Strain"][j0:j1]
    return arr.copy()


def welch_psd(arr, fs):
    fp, psd = signal.welch(
        arr, fs=fs, nperseg=NPERSEG, window="hann", noverlap=NPERSEG // 2
    )
    return fp, psd


def band_median(fp, psd):
    mask = (fp >= F_LOW) & (fp <= F_HIGH)
    return float(np.median(psd[mask]))


def band_power(arr, fs):
    """RMS^2 of band-passed signal (simple Parseval estimate)."""
    fft = np.fft.rfft(arr) / fs
    ffd = np.fft.rfftfreq(len(arr), 1.0 / fs)
    df = float(fs) / len(arr)
    mask = (ffd >= F_LOW) & (ffd <= F_HIGH)
    return float(4.0 * np.sum(np.abs(fft[mask])**2) * df)


def gr_template(ffd, Mc_kg, eta, dL_m):
    h = np.zeros(len(ffd), dtype=complex)
    mask = (ffd >= F_LOW) & (ffd <= F_HIGH) & (ffd > 0)
    f = ffd[mask]
    psi = (3.0 / (128.0 * eta)) * (np.pi * G * Mc_kg / C**3 * f)**(-5.0 / 3.0)
    c1 = (np.sqrt(5 * np.pi / 24)
          * (G * Mc_kg / C**3)**(5.0 / 6.0)
          * np.pi**(-7.0 / 6.0) / dL_m)
    h[mask] = c1 * f**(-7.0 / 6.0) * np.exp(1j * psi)
    return h


def nwip(a, b, ffd, pi, df):
    return 4.0 * np.real(np.sum(a * np.conj(b) / pi)) * df


def mf_snr(dfd, h, ffd, pi, df):
    nn = nwip(h, h, ffd, pi, df)
    if nn <= 0:
        return 0.0
    return abs(nwip(dfd, h, ffd, pi, df)) / np.sqrt(nn)


# ---------------------------------------------------------------------------
# Per-detector processing
# ---------------------------------------------------------------------------

def process_detector(label, path):
    log(f"\n{'='*60}")
    log(f"  DETECTOR: {label}")
    log(f"{'='*60}")

    if not path.exists():
        log(f"  BLOCKED: {path} not found")
        return None

    strain_on, fs, gps0 = load_trigger_window(path)
    if not np.all(np.isfinite(strain_on)) or len(strain_on) == 0:
        log("  BLOCKED: trigger window not finite")
        return None

    log(f"  GPS0={gps0}  t_ev={TRIGGER_GPS-gps0:.1f}s  fs={fs}Hz")
    log(f"  Trigger window: {len(strain_on)} samples = {len(strain_on)/fs:.3f}s")

    # --- Per-window Welch PSDs ---
    log(f"\n  Off-source window PSDs ({WIN_DUR_S}s each):")
    psds = {}
    window_rows = []
    for win_label, offset in OFF_OFFSETS:
        arr = load_off_window(path, gps0, fs, offset, WIN_DUR_S)
        if arr is None:
            log(f"    {win_label:12s}: OUTSIDE FILE or TOO SHORT — skipped")
            window_rows.append({
                "detector": label, "window": win_label,
                "offset_s": offset, "status": "OUTSIDE",
                "psd_median": "N/A", "bandpower": "N/A",
            })
            continue
        fp, psd = welch_psd(arr, fs)
        med = band_median(fp, psd)
        bp = band_power(arr, fs)
        log(f"    {win_label:12s}: PSD_median={med:.3e}  bandpower={bp:.3e}")
        psds[win_label] = (fp, psd, med, bp)
        window_rows.append({
            "detector": label, "window": win_label,
            "offset_s": offset, "status": "OK",
            "psd_median": f"{med:.4e}", "bandpower": f"{bp:.4e}",
        })

    if not psds:
        log("  BLOCKED: no usable off-source windows")
        return None

    # --- Robust median PSD ---
    # Filter out any window whose PSD contains NaN
    clean_psds = [
        (lbl, v) for lbl, v in psds.items()
        if not np.any(np.isnan(v[1]))
    ]
    if not clean_psds:
        log("  BLOCKED: all PSD windows contain NaN")
        return None
    all_psd_arrays = [v[1] for _, v in clean_psds]
    all_fp = clean_psds[0][1][0]
    psd_stack = np.array(all_psd_arrays)
    psd_robust = np.nanmedian(psd_stack, axis=0)
    med_robust = band_median(all_fp, psd_robust)
    med_single = list(psds.values())[0][2]  # first window (minus500)

    log(f"\n  PSD_robust (median of {len(all_psd_arrays)} windows):")
    log(f"    band_median = {med_robust:.4e}")
    log(f"    minus500_median = {med_single:.4e}")
    if med_single > 0:
        ratio_robust_vs_single = med_robust / med_single
        log(f"    robust/single ratio = {ratio_robust_vs_single:.3f}")
    else:
        ratio_robust_vs_single = float("nan")

    if med_robust / med_single < 0.5 or med_robust / med_single > 2.0:
        psd_status = "PSD_WINDOW_NOT_REPRESENTATIVE"
    else:
        psd_status = "PSD_WINDOWS_CONSISTENT"

    log(f"  PSD_STATUS: {psd_status}")

    # --- Trigger bandpower vs PSD ---
    bp_trigger = band_power(strain_on, fs)
    bp_noise_est = med_robust * (F_HIGH - F_LOW)
    bp_ratio = bp_trigger / bp_noise_est if bp_noise_est > 0 else float("in")
    log(f"\n  Trigger bandpower: {bp_trigger:.4e}")
    log(f"  Noise estimate (robust PSD * BW): {bp_noise_est:.4e}")
    log(f"  bp_trigger / bp_noise = {bp_ratio:.2f}")

    # --- MF-SNR with robust PSD ---
    ffd = np.fft.rfftfreq(len(strain_on), 1.0 / fs)
    df = float(fs) / len(strain_on)
    dfd = np.fft.rfft(strain_on) / fs
    h_gr = gr_template(ffd, MC_KG, ETA, DL_M)
    h_ssz, _, _, _ = apply_ssz_v0_to_frequency_waveform(
        h_gr, ffd, M_TOT_KG, MU_KG, branch="g2_decay"
    )

    pi_robust = np.interp(ffd, all_fp, psd_robust,
                           left=psd_robust[1], right=psd_robust[-1])
    finite_pos = pi_robust[(pi_robust > 0) & np.isfinite(pi_robust)]
    floor = float(finite_pos.min()) if len(finite_pos) > 0 else 1e-50
    pi_robust = np.where((pi_robust <= 0) | ~np.isfinite(pi_robust),
                         floor, pi_robust)

    snr_gr_robust = mf_snr(dfd, h_gr, ffd, pi_robust, df)
    snr_ssz_robust = mf_snr(dfd, h_ssz, ffd, pi_robust, df)
    lnl_gr = -0.5 * nwip(dfd - h_gr, dfd - h_gr, ffd, pi_robust, df)
    lnl_ssz = -0.5 * nwip(dfd - h_ssz, dfd - h_ssz, ffd, pi_robust, df)
    delta_lnl = lnl_ssz - lnl_gr

    log("\n  With robust PSD:")
    log(f"    MF-SNR GR  = {snr_gr_robust:.2f}")
    log(f"    MF-SNR SSZ = {snr_ssz_robust:.2f}")
    log(f"    lnL_GR     = {lnl_gr:.4e}")
    log(f"    lnL_SSZ    = {lnl_ssz:.4e}")
    log(f"    delta_lnL  = {delta_lnl:.4e}")

    snr_status = "OK" if snr_gr_robust < 200 else "ANOMALOUS_HIGH_SNR"
    log(f"    SNR_STATUS: {snr_status}")

    return {
        "label": label,
        "psd_status": psd_status,
        "snr_status": snr_status,
        "snr_gr_robust": snr_gr_robust,
        "snr_ssz_robust": snr_ssz_robust,
        "lnl_gr": lnl_gr,
        "lnl_ssz": lnl_ssz,
        "delta_lnl": delta_lnl,
        "bp_trigger": bp_trigger,
        "bp_noise_est": bp_noise_est,
        "bp_ratio": bp_ratio,
        "med_robust": med_robust,
        "med_single": med_single,
        "ratio_robust_vs_single": ratio_robust_vs_single,
        "n_windows": len(all_psd_arrays),
        "window_rows": window_rows,
        "all_fp": all_fp,
        "psd_robust": psd_robust,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

log(f"Robust Multi-Window PSD Recheck — {NOW}")
log(f"Trigger GPS: {TRIGGER_GPS}")
log(f"Off-source windows: {[o for _, o in OFF_OFFSETS]} s (each {WIN_DUR_S}s)")

h1 = process_detector("H1", H1_PATH)
l1 = process_detector("L1", L1_PATH)

# --- H1/L1 coherence check ---
log(f"\n{'='*60}")
log("  H1/L1 COHERENCE CHECK (robust PSD)")
log(f"{'='*60}")

coherence_status = "BLOCKED"
h1_l1_ratio_robust = float("nan")
h1_l1_ratio_str = "N/A"

if h1 and l1:
    h1_l1_ratio_robust = h1["snr_gr_robust"] / l1["snr_gr_robust"] if l1["snr_gr_robust"] > 0 else float("nan")
    log(f"  H1 MF-SNR GR (robust): {h1['snr_gr_robust']:.2f}")
    log(f"  L1 MF-SNR GR (robust): {l1['snr_gr_robust']:.2f}")
    log(f"  H1/L1 SNR ratio:       {h1_l1_ratio_robust:.3f}")
    log(f"  H1 PSD status: {h1['psd_status']}")
    log(f"  L1 PSD status: {l1['psd_status']}")
    log(f"  H1 bp_ratio (trigger/noise): {h1['bp_ratio']:.1f}")
    log(f"  L1 bp_ratio (trigger/noise): {l1['bp_ratio']:.1f}")
    h1_l1_ratio_str = f"{h1_l1_ratio_robust:.3f}"

    both_ok = (h1["psd_status"] == "PSD_WINDOWS_CONSISTENT"
               and l1["psd_status"] == "PSD_WINDOWS_CONSISTENT")
    snr_ok = (h1["snr_status"] == "OK" and l1["snr_status"] == "OK")

    if both_ok and snr_ok:
        coherence_status = "COHERENCE_RECHECK_PASS"
    elif both_ok and not snr_ok:
        coherence_status = "COHERENCE_PARTIAL_SNR_ANOMALY"
    elif not both_ok:
        coherence_status = "COHERENCE_NEEDS_FURTHER_PSD_WORK"
    else:
        coherence_status = "COHERENCE_PARTIAL"

log(f"\n  COHERENCE_STATUS: {coherence_status}")

# --- Write CSV manifest ---
all_rows = []
for res in [h1, l1]:
    if res:
        all_rows.extend(res["window_rows"])

csv_path = MANIFEST / "robust_psd_windows_used.csv"
if all_rows:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["detector", "window", "offset_s",
                           "status", "psd_median", "bandpower"]
        )
        writer.writeheader()
        writer.writerows(all_rows)
    log(f"\n  -> {csv_path}")

# --- Write main report ---


def fmt(v, fmt_str=".4e"):
    if isinstance(v, float) and np.isnan(v):
        return "N/A"
    try:
        return format(v, fmt_str)
    except Exception:
        return str(v)


h1_block = "BLOCKED (file not found)" if not h1 else """
| PSD status | {h1['psd_status']} |
| n windows used | {h1['n_windows']} |
| PSD_robust band median | {fmt(h1['med_robust'])} 1/Hz |
| PSD_single (minus500) band median | {fmt(h1['med_single'])} 1/Hz |
| robust/single ratio | {fmt(h1['ratio_robust_vs_single'], '.3f')} |
| MF-SNR GR (robust PSD) | {fmt(h1['snr_gr_robust'], '.2f')} |
| MF-SNR SSZ (robust PSD) | {fmt(h1['snr_ssz_robust'], '.2f')} |
| lnL_GR | {fmt(h1['lnl_gr'])} |
| lnL_SSZ | {fmt(h1['lnl_ssz'])} |
| delta_lnL | {fmt(h1['delta_lnl'])} |
| bp_trigger | {fmt(h1['bp_trigger'])} |
| bp_noise_estimate | {fmt(h1['bp_noise_est'])} |
| bp_trigger/bp_noise | {fmt(h1['bp_ratio'], '.1f')} |
| SNR_STATUS | {h1['snr_status']} |
"""

l1_block = "BLOCKED (file not found)" if not l1 else """
| PSD status | {l1['psd_status']} |
| n windows used | {l1['n_windows']} |
| PSD_robust band median | {fmt(l1['med_robust'])} 1/Hz |
| PSD_single (minus500) band median | {fmt(l1['med_single'])} 1/Hz |
| robust/single ratio | {fmt(l1['ratio_robust_vs_single'], '.3f')} |
| MF-SNR GR (robust PSD) | {fmt(l1['snr_gr_robust'], '.2f')} |
| MF-SNR SSZ (robust PSD) | {fmt(l1['snr_ssz_robust'], '.2f')} |
| lnL_GR | {fmt(l1['lnl_gr'])} |
| lnL_SSZ | {fmt(l1['lnl_ssz'])} |
| delta_lnL | {fmt(l1['delta_lnl'])} |
| bp_trigger | {fmt(l1['bp_trigger'])} |
| bp_noise_estimate | {fmt(l1['bp_noise_est'])} |
| bp_trigger/bp_noise | {fmt(l1['bp_ratio'], '.1f')} |
| SNR_STATUS | {l1['snr_status']} |
"""

report_main = """# Robust Multi-Window PSD Report

Generated: {NOW}  
Event: GW240925 (trigger GPS {TRIGGER_GPS})  
No LIGO claim. No posterior. No SSZ support/falsification.

## Motivation

Previous diagnostics showed L1 bp_trigger/bp_off ~ 75000× using a single
-500s off-source window. This suggests the -500s window is too quiet to
be representative. We re-estimate the PSD using {len(OFF_OFFSETS)} windows
centred at offsets {[o for _, o in OFF_OFFSETS]} s from trigger, each {WIN_DUR_S}s long.
The robust PSD is the **median** across available windows.

## H1 Results

| Quantity | Value |
|---------|-------|
{h1_block}

## L1 Results

| Quantity | Value |
|---------|-------|
{l1_block}

## H1/L1 Coherence (Robust PSD)

| Quantity | Value |
|---------|-------|
| H1/L1 MF-SNR ratio | {h1_l1_ratio_str} |
| H1 PSD consistency | {h1['psd_status'] if h1 else 'N/A'} |
| L1 PSD consistency | {l1['psd_status'] if l1 else 'N/A'} |
| COHERENCE_STATUS | {coherence_status} |

## Interpretation

The key question: does the robust multi-window PSD give a stable,
representative noise floor, and do H1/L1 SNRs become consistent?

- If `PSD_WINDOWS_CONSISTENT`: the noise floor is stable across time;
  single-window anomaly was real, robust PSD is trusted.
- If `PSD_WINDOW_NOT_REPRESENTATIVE`: the noise floor varies significantly,
  meaning the previous single-window SNR/lnL values were not reliable.
  Further data quality work is needed before SSZ interpretation.

## Gate Status

```
PSD_ROBUST_RECHECK:             {coherence_status}
H1_PSD_STATUS:                  {h1['psd_status'] if h1 else 'BLOCKED'}
L1_PSD_STATUS:                  {l1['psd_status'] if l1 else 'BLOCKED'}
H1_SNR_STATUS:                  {h1['snr_status'] if h1 else 'BLOCKED'}
L1_SNR_STATUS:                  {l1['snr_status'] if l1 else 'BLOCKED'}
READY_FOR_REAL_LIGO_SSZ_CLAIM:  NO
SSZ_SUPPORT_CLAIM_MADE:         NO
SSZ_FALSIFICATION_CLAIM_MADE:   NO
```
"""

(REPORTS / "ROBUST_MULTIWINDOW_PSD_REPORT.md").write_text(
    report_main, encoding="utf-8"
)
log("\n  -> reports/ROBUST_MULTIWINDOW_PSD_REPORT.md")

# --- Write coherence recheck report ---
coh_report = """# H1/L1 Coherence Recheck — Robust PSD

Generated: {NOW}  
Follows: ROBUST_MULTIWINDOW_PSD_REPORT.md

## Background

The previous H1/L1 coherence run used a single off-source PSD window (-500s).
L1 showed bp_trigger/bp_off ~ 75000×, flagged as L1_PSD_WINDOW_NOT_REPRESENTATIVE.
This recheck uses the median of {len(OFF_OFFSETS)} windows.

## Robust PSD Window Inventory

See: `data_manifest/robust_psd_windows_used.csv`

## Coherence Metrics (Robust PSD)

| Metric | H1 | L1 |
|--------|-----|-----|
| PSD_status | {h1['psd_status'] if h1 else 'BLOCKED'} | {l1['psd_status'] if l1 else 'BLOCKED'} |
| n_windows_used | {h1['n_windows'] if h1 else 'N/A'} | {l1['n_windows'] if l1 else 'N/A'} |
| robust/single ratio | {fmt(h1['ratio_robust_vs_single'], '.3') if h1 else 'N/A'} | {fmt(l1['ratio_robust_vs_single'], '.3') if l1 else 'N/A'} |
| MF-SNR GR | {fmt(h1['snr_gr_robust'], '.2') if h1 else 'N/A'} | {fmt(l1['snr_gr_robust'], '.2') if l1 else 'N/A'} |
| delta_lnL (SSZ-GR) | {fmt(h1['delta_lnl']) if h1 else 'N/A'} | {fmt(l1['delta_lnl']) if l1 else 'N/A'} |
| bp_ratio (trigger/noise) | {fmt(h1['bp_ratio'], '.1') if h1 else 'N/A'} | {fmt(l1['bp_ratio'], '.1') if l1 else 'N/A'} |

## Status

```
COHERENCE_STATUS:               {coherence_status}
H1_L1_SNR_RATIO_ROBUST:         {h1_l1_ratio_str}
NEXT_STEP:                      {'Further PSD/DQ work if PARTIAL or BLOCKED' if 'PARTIAL' in coherence_status or 'BLOCKED' in coherence_status else 'Proceed to SSZ forward-model test if PASS'}
READY_FOR_REAL_LIGO_SSZ_CLAIM:  NO
```
"""

(REPORTS / "H1_L1_COHERENCE_RECHECK_ROBUST_PSD.md").write_text(
    coh_report, encoding="utf-8"
)
log("  -> reports/H1_L1_COHERENCE_RECHECK_ROBUST_PSD.md")

flush_log()
log("  -> logs/robust_psd_recheck.log")
log(f"\nFINAL GATE: {coherence_status}")
log("READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
