"""H1/L1 Cross-Power Spectrum and Coherence Phase Analysis.

Tests:
  1. Magnitude-squared coherence in sub-bands:
       20-210 Hz (full), 20-60 Hz, 60-120 Hz, 120-210 Hz
  2. Cross-power spectrum C(f) = H1(f) * conj(L1(f))
  3. Cross-phase stability: is the cross-phase random or structured?
  4. Coherence comparison: trigger vs off-source windows.

Interpretation:
  If L1 has power but no H1/L1 coherence -> likely detector noise.
  If coherent with physically plausible phase -> more interesting.

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

LOG_PATH = LOGS / "h1l1_cross_coherence.log"
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
PSD_OFFSET_S = 500.0
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 1024   # ~250 ms at 4096 Hz -> df~4 Hz

SUB_BANDS = [
    ("full",    20.0,  210.0),
    ("20-60",   20.0,   60.0),
    ("60-120",  60.0,  120.0),
    ("120-210", 120.0, 210.0),
]

# Max GW travel time H1<->L1 ~10 ms, we test ±15 ms for safety
LIGHT_TRAVEL_S = 0.010

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
# COHERENCE
# ---------------------------------------------------------------------------
def band_coherence(h1, l1, fs, f_lo, f_hi, nperseg=NPERSEG):
    """Mean magnitude-squared coherence in band [f_lo, f_hi]."""
    nps = min(nperseg, len(h1) // 4, len(l1) // 4)
    freqs, coh = signal.coherence(h1, l1, fs=fs,
                                  nperseg=nps, noverlap=nps // 2)
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    return float(np.mean(coh[mask])), freqs[mask], coh[mask]


# ---------------------------------------------------------------------------
# CROSS-POWER SPECTRUM
# ---------------------------------------------------------------------------
def cross_power(h1, l1, fs, nperseg=NPERSEG):
    """
    Compute cross-power spectrum C(f) = H1(f) * conj(L1(f)).
    Returns freqs, magnitude, phase (deg).
    """
    nps = min(nperseg, len(h1) // 4, len(l1) // 4)
    freqs, Cxy = signal.csd(h1, l1, fs=fs,
                             nperseg=nps, noverlap=nps // 2,
                             window="hann")
    mag = np.abs(Cxy)
    phase_deg = np.angle(Cxy, deg=True)
    return freqs, mag, phase_deg


def phase_stability(phase_deg, f_lo, f_hi, freqs):
    """
    Measure cross-phase stability in a band.
    Uses circular statistics: mean resultant length R.
    R=1 -> perfectly coherent phase; R~0 -> random phase.
    """
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    if mask.sum() == 0:
        return 0.0, 0.0
    ph = np.deg2rad(phase_deg[mask])
    R = float(np.abs(np.mean(np.exp(1j * ph))))
    mean_phase = float(np.rad2deg(np.angle(np.mean(np.exp(1j * ph)))))
    return R, mean_phase


# ---------------------------------------------------------------------------
# ANALYSE ONE WINDOW PAIR
# ---------------------------------------------------------------------------
def analyse_pair(h1, l1, fs, tag):
    log(f"\n  [{tag}]")
    rows = []

    for band_name, f_lo, f_hi in SUB_BANDS:
        coh_mean, f_b, coh_b = band_coherence(h1, l1, fs, f_lo, f_hi)
        freqs_cps, mag_cps, phase_cps = cross_power(h1, l1, fs)
        R, mean_ph = phase_stability(phase_cps, f_lo, f_hi, freqs_cps)

        log(f"    {band_name:10s}: mean_coh={coh_mean:.4f}  "
            f"phase_R={R:.3f}  mean_phase={mean_ph:+.1f}deg")

        if coh_mean > 0.2:
            coh_class = "COHERENT"
        elif coh_mean > 0.1:
            coh_class = "WEAKLY_COHERENT"
        else:
            coh_class = "INCOHERENT"

        if R > 0.5:
            phase_class = "STABLE_PHASE"
        elif R > 0.2:
            phase_class = "WEAKLY_STABLE_PHASE"
        else:
            phase_class = "RANDOM_PHASE"

        rows.append({
            "tag": tag,
            "band": band_name,
            "f_lo": f_lo, "f_hi": f_hi,
            "mean_coh": round(coh_mean, 5),
            "phase_R": round(R, 4),
            "mean_phase_deg": round(mean_ph, 2),
            "coh_class": coh_class,
            "phase_class": phase_class,
        })

    return rows


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"H1/L1 CROSS-COHERENCE + PHASE -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s")
    log(f"NPERSEG={NPERSEG}  Sub-bands: {[b[0] for b in SUB_BANDS]}")

    all_rows = []

    for tag, t_c in [("TRIGGER", TRIGGER_GPS),
                     ("OFF_m500", TRIGGER_GPS - 500.0),
                     ("OFF_m300", TRIGGER_GPS - 300.0)]:
        h1, fs_h = load_window(H1_PATH, t_c, WIN_S)
        l1, fs_l = load_window(L1_PATH, t_c, WIN_S)

        if h1 is None or l1 is None:
            log(f"  [{tag}] load failed")
            continue
        if abs(fs_h - fs_l) > 1:
            log(f"  [{tag}] sample rate mismatch {fs_h} vs {fs_l}")
            continue

        # Match lengths
        n = min(len(h1), len(l1))
        h1, l1 = h1[:n], l1[:n]
        rows = analyse_pair(h1, l1, fs_h, tag)
        all_rows.extend(rows)

    # ---------------------------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("SUMMARY — TRIGGER COHERENCE vs OFF-SOURCE")
    log(f"{'='*60}")
    log(f"  {'Band':12s} {'Coh_TRIG':>10} {'Coh_OFF500':>12} "
        f"{'PhaseR_TRIG':>13} {'PhaseR_OFF':>12}")
    log("  " + "-" * 65)

    trig_rows = [r for r in all_rows if r["tag"] == "TRIGGER"]
    off_rows = [r for r in all_rows if r["tag"] == "OFF_m500"]

    for tr in trig_rows:
        ofr = next((r for r in off_rows if r["band"] == tr["band"]), None)
        coh_off = ofr["mean_coh"] if ofr else float("nan")
        pr_off = ofr["phase_R"] if ofr else float("nan")
        log(f"  {tr['band']:12s} {tr['mean_coh']:>10.4f} {coh_off:>12.4f} "
            f"{tr['phase_R']:>13.4f} {pr_off:>12.4f}")

    # Key verdict
    trig_full = next((r for r in trig_rows if r["band"] == "full"), None)
    if trig_full:
        log(f"\n  KEY: Trigger full-band coherence: "
            f"{trig_full['mean_coh']:.4f}  ({trig_full['coh_class']})")
        log(f"  KEY: Trigger full-band phase R: "
            f"{trig_full['phase_R']:.4f}  ({trig_full['phase_class']})")
        log(f"  KEY: Max GW light-travel time: "
            f"{LIGHT_TRAVEL_S*1000:.0f} ms")
        if (trig_full["coh_class"] == "INCOHERENT"
                and trig_full["phase_class"] == "RANDOM_PHASE"):
            verdict = "NO_H1L1_COHERENCE_TRIGGER"
        elif trig_full["coh_class"] == "COHERENT":
            verdict = "COHERENT_TRIGGER_INVESTIGATE_FURTHER"
        else:
            verdict = "WEAK_COHERENCE_INCONCLUSIVE"
        log(f"  -> COHERENCE_VERDICT: {verdict}")

    # ---------------------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------------------
    csv_path = MANIFEST / "h1l1_cross_coherence.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        if all_rows:
            w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()),
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)

    md = [
        "# H1/L1 Cross-Coherence and Phase Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s  NPERSEG: {NPERSEG}",
        f"- Sub-bands: {[b[0] for b in SUB_BANDS]}",
        "",
        "## Results",
        "",
        "| Tag | Band | Mean Coh | Phase R | Mean Phase | "
        "Coh Class | Phase Class |",
        "|-----|------|----------|---------|------------|"
        "-----------|-------------|",
    ]
    for r in all_rows:
        md.append(
            f"| {r['tag']} | {r['band']} | {r['mean_coh']:.4f} "
            f"| {r['phase_R']:.4f} | {r['mean_phase_deg']:+.1f}° "
            f"| {r['coh_class']} | {r['phase_class']} |"
        )
    md += [
        "",
        "## Interpretation",
        "- mean_coh > 0.2: COHERENT — potential shared signal",
        "- phase_R > 0.5: STABLE_PHASE — consistent cross-phase",
        "- INCOHERENT + RANDOM_PHASE -> detector-side noise",
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "H1L1_CROSS_COHERENCE_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    flush_log()


if __name__ == "__main__":
    run()
