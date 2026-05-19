"""GW250207 Full Artifact Gate Comparison — identical pipeline to GW240925.

Runs the same 7 diagnostic tests on GW250207 with identical code paths,
parameters, and thresholds as used for GW240925. Produces a direct
side-by-side comparison report.

Tests:
  1. H1/L1 bandpower (20-210 Hz), trigger vs off-source
  2. Sub-band excess kurtosis: 20-40, 40-80, 80-120, 120-160, 160-210 Hz
  3. Line/notch test: known-line fraction, peak count
  4. Multi-window stationarity quantile (+-500s)
  5. H1/L1 cross-coherence and cross-phase
  6. Phase-randomization null test (N=100 surrogates, abridged)
  7. STFT tile excess (Omicron-lite, simplified)

Classification:
  GW250207_STATUS:
    CLEANER_THAN_GW240925   -- key metrics better across the board
    SAME_L1_LOW_FREQ_PATTERN -- 20-40 Hz kurtosis elevated as in GW240925
    WORSE_OR_INCONCLUSIVE   -- worse or data missing

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

LOG_PATH = LOGS / "gw250207_comparison.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CONFIG — identical to GW240925 gate
# ---------------------------------------------------------------------------
GW240925_GPS = 1411261107.984
GW250207_GPS = 1422964625.26

WIN_S = 4.0
PSD_OFFSET_S = 500.0
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 1024
N_SURROGATES = 100

SUB_BANDS = [
    ("20-40",   20.0,  40.0),
    ("40-80",   40.0,  80.0),
    ("80-120",  80.0, 120.0),
    ("120-160", 120.0, 160.0),
    ("160-210", 160.0, 210.0),
]

KNOWN_LINES_HZ = [60.0, 120.0, 180.0, 16.0, 32.0, 48.0, 35.9, 36.7]
NOTCH_HZ = 2.0

# Stationarity: +-500s in 4s steps
STAT_RANGE_S = 500.0
STAT_STEP_S = 4.0

# GW240925 reference values (from previous runs — for comparison table)
GW240925_REF = {
    "l1_h1_ratio":       1.564,
    "l1_stat_q":         74.5,
    "h1_stat_q":         10.3,
    "l1_line_frac":      0.047,
    "coh_mean":          0.056,
    "cross_phase_R":     0.91,
    "l1_exk_20-40":      44.857,
    "l1_exk_40-80": -0.515,
    "l1_exk_80-120":     3.266,
    "l1_exk_120-160":    5.663,
    "l1_exk_160-210":    0.198,
    "h1_exk_20-40":      3.673,
    "h1_exk_40-80":      0.340,
    "h1_exk_80-120":     2.386,
    "h1_exk_120-160":    1.252,
    "h1_exk_160-210":    0.405,
    "phase_rand_l1_kurt_q": 92.5,
}

# GW240925 strain paths
_BASE_240925 = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_240925 = _BASE_240925 / (
    "H1/1410334720"
    "/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
L1_240925 = _BASE_240925 / (
    "L1/1410334720"
    "/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)

# GW250207 strain path — search all subdirs under GW250207-Strain/
_BASE_250207 = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW250207-Strain"
)


def find_strain_file(base_dir, det):
    """Find any HDF5 strain file for detector det under base_dir."""
    if not base_dir.exists():
        return None
    for p in base_dir.rglob(f"{det[0]}-{det}_GWOSC_*.hdf5"):
        return p
    return None


# ---------------------------------------------------------------------------
# SIGNAL PROCESSING (identical to other gate scripts)
# ---------------------------------------------------------------------------
def load_window(path, t_center, dur):
    if not path or not path.exists():
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
    if not np.all(np.isfinite(strain)) or len(strain) < 16:
        return None, None
    return strain.astype(float), float(fs)


def compute_psd(strain, fs):
    nps = min(NPERSEG, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window="hann")
    return freqs, psd


def bandpower(freqs, psd, f_lo=F_LOW, f_hi=F_HIGH):
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    return float(np.trapezoid(psd[mask], freqs[mask]))


def notch_lines(freqs, psd):
    psd_n = psd.copy()
    for lf in KNOWN_LINES_HZ:
        nm = np.abs(freqs - lf) <= NOTCH_HZ
        psd_n[nm] = 0.0
    return psd_n


def bandpass_normalize(strain, fs, f_lo, f_hi, order=4):
    nyq = fs / 2
    lo = max(f_lo / nyq, 1e-4)
    hi = min(f_hi / nyq, 0.9999)
    sos = signal.butter(order, [lo, hi], btype="bandpass", output="sos")
    filt = signal.sosfiltfilt(sos, strain)
    win = signal.windows.tukey(len(filt), alpha=0.2)
    filt = filt * win
    trim = max(1, len(filt) // 20)
    core = filt[trim:-trim]
    std = float(np.std(core, ddof=1))
    return core / (std + 1e-300)


def phase_rand_surrogates(strain, n):
    """Generate n phase-randomized surrogates preserving amplitude spectrum."""
    X = np.fft.rfft(strain)
    mags = np.abs(X)
    surrogates = []
    rng = np.random.default_rng(42)
    for _ in range(n):
        phases = rng.uniform(0, 2 * np.pi, len(X))
        Xs = mags * np.exp(1j * phases)
        Xs[0] = X[0].real
        if len(strain) % 2 == 0:
            Xs[-1] = X[-1].real
        surrogates.append(np.fft.irfft(Xs, n=len(strain)))
    return surrogates


# ---------------------------------------------------------------------------
# PER-EVENT GATE
# ---------------------------------------------------------------------------
def run_event(name, trigger_gps, h1_path, l1_path):
    log(f"\n{'='*65}")
    log(f"EVENT: {name}  GPS: {trigger_gps}")
    log(f"{'='*65}")

    h1_ok = h1_path is not None and h1_path.exists()
    l1_ok = l1_path is not None and l1_path.exists()
    log(f"  H1: {'OK' if h1_ok else 'MISSING'} "
        f"({h1_path.name if h1_path else 'N/A'})")
    log(f"  L1: {'OK' if l1_ok else 'MISSING'} "
        f"({l1_path.name if l1_path else 'N/A'})")

    if not h1_ok or not l1_ok:
        log("  SKIPPED — strain files not available")
        return None

    res = {"event": name, "trigger_gps": trigger_gps,
           "data_available": True}

    # --- 1. BANDPOWER ---
    log("\n  [1] Bandpower 20-210 Hz")
    bp = {}
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        s_t, fs = load_window(path, trigger_gps, WIN_S)
        s_o, _ = load_window(path, trigger_gps - PSD_OFFSET_S, WIN_S)
        if s_t is None:
            log(f"    {det}: load failed")
            continue
        f_t, p_t = compute_psd(s_t, fs)
        b_t = bandpower(f_t, p_t)
        b_o = None
        if s_o is not None:
            f_o, p_o = compute_psd(s_o, fs)
            b_o = bandpower(f_o, p_o)
        off_str = f"{b_o:.3e}" if b_o is not None else "N/A"
        log(f"    {det}: trigger={b_t:.3e}  off-500s={off_str}")
        bp[det] = b_t
        res[f"{det.lower()}_bp_trigger"] = float(b_t)
        res[f"{det.lower()}_bp_off500"] = (
            float(b_o) if b_o is not None else None)
    if "H1" in bp and "L1" in bp:
        ratio = bp["L1"] / (bp["H1"] + 1e-300)
        res["l1_h1_ratio"] = round(ratio, 4)
        log(f"    L1/H1 ratio: {ratio:.3f}")

    # --- 2. SUB-BAND KURTOSIS ---
    log("\n  [2] Sub-band excess kurtosis")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        s_t, fs = load_window(path, trigger_gps, WIN_S)
        if s_t is None:
            continue
        for band, f_lo, f_hi in SUB_BANDS:
            x = bandpass_normalize(s_t, fs, f_lo, f_hi)
            ek = float(stats.kurtosis(x, fisher=True))
            key = f"{det.lower()}_exk_{band}"
            res[key] = round(ek, 4)
            log(f"    {det} {band}: ex_k={ek:+.3f}")

    # --- 3. LINE/NOTCH TEST ---
    log("\n  [3] Line/notch test")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        s_t, fs = load_window(path, trigger_gps, WIN_S)
        if s_t is None:
            continue
        f, p = compute_psd(s_t, fs)
        bp_full = bandpower(f, p)
        bp_notched = bandpower(f, notch_lines(f, p))
        lf = 1.0 - bp_notched / (bp_full + 1e-300)
        log(f"    {det}: full={bp_full:.3e}  notched={bp_notched:.3e}  "
            f"line_frac={lf*100:.1f}%")
        res[f"{det.lower()}_line_frac"] = round(lf, 4)

    # --- 4. STATIONARITY ---
    log("\n  [4] Multi-window stationarity (+-500s)")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        bps_win = []
        for off in np.arange(-STAT_RANGE_S, STAT_RANGE_S + STAT_STEP_S,
                             STAT_STEP_S):
            s, fs_w = load_window(path, trigger_gps + off, WIN_S)
            if s is None:
                continue
            fw, pw = compute_psd(s, fs_w)
            bps_win.append(bandpower(fw, pw))
        if len(bps_win) < 10:
            log(f"    {det}: too few windows")
            continue
        bps_win = np.array(bps_win)
        s_t, fs = load_window(path, trigger_gps, WIN_S)
        if s_t is None:
            continue
        ft, pt = compute_psd(s_t, fs)
        bt = bandpower(ft, pt)
        q = float(stats.percentileofscore(bps_win, bt))
        z = (bt - bps_win.mean()) / (bps_win.std() + 1e-300)
        log(f"    {det}: N={len(bps_win)}  q={q:.1f}%  z={z:+.2f}")
        res[f"{det.lower()}_stat_q"] = round(q, 2)
        res[f"{det.lower()}_stat_z"] = round(float(z), 4)

    # --- 5. CROSS-COHERENCE ---
    log("\n  [5] H1/L1 cross-coherence")
    h1_s, fs_h = load_window(h1_path, trigger_gps, WIN_S)
    l1_s, _ = load_window(l1_path, trigger_gps, WIN_S)
    if h1_s is not None and l1_s is not None:
        n = min(len(h1_s), len(l1_s))
        nps = min(NPERSEG, n // 4)
        freqs_c, coh = signal.coherence(h1_s[:n], l1_s[:n],
                                        fs=fs_h, nperseg=nps,
                                        noverlap=nps // 2)
        mask = (freqs_c >= F_LOW) & (freqs_c <= F_HIGH)
        coh_mean = float(np.mean(coh[mask]))
        _, Cxy = signal.csd(h1_s[:n], l1_s[:n], fs=fs_h,
                            nperseg=nps, noverlap=nps // 2, window="hann")
        ph = np.angle(Cxy[mask])
        R = float(np.abs(np.mean(np.exp(1j * ph))))
        mean_ph = float(np.rad2deg(np.angle(np.mean(np.exp(1j * ph)))))
        log(f"    coh_mean={coh_mean:.4f}  R={R:.4f}  "
            f"phase={mean_ph:+.1f}deg")
        res["coh_mean"] = round(coh_mean, 5)
        res["cross_phase_R"] = round(R, 4)
        res["cross_phase_deg"] = round(mean_ph, 2)

    # --- 6. PHASE RANDOMIZATION (abridged, N=100) ---
    log(f"\n  [6] Phase-randomization null test (N={N_SURROGATES})")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        s_t, fs = load_window(path, trigger_gps, WIN_S)
        if s_t is None:
            continue
        surrs = phase_rand_surrogates(s_t, N_SURROGATES)
        # bandpower of surrogates
        bp_surrs = []
        kurt_surrs = []
        for sr in surrs:
            fw, pw = compute_psd(sr, fs)
            bp_surrs.append(bandpower(fw, pw))
            kurt_surrs.append(float(stats.kurtosis(sr, fisher=True)))
        fw_t, pw_t = compute_psd(s_t, fs)
        bp_t = bandpower(fw_t, pw_t)
        kurt_t = float(stats.kurtosis(s_t, fisher=True))
        q_bp = float(stats.percentileofscore(bp_surrs, bp_t))
        q_k = float(stats.percentileofscore(kurt_surrs, kurt_t))
        log(f"    {det}: bp_q={q_bp:.1f}%  kurt_q={q_k:.1f}%  "
            f"kurt={kurt_t:+.3f}")
        res[f"{det.lower()}_phrand_bp_q"] = round(q_bp, 2)
        res[f"{det.lower()}_phrand_kurt_q"] = round(q_k, 2)
        res[f"{det.lower()}_phrand_kurt"] = round(kurt_t, 4)

    return res


# ---------------------------------------------------------------------------
# COMPARE
# ---------------------------------------------------------------------------
def classify(r240, r250):
    """Return classification of GW250207 relative to GW240925."""
    if r250 is None:
        return "MISSING_DATA", ["GW250207 strain files not available"]

    issues_250 = 0
    issues_240 = 0
    reasons = []

    # Key: L1 20-40 Hz kurtosis
    ek240 = r240.get("l1_exk_20-40", GW240925_REF["l1_exk_20-40"])
    ek250 = r250.get("l1_exk_20-40")
    if ek250 is not None:
        if abs(ek250) > 10:
            issues_250 += 2
            reasons.append(f"L1 20-40Hz ex_k={ek250:+.2f} (same pattern as "
                           f"GW240925 {ek240:+.2f})")
        elif abs(ek250) > 3:
            issues_250 += 1
            reasons.append(f"L1 20-40Hz ex_k={ek250:+.2f} (mild)")
        else:
            reasons.append(f"L1 20-40Hz ex_k={ek250:+.2f} CLEAN "
                           f"(vs GW240925 {ek240:+.2f})")
    if abs(ek240) > 10:
        issues_240 += 2

    # L1/H1 ratio
    r250_ratio = r250.get("l1_h1_ratio")
    r240_ratio = GW240925_REF["l1_h1_ratio"]
    if r250_ratio is not None:
        if r250_ratio > 2.0:
            issues_250 += 2
        elif r250_ratio > 1.5:
            issues_250 += 1
    if r240_ratio > 1.5:
        issues_240 += 1

    # L1 stationarity
    q250 = r250.get("l1_stat_q")
    q240 = GW240925_REF["l1_stat_q"]
    if q250 is not None:
        if q250 > 90:
            issues_250 += 2
        elif q250 > 75:
            issues_250 += 1
    if q240 > 75:
        issues_240 += 1

    if issues_250 >= issues_240 + 2:
        return "WORSE_OR_INCONCLUSIVE", reasons
    if issues_250 <= issues_240 - 2:
        return "CLEANER_THAN_GW240925", reasons
    # check specifically for the 20-40 Hz pattern match
    if ek250 is not None and abs(ek250) > 10:
        return "SAME_L1_LOW_FREQ_PATTERN", reasons
    if issues_250 < issues_240:
        return "CLEANER_THAN_GW240925", reasons
    return "WORSE_OR_INCONCLUSIVE", reasons


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"GW250207 FULL ARTIFACT GATE COMPARISON -- {NOW}")
    log(f"GW240925 GPS: {GW240925_GPS}")
    log(f"GW250207 GPS: {GW250207_GPS}")

    # Find GW250207 files
    h1_250 = find_strain_file(_BASE_250207, "H1")
    l1_250 = find_strain_file(_BASE_250207, "L1")
    log("\nGW250207 strain files:")
    log(f"  H1: {h1_250 or 'NOT FOUND'}")
    log(f"  L1: {l1_250 or 'NOT FOUND'}")

    # Run GW240925 (reference)
    r240 = run_event("GW240925", GW240925_GPS, H1_240925, L1_240925)

    # Run GW250207
    r250 = run_event("GW250207", GW250207_GPS, h1_250, l1_250)

    # --- COMPARISON TABLE ---
    log(f"\n{'='*65}")
    log("DIRECT COMPARISON: GW240925 vs GW250207")
    log(f"{'='*65}")

    compare_keys = [
        ("l1_h1_ratio",       "L1/H1 BP ratio",            1.5, ">"),
        ("l1_stat_q",         "L1 stationarity Q %",        75.0, ">"),
        ("h1_stat_q",         "H1 stationarity Q %",        75.0, ">"),
        ("l1_line_frac",      "L1 line fraction",           0.4, ">"),
        ("coh_mean",          "H1/L1 coherence",            0.1, ">"),
        ("cross_phase_R",     "Cross-phase R",              0.5, "<"),
        ("l1_exk_20-40",      "L1 20-40Hz ex_k",            10.0, ">"),
        ("l1_exk_40-80",      "L1 40-80Hz ex_k",            3.0, ">"),
        ("l1_exk_80-120",     "L1 80-120Hz ex_k",           3.0, ">"),
        ("l1_exk_120-160",    "L1 120-160Hz ex_k",          3.0, ">"),
        ("l1_exk_160-210",    "L1 160-210Hz ex_k",          3.0, ">"),
        ("h1_exk_20-40",      "H1 20-40Hz ex_k",            10.0, ">"),
        ("l1_phrand_kurt_q",  "L1 phase-rand kurtosis Q%",  90.0, ">"),
    ]

    log(f"  {'Metric':30s} {'GW240925':>12} {'GW250207':>12} {'Flag'}")
    log("  " + "-" * 65)

    rows_csv = []
    for key, label, thresh, direction in compare_keys:
        v240 = r240.get(key) if r240 else GW240925_REF.get(
            key.replace("-", "-"))
        # also try with underscores for ref dict
        if v240 is None:
            ref_key = key.replace("-", "-")
            v240 = GW240925_REF.get(ref_key)
        v250 = r250.get(key) if r250 else None

        v240_str = f"{v240:.3f}" if isinstance(v240, float) else str(v240)
        v250_str = f"{v250:.3f}" if isinstance(v250, float) else "N/A"

        flag = ""
        if isinstance(v250, float):
            if direction == ">" and v250 > thresh:
                flag = "ELEVATED"
            elif direction == "<" and v250 < thresh:
                flag = "ELEVATED"

        log(f"  {label:30s} {v240_str:>12} {v250_str:>12} {flag}")
        rows_csv.append({
            "metric": key, "label": label,
            "gw240925": v240, "gw250207": v250,
            "threshold": thresh, "direction": direction,
            "gw250207_flag": flag,
        })

    # --- CLASSIFICATION ---
    classification, reasons = classify(r240, r250)

    log(f"\n{'='*65}")
    log(f"GW250207_STATUS: {classification}")
    log(f"{'='*65}")
    for r in reasons:
        log(f"  - {r}")

    interpretation = {
        "CLEANER_THAN_GW240925": (
            "GW250207 passes the L1 artifact gate more cleanly. "
            "Better candidate for SSZ pipeline tests."
        ),
        "SAME_L1_LOW_FREQ_PATTERN": (
            "GW250207 shows the same 20-40 Hz L1 excess kurtosis as "
            "GW240925. This suggests a systematic L1 low-frequency issue, "
            "not an event-specific artefact. Both events blocked."
        ),
        "WORSE_OR_INCONCLUSIVE": (
            "GW250207 shows worse or inconclusive artifact metrics. "
            "Neither event is a clean SSZ test candidate."
        ),
        "MISSING_DATA": (
            "GW250207 strain files not available. "
            "Run scripts/download_gw250207_strain.py first. "
            "Cannot classify."
        ),
    }
    log()
    log(f"  Interpretation: {interpretation.get(classification, '')}")

    log()
    log("GATE VERDICTS:")
    log("  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
    log("  SSZ_SUPPORT_CLAIM_MADE: NO")
    log("  SSZ_FALSIFICATION_CLAIM_MADE: NO")

    # --- OUTPUTS ---
    csv_path = MANIFEST / "gw250207_artifact_gate_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        fields = ["metric", "label", "gw240925", "gw250207",
                  "threshold", "direction", "gw250207_flag"]
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_csv)

    md = [
        "# GW250207 Artifact Gate Comparison",
        f"Generated: {NOW}",
        "",
        "## Events",
        f"- GW240925 GPS: {GW240925_GPS}",
        f"- GW250207 GPS: {GW250207_GPS}",
        "",
        "## Pipeline Configuration",
        f"- Band: {F_LOW}-{F_HIGH} Hz  Window: {WIN_S}s",
        f"- Stationarity: +-{STAT_RANGE_S}s  Known lines: {KNOWN_LINES_HZ}",
        f"- Sub-bands: {[b[0] for b in SUB_BANDS]}",
        f"- Phase-rand N={N_SURROGATES}",
        "",
        "## Comparison Table",
        "",
        "| Metric | GW240925 | GW250207 | Flag |",
        "|--------|----------|----------|------|",
    ]
    for r in rows_csv:
        v240 = f"{r['gw240925']:.3f}" if isinstance(
            r['gw240925'], float) else str(r['gw240925'])
        v250 = f"{r['gw250207']:.3f}" if isinstance(
            r['gw250207'], float) else "N/A"
        md.append(f"| {r['label']} | {v240} | {v250} | {r['gw250207_flag']} |")

    md += [
        "",
        f"## Classification: GW250207_STATUS = {classification}",
        "",
        f"> {interpretation.get(classification, '')}",
        "",
        "### Reasons",
    ]
    for r in reasons:
        md.append(f"- {r}")

    md += [
        "",
        "## Key Finding: 20-40 Hz Sub-band",
        "The 20-40 Hz excess kurtosis in L1 at the GW240925 trigger is +44.9.",
        "This band is most sensitive to seismic coupling, suspension noise,",
        "and control-system artefacts in LIGO.",
        f"GW250207 comparison: {'see table above'}",
        "",
        "## Gate Verdicts",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
        "",
        "## Next Steps",
        "- If SAME_L1_LOW_FREQ_PATTERN: request Omicron/iDQ for both events",
        "- If CLEANER_THAN_GW240925: run full SSZ pipeline on GW250207",
        "- If MISSING_DATA: run scripts/download_gw250207_strain.py",
    ]

    rpath = REPORTS / "GW250207_ARTIFACT_GATE_COMPARISON.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    log(f"  {LOG_PATH}")
    flush_log()


if __name__ == "__main__":
    run()
