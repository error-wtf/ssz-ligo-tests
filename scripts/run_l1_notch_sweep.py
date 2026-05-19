"""L1 Notch Sweep — Systematic Peak Removal.

Systematically removes the strongest 1, 3, 5, 10, 20 frequency peaks
from L1 PSD and recomputes bandpower.

If L1/H1 excess disappears after removing a few peaks: line-dominated.
If it persists: genuinely broadband excess.

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

LOG_PATH = LOGS / "l1_notch_sweep.log"
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
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 4096
NOTCH_HZ = 1.5       # Hz half-width per notch
N_NOTCH_STEPS = [0, 1, 3, 5, 10, 20]

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
# PSD + BANDPOWER
# ---------------------------------------------------------------------------
def compute_psd(strain, fs, nperseg=None):
    nps = nperseg or min(NPERSEG, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              window="hann", noverlap=nps // 2)
    return freqs, psd


def bandpower_from_psd(freqs, psd, f_lo=F_LOW, f_hi=F_HIGH):
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    return float(np.trapezoid(psd[mask], freqs[mask]))


def local_median_psd(freqs, psd, bw=8.0):
    df = freqs[1] - freqs[0]
    hw = max(1, int(bw / df))
    n = len(psd)
    med = np.zeros(n)
    for i in range(n):
        lo = max(0, i - hw)
        hi = min(n, i + hw + 1)
        med[i] = np.median(psd[lo:hi])
    return med


def find_top_peaks(freqs, psd, f_lo=F_LOW, f_hi=F_HIGH, n_top=20):
    """Find top N peaks by height above local median, in-band."""
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    f_b = freqs[mask]
    p_b = psd[mask]
    med = local_median_psd(f_b, p_b)
    ratio_db = 10.0 * np.log10(np.clip(p_b / (med + 1e-300), 1e-10, None))

    # Simple: sort by ratio_db descending, deduplicate by 2 Hz separation
    order = np.argsort(ratio_db)[::-1]
    selected = []
    for idx in order:
        pf = float(f_b[idx])
        if not any(abs(pf - sf) < 2.0 for sf in selected):
            selected.append(pf)
        if len(selected) >= n_top:
            break
    heights = [float(ratio_db[np.argmin(np.abs(f_b - pf))])
               for pf in selected]
    return selected, heights


def notch_psd(freqs, psd, peak_freqs, n_notch, notch_hz=NOTCH_HZ):
    """Zero out top n_notch peaks from peak_freqs list."""
    psd_n = psd.copy()
    for pf in peak_freqs[:n_notch]:
        nm = np.abs(freqs - pf) <= notch_hz
        psd_n[nm] = 0.0
    return psd_n


# ---------------------------------------------------------------------------
# ANALYSE ONE DETECTOR
# ---------------------------------------------------------------------------
def analyse_det(det, path, t_c):
    strain, fs = load_window(path, t_c, WIN_S)
    if strain is None:
        return None, None, None

    freqs, psd = compute_psd(strain, fs)
    peak_freqs, peak_heights = find_top_peaks(freqs, psd, n_top=max(N_NOTCH_STEPS))

    log(f"\n  [{det}]  Top peaks (sorted by height):")
    for pf, ph in zip(peak_freqs[:10], peak_heights[:10]):
        log(f"    {pf:7.2f} Hz  +{ph:.1f} dB")

    bp_series = {}
    for n in N_NOTCH_STEPS:
        psd_n = notch_psd(freqs, psd, peak_freqs, n)
        bp = bandpower_from_psd(freqs, psd_n)
        bp_series[n] = bp

    bp0 = bp_series[0]
    log(f"  Bandpower after notching N peaks:")
    for n in N_NOTCH_STEPS:
        frac = bp_series[n] / bp0
        log(f"    N={n:2d}:  {bp_series[n]:.4e}  ({frac*100:.1f}% of full)")

    return freqs, psd, bp_series, peak_freqs, peak_heights


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"L1 NOTCH SWEEP -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s  "
        f"Band: {F_LOW}-{F_HIGH}Hz  Notch: +/-{NOTCH_HZ}Hz")

    results = {}
    for det, path in [("H1", H1_PATH), ("L1", L1_PATH)]:
        log(f"\n{'='*60}")
        log(f"DETECTOR: {det}  (TRIGGER)")
        log(f"{'='*60}")
        res = analyse_det(det, path, TRIGGER_GPS)
        if res[0] is not None:
            results[det] = res

    # ---------------------------------------------------------------------------
    # L1/H1 RATIO SWEEP
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("L1/H1 BANDPOWER RATIO SWEEP")
    log(f"{'='*60}")
    log(f"  {'N notched':>10} {'H1 BP':>14} {'L1 BP':>14} "
        f"{'L1/H1':>8} {'L1 frac':>10}")
    log("  " + "-" * 62)

    sweep_rows = []
    if "H1" in results and "L1" in results:
        bp_h1 = results["H1"][2]
        bp_l1 = results["L1"][2]
        bp_l1_0 = bp_l1[0]
        for n in N_NOTCH_STEPS:
            h_bp = bp_h1[n]
            l_bp = bp_l1[n]
            ratio = l_bp / (h_bp + 1e-300)
            l1_frac = l_bp / (bp_l1_0 + 1e-300)
            log(f"  {n:>10}  {h_bp:>14.4e}  {l_bp:>14.4e}  "
                f"{ratio:>8.3f}  {l1_frac*100:>8.1f}%")
            sweep_rows.append({
                "n_notched": n,
                "h1_bp": h_bp, "l1_bp": l_bp,
                "l1_h1_ratio": round(ratio, 5),
                "l1_frac_remaining": round(l1_frac, 5),
            })

        # Verdict
        ratio_0 = sweep_rows[0]["l1_h1_ratio"]
        ratio_10 = next((r["l1_h1_ratio"] for r in sweep_rows
                         if r["n_notched"] == 10), None)
        if ratio_10 and ratio_0 > 0:
            ratio_change = ratio_10 / ratio_0
            log(f"\n  L1/H1 ratio change after 10 notches: "
                f"{ratio_change*100:.1f}% of original")
            if ratio_change < 0.5:
                sweep_verdict = "NOTCHING_ELIMINATES_EXCESS"
            elif ratio_change < 0.8:
                sweep_verdict = "NOTCHING_PARTIALLY_EXPLAINS_EXCESS"
            else:
                sweep_verdict = "EXCESS_PERSISTS_BROADBAND"
            log(f"  -> SWEEP_VERDICT: {sweep_verdict}")

    # ---------------------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------------------
    peaks_rows = []
    for det in ["H1", "L1"]:
        if det in results and results[det][0] is not None:
            for rank, (pf, ph) in enumerate(
                    zip(results[det][3], results[det][4])):
                peaks_rows.append({
                    "det": det, "rank": rank + 1,
                    "freq_hz": round(pf, 3),
                    "height_db": round(ph, 2),
                })

    peaks_csv = MANIFEST / "l1_notch_sweep_peaks.csv"
    with open(peaks_csv, "w", newline="", encoding="utf-8") as fh:
        if peaks_rows:
            w = csv.DictWriter(fh, fieldnames=list(peaks_rows[0].keys()))
            w.writeheader()
            w.writerows(peaks_rows)

    sweep_csv = MANIFEST / "l1_notch_sweep_ratios.csv"
    with open(sweep_csv, "w", newline="", encoding="utf-8") as fh:
        if sweep_rows:
            w = csv.DictWriter(fh, fieldnames=list(sweep_rows[0].keys()))
            w.writeheader()
            w.writerows(sweep_rows)

    md = [
        "# L1 Notch Sweep Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s  Band: {F_LOW}-{F_HIGH}Hz",
        f"- Notch width: +/-{NOTCH_HZ}Hz per peak",
        f"- N notch steps: {N_NOTCH_STEPS}",
        "",
        "## L1/H1 Ratio Sweep",
        "",
        "| N notched | H1 BP | L1 BP | L1/H1 ratio | L1 remaining |",
        "|-----------|-------|-------|-------------|--------------|",
    ]
    for r in sweep_rows:
        md.append(
            f"| {r['n_notched']} | {r['h1_bp']:.3e} "
            f"| {r['l1_bp']:.3e} | {r['l1_h1_ratio']:.3f} "
            f"| {r['l1_frac_remaining']*100:.1f}% |"
        )
    md += [
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "L1_NOTCH_SWEEP_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {peaks_csv}")
    log(f"  {sweep_csv}")
    flush_log()


if __name__ == "__main__":
    run()
