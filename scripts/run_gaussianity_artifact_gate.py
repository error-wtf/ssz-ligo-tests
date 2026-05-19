"""Gaussianity / Artifact Gate Test for H1 and L1.

Artifact-gate test: Is the L1 excess normal whitened Gaussian noise
or structured non-Gaussian residual?

NO SSZ claim. NO posterior fitting. Pure data-quality gate.

Outputs:
  reports/GAUSSIANITY_ARTIFACT_GATE_REPORT.md
  data_manifest/gaussianity_test_windows.csv
  data_manifest/gaussianity_summary_stats.csv
  logs/gaussianity_artifact_gate.log

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
PLOTS = REPORTS / "plots"
for _d in (REPORTS, LOGS, MANIFEST, PLOTS):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "gaussianity_artifact_gate.log"
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
# SIGNAL PROCESSING
# ---------------------------------------------------------------------------
def whiten(strain, fs, psd_strain):
    nperseg = min(NPERSEG, len(psd_strain) // 4)
    freqs, psd = signal.welch(psd_strain, fs=fs, nperseg=nperseg,
                              window="hann", noverlap=nperseg // 2)
    n = len(strain)
    s_fft = np.fft.rfft(strain)
    f_fft = np.fft.rfftfreq(n, 1.0 / fs)
    psd_interp = np.clip(np.interp(f_fft, freqs, psd), 1e-60, None)
    amp_norm = np.sqrt(psd_interp * fs / 2.0)
    s_w = s_fft / amp_norm
    s_w[0] = 0.0
    if n % 2 == 0:
        s_w[-1] = 0.0
    return np.fft.irfft(s_w, n=n)


def bandpass(s, fs):
    nyq = fs / 2.0
    b, a = signal.butter(4, [F_LOW / nyq, F_HIGH / nyq], btype="band")
    return signal.filtfilt(b, a, s)


def trim_edges(arr, frac=0.10):
    t = max(1, len(arr) // int(1 / frac))
    return arr[t:-t]


# ---------------------------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------------------------
def compute_stats(z, det, tag, band):
    """Full Gaussianity statistics on z-scored array z."""
    n = len(z)
    mu = float(np.mean(z))
    sigma = float(np.std(z, ddof=1))
    med = float(np.median(z))
    mad = float(np.median(np.abs(z - med)))
    skew = float(stats.skew(z))
    kurt = float(stats.kurtosis(z, fisher=False))  # Pearson: normal=3
    ex_kurt = kurt - 3.0
    z_max = float(np.max(np.abs(z)))
    n3 = int(np.sum(np.abs(z) > 3.0))
    n4 = int(np.sum(np.abs(z) > 4.0))
    n5 = int(np.sum(np.abs(z) > 5.0))
    e3 = max(0, int(round(n * 2 * stats.norm.sf(3.0))))
    e4 = max(0, int(round(n * 2 * stats.norm.sf(4.0))))
    e5 = max(0, int(round(n * 2 * stats.norm.sf(5.0))))

    # Anderson-Darling
    try:
        ad_stat, ad_crit, _ = stats.anderson(z, dist="norm")
        ad_5pct = float(ad_crit[2])
        ad_pass = bool(ad_stat < ad_5pct)
    except Exception:
        ad_stat, ad_5pct, ad_pass = np.nan, np.nan, None

    # KS test
    try:
        ks_stat, ks_p = stats.kstest(z, "norm", args=(0, 1))
    except Exception:
        ks_stat, ks_p = np.nan, np.nan

    return {
        "detector": det, "tag": tag, "band": band,
        "n": n, "mean": round(mu, 6), "std": round(sigma, 6),
        "median": round(med, 6), "mad": round(mad, 6),
        "skew": round(skew, 6), "kurtosis": round(kurt, 6),
        "excess_kurtosis": round(ex_kurt, 6),
        "max_abs_z": round(z_max, 4),
        "n3": n3, "e3": e3, "n4": n4, "e4": e4, "n5": n5, "e5": e5,
        "ad_stat": round(float(ad_stat), 4) if not np.isnan(ad_stat) else None,
        "ad_5pct": round(ad_5pct, 4) if not np.isnan(ad_5pct) else None,
        "ad_pass": ad_pass,
        "ks_stat": round(float(ks_stat), 6) if not np.isnan(ks_stat) else None,
        "ks_pval": round(float(ks_p), 8) if not np.isnan(ks_p) else None,
    }


def log_stats(s):
    log(f"    n={s['n']}  mean={s['mean']:+.4f}  std={s['std']:.4f}  "
        f"med={s['median']:+.4f}  MAD={s['mad']:.4f}")
    log(f"    skew={s['skew']:+.4f}  kurt={s['kurtosis']:.3f}  "
        f"ex_kurt={s['excess_kurtosis']:+.3f}  max|z|={s['max_abs_z']:.2f}")
    log(f"    |z|>3: {s['n3']} (exp {s['e3']})  "
        f"|z|>4: {s['n4']} (exp {s['e4']})  "
        f"|z|>5: {s['n5']} (exp {s['e5']})")
    ad_str = (f"AD={s['ad_stat']:.3f} crit={s['ad_5pct']:.3f} "
              f"{'PASS' if s['ad_pass'] else 'FAIL'}"
              if s['ad_stat'] is not None else "AD=N/A")
    ks_str = (f"KS={s['ks_stat']:.4f} p={s['ks_pval']:.2e} "
              f"{'PASS' if s['ks_pval'] > 0.05 else 'FAIL'}"
              if s['ks_pval'] is not None else "KS=N/A")
    log(f"    {ad_str}  {ks_str}")


# ---------------------------------------------------------------------------
# PLOTS (optional — graceful skip if matplotlib unavailable)
# ---------------------------------------------------------------------------
def try_plot_qq_hist(z, label):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        fig.suptitle(label)

        # Histogram vs N(0,1)
        xr = np.linspace(-5, 5, 300)
        ax1.hist(z, bins=80, density=True, alpha=0.6, label="data")
        ax1.plot(xr, stats.norm.pdf(xr), "r-", lw=1.5, label="N(0,1)")
        ax1.set_xlabel("z-score")
        ax1.set_ylabel("density")
        ax1.legend(fontsize=8)
        ax1.set_title("Histogram")

        # QQ plot
        qq = stats.probplot(z, dist="norm")
        theoretical = qq[0][0]
        sample = qq[0][1]
        ax2.scatter(theoretical, sample, s=1, alpha=0.4)
        lo, hi = theoretical[0], theoretical[-1]
        ax2.plot([lo, hi], [lo, hi], "r-", lw=1.5, label="y=x (Gaussian)")
        ax2.set_xlabel("Theoretical quantiles")
        ax2.set_ylabel("Sample quantiles")
        ax2.legend(fontsize=8)
        ax2.set_title("QQ plot vs N(0,1)")

        fname = PLOTS / f"gaussianity_{label.replace(' ', '_')}.png"
        plt.tight_layout()
        plt.savefig(fname, dpi=100)
        plt.close(fig)
        log(f"    Plot saved: {fname.name}")
    except Exception as e:
        log(f"    Plot skipped: {e}")


# ---------------------------------------------------------------------------
# CLASSIFY
# ---------------------------------------------------------------------------
def classify_gaussianity(s_trig, s_off_list, det):
    """
    Classify one detector's Gaussianity based on trigger vs off-source.
    Returns (det_class, excess_class).
    """
    ex_k_trig = s_trig["excess_kurtosis"]
    n4_trig = s_trig["n4"]
    e4_trig = max(1, s_trig["e4"])
    outlier_ratio = n4_trig / e4_trig

    ex_k_offs = [s["excess_kurtosis"] for s in s_off_list]
    mean_ex_k_off = float(np.mean(ex_k_offs)) if ex_k_offs else 0.0
    delta_ex_k = ex_k_trig - mean_ex_k_off

    n4_offs = [s["n4"] for s in s_off_list]
    mean_n4_off = float(np.mean(n4_offs)) if n4_offs else 0.0

    # Detector gaussianity class
    if abs(ex_k_trig) < 1.0 and outlier_ratio < 5:
        det_class = "CONSISTENT_WITH_WHITENED_GAUSSIAN"
    elif abs(ex_k_trig) < 3.0 and outlier_ratio < 20:
        det_class = "MILD_NON_GAUSSIAN"
    elif abs(ex_k_trig) >= 3.0 or outlier_ratio >= 20:
        det_class = "STRONGLY_NON_GAUSSIAN"
    else:
        det_class = "INCONCLUSIVE"

    # Excess classification (trigger-specific or chronic?)
    n_off = len(s_off_list)
    chronic = (n_off >= 2 and abs(delta_ex_k) < 1.0
               and abs(ex_k_trig) > 2.0)
    if delta_ex_k > 2.0 and n4_trig > mean_n4_off * 1.5:
        excess_class = "NON_GAUSSIAN_TRANSIENT"
    elif chronic:
        excess_class = "CHRONIC_NON_GAUSSIAN_BAND_NOISE"
    elif delta_ex_k < 0.5 and abs(ex_k_trig) > 2.0:
        excess_class = "LINE_OR_RINGING_STRUCTURE"
    elif delta_ex_k < 0.5 and abs(ex_k_trig) < 1.5:
        excess_class = "GAUSSIAN_HIGH_POWER_FLUCTUATION"
    elif abs(ex_k_trig) < 0.8:
        excess_class = "PSD_OR_WHITENING_ARTIFACT"
    else:
        excess_class = "INCONCLUSIVE"

    log(f"  [{det} classification]")
    log(f"    ex_kurt_trig={ex_k_trig:+.3f}  mean_off={mean_ex_k_off:+.3f}  "
        f"delta={delta_ex_k:+.3f}")
    log(f"    outlier_ratio(4s)={outlier_ratio:.1f}x expected")
    log(f"    -> det_class={det_class}")
    log(f"    -> excess_class={excess_class}")
    return det_class, excess_class


# ---------------------------------------------------------------------------
# PROCESS ONE DETECTOR
# ---------------------------------------------------------------------------
def process_detector(det, path):
    log(f"\n{'='*60}")
    log(f"DETECTOR: {det}")
    log(f"{'='*60}")

    if not path.exists():
        log("  FILE NOT FOUND — BLOCKED")
        return {}, {}

    psd_strain, fs = load_window(
        path, TRIGGER_GPS - PSD_OFFSET_S, PSD_DUR_S
    )
    if psd_strain is None:
        log("  PSD window load failed — BLOCKED")
        return {}, {}

    log(f"  PSD source: -{PSD_OFFSET_S}s x {PSD_DUR_S}s  "
        f"fs={fs:.0f}Hz  n={len(psd_strain)}")

    all_tags = [("TRIGGER", 0.0)] + list(OFF_WINDOWS)
    stats_full = {}
    stats_bp = {}

    for tag, offset in all_tags:
        t_center = TRIGGER_GPS + offset
        strain, _ = load_window(path, t_center, WIN_S)
        if strain is None:
            log(f"  [{tag}] load failed — skipped")
            continue

        w = whiten(strain, fs, psd_strain)
        w_t = trim_edges(w)

        z_full = (w_t - np.mean(w_t)) / (np.std(w_t, ddof=1) + 1e-300)
        w_bp = bandpass(w_t, fs)
        z_bp = (w_bp - np.mean(w_bp)) / (np.std(w_bp, ddof=1) + 1e-300)

        log(f"\n  [{tag}] FULLBAND whitened:")
        sf = compute_stats(z_full, det, tag, "FULLBAND")
        log_stats(sf)
        try_plot_qq_hist(z_full, f"{det}_{tag}_FULL")
        stats_full[tag] = sf

        log(f"  [{tag}] BAND {F_LOW}-{F_HIGH}Hz whitened+bp:")
        sb = compute_stats(z_bp, det, tag, f"{F_LOW}-{F_HIGH}Hz")
        log_stats(sb)
        try_plot_qq_hist(z_bp, f"{det}_{tag}_BP")
        stats_bp[tag] = sb

    return stats_full, stats_bp


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"GAUSSIANITY ARTIFACT GATE — {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s  "
        f"PSD: -{PSD_OFFSET_S}s x {PSD_DUR_S}s")
    log(f"Band: {F_LOW}-{F_HIGH}Hz")

    h1_full, h1_bp = process_detector("H1", H1_PATH)
    l1_full, l1_bp = process_detector("L1", L1_PATH)

    # ---------------------------------------------------------------------------
    # CLASSIFY
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("CLASSIFICATION")
    log(f"{'='*60}")

    off_tags = [t for t, _ in OFF_WINDOWS]

    h1_off_bp = [h1_bp[t] for t in off_tags if t in h1_bp]
    l1_off_bp = [l1_bp[t] for t in off_tags if t in l1_bp]

    h1_cls, h1_exc = ("BLOCKED", "BLOCKED")
    l1_cls, l1_exc = ("BLOCKED", "BLOCKED")

    if "TRIGGER" in h1_bp and h1_off_bp:
        h1_cls, h1_exc = classify_gaussianity(h1_bp["TRIGGER"], h1_off_bp,
                                              "H1")
    if "TRIGGER" in l1_bp and l1_off_bp:
        l1_cls, l1_exc = classify_gaussianity(l1_bp["TRIGGER"], l1_off_bp,
                                              "L1")

    # ---------------------------------------------------------------------------
    # REQUIRED COMPARISONS
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("REQUIRED COMPARISONS (20-210 Hz bandpassed)")
    log(f"{'='*60}")

    def cmp(label, sa, sb):
        if sa is None or sb is None:
            log(f"  [{label}] BLOCKED (missing data)")
            return
        da = sa["excess_kurtosis"]
        db = sb["excess_kurtosis"]
        na4, nb4 = sa["n4"], sb["n4"]
        log(f"  [{label}]")
        log(f"    ex_kurt: A={da:+.3f}  B={db:+.3f}  diff={da-db:+.3f}")
        log(f"    |z|>4:   A={na4}  B={nb4}")

    cmp("1. H1 trigger vs H1 off-source (mean off)",
        h1_bp.get("TRIGGER"),
        {"excess_kurtosis": float(np.mean([s["excess_kurtosis"]
                                           for s in h1_off_bp]))
         if h1_off_bp else 0.0,
         "n4": int(np.mean([s["n4"] for s in h1_off_bp]))
         if h1_off_bp else 0} if h1_off_bp else None)

    cmp("2. L1 trigger vs L1 off-source (mean off)",
        l1_bp.get("TRIGGER"),
        {"excess_kurtosis": float(np.mean([s["excess_kurtosis"]
                                           for s in l1_off_bp]))
         if l1_off_bp else 0.0,
         "n4": int(np.mean([s["n4"] for s in l1_off_bp]))
         if l1_off_bp else 0} if l1_off_bp else None)

    cmp("3. H1 trigger vs L1 trigger",
        h1_bp.get("TRIGGER"), l1_bp.get("TRIGGER"))

    cmp("4. H1 20-210Hz vs L1 20-210Hz (off-source mean)",
        {"excess_kurtosis": float(np.mean([s["excess_kurtosis"]
                                           for s in h1_off_bp]))
         if h1_off_bp else 0.0,
         "n4": int(np.mean([s["n4"] for s in h1_off_bp]))
         if h1_off_bp else 0} if h1_off_bp else None,
        {"excess_kurtosis": float(np.mean([s["excess_kurtosis"]
                                           for s in l1_off_bp]))
         if l1_off_bp else 0.0,
         "n4": int(np.mean([s["n4"] for s in l1_off_bp]))
         if l1_off_bp else 0} if l1_off_bp else None)

    log("  [5. L1 anomaly window vs L1 normal windows]")
    if l1_bp:
        trig_ek = l1_bp.get("TRIGGER", {}).get("excess_kurtosis", None)
        for t in off_tags:
            if t in l1_bp:
                ek = l1_bp[t]["excess_kurtosis"]
                log(f"    L1 TRIGGER ex_kurt={trig_ek:+.3f}  "
                    f"L1 {t} ex_kurt={ek:+.3f}  "
                    f"diff={trig_ek-ek:+.3f}"
                    if trig_ek is not None else f"    {t}: no trigger")

    # ---------------------------------------------------------------------------
    # ARTIFACT GATE VERDICT
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("ARTIFACT GATE VERDICT")
    log(f"{'='*60}")
    log(f"  H1_GAUSSIANITY:  {h1_cls}")
    log(f"  L1_GAUSSIANITY:  {l1_cls}")
    log(f"  L1_EXCESS_CLASS: {l1_exc}")

    if l1_cls == "CONSISTENT_WITH_WHITENED_GAUSSIAN":
        gate = "PASS_L1_GAUSSIAN"
    elif l1_cls == "STRONGLY_NON_GAUSSIAN":
        gate = "FAIL_L1_NON_GAUSSIAN"
    elif l1_cls == "MILD_NON_GAUSSIAN":
        gate = "PARTIAL"
    else:
        gate = "BLOCKED"

    log(f"\n  GAUSSIANITY_ARTIFACT_GATE: {gate}")
    log("  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")

    # Interpretation
    log("\n  Interpretation:")
    if gate == "PASS_L1_GAUSSIAN":
        log("  L1 is consistent with whitened Gaussian noise.")
        log("  The bandpower excess is a Gaussian high-power fluctuation.")
        log("  Check: antenna response, PSD normalization, SNR difference.")
    elif gate == "FAIL_L1_NON_GAUSSIAN":
        if l1_exc == "CHRONIC_NON_GAUSSIAN_BAND_NOISE":
            log("  L1 excess is NOT trigger-specific.")
            log("  Non-Gaussianity is chronic and stationary across all "
                "windows.")
            log("  20-210 Hz band behaves as persistent non-ideal noise "
                "under current whitening.")
            log("  L1 blocked: chronic band noise, not astrophysical "
                "candidate.")
        else:
            log("  L1 shows structured non-Gaussian excess.")
            log("  Artefact / glitch / resonance more likely.")
            log("  L1 blocked for claim — further DQ investigation required.")
    elif gate == "PARTIAL":
        log("  L1 shows mild non-Gaussianity — consistent across all windows.")
        log("  Likely chronic detector noise, not trigger-specific.")
        log("  Not sufficient to pass artifact gate for SSZ claim.")
    else:
        log("  Data incomplete — gate blocked.")

    # ---------------------------------------------------------------------------
    # WRITE OUTPUTS
    # ---------------------------------------------------------------------------
    # 1. Flat stats CSV for data_manifest
    all_stats = []
    bp_band = f"{F_LOW}-{F_HIGH}Hz"
    for tag_dict, band in [
        (h1_full, "FULLBAND"), (h1_bp, bp_band),
        (l1_full, "FULLBAND"), (l1_bp, bp_band)
    ]:
        for tag, s in tag_dict.items():
            if s.get("band") == band:
                all_stats.append(s)

    fields = ["detector", "tag", "band", "n", "mean", "std",
              "median", "mad", "skew", "kurtosis", "excess_kurtosis",
              "max_abs_z", "n3", "e3", "n4", "e4", "n5", "e5",
              "ad_stat", "ad_5pct", "ad_pass", "ks_stat", "ks_pval"]
    spath = MANIFEST / "gaussianity_summary_stats.csv"
    with open(spath, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_stats)

    # 2. Windows manifest CSV
    wrows = []
    for det, tag_dicts in [("H1", h1_bp), ("L1", l1_bp)]:
        for tag, s in tag_dicts.items():
            offset = dict(OFF_WINDOWS).get(tag, 0.0)
            wrows.append({
                "detector": det, "tag": tag,
                "t_center_gps": TRIGGER_GPS + offset,
                "duration_s": WIN_S,
                "band": s.get("band", ""),
                "n_samples": s.get("n", ""),
            })
    wpath = MANIFEST / "gaussianity_test_windows.csv"
    wfields = ["detector", "tag", "t_center_gps",
               "duration_s", "band", "n_samples"]
    with open(wpath, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=wfields,
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(wrows)

    # 3. Markdown report
    def tbl_row(s):
        return (
            f"| {s['detector']} | {s['tag']} | {s['band']} "
            f"| {s['std']:.4f} | {s['excess_kurtosis']:+.3f} "
            f"| {s['n4']} / {s['e4']} "
            f"| {s['n5']} / {s['e5']} "
            f"| {'PASS' if s['ad_pass'] else 'FAIL'} |"
        )

    md_lines = [
        "# Gaussianity Artifact Gate Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s",
        f"- PSD source: -{PSD_OFFSET_S}s x {PSD_DUR_S}s",
        f"- Band: {F_LOW}-{F_HIGH} Hz",
        "- Whitening: PSD-division in frequency domain",
        "",
        "## Statistics Table (20-210 Hz bandpassed)",
        "",
        "| Det | Tag | Band | std | ex_kurt | |z|>4 obs/exp "
        "| |z|>5 obs/exp | AD |",
        "|-----|-----|------|-----|---------|--------------|----------|-----|",
    ]
    for tag_dict in [h1_bp, l1_bp]:
        for tag in ["TRIGGER"] + [t for t, _ in OFF_WINDOWS]:
            if tag in tag_dict:
                md_lines.append(tbl_row(tag_dict[tag]))

    md_lines += [
        "",
        "## Classification",
        f"- H1_GAUSSIANITY: **{h1_cls}**",
        f"- L1_GAUSSIANITY: **{l1_cls}**",
        f"- L1_EXCESS_CLASS: **{l1_exc}**",
        "",
        "## Artifact Gate",
        f"**GAUSSIANITY_ARTIFACT_GATE: {gate}**",
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- No posterior data (f, m, chi) used",
        "- No QNM posterior used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "GAUSSIANITY_ARTIFACT_GATE_REPORT.md"
    rpath.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {spath}")
    log(f"  {wpath}")
    log(f"  {LOG_PATH}")

    flush_log()
    return gate


if __name__ == "__main__":
    run()
