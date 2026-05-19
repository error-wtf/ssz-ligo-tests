"""H1/L1 Time-Delay Replication Test.

Tests whether the L1 20-40 Hz anomaly has a delayed H1 counterpart
(real GW signal) or is L1-only detector structure.

Subbands: 20-40, 40-80, 80-120, 120-160, 160-210, 20-210 Hz
Delays: coarse +/-50ms, fine +/-10ms; sign-flip test (-L1)
Metrics: xcorr, coherence, cross-phase std, residual std

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
LOGS = Path(__file__).parent.parent / "logs"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for _d in (REPORTS, LOGS, MANIFEST):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "h1_l1_time_delay_replication.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(str(msg))


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


TRIGGER_GPS = 1411261107.984
WIN_S = 4.0
PSD_OFFSET_S = 500.0
NPERSEG = 1024
COARSE_MAX_MS = 50.0
FINE_MAX_MS = 10.0
PHYSICAL_MAX_MS = 10.012
COARSE_STEP_MS = 1.0
FINE_STEP_MS = 0.244

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


def load_strain(path, t_center, dur):
    """Load strain with enough padding for the coarse delay scan.

    Loads [t_center - dur/2 - pad, t_center + dur/2 + pad + COARSE_MAX_S]
    so that extract() can always find dur seconds starting at t_center,
    and scan() can shift L1 by up to +COARSE_MAX_S forward.
    """
    if not path.exists():
        return None, None, None
    shift_pad = COARSE_MAX_MS / 1000.0 + 0.05   # max positive shift
    pre_pad = COARSE_MAX_MS / 1000.0 + 0.05     # max negative shift
    with h5py.File(path, "r") as f:
        gps0 = float(f["meta"]["GPSstart"][()])
        n_total = f["strain/Strain"].shape[0]
        dur_file = float(f["meta"]["Duration"][()])
        fs = n_total / dur_file
        t_off = t_center - gps0
        i0 = max(0, int((t_off - dur / 2 - pre_pad) * fs))
        i1 = min(n_total, int((t_off + dur / 2 + shift_pad) * fs))
        strain = f["strain/Strain"][i0:i1].astype(float)
        t0 = gps0 + i0 / fs
    min_needed = int((dur + pre_pad + shift_pad) * fs * 0.9)
    if not np.all(np.isfinite(strain)) or len(strain) < min_needed:
        return None, None, None
    return strain, float(fs), float(t0)


def extract(strain, fs, t0, t_center, dur):
    i0 = int(round((t_center - dur / 2 - t0) * fs))
    n = int(round(dur * fs))
    if i0 < 0 or i0 + n > len(strain):
        return None
    return strain[i0:i0 + n].copy()


def bandpass(x, fs, f_lo, f_hi, order=4):
    nyq = fs / 2.0
    sos = signal.butter(order, [max(f_lo, 1.0), min(f_hi, nyq * 0.99)],
                        btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def whiten(x, fs, ref_f, ref_a):
    n = len(x)
    ff = np.fft.rfftfreq(n, d=1.0 / fs)
    ai = np.interp(ff, ref_f, ref_a + 1e-300)
    return np.fft.irfft(np.fft.rfft(x) / ai, n=n)


def prep(raw, fs, ref_f, ref_a, f_lo, f_hi):
    w = whiten(raw, fs, ref_f, ref_a) if ref_f is not None else raw.copy()
    bp = bandpass(w, fs, f_lo, f_hi)
    s = np.std(bp)
    return bp / (s + 1e-300)


def ref_asd_from_file(path, dur=32.0):
    """Compute ASD from the first `dur` seconds of the HDF5 file."""
    if not path.exists():
        return None, None
    with h5py.File(path, "r") as f:
        n_total = f["strain/Strain"].shape[0]
        dur_file = float(f["meta"]["Duration"][()])
        fs = n_total / dur_file
        n_ref = min(int(dur * fs), n_total // 2)
        offset = n_total // 8  # skip first 12.5% for settling
        strain = f["strain/Strain"][offset:offset + n_ref].astype(float)
    if not np.all(np.isfinite(strain)) or len(strain) < NPERSEG * 4:
        return None, None
    nps = min(NPERSEG, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window="hann")
    return freqs, np.sqrt(np.maximum(psd, 1e-100))


def xcorr_lag_scan(h1_n, l1_n, fs, delays_ms):
    """Compute normalized cross-correlation at specified lags via FFT.

    Uses the proper xcorr function evaluated at requested lag offsets,
    not zero-lag of time-shifted copies (which aliases sinusoidal bands).
    Returns list of (dt_ms, xc) for each requested delay.
    """
    n = len(h1_n)
    a = h1_n - h1_n.mean()
    b = l1_n - l1_n.mean()
    norm = np.sqrt(np.dot(a, a) * np.dot(b, b) + 1e-300)
    # Full xcorr via FFT: lags run from -(n-1) to +(n-1)
    xc_full = np.fft.irfft(
        np.fft.rfft(a, n=2 * n) * np.conj(np.fft.rfft(b, n=2 * n)),
        n=2 * n
    )[:2 * n]
    # Re-order to centered form: negative lags, zero, positive lags
    # irfft output: lags 0..n-1 at indices 0..n-1, lags -n..-1 at n..2n-1
    xc_full = np.concatenate([xc_full[n + 1:], xc_full[:n]]) / norm
    # xc_full[n-1] = lag 0, xc_full[0] = lag -(n-1)
    # Map delays_ms to sample indices
    results = []
    for dt_ms in delays_ms:
        lag_samp = int(round(dt_ms / 1000.0 * fs))
        idx = lag_samp + (n - 1)  # offset into the reordered array
        if 0 <= idx < len(xc_full):
            xc = float(np.clip(xc_full[idx], -1.0, 1.0))
        else:
            xc = float("nan")
        results.append((dt_ms, xc))
    return results


def scan(h1_n, l1_seg, fs, f_lo, f_hi, delays_ms):
    """Evaluate xcorr, coherence, phase-std, residual-std at each lag.

    Uses a single prepared L1 segment and evaluates the cross-correlation
    function at the requested lags via FFT — no re-shifting or re-filtering.
    """
    n = len(h1_n)
    xc_pairs = xcorr_lag_scan(h1_n, l1_seg, fs, delays_ms)
    nps = min(NPERSEG, n // 4)
    fc, coh = signal.coherence(h1_n, l1_seg, fs=fs,
                               nperseg=nps, noverlap=nps // 2)
    band_mask = (fc >= f_lo) & (fc <= f_hi)
    coh_m = float(np.mean(coh[band_mask])) if band_mask.any() else np.nan
    H = np.fft.rfft(h1_n)
    L = np.fft.rfft(l1_seg)
    ff = np.fft.rfftfreq(n, d=1.0 / fs)
    fm = (ff >= f_lo) & (ff <= f_hi)
    ph_std = float(np.std(np.angle(H[fm] * np.conj(L[fm])))) if fm.any() else np.nan
    a = float(np.dot(h1_n, l1_seg) / (np.dot(l1_seg, l1_seg) + 1e-300))
    res_std = float(np.std(h1_n - a * l1_seg))
    rows = []
    for dt_ms, xc in xc_pairs:
        rows.append((dt_ms, xc, coh_m, ph_std, res_std))
    return rows


def classify(trig_rows, off_rows, band_name):
    """Classify H1/L1 replication status for one subband.

    Saturation guard: if |xcorr| > 0.95 at the boundary of the scan range
    (|dt| == FINE_MAX_MS), the peak is not resolved — classify as SYSTEMATIC.
    This indicates a broadband correlated term (e.g. common-mode drift,
    identical whitening reference, or non-GW correlation) rather than a
    physical time-delay peak.
    """
    def best_physical(rows):
        ph = [(dt, xc, coh) for dt, xc, coh, _, _ in rows
              if abs(dt) <= PHYSICAL_MAX_MS and np.isfinite(xc)]
        if not ph:
            return None
        return max(ph, key=lambda r: abs(r[1]))

    def best_unphysical(rows):
        uph = [(dt, xc, coh) for dt, xc, coh, _, _ in rows
               if abs(dt) > PHYSICAL_MAX_MS and np.isfinite(xc)]
        if not uph:
            return None
        return max(uph, key=lambda r: abs(r[1]))

    def noise_floor(rows):
        """Mean |xcorr| in unphysical range as noise floor estimate."""
        vals = [abs(xc) for dt, xc, _, _, _ in rows
                if abs(dt) > PHYSICAL_MAX_MS and np.isfinite(xc)]
        return float(np.mean(vals)) if vals else 0.05

    bp = best_physical(trig_rows)
    bu = best_unphysical(trig_rows)
    nfloor = noise_floor(trig_rows)

    if bp is None:
        return "INCONCLUSIVE", bp, bu

    # Saturation check: peak at scan boundary with |xc| > 0.95
    at_boundary = abs(abs(bp[0]) - FINE_MAX_MS) < FINE_STEP_MS * 2
    if at_boundary and abs(bp[1]) > 0.95:
        return "SYSTEMATIC_SATURATION", bp, bu

    # SNR = |peak xcorr| / noise floor (unphysical range mean)
    peak_snr = abs(bp[1]) / (nfloor + 1e-10)

    if peak_snr > 5 and (bu is None or abs(bp[1]) > abs(bu[1]) * 1.5):
        verdict = "PHYSICAL_DELAY_COHERENT"
    elif bu is not None and abs(bu[1]) > abs(bp[1]) * 1.5:
        verdict = "UNPHYSICAL_DELAY_PREFERRED"
    elif peak_snr < 2:
        verdict = "L1_ONLY_STRUCTURE"
    else:
        verdict = "INCONCLUSIVE"
    return verdict, bp, bu


def run():
    log(f"H1/L1 TIME-DELAY REPLICATION TEST -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s")
    log(f"Delays coarse: +/-{COARSE_MAX_MS}ms step={COARSE_STEP_MS}ms")
    log(f"Delays fine:   +/-{FINE_MAX_MS}ms step={FINE_STEP_MS}ms")
    log(f"Physical range: |dt|<={PHYSICAL_MAX_MS}ms")

    delays_coarse = np.arange(-COARSE_MAX_MS, COARSE_MAX_MS + COARSE_STEP_MS,
                               COARSE_STEP_MS)
    delays_fine = np.arange(-FINE_MAX_MS, FINE_MAX_MS + FINE_STEP_MS,
                             FINE_STEP_MS)

    log("\nLoading reference ASDs from file (first 32s of HDF5)...")
    h1_rf, h1_ra = ref_asd_from_file(H1_PATH, dur=32.0)
    l1_rf, l1_ra = ref_asd_from_file(L1_PATH, dur=32.0)
    log(f"  H1 ref ASD: {'OK' if h1_rf is not None else 'FAILED'}")
    log(f"  L1 ref ASD: {'OK' if l1_rf is not None else 'FAILED'}")

    all_csv = []
    verdicts = {}

    windows = [
        ("TRIGGER",  TRIGGER_GPS),
        ("OFF_m500", TRIGGER_GPS - PSD_OFFSET_S),
    ]

    for win_tag, t_center in windows:
        log(f"\n{'='*60}")
        log(f"WINDOW: {win_tag}")
        log(f"{'='*60}")

        h1_pad, fs, t0_h1 = load_strain(H1_PATH, t_center, WIN_S)
        l1_pad, fs_l, t0_l1 = load_strain(L1_PATH, t_center, WIN_S)

        if h1_pad is None or l1_pad is None:
            log("  LOAD FAILED — skip")
            continue

        log(f"  fs={fs:.0f}Hz  H1={len(h1_pad)} L1={len(l1_pad)} samples")
        log(f"  H1 t0={t0_h1:.3f}  t_center={t_center:.3f}  "
            f"offset={t_center - t0_h1:.3f}s  "
            f"array_end={t0_h1 + len(h1_pad)/fs:.3f}")

        h1_seg = extract(h1_pad, fs, t0_h1, t_center, WIN_S)
        if h1_seg is None:
            log(f"  H1 extract failed: i0={int(round((t_center - t0_h1)*fs))} "
                f"n={int(round(WIN_S*fs))} len={len(h1_pad)} — skip")
            continue

        l1_seg = extract(l1_pad, fs_l, t0_l1, t_center, WIN_S)
        if l1_seg is None:
            log("  L1 extract failed — skip")
            continue

        for band_name, f_lo, f_hi in SUBBANDS:
            log(f"\n  Band: {band_name} Hz")
            h1_n = prep(h1_seg, fs, h1_rf, h1_ra, f_lo, f_hi)
            l1_n_pos = prep(l1_seg, fs_l, l1_rf, l1_ra, f_lo, f_hi)
            l1_n_neg = prep(-l1_seg, fs_l, l1_rf, l1_ra, f_lo, f_hi)

            rows_c = scan(h1_n, l1_n_pos, fs, f_lo, f_hi, delays_coarse)
            rows_f = scan(h1_n, l1_n_pos, fs, f_lo, f_hi, delays_fine)
            rows_neg = scan(h1_n, l1_n_neg, fs, f_lo, f_hi, delays_fine)

            verdict, bp, bu = classify(rows_f, [], band_name)
            verdicts[(win_tag, band_name)] = verdict
            log(f"    VERDICT: {verdict}")
            if bp:
                log(f"    Best physical: dt={bp[0]:+.2f}ms "
                    f"xcorr={bp[1]:+.5f} coh={bp[2]:.4f}")
            if bu:
                log(f"    Best unphysical: dt={bu[0]:+.2f}ms "
                    f"xcorr={bu[1]:+.5f} coh={bu[2]:.4f}")

            # Sign flip summary
            xc_pos = [r[1] for r in rows_f
                      if abs(r[0]) <= PHYSICAL_MAX_MS and np.isfinite(r[1])]
            xc_neg = [r[1] for r in rows_neg
                      if abs(r[0]) <= PHYSICAL_MAX_MS and np.isfinite(r[1])]
            if xc_pos and xc_neg:
                best_pos = max(xc_pos, key=abs)
                best_neg = max(xc_neg, key=abs)
                log(f"    Sign-flip: +L1 best_xc={best_pos:+.5f}  "
                    f"-L1 best_xc={best_neg:+.5f}")

            for sign_tag, rows in [("POS", rows_c), ("NEG", rows_neg[:len(rows_c)])]:
                for dt_ms, xc, coh_m, ph_std, res_std in rows:
                    all_csv.append({
                        "window": win_tag,
                        "band": band_name,
                        "sign": sign_tag,
                        "delay_ms": round(float(dt_ms), 3),
                        "xcorr": round(float(xc), 7) if np.isfinite(xc) else "",
                        "coh": round(float(coh_m), 6) if np.isfinite(coh_m) else "",
                        "phase_std": round(float(ph_std), 5) if np.isfinite(ph_std) else "",
                        "resid_std": round(float(res_std), 6) if np.isfinite(res_std) else "",
                        "is_physical": abs(dt_ms) <= PHYSICAL_MAX_MS,
                    })

    # ---------------------------------------------------------------------------
    # L1 20-40 Hz specific classification
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("FINAL CLASSIFICATION")
    log(f"{'='*60}")

    v_2040 = verdicts.get(("TRIGGER", "20-40"), "INCONCLUSIVE")
    v_full = verdicts.get(("TRIGGER", "20-210"), "INCONCLUSIVE")

    if v_2040 == "PHYSICAL_DELAY_COHERENT":
        l1_2040_status = "H1_REPLICATED_WITH_DELAY"
    elif v_2040 == "L1_ONLY_STRUCTURE":
        l1_2040_status = "L1_ONLY_NON_GAUSSIAN"
    elif v_2040 == "SYSTEMATIC_SATURATION":
        l1_2040_status = "SYSTEMATIC_SATURATION_UNRESOLVED"
    else:
        l1_2040_status = "INCONCLUSIVE"

    v_off_2040 = verdicts.get(("OFF_m500", "20-40"), "INCONCLUSIVE")
    v_off_full = verdicts.get(("OFF_m500", "20-210"), "INCONCLUSIVE")

    # If trigger and off-source give same verdict, the "signal" is not
    # specific to the trigger — it is a persistent systematic or
    # environmental common-mode correlation present throughout the file.
    trig_specific = (v_2040 != v_off_2040)

    log(f"H1_L1_REPLICATION_STATUS TRIGGER (full band): {v_full}")
    log(f"H1_L1_REPLICATION_STATUS TRIGGER (20-40 Hz):  {v_2040}")
    log(f"H1_L1_REPLICATION_STATUS OFF_m500 (full band): {v_off_full}")
    log(f"H1_L1_REPLICATION_STATUS OFF_m500 (20-40 Hz):  {v_off_2040}")
    log(f"TRIGGER_SPECIFIC: {trig_specific}")
    log(f"L1_20_40_STATUS:  {l1_2040_status}")
    if not trig_specific:
        log("WARNING: Trigger and off-source give same verdict.")
        log("  The coherence is NOT specific to the trigger window.")
        log("  Likely cause: persistent H1/L1 environmental correlation")
        log("  (Schumann resonances, common noise) or data artifact.")
        log("  This result CANNOT be used to claim GW signal replication.")
    log("")
    log("READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
    log("SSZ_SUPPORT_CLAIM_MADE: NO")
    log("SSZ_FALSIFICATION_CLAIM_MADE: NO")

    # ---------------------------------------------------------------------------
    # CSV
    # ---------------------------------------------------------------------------
    csv_path = MANIFEST / "h1_l1_delay_scan.csv"
    if all_csv:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(all_csv[0].keys()))
            w.writeheader()
            w.writerows(all_csv)
        log(f"\nCSV: {csv_path}  ({len(all_csv)} rows)")

    # ---------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------
    md = [
        "# H1/L1 Time-Delay Replication Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s",
        f"- Coarse scan: +/-{COARSE_MAX_MS}ms step={COARSE_STEP_MS}ms",
        f"- Fine scan: +/-{FINE_MAX_MS}ms step={FINE_STEP_MS}ms",
        f"- Physical range: |dt| <= {PHYSICAL_MAX_MS}ms",
        f"- Sign-flip test: +L1 and -L1",
        "",
        "## Subbands",
        "| Band | f_lo | f_hi |",
        "|------|------|------|",
    ]
    for bn, fl, fh in SUBBANDS:
        md.append(f"| {bn} | {fl} | {fh} |")

    specificity_flag = "YES" if trig_specific else "NO — PERSISTENT_SYSTEMATIC"
    md += [
        "",
        "## Final Classification",
        "| Key | Value |",
        "|-----|-------|",
        f"| H1_L1_REPLICATION_STATUS TRIGGER (20-210 Hz) | {v_full} |",
        f"| H1_L1_REPLICATION_STATUS TRIGGER (20-40 Hz) | {v_2040} |",
        f"| H1_L1_REPLICATION_STATUS OFF_m500 (20-210 Hz) | {v_off_full} |",
        f"| H1_L1_REPLICATION_STATUS OFF_m500 (20-40 Hz) | {v_off_2040} |",
        f"| TRIGGER_SPECIFIC | {specificity_flag} |",
        f"| L1_20_40_STATUS | {l1_2040_status} |",
        "",
        "## Subband Verdicts",
        "| Band | TRIGGER | OFF_m500 |",
        "|------|---------|----------|",
    ]
    for bn, _, _ in SUBBANDS:
        vt = verdicts.get(("TRIGGER", bn), "N/A")
        vo = verdicts.get(("OFF_m500", bn), "N/A")
        md.append(f"| {bn} Hz | {vt} | {vo} |")

    if not trig_specific:
        md += [
            "",
            "## WARNING: Non-Specific Coherence",
            "The trigger and off-source windows show the same verdict.",
            "The H1/L1 coherence is NOT specific to the trigger.",
            "Likely cause: persistent environmental common-mode correlation",
            "(Schumann resonances, 60 Hz harmonics, or common noise floor).",
            "**This result CANNOT be used to claim GW signal replication.**",
            "Further analysis with longer off-source baselines required.",
        ]

    md += [
        "",
        "## Interpretation Key",
        "- PHYSICAL_DELAY_COHERENT: peak |xcorr| at |dt|<=10ms,",
        "  SNR>5 vs unphysical range noise floor",
        "- L1_ONLY_STRUCTURE: no physical peak, SNR<2",
        "- UNPHYSICAL_DELAY_PREFERRED: peak outside physical range",
        "- INCONCLUSIVE: ambiguous evidence",
        "- SYSTEMATIC_SATURATION: xcorr saturated at scan boundary",
        "",
        "## Anti-Circularity",
        "- No PE/QNM posteriors used",
        "- No Kerr/SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]

    rpath = REPORTS / "H1_L1_TIME_DELAY_REPLICATION_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")
    log(f"Report: {rpath}")
    flush_log()


if __name__ == "__main__":
    run()
