"""L1 Harmonic Oscillator / Resonance Structure Test.

Prüft ob L1-Auffälligkeit Struktur eines harmonischen Oszillators hat.
Kein SSZ-Claim. Reiner Struktur-/Artefakt-Test.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
"""
import datetime
import csv
import numpy as np
import h5py
from pathlib import Path
from scipy import signal
from scipy.signal import find_peaks

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
for _d in (REPORTS, LOGS):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "l1_harmonic_oscillator_test.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


TRIGGER_GPS = 1411261107.984
F_LOW, F_HIGH = 20.0, 210.0
WIN_S = 4.0
NPERSEG = 4096
OFF_OFFSET_S = 500.0
OFF_DUR_S = 16.0
PEAK_DB = 6.0
PEAK_DIST_HZ = 5.0
HARM_TOL_HZ = 3.0

_BASE = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_PATH = _BASE / "H1/1410334720/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
L1_PATH = _BASE / "L1/1410334720/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"


def load_window(path, t_center, dur):
    if not path.exists():
        return None, None
    with h5py.File(path, "r") as f:
        gps0 = float(f["meta"]["GPSstart"][()])
        duration_s = float(f["meta"]["Duration"][()])
        n_total = f["strain/Strain"].shape[0]
        fs = n_total / duration_s
        t_off = t_center - gps0
        i0 = max(0, int((t_off - dur / 2) * fs))
        i1 = min(n_total, int((t_off + dur / 2) * fs))
        strain = f["strain/Strain"][i0:i1]
    if not np.all(np.isfinite(strain)) or len(strain) == 0:
        return None, None
    return strain, fs


def bandpass(s, fs):
    nyq = fs / 2.0
    b, a = signal.butter(4, [F_LOW / nyq, F_HIGH / nyq], btype="band")
    return signal.filtfilt(b, a, s)


