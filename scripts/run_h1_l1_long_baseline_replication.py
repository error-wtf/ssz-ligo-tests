"""H1/L1 Long-Baseline Replication Test.

Extends the single off-source window test to a full background distribution
(-1000s to +1000s, safety exclusion +-64s). Tests whether trigger |xcorr|
is statistically distinct from the off-source population.

Key rule: Use argmax(|C(tau)|) not argmax(C(tau)).
Negative correlation is valid coherence for H1/L1 (opposite arm orientation).

Key interpretation:
  A high |corr| at the trigger is only meaningful if it is statistically
  stronger than comparable off-source windows processed in the same way.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
"""
import csv
import datetime
import numpy as np
import h5py
from pathlib import Path
from scipy import signal

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS    = Path(__file__).parent.parent / "logs"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for _d in (REPORTS, LOGS, MANIFEST):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "h1_l1_long_baseline_replication.log"
_log_lines = []

def log(msg=""):
    print(msg)
    _log_lines.append(str(msg))

def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TRIGGER_GPS       = 1411261107.984
SAFETY_EXCLUDE_S  = 64.0
OFFSOURCE_RANGE_S = 1000.0
N_OFFSOURCE_TARGET = 100
TRIGGER_DURATIONS  = [4.0, 8.0, 16.0, 32.0]
PHYSICAL_MAX_MS    = 10.012
FINE_MAX_MS        = 10.0
FINE_STEP_MS       = 0.244
REF_DUR_S          = 32.0
NPERSEG            = 1024
Z_THRESHOLD_INTERESTING = 3.0
Z_THRESHOLD_STRONG      = 5.0

SUBBANDS = [
    ("20-40",   20.0,  40.0),
    ("40-80",   40.0,  80.0),
    ("80-120",  80.0, 120.0),
    ("120-160", 120.0, 160.0),
    ("160-210", 160.0, 210.0),
    ("20-210",  20.0, 210.0),
]

