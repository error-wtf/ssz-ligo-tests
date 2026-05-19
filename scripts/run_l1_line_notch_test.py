"""L1 Line / Narrowband Test — 20-210 Hz.

Questions:
  Is the L1 bandpower excess broadband or concentrated in narrow lines?
  Does the excess survive after notching known peaks?

Method:
  1. Compute Welch PSD for H1 and L1 in trigger window.
  2. Find peaks above threshold (> 6 dB over local median).
  3. Mark known instrumental/calibration/suspension lines.
  4. Compute bandpower WITH and WITHOUT notched peaks.
  5. Compare L1 vs H1 notched/un-notched bandpower ratio.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
"""
import datetime
import csv
import numpy as np
import h5py
from pathlib import Path
from scipy import signal

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for _d in (REPORTS, LOGS, MANIFEST):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "l1_line_notch_test.log"
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
PSD_DUR_S = 64.0
PSD_OFFSET_S = 500.0
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 4096

# Peak detection
PEAK_THRESHOLD_DB = 6.0    # dB above local median
LOCAL_MEDIAN_BW = 10.0     # Hz — bandwidth for local median estimation
MIN_PEAK_SEPARATION = 2.0  # Hz

# Notch width
NOTCH_HZ = 2.0  # Hz each side of peak

# Known LIGO instrumental lines (approximate — not exhaustive)
# Sources: LIGO DCC, known calibration/suspension/mains frequencies
KNOWN_LINES = {
    "mains_60": 60.0,
    "mains_120": 120.0,
    "mains_180": 180.0,
    "mains_240": 240.0,  # outside band but noted
    "cal_line_1": 35.9,
    "cal_line_2": 36.7,
    "violin_mode_1": 500.1,  # outside band
    "suspension_41": 41.0,
}
KNOWN_LINE_FREQS = np.array(list(KNOWN_LINES.values()))

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
# PSD
# ---------------------------------------------------------------------------
def compute_psd(strain, fs, nperseg=None):
    nperseg = nperseg or min(NPERSEG, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nperseg,
                              window="hann", noverlap=nperseg // 2)
    return freqs, psd


# ---------------------------------------------------------------------------
# PEAK DETECTION
# ---------------------------------------------------------------------------
def local_median_psd(freqs, psd, bw=LOCAL_MEDIAN_BW):
    """Per-frequency local median PSD over a ±bw Hz sliding window."""
    df = freqs[1] - freqs[0]
    hw = int(bw / df)
    n = len(psd)
    med = np.zeros(n)
    for i in range(n):
        lo = max(0, i - hw)
        hi = min(n, i + hw + 1)
        med[i] = np.median(psd[lo:hi])
    return med


def find_peaks_above_threshold(freqs, psd, f_low=F_LOW, f_high=F_HIGH,
                               threshold_db=PEAK_THRESHOLD_DB,
                               min_sep_hz=MIN_PEAK_SEPARATION):
    mask = (freqs >= f_low) & (freqs <= f_high)
    f_b = freqs[mask]
    p_b = psd[mask]
    med = local_median_psd(f_b, p_b)

    ratio_db = 10.0 * np.log10(np.clip(p_b / (med + 1e-300), 1e-10, None))
    above = ratio_db > threshold_db

    peak_freqs = []
    peak_heights_db = []
    peak_psd = []

    i = 0
    while i < len(f_b):
        if above[i]:
            # Find local maximum in this run
            j = i
            while j < len(f_b) and above[j]:
                j += 1
            seg = slice(i, j)
            best = np.argmax(ratio_db[seg]) + i
            if (not peak_freqs or
                    (f_b[best] - peak_freqs[-1]) > min_sep_hz):
                peak_freqs.append(float(f_b[best]))
                peak_heights_db.append(float(ratio_db[best]))
                peak_psd.append(float(p_b[best]))
            i = j
        else:
            i += 1

    return (np.array(peak_freqs), np.array(peak_heights_db),
            np.array(peak_psd))


def classify_peak(freq, tol_hz=2.0):
    """Check if a peak frequency matches a known instrumental line."""
    dists = np.abs(KNOWN_LINE_FREQS - freq)
    idx = np.argmin(dists)
    if dists[idx] <= tol_hz:
        name = list(KNOWN_LINES.keys())[idx]
        return f"KNOWN_LINE:{name}@{KNOWN_LINE_FREQS[idx]:.1f}Hz"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# BANDPOWER
# ---------------------------------------------------------------------------
def bandpower(freqs, psd, f_low=F_LOW, f_high=F_HIGH):
    """Integrate PSD over band using trapezoidal rule."""
    mask = (freqs >= f_low) & (freqs <= f_high)
    return float(np.trapezoid(psd[mask], freqs[mask]))


def notched_psd(freqs, psd, peak_freqs, notch_hz=NOTCH_HZ):
    """Zero out PSD within ±notch_hz of each peak — returns copy."""
    psd_n = psd.copy()
    for pf in peak_freqs:
        nm = np.abs(freqs - pf) <= notch_hz
        psd_n[nm] = 0.0
    return psd_n


# ---------------------------------------------------------------------------
# ANALYSE ONE WINDOW
# ---------------------------------------------------------------------------
def analyse_window(det, path, t_center, dur, tag):
    strain, fs = load_window(path, t_center, dur)
    if strain is None:
        log(f"  [{det} {tag}] load failed")
        return None

    freqs, psd = compute_psd(strain, fs)
    bp_full = bandpower(freqs, psd)

    peak_freqs, peak_dbs, peak_psds = find_peaks_above_threshold(freqs, psd)

    log(f"\n  [{det} {tag}]  bandpower={bp_full:.4e}")
    log(f"    Peaks in {F_LOW}-{F_HIGH}Hz ({len(peak_freqs)} found, "
        f">+{PEAK_THRESHOLD_DB}dB over local median):")

    peak_rows = []
    for pf, pdb, pp in zip(peak_freqs, peak_dbs, peak_psds):
        cls = classify_peak(pf)
        log(f"      {pf:7.2f} Hz  +{pdb:.1f} dB  {cls}")
        peak_rows.append({"det": det, "tag": tag,
                          "freq_hz": round(pf, 3),
                          "height_db": round(pdb, 2),
                          "classification": cls})

    # Bandpower with and without peaks notched
    psd_notched = notched_psd(freqs, psd, peak_freqs)
    bp_notched = bandpower(freqs, psd_notched)
    notch_frac = (bp_full - bp_notched) / (bp_full + 1e-300)

    log(f"    Bandpower (full):    {bp_full:.4e}")
    log(f"    Bandpower (notched): {bp_notched:.4e}")
    log(f"    Fraction in peaks:   {notch_frac*100:.1f}%")

    if notch_frac > 0.5:
        structure = "LINE_DOMINATED"
    elif notch_frac > 0.2:
        structure = "PARTIALLY_LINE_DOMINATED"
    else:
        structure = "BROADBAND_EXCESS"

    log(f"    Structure class: {structure}")

    return {
        "det": det, "tag": tag,
        "bp_full": bp_full, "bp_notched": bp_notched,
        "notch_frac": round(notch_frac, 4),
        "n_peaks": len(peak_freqs),
        "structure": structure,
        "peak_rows": peak_rows,
        "freqs": freqs, "psd": psd, "psd_notched": psd_notched,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"L1 LINE / NOTCH TEST -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s  "
        f"Band: {F_LOW}-{F_HIGH}Hz  Threshold: +{PEAK_THRESHOLD_DB}dB")
    log(f"Notch width: +/-{NOTCH_HZ}Hz per peak")

    log(f"\n{'='*60}")
    log("TRIGGER WINDOW ANALYSIS")
    log(f"{'='*60}")

    h1_trig = analyse_window("H1", H1_PATH, TRIGGER_GPS, WIN_S, "TRIGGER")
    l1_trig = analyse_window("L1", L1_PATH, TRIGGER_GPS, WIN_S, "TRIGGER")

    # Off-source for comparison
    log(f"\n{'='*60}")
    log("OFF-SOURCE WINDOW ANALYSIS (L1, -500s)")
    log(f"{'='*60}")
    l1_off = analyse_window("L1", L1_PATH, TRIGGER_GPS - 500.0,
                            WIN_S, "OFF_m500")

    # ---------------------------------------------------------------------------
    # CROSS-COMPARISON
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("CROSS-COMPARISON")
    log(f"{'='*60}")

    if h1_trig and l1_trig:
        ratio_full = l1_trig["bp_full"] / (h1_trig["bp_full"] + 1e-300)
        ratio_notched = (l1_trig["bp_notched"]
                         / (h1_trig["bp_notched"] + 1e-300))
        log(f"  L1/H1 bandpower ratio (full):    {ratio_full:.3f}")
        log(f"  L1/H1 bandpower ratio (notched): {ratio_notched:.3f}")
        ratio_change = ratio_notched / (ratio_full + 1e-300)
        log(f"  Ratio change after notching:     {ratio_change:.3f}")
        if ratio_change < 0.7:
            notch_verdict = "NOTCHING_REDUCES_EXCESS_SIGNIFICANTLY"
        elif ratio_change < 0.9:
            notch_verdict = "NOTCHING_PARTIALLY_EXPLAINS_EXCESS"
        else:
            notch_verdict = "EXCESS_PERSISTS_AFTER_NOTCHING"
        log(f"  -> {notch_verdict}")

    if l1_trig and l1_off:
        log(f"\n  L1 trigger  structure: {l1_trig['structure']}")
        log(f"  L1 off-500s structure: {l1_off['structure']}")
        log(f"  L1 trigger  n_peaks: {l1_trig['n_peaks']}")
        log(f"  L1 off-500s n_peaks: {l1_off['n_peaks']}")
        log(f"  L1 trigger  notch_frac: {l1_trig['notch_frac']*100:.1f}%")
        log(f"  L1 off-500s notch_frac: {l1_off['notch_frac']*100:.1f}%")

        if (l1_trig["structure"] == "LINE_DOMINATED"
                and l1_off["structure"] == "LINE_DOMINATED"):
            structure_verdict = "CHRONIC_LINE_DOMINATED"
        elif l1_trig["notch_frac"] > l1_off["notch_frac"] * 1.5:
            structure_verdict = "TRIGGER_MORE_LINE_DOMINATED"
        else:
            structure_verdict = "CONSISTENT_LINE_STRUCTURE_BOTH_WINDOWS"
        log(f"  -> {structure_verdict}")

    # ---------------------------------------------------------------------------
    # WRITE OUTPUTS
    # ---------------------------------------------------------------------------
    # Collect all peak rows
    all_peaks = []
    for res in [h1_trig, l1_trig, l1_off]:
        if res:
            all_peaks.extend(res.get("peak_rows", []))

    peak_path = MANIFEST / "l1_line_notch_peaks.csv"
    if all_peaks:
        with open(peak_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(all_peaks[0].keys()),
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(all_peaks)

    # Summary CSV
    summary_rows = []
    for res in [h1_trig, l1_trig, l1_off]:
        if res:
            summary_rows.append({
                k: res[k] for k in
                ["det", "tag", "bp_full", "bp_notched",
                 "notch_frac", "n_peaks", "structure"]
            })
    sum_path = MANIFEST / "l1_line_notch_summary.csv"
    sum_fields = ["det", "tag", "bp_full", "bp_notched",
                  "notch_frac", "n_peaks", "structure"]
    with open(sum_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sum_fields)
        w.writeheader()
        w.writerows(summary_rows)

    # Markdown report
    md = [
        "# L1 Line / Notch Test Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s",
        f"- Band: {F_LOW}-{F_HIGH} Hz",
        f"- Peak threshold: +{PEAK_THRESHOLD_DB} dB over local median",
        f"- Notch width: +/-{NOTCH_HZ} Hz per peak",
        "",
        "## Bandpower Summary",
        "",
        "| Det | Window | BP full | BP notched | In-line % | N peaks"
        " | Structure |",
        "|-----|--------|---------|------------|-----------|---------|"
        "-----------|",
    ]
    for r in summary_rows:
        md.append(
            f"| {r['det']} | {r['tag']} | {r['bp_full']:.3e} "
            f"| {r['bp_notched']:.3e} | {r['notch_frac']*100:.1f}% "
            f"| {r['n_peaks']} | {r['structure']} |"
        )
    md += [
        "",
        "## Peak List",
        "",
        "| Det | Window | Freq (Hz) | Height (dB) | Classification |",
        "|-----|--------|-----------|-------------|----------------|",
    ]
    for p in all_peaks:
        md.append(
            f"| {p['det']} | {p['tag']} | {p['freq_hz']:.2f} "
            f"| +{p['height_db']:.1f} | {p['classification']} |"
        )
    md += [
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "L1_LINE_NOTCH_TEST_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {peak_path}")
    log(f"  {sum_path}")
    flush_log()


if __name__ == "__main__":
    run()