def psd_peaks(s, fs):
    nperseg = min(NPERSEG, len(s) // 4)
    freqs, psd = signal.welch(s, fs=fs, nperseg=nperseg,
                              window="hann", noverlap=nperseg // 2)
    mask = (freqs >= F_LOW) & (freqs <= F_HIGH)
    fb, pb = freqs[mask], psd[mask]
    if len(pb) < 10:
        return [], [], freqs, psd
    db = 10.0 * np.log10(pb + 1e-300)
    med = np.median(db)
    df = fb[1] - fb[0]
    min_d = max(1, int(PEAK_DIST_HZ / df))
    idx, _ = find_peaks(db, height=med + PEAK_DB, distance=min_d)
    return fb[idx].tolist(), (db[idx] - med).tolist(), freqs, psd


def harmonic_test(peaks):
    if len(peaks) < 2:
        return None, 0, []
    best_f0, best_n, best_t = None, 0, []
    for f0 in peaks:
        if f0 < 1.0:
            continue
        n, t = 0, []
        for fp in peaks:
            nr = round(fp / f0)
            if nr < 1:
                continue
            res = fp - nr * f0
            if abs(res) <= HARM_TOL_HZ:
                n += 1
                t.append((nr, fp, nr * f0, res))
        if n > best_n:
            best_n, best_f0, best_t = n, f0, t
    return best_f0, best_n, best_t


def damped_osc_test(bp, fs):
    env = np.abs(signal.hilbert(bp))
    n = len(env) // 2
    t = np.arange(n) / fs
    e = env[:n]
    m = e > 0
    if m.sum() < 10:
        return None, None, "INSUFFICIENT_DATA"
    c = np.polyfit(t[m], np.log(e[m]), 1)
    gamma = -c[0]
    pred = np.polyval(c, t[m])
    le = np.log(e[m])
    ss_res = np.sum((le - pred) ** 2)
    ss_tot = np.sum((le - np.mean(le)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    if r2 > 0.85 and gamma > 0:
        q = "DAMPED_OSCILLATOR_LIKELY"
    elif r2 > 0.6 and gamma > 0:
        q = "WEAK_DECAY_HINT"
    elif gamma <= 0:
        q = "GROWING_OR_FLAT"
    else:
        q = "NO_CLEAR_DECAY"
    return gamma, r2, q


def analyse(label, path, t_center, dur, tag="TRIGGER"):
    log(f"\n{'='*55}")
    log(f"{label} [{tag}]  t_center={t_center:.3f}  dur={dur}s")
    log(f"{'='*55}")
    r = {"label": label, "tag": tag}

    strain, fs = load_window(path, t_center, dur)
    if strain is None:
        log("  BLOCKED: file not found or load failed")
        r["status"] = "BLOCKED"
        return r

    log(f"  Loaded {len(strain)} samples @ {fs:.0f} Hz")
    bp = bandpass(strain, fs)
    peaks, heights, freqs, psd = psd_peaks(bp, fs)

    log(f"  Peaks ({len(peaks)}): "
        + ", ".join(f"{p:.1f}Hz(+{h:.1f}dB)" for p, h in zip(peaks, heights)))

    f0, n_harm, table = harmonic_test(peaks)
    r.update({"n_peaks": len(peaks), "peaks": peaks,
              "best_f0": f0, "n_harmonics": n_harm})

    if f0 is not None:
        log(f"  Harmonic test: f0={f0:.2f}Hz, {n_harm} peaks match")
        for row in table:
            nr, fp, exp, res = row
            log(f"    n={nr}  f={fp:.2f}Hz  n*f0={exp:.2f}Hz  d={res:+.2f}Hz")
    else:
        log("  Harmonic test: no fundamental found")

    gamma, r2, osc_q = damped_osc_test(bp, fs)
    r.update({"gamma": gamma, "r2": r2, "osc_quality": osc_q})
    if gamma is not None:
        log(f"  Envelope: gamma={gamma:.3f}/s  R2={r2:.3f}  -> {osc_q}")

    if n_harm >= 3:
        status = "HARMONIC_STRUCTURE_FOUND"
    elif n_harm == 2:
        status = "POSSIBLE_HARMONIC_PAIR"
    elif len(peaks) == 1:
        status = "SINGLE_PEAK_NO_HARMONICS"
    elif len(peaks) == 0:
        status = "NO_CLEAR_PEAK_STRUCTURE"
    else:
        status = "MULTIPLE_PEAKS_NO_HARMONIC_PATTERN"

    r["status"] = status
    log(f"  STATUS: {status}")
    return r


def run():
    log(f"L1 HARMONIC OSCILLATOR TEST — {NOW}")
    log(f"Band: {F_LOW}-{F_HIGH}Hz | Win: {WIN_S}s | "
        f"+{PEAK_DB}dB threshold | ±{HARM_TOL_HZ}Hz harmonic tol")

    results = []

    # 1. L1 trigger
    log("\n[1] L1 TRIGGER WINDOW")
    r_l1 = analyse("L1", L1_PATH, TRIGGER_GPS, WIN_S, "TRIGGER")
    results.append(r_l1)

    # 2. H1 trigger (cross-check: same peaks?)
    log("\n[2] H1 TRIGGER WINDOW (cross-check)")
    r_h1 = analyse("H1", H1_PATH, TRIGGER_GPS, WIN_S, "TRIGGER")
    results.append(r_h1)

    # 3. L1 off-source (same pattern in quiet data → artefact)
    log("\n[3] L1 OFF-SOURCE (-500s)")
    r_l1_off = analyse("L1", L1_PATH,
                       TRIGGER_GPS - OFF_OFFSET_S, OFF_DUR_S, "OFF_SOURCE")
    results.append(r_l1_off)

    # 4. H1 off-source
    log("\n[4] H1 OFF-SOURCE (-500s)")
    r_h1_off = analyse("H1", H1_PATH,
                       TRIGGER_GPS - OFF_OFFSET_S, OFF_DUR_S, "OFF_SOURCE")
    results.append(r_h1_off)

    # ---------------------------------------------------------------------------
    # CROSS-DETECTOR COMPARISON
    # ---------------------------------------------------------------------------
    log("\n" + "=" * 55)
    log("CROSS-DETECTOR COMPARISON")
    log("=" * 55)

    l1_peaks = set(round(p) for p in r_l1.get("peaks", []))
    h1_peaks = set(round(p) for p in r_h1.get("peaks", []))
    shared = l1_peaks & h1_peaks
    only_l1 = l1_peaks - h1_peaks
    only_h1 = h1_peaks - l1_peaks

    log(f"  L1 trigger peaks (rounded Hz): {sorted(l1_peaks)}")
    log(f"  H1 trigger peaks (rounded Hz): {sorted(h1_peaks)}")
    log(f"  Shared peaks: {sorted(shared)}")
    log(f"  Only in L1:  {sorted(only_l1)}")
    log(f"  Only in H1:  {sorted(only_h1)}")

    if shared:
        log("  -> Shared peaks: POSSIBLE ASTROPHYSICAL SIGNAL or COMMON ARTEFACT")
    if only_l1:
        log("  -> L1-only peaks: INSTRUMENT/LOCAL ARTEFACT CANDIDATE")

    # Off-source check
    l1_off_peaks = set(round(p) for p in r_l1_off.get("peaks", []))
    shared_with_off = l1_peaks & l1_off_peaks
    log(f"\n  L1 off-source peaks: {sorted(l1_off_peaks)}")
    if shared_with_off:
        log(f"  -> L1 peaks {sorted(shared_with_off)} ALSO IN OFF-SOURCE "
            "-> PERSISTENT ARTEFACT / SPECTRAL LINE")
        overall_status = "RESONANCE_IN_OFF_SOURCE_TOO"
    else:
        overall_status = r_l1.get("status", "DIAGNOSTIC_INCONCLUSIVE")

    log(f"\nOVERALL L1 HARMONIC STATUS: {overall_status}")

    # ---------------------------------------------------------------------------
    # WRITE REPORT
    # ---------------------------------------------------------------------------
    report_path = REPORTS / "L1_HARMONIC_OSCILLATOR_TEST.md"
    lines = [
        "# L1 Harmonic Oscillator / Resonance Test",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Band: {F_LOW}–{F_HIGH} Hz",
        f"- Trigger window: {WIN_S}s",
        f"- Peak threshold: +{PEAK_DB} dB above local median",
        f"- Harmonic tolerance: ±{HARM_TOL_HZ} Hz",
        "",
        "## Results",
    ]
    for r in results:
        lines.append(f"\n### {r['label']} [{r['tag']}]")
        lines.append(f"- Status: **{r.get('status', 'N/A')}**")
        lines.append(f"- Peaks: {r.get('peaks', [])}")
        lines.append(f"- Best f0: {r.get('best_f0')} Hz")
        lines.append(f"- Harmonics matched: {r.get('n_harmonics', 0)}")
        if r.get("gamma") is not None:
            lines.append(
                f"- Envelope decay: γ={r['gamma']:.3f}/s  "
                f"R²={r['r2']:.3f}  {r['osc_quality']}"
            )

    lines += [
        "",
        "## Cross-Detector",
        f"- L1 trigger peaks: {sorted(l1_peaks)}",
        f"- H1 trigger peaks: {sorted(h1_peaks)}",
        f"- Shared: {sorted(shared)}",
        f"- L1-only: {sorted(only_l1)}",
        f"- L1 off-source peaks: {sorted(l1_off_peaks)}",
        f"- Peaks also in off-source: {sorted(shared_with_off)}",
        "",
        f"## OVERALL STATUS: {overall_status}",
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- No posterior data used",
        "- No claim made",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"\nReport: {report_path}")

    # CSV manifest
    csv_path = REPORTS / "L1_HARMONIC_OSCILLATOR_TEST.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["label", "tag", "status", "n_peaks", "best_f0",
                        "n_harmonics", "gamma", "r2", "osc_quality"],
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(results)
    log(f"CSV:    {csv_path}")

    flush_log()
    return overall_status


if __name__ == "__main__":
    run()