_BASE = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_PATH = _BASE / "H1/1410334720/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
L1_PATH = _BASE / "L1/1410334720/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def ref_asd_from_file(path, dur=32.0):
    if not path.exists():
        return None, None
    with h5py.File(path, "r") as f:
        n_total   = f["strain/Strain"].shape[0]
        dur_file  = float(f["meta"]["Duration"][()])
        fs        = n_total / dur_file
        n_ref     = min(int(dur * fs), n_total // 2)
        offset    = n_total // 8
        strain    = f["strain/Strain"][offset:offset + n_ref].astype(float)
    if not np.all(np.isfinite(strain)) or len(strain) < NPERSEG * 4:
        return None, None
    nps = min(NPERSEG, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps, noverlap=nps//2, window="hann")
    return freqs, np.sqrt(np.maximum(psd, 1e-100))


def load_window(path, t_center, dur, pad_s=0.12):
    if not path.exists():
        return None, None
    with h5py.File(path, "r") as f:
        gps0     = float(f["meta"]["GPSstart"][()])
        n_total  = f["strain/Strain"].shape[0]
        dur_file = float(f["meta"]["Duration"][()])
        fs       = n_total / dur_file
        t_off    = t_center - gps0
        i0 = max(0, int((t_off - dur/2 - pad_s) * fs))
        i1 = min(n_total, int((t_off + dur/2 + pad_s) * fs))
        if i1 <= i0:
            return None, None
        strain = f["strain/Strain"][i0:i1].astype(float)
        t0     = gps0 + i0 / fs
    n_needed = int((dur + pad_s) * fs * 0.8)
    if not np.all(np.isfinite(strain)) or len(strain) < n_needed:
        return None, None
    i_center = int(round((t_center - t0 - dur/2) * fs))
    n_win    = int(round(dur * fs))
    if i_center < 0 or i_center + n_win > len(strain):
        return None, None
    return strain[i_center:i_center + n_win].copy(), float(fs)

# ---------------------------------------------------------------------------
# Signal processing
# ---------------------------------------------------------------------------
def bandpass(x, fs, f_lo, f_hi, order=4):
    nyq = fs / 2.0
    sos = signal.butter(order, [max(f_lo, 1.0), min(f_hi, nyq * 0.99)],
                        btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)

def whiten(x, fs, ref_f, ref_a):
    n  = len(x)
    ff = np.fft.rfftfreq(n, d=1.0/fs)
    ai = np.interp(ff, ref_f, ref_a + 1e-300)
    return np.fft.irfft(np.fft.rfft(x) / ai, n=n)

def prep(raw, fs, ref_f, ref_a, f_lo, f_hi):
    w  = whiten(raw, fs, ref_f, ref_a) if ref_f is not None else raw.copy()
    bp = bandpass(w, fs, f_lo, f_hi)
    s  = np.std(bp)
    return bp / (s + 1e-300)

# ---------------------------------------------------------------------------
# Core xcorr: argmax(|C(tau)|)
# ---------------------------------------------------------------------------
def best_abs_xcorr(h1_n, l1_n, fs):
    """Return (abs_corr, dt_ms, raw_corr) at the peak of |C(tau)|.

    Uses argmax(|C(tau)|) -- sign-convention-safe.
    A negative peak is a valid coherence result for H1/L1.
    """
    delays_ms = np.arange(-FINE_MAX_MS, FINE_MAX_MS + FINE_STEP_MS, FINE_STEP_MS)
    n    = len(h1_n)
    a    = h1_n - h1_n.mean()
    b    = l1_n - l1_n.mean()
    norm = np.sqrt(np.dot(a, a) * np.dot(b, b) + 1e-300)
    xc_full = np.fft.irfft(
        np.fft.rfft(a, n=2*n) * np.conj(np.fft.rfft(b, n=2*n)), n=2*n
    )[:2*n]
    xc_full = np.concatenate([xc_full[n+1:], xc_full[:n]]) / norm
    best_abs = 0.0; best_dt = 0.0; best_raw = 0.0
    for dt_ms in delays_ms:
        if abs(dt_ms) > PHYSICAL_MAX_MS:
            continue
        lag_samp = int(round(dt_ms / 1000.0 * fs))
        idx = lag_samp + (n - 1)
        if 0 <= idx < len(xc_full):
            xc = float(np.clip(xc_full[idx], -1.0, 1.0))
            if abs(xc) > best_abs:
                best_abs = abs(xc)
                best_dt  = float(dt_ms)
                best_raw = xc
    return best_abs, best_dt, best_raw


def mean_band_coherence(h1_n, l1_n, fs, f_lo, f_hi):
    nps = min(NPERSEG, len(h1_n) // 4)
    if nps < 16:
        return float("nan")
    fc, coh = signal.coherence(h1_n, l1_n, fs=fs, nperseg=nps, noverlap=nps//2)
    mask = (fc >= f_lo) & (fc <= f_hi)
    return float(np.mean(coh[mask])) if mask.any() else float("nan")


def coherence_excess(h1_n_trig, l1_n_trig, h1_n_off, l1_n_off, fs, f_lo, f_hi):
    """coherence(trigger) - coherence(off-source) per band."""
    c_trig = mean_band_coherence(h1_n_trig, l1_n_trig, fs, f_lo, f_hi)
    c_off  = mean_band_coherence(h1_n_off,  l1_n_off,  fs, f_lo, f_hi)
    if np.isfinite(c_trig) and np.isfinite(c_off):
        return float(c_trig - c_off)
    return float("nan")


# ---------------------------------------------------------------------------
# Off-source window generation
# ---------------------------------------------------------------------------
def make_offsource_times(trigger_gps, dur, n_target, baseline_s, safety_s):
    """Generate up to n_target off-source window center times."""
    step = max(dur * 1.5, (2 * baseline_s - 2 * safety_s) / n_target)
    times = []
    t = trigger_gps - baseline_s
    while t <= trigger_gps + baseline_s:
        if abs(t - trigger_gps) >= safety_s + dur / 2:
            times.append(t)
        t += step
        if len(times) >= n_target:
            break
    return times


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def classify_trigger_vs_background(trig_abs_corr, off_abs_corrs):
    """Classify trigger relative to off-source distribution.

    Returns (verdict, z_score, percentile)
    """
    off = [v for v in off_abs_corrs if np.isfinite(v)]
    if not off:
        return "INCONCLUSIVE", float("nan"), float("nan")
    mu    = float(np.mean(off))
    sigma = float(np.std(off)) if len(off) > 1 else 0.0
    z = (trig_abs_corr - mu) / (sigma + 1e-10)
    pct = float(np.mean(np.array(off) <= trig_abs_corr) * 100)
    if trig_abs_corr < mu - sigma:
        verdict = "BELOW_OFFSOURCE"
    elif z >= Z_THRESHOLD_STRONG:
        verdict = "TRIGGER_SPECIFIC"
    elif z >= Z_THRESHOLD_INTERESTING:
        verdict = "TRIGGER_SPECIFIC"
    elif abs(z) < 1.0:
        verdict = "CONSISTENT_WITH_OFFSOURCE"
    else:
        verdict = "INCONCLUSIVE"
    return verdict, float(z), float(pct)


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------
def run():
    log(f"H1/L1 LONG-BASELINE REPLICATION TEST -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}")
    log(f"Off-source range: +/-{OFFSOURCE_RANGE_S}s  Safety exclusion: +/-{SAFETY_EXCLUDE_S}s")
    log(f"Trigger durations: {TRIGGER_DURATIONS}s")
    log(f"Peak detection: argmax(|C(tau)|) -- sign-convention-safe")
    log("")

    log("Loading reference ASDs...")
    h1_rf, h1_ra = ref_asd_from_file(H1_PATH, dur=REF_DUR_S)
    l1_rf, l1_ra = ref_asd_from_file(L1_PATH, dur=REF_DUR_S)
    log(f"  H1 ref ASD: {'OK' if h1_rf is not None else 'FAILED'}")
    log(f"  L1 ref ASD: {'OK' if l1_rf is not None else 'FAILED'}")

    if h1_rf is None or l1_rf is None:
        log("FATAL: could not load reference ASDs. Check HDF5 paths.")
        flush_log()
        return

    all_xcorr_rows = []
    all_quantile_rows = []

    for dur in TRIGGER_DURATIONS:
        log(f"\n{'='*65}")
        log(f"TRIGGER DURATION: {dur}s")
        log(f"{'='*65}")

        # --- Trigger window ---
        h1_trig, fs_h1 = load_window(H1_PATH, TRIGGER_GPS, dur)
        l1_trig, fs_l1 = load_window(L1_PATH, TRIGGER_GPS, dur)
        if h1_trig is None or l1_trig is None:
            log("  TRIGGER LOAD FAILED -- skip duration")
            continue
        fs = fs_h1
        log(f"  Trigger loaded: fs={fs:.0f}Hz  H1={len(h1_trig)} L1={len(l1_trig)} samples")

        # --- Off-source window times ---
        off_times = make_offsource_times(
            TRIGGER_GPS, dur, N_OFFSOURCE_TARGET, OFFSOURCE_RANGE_S, SAFETY_EXCLUDE_S
        )
        log(f"  Off-source windows attempted: {len(off_times)}")

        # Pre-load off-source windows
        off_windows = []
        for t_off in off_times:
            h1_off, _ = load_window(H1_PATH, t_off, dur)
            l1_off, _ = load_window(L1_PATH, t_off, dur)
            if h1_off is not None and l1_off is not None:
                off_windows.append((t_off, h1_off, l1_off))
        log(f"  Off-source windows loaded successfully: {len(off_windows)}")

        for band_name, f_lo, f_hi in SUBBANDS:
            log(f"\n  Band: {band_name} Hz ({f_lo}–{f_hi})")

            # Prepare trigger
            h1_t_n = prep(h1_trig, fs, h1_rf, h1_ra, f_lo, f_hi)
            l1_t_n = prep(l1_trig, fs, l1_rf, l1_ra, f_lo, f_hi)
            trig_abs, trig_dt, trig_raw = best_abs_xcorr(h1_t_n, l1_t_n, fs)
            trig_coh = mean_band_coherence(h1_t_n, l1_t_n, fs, f_lo, f_hi)

            all_xcorr_rows.append({
                "window_type": "TRIGGER",
                "t_center":    round(TRIGGER_GPS, 3),
                "t_offset_s":  0.0,
                "dur_s":       dur,
                "band":        band_name,
                "abs_corr":    round(trig_abs, 7),
                "raw_corr":    round(trig_raw, 7),
                "peak_dt_ms":  round(trig_dt, 3),
                "mean_coh":    round(trig_coh, 6) if np.isfinite(trig_coh) else "",
            })

            # Prepare off-source
            off_abs_corrs = []
            for t_off, h1_off, l1_off in off_windows:
                h1_o_n = prep(h1_off, fs, h1_rf, h1_ra, f_lo, f_hi)
                l1_o_n = prep(l1_off, fs, l1_rf, l1_ra, f_lo, f_hi)
                abs_c, dt_c, raw_c = best_abs_xcorr(h1_o_n, l1_o_n, fs)
                coh_c = mean_band_coherence(h1_o_n, l1_o_n, fs, f_lo, f_hi)
                off_abs_corrs.append(abs_c)
                all_xcorr_rows.append({
                    "window_type": "OFFSOURCE",
                    "t_center":    round(t_off, 3),
                    "t_offset_s":  round(t_off - TRIGGER_GPS, 1),
                    "dur_s":       dur,
                    "band":        band_name,
                    "abs_corr":    round(abs_c, 7),
                    "raw_corr":    round(raw_c, 7),
                    "peak_dt_ms":  round(dt_c, 3),
                    "mean_coh":    round(coh_c, 6) if np.isfinite(coh_c) else "",
                })

            # Classification
            verdict, z, pct = classify_trigger_vs_background(trig_abs, off_abs_corrs)
            off_valid = [v for v in off_abs_corrs if np.isfinite(v)]
            off_mu    = float(np.mean(off_valid))  if off_valid else float("nan")
            off_sigma = float(np.std(off_valid))   if len(off_valid) > 1 else float("nan")
            off_p95   = float(np.percentile(off_valid, 95)) if off_valid else float("nan")
            off_p99   = float(np.percentile(off_valid, 99)) if off_valid else float("nan")

            sign_label = "OPPOSITE_SIGN" if trig_raw < 0 else "SAME_SIGN"

            log(f"    TRIGGER:  abs_corr={trig_abs:.5f}  raw={trig_raw:+.5f}  dt={trig_dt:+.2f}ms  sign={sign_label}")
            log(f"    OFFSOURCE ({len(off_valid)} windows): mean={off_mu:.5f}  sigma={off_sigma:.5f}  p95={off_p95:.5f}  p99={off_p99:.5f}")
            log(f"    Z-score:  {z:.2f}    percentile: {pct:.1f}%")
            log(f"    VERDICT:  {verdict}")

            if verdict == "CONSISTENT_WITH_OFFSOURCE":
                log(f"    NOTE: Trigger abs_corr is not above off-source distribution.")
                log(f"          This indicates stationary common-mode coupling.")
                log(f"          Not event-specific. Cannot support signal claim.")
            elif verdict == "TRIGGER_SPECIFIC":
                log(f"    NOTE: Trigger abs_corr is statistically elevated (Z={z:.1f}).")
                log(f"          Requires further coherence-phase and DQ checks.")
            elif verdict == "BELOW_OFFSOURCE":
                log(f"    NOTE: Trigger abs_corr is below off-source mean.")

            all_quantile_rows.append({
                "dur_s":        dur,
                "band":         band_name,
                "trig_abs_corr": round(trig_abs, 7),
                "trig_raw_corr": round(trig_raw, 7),
                "trig_dt_ms":   round(trig_dt, 3),
                "trig_sign":    sign_label,
                "off_n":        len(off_valid),
                "off_mean":     round(off_mu, 7)    if np.isfinite(off_mu) else "",
                "off_sigma":    round(off_sigma, 7) if np.isfinite(off_sigma) else "",
                "off_p50":      round(float(np.percentile(off_valid, 50)), 7) if off_valid else "",
                "off_p95":      round(off_p95, 7)   if np.isfinite(off_p95) else "",
                "off_p99":      round(off_p99, 7)   if np.isfinite(off_p99) else "",
                "z_score":      round(z, 3)          if np.isfinite(z) else "",
                "percentile":   round(pct, 1)        if np.isfinite(pct) else "",
                "verdict":      verdict,
                "H1_L1_XCORR_TRIGGER_STATUS": verdict,
            })

    # ---------------------------------------------------------------------------
    # Write CSVs
    # ---------------------------------------------------------------------------
    xcorr_path = MANIFEST / "h1_l1_long_baseline_xcorr.csv"
    if all_xcorr_rows:
        with open(xcorr_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(all_xcorr_rows[0].keys()))
            w.writeheader(); w.writerows(all_xcorr_rows)
        log(f"\nCSV: {xcorr_path}  ({len(all_xcorr_rows)} rows)")

    quant_path = MANIFEST / "h1_l1_xcorr_quantiles.csv"
    if all_quantile_rows:
        with open(quant_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(all_quantile_rows[0].keys()))
            w.writeheader(); w.writerows(all_quantile_rows)
        log(f"CSV: {quant_path}  ({len(all_quantile_rows)} rows)")

    # ---------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------
    log(f"\n{'='*65}")
    log("FINAL SUMMARY")
    log(f"{'='*65}")

    md = [
        "# H1/L1 Long-Baseline Replication Report",
        f"Generated: {NOW}",
        "",
        "## Key Interpretation Rule",
        "",
        "> A high |corr| at the trigger is only meaningful if it is",
        "> statistically stronger than comparable off-source windows",
        "> processed in the same way.",
        "",
        "## Sign Convention",
        "",
        "Peak detection uses `argmax(|C(tau)|)`, not `argmax(C(tau))`.",
        "H1/L1 may be anti-correlated due to opposite arm orientations.",
        "Negative raw_corr with high abs_corr is a valid coherence result.",
        "",
        "```text",
        "corr = +0.99  ->  strongly co-directed",
        "corr = -0.99  ->  strongly counter-directed (same pattern, mirrored)",
        "|corr| = 0.99 ->  strongly coupled in either case",
        "```",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Off-source range: +/-{OFFSOURCE_RANGE_S}s",
        f"- Safety exclusion zone: +/-{SAFETY_EXCLUDE_S}s",
        f"- Target off-source windows: {N_OFFSOURCE_TARGET}",
        f"- Trigger durations tested: {TRIGGER_DURATIONS}s",
        f"- Physical H1/L1 delay range: |dt| <= {PHYSICAL_MAX_MS}ms",
        "",
        "## Results Summary",
        "",
        "| dur_s | band | trig_abs_corr | trig_sign | off_mean | off_p95 | z_score | verdict |",
        "|-------|------|---------------|-----------|----------|---------|---------|---------|",
    ]

    for row in all_quantile_rows:
        md.append(
            f"| {row['dur_s']} | {row['band']} "
            f"| {row['trig_abs_corr']} "
            f"| {row['trig_sign']} "
            f"| {row['off_mean']} "
            f"| {row['off_p95']} "
            f"| {row['z_score']} "
            f"| {row['verdict']} |"
        )

    md += [
        "",
        "## Classification Key",
        "",
        "```text",
        "TRIGGER_SPECIFIC:           trigger abs_corr > off-source by Z >= 3",
        "CONSISTENT_WITH_OFFSOURCE:  trigger in off-source distribution (Z < 1)",
        "BELOW_OFFSOURCE:            trigger below off-source mean",
        "INCONCLUSIVE:               ambiguous evidence",
        "```",
        "",
        "## Anti-Circularity",
        "- No PE/QNM posteriors used",
        "- No Kerr/SSZ parameters used",
        "- Peak detection: argmax(|C(tau)|)",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]

    rpath = REPORTS / "H1_L1_LONG_BASELINE_REPLICATION_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")
    log(f"Report: {rpath}")
    flush_log()


if __name__ == "__main__":
    run()
