"""GW250207 Artifact Gate — Full Cross-Event Comparison.

Runs the same artifact-gating diagnostics on GW250207 as on GW240925:
  1. Bandpower H1/L1 (20-210 Hz), trigger vs off-source
  2. Multi-window stationarity (+-500s)
  3. Line/notch test (PSD peak detection)
  4. Sub-band Gaussianity (5 bands)
  5. Cross-coherence H1/L1 magnitude and phase
  6. Comparative summary: GW240925 vs GW250207

Goal: Determine if GW250207 is a cleaner test candidate for SSZ analysis.

GW250207 GPS: 1422964625.26 (S250207bg)
File: O4b4DiscC00_4KHZ_R1, 4096s block at 1422964096

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

LOG_PATH = LOGS / "gw250207_artifact_gate.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
GW240925_GPS = 1411261107.984
GW250207_GPS = 1422964625.26

WIN_S = 4.0
PSD_REF_DUR_S = 64.0
PSD_OFFSET_S = 500.0
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 1024

SUB_BANDS = [
    ("20-40",   20.0,  40.0),
    ("40-80",   40.0,  80.0),
    ("80-120",  80.0, 120.0),
    ("120-160", 120.0, 160.0),
    ("160-210", 160.0, 210.0),
]

KNOWN_LINES_HZ = [
    60.0, 120.0, 180.0,  # mains harmonics
    16.0, 32.0, 48.0,    # control system
    35.9, 36.7,           # violin mode approximate
]
NOTCH_HZ = 2.0

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

# GW250207 strain paths (download required)
_BASE_250207 = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW250207-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_250207 = _BASE_250207 / (
    "H1/1422964096"
    "/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1422964096-4096.hdf5"
)
L1_250207 = _BASE_250207 / (
    "L1/1422964096"
    "/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1422964096-4096.hdf5"
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
def compute_psd(strain, fs, nperseg=NPERSEG):
    nps = min(nperseg, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window="hann")
    return freqs, psd


def bandpower(freqs, psd, f_lo=F_LOW, f_hi=F_HIGH):
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    return float(np.trapezoid(psd[mask], freqs[mask]))


def notch_known_lines(freqs, psd, known=KNOWN_LINES_HZ, hw=NOTCH_HZ):
    psd_n = psd.copy()
    for lf in known:
        nm = np.abs(freqs - lf) <= hw
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


def band_coherence(h1, l1, fs, f_lo=F_LOW, f_hi=F_HIGH, nperseg=NPERSEG):
    nps = min(nperseg, len(h1) // 4, len(l1) // 4)
    freqs, coh = signal.coherence(h1, l1, fs=fs,
                                  nperseg=nps, noverlap=nps // 2)
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    freqs_cp, Cxy = signal.csd(
        h1, l1, fs=fs,
        nperseg=nps, noverlap=nps // 2, window="hann")
    ph = np.deg2rad(np.angle(Cxy[mask], deg=True))
    R = float(np.abs(np.mean(np.exp(1j * ph))))
    mean_ph = float(np.rad2deg(np.angle(np.mean(np.exp(1j * ph)))))
    return float(np.mean(coh[mask])), R, mean_ph


# ---------------------------------------------------------------------------
# SINGLE-EVENT ARTIFACT GATE
# ---------------------------------------------------------------------------
def run_event_gate(event_name, trigger_gps, h1_path, l1_path):
    log(f"\n{'='*65}")
    log(f"EVENT: {event_name}  GPS: {trigger_gps}")
    log(f"{'='*65}")

    h1_ok = h1_path.exists()
    l1_ok = l1_path.exists()
    log(f"  H1 file: {'OK' if h1_ok else 'MISSING'} — {h1_path.name}")
    log(f"  L1 file: {'OK' if l1_ok else 'MISSING'} — {l1_path.name}")

    if not h1_ok or not l1_ok:
        log("  -> SKIPPED: strain files not available")
        log("  -> Run scripts/download_gw250207_strain.py first")
        return None

    result = {"event": event_name, "trigger_gps": trigger_gps}

    # -- 1. BANDPOWER (trigger + off-source) --
    log("\n  [1] Bandpower 20-210 Hz")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        s_trig, fs = load_window(path, trigger_gps, WIN_S)
        s_off, _ = load_window(path, trigger_gps - PSD_OFFSET_S, WIN_S)
        if s_trig is None:
            log(f"    {det}: load failed")
            continue
        f_t, p_t = compute_psd(s_trig, fs)
        bp_t = bandpower(f_t, p_t)
        bp_o = None
        if s_off is not None:
            f_o, p_o = compute_psd(s_off, fs)
            bp_o = bandpower(f_o, p_o)
        off_str = f"{bp_o:.3e}" if bp_o is not None else "N/A"
        log(f"    {det}: trigger={bp_t:.3e}  off-500s={off_str}")
        result[f"{det.lower()}_bp_trigger"] = float(bp_t)
        result[f"{det.lower()}_bp_off500"] = (
            float(bp_o) if bp_o is not None else None)

    h1_bp = result.get("h1_bp_trigger")
    l1_bp = result.get("l1_bp_trigger")
    if h1_bp is not None and l1_bp is not None:
        ratio = l1_bp / (h1_bp + 1e-300)
        result["l1_h1_ratio"] = round(ratio, 4)
        log(f"    L1/H1 ratio: {ratio:.3f}")

    # -- 2. MULTI-WINDOW STATIONARITY (+-500s, 4s steps) --
    log("\n  [2] Multi-window stationarity (+-500s)")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        bps = []
        offsets = np.arange(-500.0, 504.0, 4.0)
        for off in offsets:
            s, fs = load_window(path, trigger_gps + off, WIN_S)
            if s is None:
                continue
            f, p = compute_psd(s, fs)
            bps.append(bandpower(f, p))
        if len(bps) < 10:
            log(f"    {det}: too few windows ({len(bps)})")
            continue
        bps = np.array(bps)
        trig_s, trig_fs = load_window(path, trigger_gps, WIN_S)
        if trig_s is None:
            continue
        ft, pt = compute_psd(trig_s, trig_fs)
        bp_trig = bandpower(ft, pt)
        q = float(stats.percentileofscore(bps, bp_trig))
        z = (bp_trig - bps.mean()) / (bps.std() + 1e-300)
        log(f"    {det}: N={len(bps)}  quantile={q:.1f}%  z={z:+.2f}")
        result[f"{det.lower()}_stationarity_q"] = round(q, 2)
        result[f"{det.lower()}_stationarity_z"] = round(float(z), 4)

    # -- 3. LINE TEST --
    log("\n  [3] Line/notch test")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        s, fs = load_window(path, trigger_gps, WIN_S)
        if s is None:
            continue
        f, p = compute_psd(s, fs)
        bp_full = bandpower(f, p)
        p_notched = notch_known_lines(f, p)
        bp_notched = bandpower(f, p_notched)
        frac_in_lines = 1.0 - bp_notched / (bp_full + 1e-300)
        log(f"    {det}: full={bp_full:.3e}  notched={bp_notched:.3e}  "
            f"line_frac={frac_in_lines*100:.1f}%")
        result[f"{det.lower()}_line_frac"] = round(frac_in_lines, 4)

    # -- 4. SUB-BAND KURTOSIS --
    log("\n  [4] Sub-band Gaussianity")
    for det, path in [("H1", h1_path), ("L1", l1_path)]:
        s, fs = load_window(path, trigger_gps, WIN_S)
        if s is None:
            continue
        for band_name, f_lo, f_hi in SUB_BANDS:
            x = bandpass_normalize(s, fs, f_lo, f_hi)
            ex_k = float(stats.kurtosis(x, fisher=True))
            label = f"{det}_{band_name}"
            log(f"    {label}: ex_k={ex_k:+.3f}")
            result[f"{det.lower()}_exk_{band_name}"] = round(ex_k, 4)

    # -- 5. CROSS-COHERENCE --
    log("\n  [5] H1/L1 cross-coherence")
    h1_s, fs_h = load_window(h1_path, trigger_gps, WIN_S)
    l1_s, fs_l = load_window(l1_path, trigger_gps, WIN_S)
    if h1_s is not None and l1_s is not None:
        n = min(len(h1_s), len(l1_s))
        coh_mean, R, mean_ph = band_coherence(
            h1_s[:n], l1_s[:n], fs_h)
        log(f"    mean_coh={coh_mean:.4f}  phase_R={R:.4f}  "
            f"mean_phase={mean_ph:+.1f}deg")
        result["coh_mean"] = round(coh_mean, 5)
        result["cross_phase_R"] = round(R, 4)
        result["cross_phase_deg"] = round(mean_ph, 2)

    return result


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"GW250207 ARTIFACT GATE — CROSS-EVENT COMPARISON -- {NOW}")
    log(f"GW240925 GPS: {GW240925_GPS}")
    log(f"GW250207 GPS: {GW250207_GPS}")

    results = []

    r240 = run_event_gate(
        "GW240925", GW240925_GPS, H1_240925, L1_240925)
    if r240:
        results.append(r240)

    r250 = run_event_gate(
        "GW250207", GW250207_GPS, H1_250207, L1_250207)
    if r250:
        results.append(r250)

    # ---------------------------------------------------------------------------
    # COMPARISON SUMMARY
    # ---------------------------------------------------------------------------
    log(f"\n{'='*65}")
    log("CROSS-EVENT COMPARISON SUMMARY")
    log(f"{'='*65}")

    metrics = [
        ("l1_h1_ratio", "L1/H1 BP ratio"),
        ("l1_stationarity_q", "L1 stationarity quantile (%)"),
        ("h1_stationarity_q", "H1 stationarity quantile (%)"),
        ("l1_line_frac", "L1 line fraction"),
        ("coh_mean", "H1/L1 coherence"),
        ("cross_phase_R", "Cross-phase stability R"),
        ("cross_phase_deg", "Mean cross-phase (deg)"),
    ]

    for key, label in metrics:
        vals = [(r["event"], r.get(key)) for r in results]
        parts = "  ".join(
            f"{ev}: {v:.4f}" if isinstance(v, float) else f"{ev}: N/A"
            for ev, v in vals
        )
        log(f"  {label:35s} {parts}")

    # Gate verdict
    log(f"\n  {'EVENT':15s} {'L1/H1':>8} {'L1-Q%':>8} {'Coh':>8} "
        f"{'Phase':>10} {'GATE'}")
    log("  " + "-" * 60)
    for r in results:
        ratio = r.get("l1_h1_ratio", float("nan"))
        q = r.get("l1_stationarity_q", float("nan"))
        coh = r.get("coh_mean", float("nan"))
        ph = r.get("cross_phase_deg", float("nan"))

        if ratio < 1.5 and q < 90:
            gate = "PASS_INVESTIGATE_SSZ"
        elif ratio > 2.0 or q > 95:
            gate = "FAIL_L1_EXCESS"
        else:
            gate = "MARGINAL_NEEDS_DQ"
        log(f"  {r['event']:15s} {ratio:>8.3f} {q:>8.1f} "
            f"{coh:>8.4f} {ph:>+10.1f} {gate}")

    # ---------------------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------------------
    csv_path = MANIFEST / "gw250207_artifact_gate.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        if results:
            fields = list(results[0].keys())
            for r in results[1:]:
                for k in r:
                    if k not in fields:
                        fields.append(k)
            w = csv.DictWriter(fh, fieldnames=fields,
                               extrasaction="ignore", restval="N/A")
            w.writeheader()
            w.writerows(results)

    md_lines = [
        "# GW250207 Artifact Gate — Cross-Event Comparison",
        f"Generated: {NOW}",
        "",
        "## Events",
        f"- GW240925 GPS: {GW240925_GPS}",
        f"- GW250207 GPS: {GW250207_GPS}",
        "",
        "## Configuration",
        f"- Band: {F_LOW}-{F_HIGH} Hz  Window: {WIN_S}s",
        f"- Stationarity: +-{PSD_OFFSET_S}s in 4s steps",
        f"- Known lines notched: {KNOWN_LINES_HZ}",
        "",
        "## Comparison Table",
        "",
        "| Metric | GW240925 | GW250207 |",
        "|--------|----------|----------|",
    ]

    def _fmt(v):
        return f"{v:.4f}" if isinstance(v, float) else str(v)

    for key, label in metrics:
        v240 = results[0].get(key, "N/A") if results else "N/A"
        v250 = results[1].get(key, "N/A") if len(results) > 1 else "N/A"
        md_lines.append(f"| {label} | {_fmt(v240)} | {_fmt(v250)} |")

    md_lines += [
        "",
        "## Interpretation",
        "- L1/H1 ratio < 1.5 and L1-Q < 90%: cleaner event",
        "- L1/H1 ratio > 2.0 or L1-Q > 95%: L1 excess, gate FAIL",
        "",
        "## GW250207 Strain Data",
        "- Required: O4b 4kHz HDF5, 4096s block at GPS 1422964096",
        "- Download: run `scripts/download_gw250207_strain.py`",
        "- GWOSC: https://gwosc.org/events/GW250207_115645/",
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]

    rpath = REPORTS / "GW250207_ARTIFACT_GATE_REPORT.md"
    rpath.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    flush_log()


if __name__ == "__main__":
    run()
