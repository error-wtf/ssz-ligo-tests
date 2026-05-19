"""L1 STFT Omicron-Lite — Time-Frequency Burst vs Persistent Band.

Omicron-lite replacement using short-time FFT (STFT):
  - Computes spectrogram (STFT) for trigger and off-source windows.
  - Compares tile energies in 20-210 Hz band.
  - Classifies excess as: SINGLE_BURST, PERSISTENT_BAND, or NOISE_FLOOR.
  - Identifies time-frequency clusters above threshold.

This is NOT an official Omicron run. It is a simple pre-filter diagnostic.

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

LOG_PATH = LOGS / "l1_stft_omicron_lite.log"
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
OFF_WIN_S = 16.0           # longer off-source for better baseline
PSD_DUR_S = 64.0
PSD_OFFSET_S = 500.0
F_LOW, F_HIGH = 20.0, 210.0

# STFT parameters
STFT_NPERSEG = 512         # ~125 ms at 4096 Hz -> df ~8 Hz
STFT_NOVERLAP_FRAC = 0.75  # 75% overlap -> ~31 ms step

# Tile threshold: dB above median spectrogram tile in off-source
TILE_THRESHOLD_DB = 8.0

# Clustering: minimum adjacent tiles to be a "cluster"
MIN_CLUSTER_SIZE = 3

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
# SPECTROGRAM
# ---------------------------------------------------------------------------
def compute_spectrogram(strain, fs):
    nperseg = min(STFT_NPERSEG, len(strain) // 4)
    noverlap = int(nperseg * STFT_NOVERLAP_FRAC)
    freqs, times, Sxx = signal.spectrogram(
        strain, fs=fs, nperseg=nperseg, noverlap=noverlap,
        window="hann", scaling="density"
    )
    return freqs, times, Sxx


def band_mask(freqs, f_low=F_LOW, f_high=F_HIGH):
    return (freqs >= f_low) & (freqs <= f_high)


# ---------------------------------------------------------------------------
# TILE ANALYSIS
# ---------------------------------------------------------------------------
def analyse_tiles(freqs, times, Sxx, label, off_median=None):
    """
    Analyse time-frequency tiles in the band.
    off_median: per-frequency median from off-source (for normalization).
    """
    bm = band_mask(freqs)
    Sxx_b = Sxx[bm, :]   # shape (n_freq_band, n_time)
    f_b = freqs[bm]

    n_freq, n_time = Sxx_b.shape
    log(f"\n  [{label}] Spectrogram: {n_freq} freq bins x {n_time} time bins")
    log(f"    df={f_b[1]-f_b[0]:.2f}Hz  dt={times[1]-times[0]:.3f}s")

    # Normalize by off-source per-frequency median if available
    if off_median is not None:
        med_b = off_median[bm][:, np.newaxis]
        med_b = np.clip(med_b, 1e-60, None)
        Sxx_norm = Sxx_b / med_b
    else:
        med_b = np.median(Sxx_b, axis=1)[:, np.newaxis]
        med_b = np.clip(med_b, 1e-60, None)
        Sxx_norm = Sxx_b / med_b

    Sxx_db = 10.0 * np.log10(np.clip(Sxx_norm, 1e-10, None))

    # Bandpower per time bin
    bp_t = np.trapezoid(Sxx_b, f_b, axis=0)
    bp_mean = float(np.mean(bp_t))
    bp_std = float(np.std(bp_t))
    bp_max = float(np.max(bp_t))
    bp_max_t = float(times[np.argmax(bp_t)])

    log(f"    Band bandpower (mean): {bp_mean:.4e}")
    pct = bp_std / bp_mean * 100
    log(f"    Band bandpower (std):  {bp_std:.4e}  ({pct:.1f}%)")
    log(f"    Band bandpower (max):  {bp_max:.4e} at t={bp_max_t:.3f}s")

    # Hot tiles
    hot = Sxx_db > TILE_THRESHOLD_DB
    n_hot = int(np.sum(hot))
    n_total = Sxx_db.size
    log(f"    Hot tiles (>{TILE_THRESHOLD_DB}dB): {n_hot}/{n_total} "
        f"({n_hot/n_total*100:.1f}%)")

    # Time distribution of hot tiles
    hot_by_time = np.sum(hot, axis=0)
    hot_by_freq = np.sum(hot, axis=1)
    t_hot_frac = np.sum(hot_by_time > 0) / n_time
    log(f"    Time bins with hot tiles: {t_hot_frac*100:.1f}%")

    # Max hot-tile cluster (contiguous hot region)
    # Flatten to 1D per time bin — is any freq hot?
    any_hot_time = hot_by_time > 0
    max_cluster = 0
    cur = 0
    for v in any_hot_time:
        cur = cur + 1 if v else 0
        max_cluster = max(max_cluster, cur)
    log(f"    Max consecutive hot time bins: {max_cluster}")

    # Classification
    if t_hot_frac > 0.7:
        tf_class = "PERSISTENT_BAND"
    elif max_cluster >= MIN_CLUSTER_SIZE and t_hot_frac < 0.3:
        tf_class = "SINGLE_BURST_CANDIDATE"
    elif n_hot == 0:
        tf_class = "NOISE_FLOOR"
    else:
        tf_class = "SCATTERED_EXCESS"

    log(f"    TF class: {tf_class}")

    # Top hot frequency bins (most often hot)
    top_freq_idx = np.argsort(hot_by_freq)[::-1][:5]
    log("    Most frequent hot freq bins:")
    for idx in top_freq_idx:
        if hot_by_freq[idx] > 0:
            log(f"      {f_b[idx]:.1f}Hz  hot in "
                f"{hot_by_freq[idx]}/{n_time} time bins")

    return {
        "label": label,
        "n_freq": n_freq, "n_time": n_time,
        "bp_mean": bp_mean, "bp_std": bp_std,
        "bp_max": bp_max, "bp_max_t": bp_max_t,
        "n_hot": n_hot, "n_total": n_total,
        "t_hot_frac": round(t_hot_frac, 4),
        "max_cluster": max_cluster,
        "tf_class": tf_class,
        "Sxx_b": Sxx_b, "f_b": f_b, "times": times,
        "hot_by_time": hot_by_time, "hot_by_freq": hot_by_freq,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"L1 STFT OMICRON-LITE -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s  Band: {F_LOW}-{F_HIGH}Hz")
    log(f"STFT nperseg={STFT_NPERSEG}  noverlap={STFT_NOVERLAP_FRAC*100:.0f}%"
        f"  hot_threshold={TILE_THRESHOLD_DB}dB")

    results = []

    for det, path in [("H1", H1_PATH), ("L1", L1_PATH)]:
        log(f"\n{'='*60}")
        log(f"DETECTOR: {det}")
        log(f"{'='*60}")

        if not path.exists():
            log("  FILE NOT FOUND")
            continue

        # Load off-source first to get baseline median
        off_strain, fs = load_window(path, TRIGGER_GPS - PSD_OFFSET_S,
                                     OFF_WIN_S)
        if off_strain is None:
            log("  Off-source load failed")
            continue

        f_off, t_off_arr, Sxx_off = compute_spectrogram(off_strain, fs)
        bm = band_mask(f_off)
        # Per-frequency median over the entire off-source spectrogram
        Sxx_off_b = Sxx_off[bm, :]
        _ = np.median(Sxx_off_b, axis=1)  # kept for possible future use
        off_median_full = np.median(Sxx_off, axis=1)

        log(f"  Off-source baseline: fs={fs:.0f}Hz  "
            f"n={len(off_strain)}  spec shape={Sxx_off.shape}")

        # Trigger window
        trig_strain, _ = load_window(path, TRIGGER_GPS, WIN_S)
        if trig_strain is None:
            log("  Trigger load failed")
            continue

        f_trig, t_trig, Sxx_trig = compute_spectrogram(trig_strain, fs)
        r_trig = analyse_tiles(f_trig, t_trig, Sxx_trig,
                               f"{det}_TRIGGER", off_median_full)
        r_trig["det"] = det
        r_trig["tag"] = "TRIGGER"
        results.append(r_trig)

        # Off-source window (same duration as trigger)
        off4_strain, _ = load_window(path, TRIGGER_GPS - PSD_OFFSET_S, WIN_S)
        if off4_strain is not None:
            f_o, t_o, Sxx_o = compute_spectrogram(off4_strain, fs)
            r_off = analyse_tiles(f_o, t_o, Sxx_o,
                                  f"{det}_OFF_m500", off_median_full)
            r_off["det"] = det
            r_off["tag"] = "OFF_m500"
            results.append(r_off)

    # ---------------------------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("SUMMARY")
    log(f"{'='*60}")
    log(f"  {'Label':<25} {'BP mean':>12} {'Hot%':>8} "
        f"{'MaxCluster':>12} {'TF class'}")
    log("  " + "-" * 70)
    for r in results:
        log(f"  {r['label']:<25} {r['bp_mean']:>12.3e} "
            f"{r['t_hot_frac']*100:>7.1f}% "
            f"{r['max_cluster']:>12d}  {r['tf_class']}")

    # Key classification: trigger vs off-source
    l1_trig = next((r for r in results
                    if r["det"] == "L1" and r["tag"] == "TRIGGER"), None)
    l1_off = next((r for r in results
                   if r["det"] == "L1" and r["tag"] == "OFF_m500"), None)

    if l1_trig and l1_off:
        log(f"\n  KEY: L1 trigger TF class: {l1_trig['tf_class']}")
        log(f"  KEY: L1 off-source TF class: {l1_off['tf_class']}")
        if (l1_trig["tf_class"] == l1_off["tf_class"]
                == "PERSISTENT_BAND"):
            verdict = "CHRONIC_PERSISTENT_BAND_NOISE"
        elif (l1_trig["tf_class"] == "SINGLE_BURST_CANDIDATE"
              and l1_off["tf_class"] != "SINGLE_BURST_CANDIDATE"):
            verdict = "TRIGGER_SPECIFIC_BURST"
        else:
            verdict = "INCONCLUSIVE"
        log(f"  -> L1_STFT_VERDICT: {verdict}")

    # ---------------------------------------------------------------------------
    # WRITE OUTPUTS
    # ---------------------------------------------------------------------------
    out_rows = [{k: r[k] for k in
                 ["det", "tag", "bp_mean", "bp_std", "bp_max", "bp_max_t",
                  "n_hot", "n_total", "t_hot_frac", "max_cluster", "tf_class"]
                 } for r in results]

    csv_path = MANIFEST / "l1_stft_omicron_lite.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    md = [
        "# L1 STFT Omicron-Lite Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- STFT nperseg: {STFT_NPERSEG} ({STFT_NPERSEG/4096*1000:.0f} ms)",
        f"- Overlap: {STFT_NOVERLAP_FRAC*100:.0f}%",
        "- Hot tile threshold: "
        f"+{TILE_THRESHOLD_DB} dB over off-source median",
        f"- Band: {F_LOW}-{F_HIGH} Hz",
        "",
        "## Results",
        "",
        "| Det | Window | BP mean | Hot% | MaxCluster | TF Class |",
        "|-----|--------|---------|------|------------|----------|",
    ]
    for r in out_rows:
        md.append(
            f"| {r['det']} | {r['tag']} | {r['bp_mean']:.3e} "
            f"| {r['t_hot_frac']*100:.1f}% | {r['max_cluster']} "
            f"| {r['tf_class']} |"
        )
    md += [
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "L1_STFT_OMICRON_LITE_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    flush_log()


if __name__ == "__main__":
    run()
