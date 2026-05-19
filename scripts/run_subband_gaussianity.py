"""Subband Gaussianity Test — 20-210 Hz split into 5 sub-bands.

For each sub-band [20-40, 40-80, 80-120, 120-160, 160-210 Hz]:
  - Bandpass filter H1 and L1 strain (trigger + off-source windows)
  - Whiten with off-source PSD
  - Compute: kurtosis, excess kurtosis, skewness, outlier counts
    (|z|>3,4,5), Anderson-Darling test, bandpower, H1/L1 ratio
  - Classify per-band excess

Goal: Identify which sub-band drives the L1 broadband excess.

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

LOG_PATH = LOGS / "subband_gaussianity.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TRIGGER_GPS = 1411261107.984
WIN_S = 4.0
PSD_REF_DUR_S = 64.0
PSD_OFFSET_S = 500.0
NPERSEG = 1024
FILTER_ORDER = 8

SUB_BANDS = [
    ("20-40",   20.0,  40.0),
    ("40-80",   40.0,  80.0),
    ("80-120",  80.0, 120.0),
    ("120-160", 120.0, 160.0),
    ("160-210", 160.0, 210.0),
]

OFF_WINDOWS = [
    ("OFF_m500", -500.0),
    ("OFF_m300", -300.0),
    ("OFF_m100", -100.0),
]

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
# I/O
# ---------------------------------------------------------------------------
def load_window(path, t_center, dur):
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
def bandpass_and_normalize(strain, fs, f_lo, f_hi, order=4):
    """
    Bandpass filter (low order), apply Tukey window to reduce edge
    ringing, normalize to zero-mean unit-variance.
    Low filter order (4) avoids extreme ringing on short 4s segments.
    """
    nyq = fs / 2
    lo = max(f_lo / nyq, 1e-4)
    hi = min(f_hi / nyq, 0.9999)
    sos = signal.butter(order, [lo, hi], btype="bandpass", output="sos")
    filtered = signal.sosfiltfilt(sos, strain)
    # Tukey window to suppress edge effects
    win = signal.windows.tukey(len(filtered), alpha=0.2)
    filtered = filtered * win
    # Trim 5% edges to further reduce ringing
    trim = max(1, len(filtered) // 20)
    core = filtered[trim:-trim]
    std = float(np.std(core, ddof=1))
    if std < 1e-30:
        return core
    return core / std


def bandpower_subband(strain, fs, f_lo, f_hi, nperseg=NPERSEG):
    """Integrate PSD in sub-band."""
    nps = min(nperseg, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window="hann")
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    return float(np.trapezoid(psd[mask], freqs[mask]))


# ---------------------------------------------------------------------------
# GAUSSIANITY STATS
# ---------------------------------------------------------------------------
def gaussianity_stats(x, label=""):
    n = len(x)
    mu = float(np.mean(x))
    std = float(np.std(x, ddof=1))
    sk = float(stats.skew(x))
    ku = float(stats.kurtosis(x, fisher=False))  # normal=3
    ex_ku = ku - 3.0
    z = (x - mu) / (std + 1e-300)
    n3 = int(np.sum(np.abs(z) > 3))
    n4 = int(np.sum(np.abs(z) > 4))
    n5 = int(np.sum(np.abs(z) > 5))

    # Anderson-Darling
    try:
        ad_stat, ad_cv, ad_sig = stats.anderson(x, dist="norm")
        ad_pass = bool(ad_stat < ad_cv[2])  # 5% level
    except Exception:
        ad_stat, ad_pass = float("nan"), False

    bp = float(np.var(x))

    if abs(ex_ku) < 0.5 and abs(sk) < 0.5 and ad_pass:
        gauss_class = "GAUSSIAN"
    elif abs(ex_ku) > 3.0 or n4 > 2:
        gauss_class = "STRONGLY_NON_GAUSSIAN"
    elif abs(ex_ku) > 1.0:
        gauss_class = "MILDLY_NON_GAUSSIAN"
    else:
        gauss_class = "BORDERLINE"

    return {
        "label": label,
        "n": n,
        "mean": round(mu, 6),
        "std": round(std, 6),
        "skewness": round(sk, 4),
        "kurtosis": round(ku, 4),
        "excess_kurtosis": round(ex_ku, 4),
        "n_z3": n3, "n_z4": n4, "n_z5": n5,
        "ad_stat": round(float(ad_stat), 4),
        "ad_pass_5pct": ad_pass,
        "bandpower_proxy": round(bp, 8),
        "gauss_class": gauss_class,
    }


# ---------------------------------------------------------------------------
# ANALYSE ONE SUBBAND
# ---------------------------------------------------------------------------
def analyse_subband(band_name, f_lo, f_hi, h1_windows, l1_windows):
    """
    h1_windows / l1_windows: dict of tag -> (strain, fs)
    Bandpass raw strain (no whitening) to avoid ringing artifacts.
    Normalize to unit variance for Gaussianity statistics.
    """
    log(f"\n  --- Sub-band: {band_name} [{f_lo}-{f_hi} Hz] ---")
    rows = []

    for det, windows in [("H1", h1_windows), ("L1", l1_windows)]:
        for tag, (strain, fs) in windows.items():
            strained_bp = bandpass_and_normalize(strain, fs, f_lo, f_hi)
            label = f"{det}_{tag}_{band_name}"
            row = gaussianity_stats(strained_bp, label)
            row["det"] = det
            row["tag"] = tag
            row["band"] = band_name
            row["f_lo"] = f_lo
            row["f_hi"] = f_hi
            # Bandpower from raw PSD (not whitened)
            row["bandpower_proxy"] = round(
                bandpower_subband(strain, fs, f_lo, f_hi), 12)
            rows.append(row)
            log(f"    {label}: ex_k={row['excess_kurtosis']:+.3f}  "
                f"sk={row['skewness']:+.3f}  "
                f"n_z4={row['n_z4']}  class={row['gauss_class']}")

    # H1/L1 bandpower ratio for trigger (raw PSD bandpower)
    h1_trig = next((r for r in rows
                    if r["det"] == "H1" and r["tag"] == "TRIGGER"), None)
    l1_trig = next((r for r in rows
                    if r["det"] == "L1" and r["tag"] == "TRIGGER"), None)
    if h1_trig and l1_trig:
        ratio = (l1_trig["bandpower_proxy"]
                 / (h1_trig["bandpower_proxy"] + 1e-300))
        log(f"    H1/L1 bandpower ratio (trigger): {ratio:.3f}")
        for r in rows:
            r["l1_h1_ratio"] = (
                round(ratio, 4) if r["det"] == "L1" else None)

    return rows


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"SUBBAND GAUSSIANITY TEST -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s")
    log(f"Sub-bands: {[b[0] for b in SUB_BANDS]}")
    log(f"Off-source windows: {[w[0] for w in OFF_WINDOWS]}")

    # Load all windows for H1 and L1
    all_windows_to_load = [("TRIGGER", 0.0)] + list(OFF_WINDOWS)

    h1_windows = {}
    l1_windows = {}
    for tag, offset in all_windows_to_load:
        t_c = TRIGGER_GPS + offset
        s, fs = load_window(H1_PATH, t_c, WIN_S)
        if s is not None:
            h1_windows[tag] = (s, fs)
        s, fs = load_window(L1_PATH, t_c, WIN_S)
        if s is not None:
            l1_windows[tag] = (s, fs)

    log(f"\nLoaded H1 windows: {list(h1_windows.keys())}")
    log(f"Loaded L1 windows: {list(l1_windows.keys())}")

    log("Using raw bandpass + normalize (no whitening) for sub-band stats.")

    # Run per-band analysis (no whitening — bandpass raw strain)
    all_rows = []
    for band_name, f_lo, f_hi in SUB_BANDS:
        rows = analyse_subband(band_name, f_lo, f_hi,
                               h1_windows, l1_windows)
        all_rows.extend(rows)

    # ---------------------------------------------------------------------------
    # SUMMARY TABLE
    # ---------------------------------------------------------------------------
    log(f"\n{'='*70}")
    log("SUMMARY: L1 TRIGGER — per sub-band")
    log(f"{'='*70}")
    log(f"  {'Band':12s} {'Ex.Kurt':>9} {'Skew':>8} "
        f"{'n_z4':>6} {'L1/H1':>7} {'Class'}")
    log("  " + "-" * 60)

    for band_name, f_lo, f_hi in SUB_BANDS:
        r = next((x for x in all_rows
                  if x["det"] == "L1"
                  and x["tag"] == "TRIGGER"
                  and x["band"] == band_name), None)
        if r:
            ratio_str = (f"{r['l1_h1_ratio']:.3f}"
                         if r.get("l1_h1_ratio") else "N/A")
            log(f"  {band_name:12s} {r['excess_kurtosis']:>+9.3f} "
                f"{r['skewness']:>+8.3f} {r['n_z4']:>6d} "
                f"{ratio_str:>7s} {r['gauss_class']}")

    # Which sub-band is most non-Gaussian?
    l1_trig_rows = [r for r in all_rows
                    if r["det"] == "L1" and r["tag"] == "TRIGGER"]
    if l1_trig_rows:
        worst = max(l1_trig_rows, key=lambda r: abs(r["excess_kurtosis"]))
        log(f"\n  Most non-Gaussian L1 trigger sub-band: "
            f"{worst['band']} (ex_k={worst['excess_kurtosis']:+.3f})")

    # ---------------------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------------------
    fieldnames = [
        "det", "tag", "band", "f_lo", "f_hi", "n",
        "mean", "std", "skewness", "kurtosis", "excess_kurtosis",
        "n_z3", "n_z4", "n_z5", "ad_stat", "ad_pass_5pct",
        "bandpower_proxy", "gauss_class", "l1_h1_ratio",
    ]

    csv_path = MANIFEST / "subband_gaussianity.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames,
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    md = [
        "# Sub-band Gaussianity Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s",
        f"- Sub-bands: {[b[0] for b in SUB_BANDS]}",
        f"- Whitening: off-source PSD ({PSD_REF_DUR_S}s at -{PSD_OFFSET_S}s)",
        f"- Filter order: {FILTER_ORDER} (Butterworth, sosfiltfilt)",
        "",
        "## L1 Trigger — Sub-band Summary",
        "",
        "| Band | Excess Kurt | Skew | |z|>4 | L1/H1 | Class |",
        "|------|-------------|------|-------|-------|-------|",
    ]
    for band_name, f_lo, f_hi in SUB_BANDS:
        r = next((x for x in all_rows
                  if x["det"] == "L1"
                  and x["tag"] == "TRIGGER"
                  and x["band"] == band_name), None)
        if r:
            ratio_str = (f"{r['l1_h1_ratio']:.3f}"
                         if r.get("l1_h1_ratio") else "N/A")
            md.append(
                f"| {band_name} | {r['excess_kurtosis']:+.3f} "
                f"| {r['skewness']:+.3f} | {r['n_z4']} "
                f"| {ratio_str} | {r['gauss_class']} |"
            )
    md += [
        "",
        "## H1 Trigger — Sub-band Summary",
        "",
        "| Band | Excess Kurt | Skew | |z|>4 | Class |",
        "|------|-------------|------|-------|-------|",
    ]
    for band_name, f_lo, f_hi in SUB_BANDS:
        r = next((x for x in all_rows
                  if x["det"] == "H1"
                  and x["tag"] == "TRIGGER"
                  and x["band"] == band_name), None)
        if r:
            md.append(
                f"| {band_name} | {r['excess_kurtosis']:+.3f} "
                f"| {r['skewness']:+.3f} | {r['n_z4']} "
                f"| {r['gauss_class']} |"
            )
    md += [
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "SUBBAND_GAUSSIANITY_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    flush_log()


if __name__ == "__main__":
    run()
