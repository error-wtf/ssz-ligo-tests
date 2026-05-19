"""L1 Multi-Window Stationarity Quantile Test.

Tests whether the L1 trigger bandpower is a genuine outlier
or normal behaviour for L1 in the 20-210 Hz band.

Method:
  - Sample bandpower from many 4s windows spanning -1000s to +1000s
    around the trigger (step = 4s, same window length).
  - Build distribution of bandpower values.
  - Find where the trigger window sits in this distribution.
  - Report: trigger quantile, how often similar power occurs.

Same for H1 as control.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
"""
import datetime
import csv
import numpy as np
import h5py
from pathlib import Path
from scipy import signal, stats

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for _d in (REPORTS, LOGS, MANIFEST):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "l1_multiwindow_stationarity.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
TRIGGER_GPS = 1411261107.984
WIN_S = 4.0
STEP_S = 4.0              # non-overlapping windows
SCAN_RANGE_S = 1000.0     # scan ±1000s around trigger
PSD_DUR_S = 64.0
PSD_OFFSET_S = 500.0
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 512

_BASE = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_PATH = _BASE / (
    "H1/1410334720"
    "/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
L1_PATH = _BASE / (
    "L1/1410334720"
    "/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)


# ---------------------------------------------------------------------------
# I/O — batch load (single file open, slice many windows)
# ---------------------------------------------------------------------------
def load_all_windows(path, t_center, win_s, step_s, scan_s):
    """
    Load all non-overlapping windows within [t_center-scan_s, t_center+scan_s].
    Returns list of (offset_s, strain_array), fs.
    """
    if not path.exists():
        return [], None
    with h5py.File(path, "r") as f:
        gps0 = float(f["meta"]["GPSstart"][()])
        dur_file = float(f["meta"]["Duration"][()])
        n_total = f["strain/Strain"].shape[0]
        fs = n_total / dur_file
        strain_full = f["strain/Strain"][:]

    strain_full = strain_full.astype(float)
    windows = []
    offsets = np.arange(-scan_s, scan_s + step_s, step_s)
    for off in offsets:
        t_c = t_center + off
        t_off_file = t_c - gps0
        i0 = int((t_off_file - win_s / 2) * fs)
        i1 = int((t_off_file + win_s / 2) * fs)
        if i0 < 0 or i1 > n_total:
            continue
        seg = strain_full[i0:i1]
        if len(seg) == 0 or not np.all(np.isfinite(seg)):
            continue
        windows.append((float(off), seg))
    return windows, float(fs)


def load_window_single(path, t_center, dur):
    if not path.exists():
        return None, None
    with h5py.File(path, "r") as f:
        gps0 = float(f["meta"]["GPSstart"][()])
        dur_file = float(f["meta"]["Duration"][()])
        n_total = f["strain/Strain"].shape[0]
        fs = n_total / dur_file
        t_off = t_center - gps0
        i0 = max(0, int((t_off - dur / 2) * fs))
        i1 = min(n_total, int((t_off + dur / 2) * fs))
        strain = f["strain/Strain"][i0:i1]
    if not np.all(np.isfinite(strain)) or len(strain) == 0:
        return None, None
    return strain.astype(float), float(fs)


# ---------------------------------------------------------------------------
# SIGNAL PROCESSING
# ---------------------------------------------------------------------------
def bandpower(strain, fs, f_low=F_LOW, f_high=F_HIGH, nperseg=NPERSEG):
    nperseg_use = min(nperseg, len(strain) // 2)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nperseg_use,
                              window="hann", noverlap=nperseg_use // 2)
    mask = (freqs >= f_low) & (freqs <= f_high)
    return float(np.trapezoid(psd[mask], freqs[mask]))


# ---------------------------------------------------------------------------
# ANALYSE ONE DETECTOR
# ---------------------------------------------------------------------------
def analyse_detector(det, path):
    log(f"\n{'='*60}")
    log(f"DETECTOR: {det}")
    log(f"{'='*60}")

    if not path.exists():
        log("  FILE NOT FOUND")
        return None

    log(f"  Scanning +-{SCAN_RANGE_S}s in {STEP_S}s steps "
        f"({int(2*SCAN_RANGE_S/STEP_S)} windows expected)...")

    windows, fs = load_all_windows(path, TRIGGER_GPS, WIN_S,
                                   STEP_S, SCAN_RANGE_S)
    if not windows:
        log("  No windows loaded")
        return None

    log(f"  Loaded {len(windows)} windows  fs={fs:.0f}Hz")

    offsets = []
    bps = []
    for off, seg in windows:
        bp = bandpower(seg, fs)
        offsets.append(off)
        bps.append(bp)

    offsets = np.array(offsets)
    bps = np.array(bps)

    # Find trigger window (offset ~0)
    trig_idx = np.argmin(np.abs(offsets))
    trig_bp = bps[trig_idx]
    trig_off = offsets[trig_idx]

    # Exclude trigger window from distribution
    mask_off = np.abs(offsets) > WIN_S
    bps_off = bps[mask_off]

    if len(bps_off) == 0:
        log("  No off-source windows available")
        return None

    bp_mean = float(np.mean(bps_off))
    bp_std = float(np.std(bps_off, ddof=1))
    bp_med = float(np.median(bps_off))
    bp_mad = float(np.median(np.abs(bps_off - bp_med)))

    # Trigger quantile
    quantile = float(stats.percentileofscore(bps_off, trig_bp) / 100.0)
    z_score = (trig_bp - bp_mean) / (bp_std + 1e-300)

    log(f"  Off-source distribution ({len(bps_off)} windows):")
    log(f"    mean={bp_mean:.4e}  std={bp_std:.4e}  "
        f"median={bp_med:.4e}  MAD={bp_mad:.4e}")
    log(f"    min={bps_off.min():.4e}  max={bps_off.max():.4e}")
    log(f"  Trigger (offset={trig_off:+.1f}s):")
    log(f"    bandpower={trig_bp:.4e}  "
        f"quantile={quantile*100:.1f}%  z={z_score:+.2f}")

    # How often does a window exceed the trigger level?
    exceed_frac = float(np.mean(bps_off >= trig_bp))
    log(f"    Fraction of off-source windows >= trigger: "
        f"{exceed_frac*100:.1f}%")

    # Distribution percentiles
    pcts = [50, 75, 90, 95, 99, 99.9]
    log("  Distribution percentiles:")
    for p in pcts:
        pv = float(np.percentile(bps_off, p))
        marker = " <- TRIGGER" if abs(pv - trig_bp) < bp_std * 0.3 else ""
        log(f"    {p:5.1f}%ile: {pv:.4e}{marker}")

    # Classification
    if quantile > 0.999:
        stationarity = "EXTREME_OUTLIER_999"
    elif quantile > 0.99:
        stationarity = "STRONG_OUTLIER_99"
    elif quantile > 0.95:
        stationarity = "MODERATE_OUTLIER_95"
    elif quantile > 0.80:
        stationarity = "MILD_OUTLIER_80"
    else:
        stationarity = "CONSISTENT_WITH_BACKGROUND"

    log(f"  -> STATIONARITY: {stationarity}")

    # Time-series of bandpower: check for trends
    # Simple: is there a ramp in the off-source distribution?
    slope, intercept, r, p_val, se = stats.linregress(offsets, bps)
    log(f"  Bandpower vs time: slope={slope:.3e}/s  "
        f"R={r:.3f}  p={p_val:.3e}")
    if abs(r) > 0.5 and p_val < 0.01:
        trend = "SIGNIFICANT_TREND"
    else:
        trend = "NO_SIGNIFICANT_TREND"
    log(f"  -> TREND: {trend}")

    return {
        "det": det,
        "n_windows": len(bps_off),
        "trig_bp": trig_bp,
        "trig_offset": trig_off,
        "off_mean": bp_mean, "off_std": bp_std,
        "off_median": bp_med, "off_mad": bp_mad,
        "quantile": round(quantile, 5),
        "z_score": round(z_score, 3),
        "exceed_frac": round(exceed_frac, 5),
        "stationarity": stationarity,
        "trend": trend,
        "slope": round(float(slope), 6),
        "offsets": offsets, "bps": bps,
        "bps_off": bps_off,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"L1 MULTI-WINDOW STATIONARITY QUANTILE TEST -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s  Step: {STEP_S}s  "
        f"Range: +-{SCAN_RANGE_S}s")
    log(f"Band: {F_LOW}-{F_HIGH}Hz")

    h1_res = analyse_detector("H1", H1_PATH)
    l1_res = analyse_detector("L1", L1_PATH)

    # ---------------------------------------------------------------------------
    # FINAL COMPARISON
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("FINAL COMPARISON")
    log(f"{'='*60}")

    if h1_res and l1_res:
        log(f"  H1 trigger quantile: {h1_res['quantile']*100:.1f}%  "
            f"z={h1_res['z_score']:+.2f}  -> {h1_res['stationarity']}")
        log(f"  L1 trigger quantile: {l1_res['quantile']*100:.1f}%  "
            f"z={l1_res['z_score']:+.2f}  -> {l1_res['stationarity']}")

        if (l1_res["quantile"] > 0.99
                and h1_res["quantile"] < 0.95):
            coherence_verdict = "L1_OUTLIER_H1_NORMAL"
        elif (l1_res["quantile"] < 0.95
              and h1_res["quantile"] < 0.95):
            coherence_verdict = "BOTH_CONSISTENT_WITH_BACKGROUND"
        elif (l1_res["quantile"] > 0.95
              and h1_res["quantile"] > 0.95):
            coherence_verdict = "BOTH_ELEVATED"
        else:
            coherence_verdict = "MIXED"
        log(f"  -> COHERENCE_VERDICT: {coherence_verdict}")

    # ---------------------------------------------------------------------------
    # WRITE OUTPUTS
    # ---------------------------------------------------------------------------
    summary_rows = []
    for res in [h1_res, l1_res]:
        if res:
            summary_rows.append({
                k: res[k] for k in
                ["det", "n_windows", "trig_bp", "off_mean", "off_std",
                 "off_median", "off_mad", "quantile", "z_score",
                 "exceed_frac", "stationarity", "trend", "slope"]
            })

    csv_path = MANIFEST / "l1_multiwindow_stationarity.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        if summary_rows:
            w = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
            w.writeheader()
            w.writerows(summary_rows)

    # Per-window bandpower CSV (for plotting)
    win_rows = []
    for res in [h1_res, l1_res]:
        if res:
            for off, bp in zip(res["offsets"], res["bps"]):
                win_rows.append({"det": res["det"],
                                 "offset_s": round(float(off), 2),
                                 "bandpower": float(bp)})
    win_csv = MANIFEST / "l1_multiwindow_bandpower_series.csv"
    with open(win_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["det", "offset_s", "bandpower"])
        w.writeheader()
        w.writerows(win_rows)

    md = [
        "# L1 Multi-Window Stationarity Quantile Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s  Step: {STEP_S}s  Range: +/-{SCAN_RANGE_S}s",
        f"- Band: {F_LOW}-{F_HIGH} Hz",
        "",
        "## Summary",
        "",
        "| Det | N windows | Trigger BP | Off mean | Quantile | z | Status |",
        "|-----|-----------|-----------|----------|----------|---|--------|",
    ]
    for r in summary_rows:
        md.append(
            f"| {r['det']} | {r['n_windows']} | {r['trig_bp']:.3e} "
            f"| {r['off_mean']:.3e} | {r['quantile']*100:.1f}% "
            f"| {r['z_score']:+.2f} | {r['stationarity']} |"
        )
    md += [
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "L1_MULTIWINDOW_STATIONARITY_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    log(f"  {win_csv}")
    flush_log()


if __name__ == "__main__":
    run()
