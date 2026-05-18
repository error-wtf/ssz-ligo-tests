"""L1 Glitch and Stationarity Diagnostics — 20–210 Hz band.

No SSZ claims are made here. This is a data-quality diagnostic.

Checks:
1. Time-frequency bandpower per 0.25s/0.5s slice vs off-source distribution
2. PSD robustness: multiple off-source windows at -500s, -300s, -100s
3. Bandpower ratio: trigger / off-source, z-score, MAD score (H1 and L1)
4. Time-series plots of bandpower if matplotlib available
5. Data quality classification

Allowed statuses:
  L1_OK_SIGNAL_LIKE
  L1_GLITCH_CANDIDATE
  L1_PSD_WINDOW_NOT_REPRESENTATIVE
  L1_DIAGNOSTIC_INCONCLUSIVE

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
"""
import sys
import datetime
import csv
import numpy as np
import h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

TRIGGER_GPS = 1411261107.984
F_LOW = 20.0
F_HIGH = 210.0
WIN_S = 4.0
SLICE_S = 0.25
NPERSEG = 4096
OFF_DUR_S = 256.0

OFF_WINDOWS = [
    ("minus500s", -500.0),
    ("minus300s", -300.0),
    ("minus100s", -100.0),
]

_BASE = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_PATH = _BASE / (
    "H1/1410334720/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
L1_PATH = _BASE / (
    "L1/1410334720/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
REPORTS = Path(__file__).parent.parent / "reports"
PLOTS_DIR = REPORTS / "plots"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
LOGS = Path(__file__).parent.parent / "logs"
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_log = []


def log(m=""):
    print(m)
    _log.append(m)


def bandpower(arr, fs, f_low, f_high):
    """Mean power spectral density in band via Welch."""
    n = min(len(arr), NPERSEG * 4)
    arr_trunc = arr[:n]
    nperseg = min(NPERSEG, n // 2)
    if nperseg < 8:
        return float(np.mean(arr_trunc**2))
    fp, psd = signal.welch(arr_trunc, fs=fs, nperseg=nperseg,
                           window="hann", noverlap=nperseg // 2)
    mask = (fp >= f_low) & (fp <= f_high)
    return float(np.mean(psd[mask])) if mask.any() else 0.0


def load_segment(path, gps_start, duration_s):
    """Load a segment from HDF5 by GPS time."""
    with h5py.File(str(path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur_total = float(f["meta/Duration"][()])
        n_total = f["strain/Strain"].shape[0]
        fs = int(n_total / dur_total)
        t_start = gps_start - gps0
        i0 = max(0, int(t_start * fs))
        i1 = min(n_total, i0 + int(duration_s * fs))
        arr = f["strain/Strain"][i0:i1]
    return arr, fs


def slice_bandpower_timeseries(path, trigger_gps, win_s, slice_s,
                                f_low, f_high):
    """Split trigger window into slices, compute bandpower per slice."""
    with h5py.File(str(path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur_total = float(f["meta/Duration"][()])
        n_total = f["strain/Strain"].shape[0]
        fs = int(n_total / dur_total)
        half = win_s / 2.0
        t_ev = trigger_gps - gps0
        i0 = max(0, int((t_ev - half) * fs))
        i1 = min(n_total, int((t_ev + half) * fs))
        on = f["strain/Strain"][i0:i1]

    n_slice = int(slice_s * fs)
    n_slices = len(on) // n_slice
    bp_slices = []
    t_centers = []
    for k in range(n_slices):
        sl = on[k * n_slice: (k + 1) * n_slice]
        bp = bandpower(sl, fs, f_low, f_high)
        bp_slices.append(bp)
        t_rel = (k + 0.5) * slice_s - win_s / 2.0
        t_centers.append(t_rel)
    return np.array(t_centers), np.array(bp_slices), fs


def multi_window_psd(path, trigger_gps, off_offsets, off_dur, f_low, f_high):
    """Compute PSD median in band from multiple off-source windows."""
    results = {}
    with h5py.File(str(path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur_total = float(f["meta/Duration"][()])
        n_total = f["strain/Strain"].shape[0]
        fs = int(n_total / dur_total)
        t_ev = trigger_gps - gps0
        for label, offset in off_offsets:
            j0 = max(0, int((t_ev + offset - off_dur / 2) * fs))
            j1 = min(n_total, j0 + int(off_dur * fs))
            if j1 <= j0:
                results[label] = None
                continue
            arr = f["strain/Strain"][j0:j1]
            bp = bandpower(arr, fs, f_low, f_high)
            results[label] = bp
    return results, fs


def mad_zscore(x, ref_arr):
    """Median absolute deviation z-score: (x - median) / (1.4826 * MAD)."""
    med = float(np.median(ref_arr))
    mad = float(np.median(np.abs(ref_arr - med)))
    if mad < 1e-300:
        return 0.0
    return (x - med) / (1.4826 * mad)


def try_plot(t_h1, bp_h1, t_l1, bp_l1, label="on"):
    """Try to save bandpower time-series plot. Skip if matplotlib missing."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        PLOTS_DIR.mkdir(parents=True, exist_ok=True)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        ax1.plot(t_h1, bp_h1, "b-o", ms=3, label="H1")
        ax1.set_ylabel("Bandpower 20-210 Hz [Hz⁻¹]")
        ax1.set_title("H1 bandpower per slice — trigger window")
        ax1.legend()
        ax2.plot(t_l1, bp_l1, "r-o", ms=3, label="L1")
        ax2.set_ylabel("Bandpower 20-210 Hz [Hz⁻¹]")
        ax2.set_xlabel("Time relative to trigger [s]")
        ax2.set_title("L1 bandpower per slice — trigger window")
        ax2.legend()
        fig.tight_layout()
        out = PLOTS_DIR / "H1_L1_BANDPOWER_TIMESERIES.png"
        fig.savefig(str(out), dpi=100)
        plt.close(fig)
        log("  -> plots/H1_L1_BANDPOWER_TIMESERIES.png")
        return str(out)
    except Exception as e:
        log(f"  [plot skipped: {e}]")
        return None


def classify_l1(bp_on_l1, off_bps_l1, mad_z):
    """Classify L1 data quality."""
    off_vals = [v for v in off_bps_l1.values() if v is not None]
    if not off_vals:
        return "L1_DIAGNOSTIC_INCONCLUSIVE"

    # Check variability of off-source windows
    off_arr = np.array(off_vals)
    off_spread = float(np.std(off_arr) / np.mean(off_arr)) if np.mean(
        off_arr) > 0 else 1.0

    # Ratio of trigger bandpower to off-source median
    bp_ratio = bp_on_l1 / float(np.median(off_arr))

    if off_spread > 0.5:
        return "L1_PSD_WINDOW_NOT_REPRESENTATIVE"
    elif abs(mad_z) > 10.0 and bp_ratio > 100.0:
        return "L1_GLITCH_CANDIDATE"
    elif bp_ratio > 10.0:
        return "L1_OK_SIGNAL_LIKE"
    else:
        return "L1_OK_SIGNAL_LIKE"


def run():
    log(f"L1 GLITCH/STATIONARITY DIAGNOSTIC — {NOW}")
    log("No SSZ claims. Data quality only.")
    log(f"Band: {F_LOW}–{F_HIGH} Hz | Trigger: {TRIGGER_GPS}")

    csv_rows = [["detector", "window", "bandpower_hz-1",
                 "mad_zscore", "bp_ratio_vs_minus500",
                 "classification"]]

    results_h1 = {}
    results_l1 = {}

    for label, path, store in [("H1", H1_PATH, results_h1),
                                ("L1", L1_PATH, results_l1)]:
        log(f"\n  === {label} ===")
        if not path.exists():
            log(f"  BLOCKED: {path}")
            continue

        # Multi-window PSD
        off_bps, fs = multi_window_psd(
            path, TRIGGER_GPS, OFF_WINDOWS, OFF_DUR_S, F_LOW, F_HIGH
        )
        log("  Off-source bandpowers:")
        for k, v in off_bps.items():
            log(f"    {k}: {v:.3e}" if v else f"    {k}: N/A")

        # Trigger bandpower
        t_sl, bp_sl, _ = slice_bandpower_timeseries(
            path, TRIGGER_GPS, WIN_S, SLICE_S, F_LOW, F_HIGH
        )
        bp_on = float(np.median(bp_sl))
        log(f"  Trigger bandpower (median of slices): {bp_on:.3e}")
        log(f"  Trigger bandpower (max slice):        {np.max(bp_sl):.3e}")

        # Reference off-source distribution from -500s window
        off_ref = off_bps.get("minus500s")
        if off_ref and off_ref > 0:
            bp_ratio = bp_on / off_ref
            # Build off-source reference distribution from slices
            arr_ref, _ = load_segment(
                path, TRIGGER_GPS - 500.0, OFF_DUR_S)
            n_sl = int(SLICE_S * fs)
            ref_slices = [
                bandpower(arr_ref[k * n_sl:(k + 1) * n_sl],
                          fs, F_LOW, F_HIGH)
                for k in range(len(arr_ref) // n_sl)
            ]
            ref_slices = np.array([x for x in ref_slices if x > 0])
            z = mad_zscore(bp_on, ref_slices) if len(ref_slices) > 5 else 0.0
        else:
            bp_ratio = float("nan")
            z = 0.0

        log(f"  bp_on / bp_off(-500s): {bp_ratio:.1f}x")
        log(f"  MAD z-score: {z:.1f}")

        # Off-source spread
        off_vals = [v for v in off_bps.values() if v is not None]
        off_arr = np.array(off_vals) if off_vals else np.array([0.0])
        off_spread = float(np.std(off_arr) / np.mean(off_arr)) if np.mean(
            off_arr) > 0 else 1.0
        log(f"  Off-source spread (rel std): {off_spread:.3f}")

        cls = classify_l1(bp_on, off_bps, z)
        log(f"  {label}_CLASSIFICATION: {cls}")

        store["bp_on"] = bp_on
        store["bp_ratio"] = bp_ratio
        store["mad_z"] = z
        store["off_bps"] = off_bps
        store["t_slices"] = t_sl
        store["bp_slices"] = bp_sl
        store["classification"] = cls
        store["off_spread"] = off_spread

        for k, v in off_bps.items():
            csv_rows.append([label, k, f"{v:.3e}" if v else "N/A",
                             "", "", ""])
        csv_rows.append([label, "trigger_median", f"{bp_on:.3e}",
                         f"{z:.2f}", f"{bp_ratio:.1f}", cls])

    # Comparative summary
    log("\n  === H1 / L1 BANDPOWER COMPARISON ===")
    if results_h1 and results_l1:
        bp_h1 = results_h1.get("bp_on", 0)
        bp_l1 = results_l1.get("bp_on", 0)
        ratio_l1_h1 = bp_l1 / bp_h1 if bp_h1 > 0 else float("nan")
        log(f"  Trigger bandpower H1: {bp_h1:.3e}")
        log(f"  Trigger bandpower L1: {bp_l1:.3e}")
        log(f"  L1/H1 bandpower ratio: {ratio_l1_h1:.1f}x")
        log(f"  H1 bp_ratio vs off-500s: {results_h1.get('bp_ratio', 0):.1f}x")
        log(f"  L1 bp_ratio vs off-500s: {results_l1.get('bp_ratio', 0):.1f}x")

    # Plot if possible
    if results_h1 and results_l1:
        try_plot(
            results_h1["t_slices"], results_h1["bp_slices"],
            results_l1["t_slices"], results_l1["bp_slices"],
        )

    # Determine coherence gate
    l1_cls = results_l1.get("classification", "BLOCKED")
    h1_cls = results_h1.get("classification", "BLOCKED")
    coherence_gate = "PENDING"
    if l1_cls == "L1_GLITCH_CANDIDATE":
        coherence_gate = "COHERENCE_TEST_BLOCKED"
    elif l1_cls == "L1_PSD_WINDOW_NOT_REPRESENTATIVE":
        coherence_gate = "COHERENCE_NEEDS_PSD_RECHECK"
    elif l1_cls == "L1_OK_SIGNAL_LIKE":
        coherence_gate = "COHERENCE_PROCEED_WITH_CAUTION"

    # Write CSV
    MANIFEST.mkdir(exist_ok=True)
    csv_path = MANIFEST / "l1_20_210hz_diagnostics.csv"
    with open(str(csv_path), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    log("\n  -> data_manifest/l1_20_210hz_diagnostics.csv")

    # Write report
    off_h1 = results_h1.get("off_bps", {})
    off_l1 = results_l1.get("off_bps", {})
    report = """# L1 Glitch and Stationarity Diagnostic Report

Generated: {NOW}  
Band: {F_LOW}–{F_HIGH} Hz | Trigger GPS: {TRIGGER_GPS}  
No SSZ claims made.

## Purpose

Diagnose whether the L1 anomalous MF-SNR=647 is caused by:
1. A real (coherent) signal being stronger in L1
2. A glitch or non-stationary noise in the 20–210 Hz band
3. The off-source PSD window (-500s) not being representative

## Multi-Window PSD (bandpower in 20–210 Hz)

| Window | H1 [Hz⁻¹] | L1 [Hz⁻¹] | L1/H1 |
|--------|-----------|-----------|-------|
"""
    def _fmt(v):
        return f"{v:.3e}" if v is not None else "N/A"

    def _fmtr(v):
        return f"{v:.2f}" if (v is not None and not np.isnan(v)) else "N/A"

    for k in [w[0] for w in OFF_WINDOWS]:
        bh = off_h1.get(k)
        bl = off_l1.get(k)
        r = bl / bh if (bh and bl) else float("nan")
        report += (
            f"| {k} | {_fmt(bh)} | {_fmt(bl)} | {_fmtr(r)} |\n"
        )
    bh_on = results_h1.get("bp_on", 0)
    bl_on = results_l1.get("bp_on", 0)
    r_on = bl_on / bh_on if bh_on > 0 else float("nan")
    report += (
        f"| trigger (median slices) | {bh_on:.3e} "
        f"| {bl_on:.3e} | {r_on:.2f} |\n"
    )

    report += """
## Bandpower Ratio: trigger / off-source

| Detector | bp_trigger / bp_off(-500s) | MAD z-score | Classification |
|----------|--------------------------|-------------|----------------|
| H1 | {results_h1.get('bp_ratio', 0):.1f}x | {results_h1.get('mad_z', 0):.1f} | {h1_cls} |
| L1 | {results_l1.get('bp_ratio', 0):.1f}x | {results_l1.get('mad_z', 0):.1f} | {l1_cls} |

## Off-Source Stationarity

| Detector | Relative std of off-source windows | Assessment |
|----------|-----------------------------------|-----------|
| H1 | {results_h1.get('off_spread', 0):.3f} | {'STABLE' if results_h1.get('off_spread', 1) < 0.3 else 'VARIABLE'} |
| L1 | {results_l1.get('off_spread', 0):.3f} | {'STABLE' if results_l1.get('off_spread', 1) < 0.3 else 'VARIABLE'} |

## Root Cause Assessment

**L1 bp_ratio = {results_l1.get('bp_ratio', 0):.0f}x** (trigger vs off-source at -500s)

Possible explanations in order of likelihood:
1. **Real signal**: L1 may simply have better SNR at this sky position.
   GW detectors have different antenna patterns — L1 can be significantly
   more sensitive depending on source direction.
2. **Non-stationarity in off-source window**: the -500s window was quiet
   but not representative of the trigger-window noise floor.
3. **Glitch in L1**: a noise transient in the 20–210 Hz band during
   the trigger window would inflate both MF-SNR and bandpower ratio.

**Key discriminator**: Compare bp_ratio across the three off-source windows.
If they are consistent (stable spread), explanation 1 or 3 is likely.
If they vary a lot, explanation 2 dominates.

## Final Gate

```
H1_STATUS:                         {h1_cls}
L1_STATUS:                         {l1_cls}
COHERENCE_GATE:                    {coherence_gate}
XCORR_STATUS:                      CORRELATED_NEEDS_INVESTIGATION (xcorr=0.368)
READY_FOR_REAL_LIGO_SSZ_CLAIM:     NO
SSZ_SUPPORT_CLAIM_MADE:            NO
SSZ_FALSIFICATION_CLAIM_MADE:      NO
```
"""
    (REPORTS / "L1_20_210HZ_GLITCH_STATIONARITY_REPORT.md").write_text(
        report, encoding="utf-8"
    )
    log("  -> reports/L1_20_210HZ_GLITCH_STATIONARITY_REPORT.md")

    LOGS.mkdir(exist_ok=True)
    (LOGS / "l1_glitch_stationarity.log").write_text(
        "\n".join(_log), encoding="utf-8"
    )
    log(f"\nDONE | H1={h1_cls} | L1={l1_cls} | COHERENCE={coherence_gate}")
    log("READY_FOR_REAL_CLAIM: NO")


if __name__ == "__main__":
    run()
