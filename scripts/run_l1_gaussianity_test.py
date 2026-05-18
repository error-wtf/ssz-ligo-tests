"""L1 / H1 Gaussianity Test — whitened strain, event vs off-source.

Tests whether the whitened strain in the event window is consistent
with Gaussian N(0,1) noise — separately for H1 and L1.

Checks (per window):
  mean, std, skewness, kurtosis, excess kurtosis
  count |z|>3, |z|>4, |z|>5
  Anderson-Darling test (scipy)
  KS test against N(0,1)

Windows tested:
  TRIGGER   : event window (WIN_S around TRIGGER_GPS)
  OFF_m500  : -500s before trigger
  OFF_m300  : -300s before trigger
  OFF_m100  : -100s before trigger

Frequency variants:
  FULLBAND  : whitened broadband (10-1700 Hz after whitening)
  BAND_20_210 : bandpassed 20-210 Hz after whitening

Anti-circularity: No SSZ. No claim. Pure data-quality diagnostic.

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
for _d in (REPORTS, LOGS):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "l1_gaussianity_test.log"
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
PSD_DUR_S = 64.0          # off-source PSD estimation window
PSD_OFFSET_S = 500.0      # how far before trigger for PSD
NPERSEG = 4096

F_LOW, F_HIGH = 20.0, 210.0

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
    return strain.astype(float), fs


# ---------------------------------------------------------------------------
# WHITENING
# ---------------------------------------------------------------------------
def whiten(strain, fs, psd_strain, psd_nperseg=NPERSEG):
    """
    Whiten strain using PSD estimated from psd_strain.
    Returns whitened time series, unit-variance if noise is stationary.
    """
    nperseg = min(psd_nperseg, len(psd_strain) // 4)
    freqs, psd = signal.welch(psd_strain, fs=fs, nperseg=nperseg,
                              window="hann", noverlap=nperseg // 2)

    # FFT of target strain
    n = len(strain)
    s_fft = np.fft.rfft(strain)
    f_fft = np.fft.rfftfreq(n, 1.0 / fs)

    # Interpolate PSD to FFT frequency grid
    psd_interp = np.interp(f_fft, freqs, psd)
    psd_interp = np.clip(psd_interp, 1e-60, None)

    # Whiten: divide by sqrt(PSD * df/2) — keeps unit variance
    df = fs / n
    amp_norm = np.sqrt(psd_interp * fs / 2.0)
    s_white_fft = s_fft / amp_norm

    # Zero DC and Nyquist
    s_white_fft[0] = 0.0
    if n % 2 == 0:
        s_white_fft[-1] = 0.0

    return np.fft.irfft(s_white_fft, n=n)


def bandpass(s, fs, f_low=F_LOW, f_high=F_HIGH):
    nyq = fs / 2.0
    b, a = signal.butter(4, [f_low / nyq, f_high / nyq], btype="band")
    return signal.filtfilt(b, a, s)


# ---------------------------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------------------------
def gaussianity_stats(z, label):
    """Compute full Gaussianity statistics on z-scored array."""
    n = len(z)
    mu = float(np.mean(z))
    sigma = float(np.std(z))
    skew = float(stats.skew(z))
    kurt = float(stats.kurtosis(z, fisher=False))  # normal=3
    excess_kurt = kurt - 3.0
    n_3s = int(np.sum(np.abs(z) > 3.0))
    n_4s = int(np.sum(np.abs(z) > 4.0))
    n_5s = int(np.sum(np.abs(z) > 5.0))
    exp_3s = int(round(n * 2 * (1 - stats.norm.cdf(3.0))))
    exp_4s = int(round(n * 2 * (1 - stats.norm.cdf(4.0))))
    exp_5s = int(round(n * 2 * (1 - stats.norm.cdf(5.0))))

    # Anderson-Darling
    ad_stat, ad_crit, ad_sig = stats.anderson(z, dist="norm")
    ad_pass = bool(ad_stat < ad_crit[2])  # 5% significance level

    # KS test
    ks_stat, ks_pval = stats.kstest(z, "norm", args=(0, 1))

    log(f"  [{label}] n={n}  mu={mu:+.4f}  sigma={sigma:.4f}  "
        f"skew={skew:+.4f}  kurt={kurt:.3f}  ex_kurt={excess_kurt:+.3f}")
    log(f"    |z|>3: {n_3s} (exp {exp_3s})  "
        f"|z|>4: {n_4s} (exp {exp_4s})  "
        f"|z|>5: {n_5s} (exp {exp_5s})")
    log(f"    AD stat={ad_stat:.4f}  AD 5% crit={ad_crit[2]:.4f}  "
        f"-> {'PASS' if ad_pass else 'FAIL'}")
    log(f"    KS stat={ks_stat:.4f}  KS p={ks_pval:.4e}  "
        f"-> {'PASS' if ks_pval > 0.05 else 'FAIL'}")

    # Verdict
    flags = []
    if abs(mu) > 0.1:
        flags.append("NONZERO_MEAN")
    if sigma < 0.8 or sigma > 1.3:
        flags.append(f"STD_ANOMALOUS({sigma:.3f})")
    if abs(excess_kurt) > 1.0:
        flags.append(f"KURTOSIS_EXCESS({excess_kurt:+.2f})")
    if n_4s > max(1, 3 * exp_4s):
        flags.append(f"EXCESS_OUTLIERS_4s({n_4s}vs{exp_4s})")
    if not ad_pass:
        flags.append("AD_FAIL")
    if ks_pval < 0.01:
        flags.append("KS_FAIL")

    if not flags:
        verdict = "GAUSSIAN"
    else:
        verdict = "NON_GAUSSIAN:" + ",".join(flags)

    log(f"    VERDICT: {verdict}")
    return {
        "label": label, "n": n, "mean": mu, "std": sigma,
        "skew": skew, "kurtosis": kurt, "excess_kurtosis": excess_kurt,
        "n_3s": n_3s, "exp_3s": exp_3s,
        "n_4s": n_4s, "exp_4s": exp_4s,
        "n_5s": n_5s, "exp_5s": exp_5s,
        "ad_stat": ad_stat, "ad_5pct": ad_crit[2], "ad_pass": ad_pass,
        "ks_stat": ks_stat, "ks_pval": ks_pval,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# ANALYSE ONE DETECTOR
# ---------------------------------------------------------------------------
def analyse_detector(det_label, hdf5_path):
    log(f"\n{'='*60}")
    log(f"DETECTOR: {det_label}")
    log(f"{'='*60}")

    if not hdf5_path.exists():
        log("  FILE NOT FOUND — BLOCKED")
        return []

    # Load PSD estimation window (far off-source)
    psd_strain, fs = load_window(
        hdf5_path, TRIGGER_GPS - PSD_OFFSET_S, PSD_DUR_S
    )
    if psd_strain is None:
        log("  PSD window load failed — BLOCKED")
        return []
    log(f"  PSD source: -{PSD_OFFSET_S}s, {PSD_DUR_S}s, "
        f"fs={fs:.0f}Hz, n={len(psd_strain)}")

    all_windows = [("TRIGGER", 0.0)] + list(OFF_WINDOWS)
    rows = []

    for tag, offset in all_windows:
        t_center = TRIGGER_GPS + offset
        log(f"\n  --- {tag} (offset={offset:+.0f}s) ---")

        strain, _ = load_window(hdf5_path, t_center, WIN_S)
        if strain is None:
            log("  load failed")
            continue

        # Whiten
        w = whiten(strain, fs, psd_strain)

        # Trim edges (filter ringing): discard first/last 10%
        trim = max(1, len(w) // 10)
        w_trim = w[trim:-trim]

        # Normalize to zero mean / unit std from this window
        z_full = (w_trim - np.mean(w_trim)) / (np.std(w_trim) + 1e-300)

        # Bandpass version
        w_bp = bandpass(w_trim, fs)
        z_bp = (w_bp - np.mean(w_bp)) / (np.std(w_bp) + 1e-300)

        log(f"  FULLBAND whitened:")
        r_full = gaussianity_stats(z_full, f"{det_label}_{tag}_FULL")
        r_full.update({"detector": det_label, "tag": tag,
                       "band": "FULLBAND", "offset_s": offset})
        rows.append(r_full)

        log(f"  BAND {F_LOW}-{F_HIGH}Hz whitened+bandpassed:")
        r_bp = gaussianity_stats(z_bp, f"{det_label}_{tag}_BP")
        r_bp.update({"detector": det_label, "tag": tag,
                     "band": f"{F_LOW}-{F_HIGH}Hz", "offset_s": offset})
        rows.append(r_bp)

    return rows


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"L1/H1 GAUSSIANITY TEST — {NOW}")
    log(f"Trigger GPS: {TRIGGER_GPS} | Win: {WIN_S}s | "
        f"PSD: -{PSD_OFFSET_S}s x {PSD_DUR_S}s")
    log(f"Band: {F_LOW}-{F_HIGH} Hz | Whitening: PSD-division in freq domain")

    all_rows = []
    for det_label, path in [("H1", H1_PATH), ("L1", L1_PATH)]:
        rows = analyse_detector(det_label, path)
        all_rows.extend(rows)

    # ---------------------------------------------------------------------------
    # SUMMARY COMPARISON
    # ---------------------------------------------------------------------------
    log("\n" + "=" * 60)
    log("SUMMARY COMPARISON")
    log("=" * 60)

    for band in ["FULLBAND", f"{F_LOW}-{F_HIGH}Hz"]:
        log(f"\n  Band: {band}")
        log(f"  {'Label':<30} {'sigma':>7} {'ex_kurt':>9} "
            f"{'|z|>4':>7} {'exp4':>6} {'verdict'}")
        log("  " + "-" * 80)
        for r in all_rows:
            if r.get("band") != band:
                continue
            lbl = f"{r['detector']}_{r['tag']}"
            log(f"  {lbl:<30} {r['std']:>7.3f} {r['excess_kurtosis']:>+9.3f} "
                f"{r['n_4s']:>7d} {r['exp_4s']:>6d}  {r['verdict'][:40]}")

    # Key question: is L1 trigger more non-Gaussian than L1 off-source?
    log("\n  KEY QUESTION: L1 trigger vs L1 off-source (non-Gaussianity)")
    l1_trig = [r for r in all_rows
               if r["detector"] == "L1" and r["tag"] == "TRIGGER"]
    l1_off = [r for r in all_rows
              if r["detector"] == "L1" and r["tag"] != "TRIGGER"]
    for rt in l1_trig:
        band = rt["band"]
        off_kurts = [r["excess_kurtosis"] for r in l1_off
                     if r["band"] == band]
        mean_off = float(np.mean(off_kurts)) if off_kurts else 0.0
        diff = rt["excess_kurtosis"] - mean_off
        interpretation = (
            "TRIGGER_MORE_NON_GAUSSIAN" if diff > 1.0
            else "TRIGGER_SIMILAR_TO_OFF_SOURCE"
        )
        log(f"  [{band}] trigger ex_kurt={rt['excess_kurtosis']:+.3f}  "
            f"off_mean={mean_off:+.3f}  diff={diff:+.3f}  "
            f"-> {interpretation}")

    # ---------------------------------------------------------------------------
    # WRITE REPORTS
    # ---------------------------------------------------------------------------
    # Markdown
    md = ["# L1/H1 Gaussianity Test", f"Generated: {NOW}", "",
          "## Configuration",
          f"- Trigger GPS: {TRIGGER_GPS}",
          f"- Window: {WIN_S}s",
          f"- PSD source: -{PSD_OFFSET_S}s x {PSD_DUR_S}s",
          f"- Band tested: {F_LOW}-{F_HIGH} Hz",
          "- Whitening: divide FFT by sqrt(PSD*fs/2)",
          "", "## Results", ""]

    for r in all_rows:
        md.append(
            f"| {r['detector']} | {r['tag']} | {r['band']} | "
            f"sigma={r['std']:.3f} | ex_kurt={r['excess_kurtosis']:+.3f} | "
            f"|z|>4: {r['n_4s']} (exp {r['exp_4s']}) | "
            f"AD: {'PASS' if r['ad_pass'] else 'FAIL'} | "
            f"{r['verdict'][:50]} |"
        )

    md += ["", "## Anti-Circularity",
           "- No SSZ parameters fitted",
           "- No posterior data used",
           "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO"]

    rp = REPORTS / "L1_GAUSSIANITY_TEST.md"
    rp.write_text("\n".join(md) + "\n", encoding="utf-8")
    log(f"\nReport: {rp}")

    # CSV
    cp = REPORTS / "L1_GAUSSIANITY_TEST.csv"
    fields = ["detector", "tag", "band", "offset_s", "n", "mean", "std",
              "skew", "kurtosis", "excess_kurtosis",
              "n_3s", "exp_3s", "n_4s", "exp_4s", "n_5s", "exp_5s",
              "ad_stat", "ad_5pct", "ad_pass", "ks_stat", "ks_pval",
              "verdict"]
    with open(cp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    log(f"CSV:    {cp}")

    flush_log()


if __name__ == "__main__":
    run()
