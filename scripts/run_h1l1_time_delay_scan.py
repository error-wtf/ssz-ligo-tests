"""H1/L1 Time-Delay Scan.

Scans relative L1 time shift from -20ms to +20ms vs H1.
For each shift: cross-correlation, coherence (full + sub-bands), lnL proxy.

Physics:
  GW travel time H1<->L1 <= 10.012 ms (3002 km / c).
  GW240925 sky position unknown without posterior, but physical range is
  -10 to +10 ms. We scan ±20 ms to include non-physical offsets as control.

Expected result for real correlated GW signal:
  Peak cross-correlation at physically plausible shift (|dt| < 10 ms).
Expected result for uncorrelated/detector noise:
  Broad/flat/random cross-correlation — no preferred physical shift.

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

LOG_PATH = LOGS / "h1l1_time_delay_scan.log"
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
NPERSEG = 1024

MAX_DELAY_S = 0.020     # ±20 ms
DELAY_STEP_S = 0.000244  # ~1 sample at 4096 Hz
MAX_LIGHT_TRAVEL_S = 0.010  # H1/L1 light travel time

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
        # Load extra padding for shifting
        pad = MAX_DELAY_S * 2
        i0 = max(0, int((t_off - dur / 2 - pad) * fs))
        i1 = min(n_total, int((t_off + dur / 2 + pad) * fs))
        strain = f["strain/Strain"][i0:i1]
        t0 = gps0 + i0 / fs
    if not np.all(np.isfinite(strain)) or len(strain) == 0:
        return None, None
    return strain.astype(float), float(fs), float(t0)


# ---------------------------------------------------------------------------
# SIGNAL PROCESSING
# ---------------------------------------------------------------------------
def bandpass(strain, fs, f_lo=F_LOW, f_hi=F_HIGH, order=4):
    sos = signal.butter(order, [f_lo, f_hi],
                        btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, strain)


def compute_psd_asd(strain, fs, nperseg=NPERSEG):
    """Compute ASD from a reference (off-source) segment."""
    nps = min(nperseg, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window="hann")
    return freqs, np.sqrt(psd)


def whiten_with_asd(strain, fs, ref_freqs, ref_asd):
    """Whiten strain using pre-computed reference ASD."""
    n = len(strain)
    fft_freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    asd_interp = np.interp(fft_freqs, ref_freqs, ref_asd + 1e-300)
    S = np.fft.rfft(strain)
    S_w = S / asd_interp
    return np.fft.irfft(S_w, n=n)


def extract_segment(strain, fs, t0_strain, t_center, dur):
    """Extract a fixed-duration segment from a pre-loaded array."""
    offset = t_center - t0_strain
    i0 = int(offset * fs)
    n = int(dur * fs)
    if i0 < 0 or i0 + n > len(strain):
        return None
    return strain[i0:i0 + n]


# ---------------------------------------------------------------------------
# CROSS-CORRELATION BASED TIME-DELAY SCAN
# ---------------------------------------------------------------------------
def xcorr_scan(h1_seg, l1_full, fs, t0_l1, t_center_l1,
               h1_ref_asd=None, l1_ref_asd=None,
               h1_ref_freqs=None, l1_ref_freqs=None):
    """
    Scan L1 time shift relative to H1.
    For each shift dt, extract L1[t_center + dt], compute normalized xcorr.
    Returns arrays: shifts_s, xcorr_peak, coh_mean.
    """
    # Whiten with reference (off-source) ASD, then bandpass
    if h1_ref_asd is not None:
        h1_w = bandpass(
            whiten_with_asd(h1_seg, fs, h1_ref_freqs, h1_ref_asd), fs)
    else:
        h1_w = bandpass(
            whiten_with_asd(h1_seg, fs,
                            *compute_psd_asd(h1_seg, fs)), fs)
    h1_norm = h1_w / (np.std(h1_w) + 1e-300)

    shifts = np.arange(-MAX_DELAY_S, MAX_DELAY_S + DELAY_STEP_S,
                       DELAY_STEP_S)
    n_seg = len(h1_seg)
    xcorr_vals = []
    coh_vals = []

    # Center index in the padded L1 array (dt=0 case)
    center_idx = (len(l1_full) - n_seg) // 2

    for dt in shifts:
        shift_samp = int(round(dt * fs))
        i0 = center_idx + shift_samp
        i1 = i0 + n_seg
        if i0 < 0 or i1 > len(l1_full):
            xcorr_vals.append(float("nan"))
            coh_vals.append(float("nan"))
            continue
        l1_seg = l1_full[i0:i1]
        if len(l1_seg) != n_seg:
            xcorr_vals.append(float("nan"))
            coh_vals.append(float("nan"))
            continue

        if l1_ref_asd is not None:
            l1_w = bandpass(
                whiten_with_asd(l1_seg, fs,
                                l1_ref_freqs, l1_ref_asd), fs)
        else:
            l1_w = bandpass(
                whiten_with_asd(l1_seg, fs,
                                *compute_psd_asd(l1_seg, fs)), fs)
        l1_norm = l1_w / (np.std(l1_w) + 1e-300)

        # Zero-lag cross-correlation (normalized)
        xc = float(np.mean(h1_norm * l1_norm))
        xcorr_vals.append(xc)

        # Mean coherence in band
        nps = min(NPERSEG, n_seg // 4)
        freqs_c, coh_c = signal.coherence(h1_norm, l1_norm, fs=fs,
                                          nperseg=nps, noverlap=nps // 2)
        mask = (freqs_c >= F_LOW) & (freqs_c <= F_HIGH)
        coh_vals.append(float(np.mean(coh_c[mask])))

    return shifts, np.array(xcorr_vals), np.array(coh_vals)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"H1/L1 TIME-DELAY SCAN -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s  Band: {F_LOW}-{F_HIGH}Hz")
    log(f"Scan: +/-{MAX_DELAY_S*1000:.0f}ms  "
        f"step={DELAY_STEP_S*1000:.3f}ms  "
        f"max_physical={MAX_LIGHT_TRAVEL_S*1000:.0f}ms")

    # Load H1 trigger window
    h1_data = load_window(H1_PATH, TRIGGER_GPS, WIN_S)
    # Load L1 with padding for shifting
    l1_data = load_window(L1_PATH, TRIGGER_GPS, WIN_S)

    if h1_data[0] is None or l1_data[0] is None:
        log("LOAD FAILED")
        flush_log()
        return

    h1_full, fs_h, t0_h1 = h1_data
    l1_full, fs_l, t0_l1 = l1_data

    if abs(fs_h - fs_l) > 1:
        log(f"Sample rate mismatch: H1={fs_h} L1={fs_l}")
        flush_log()
        return

    fs = fs_h

    # Extract H1 segment (center of loaded array)
    n_seg = int(WIN_S * fs)
    h1_center_idx = (len(h1_full) - n_seg) // 2
    h1_seg = h1_full[h1_center_idx:h1_center_idx + n_seg]

    log(f"  H1 loaded: {len(h1_full)} samples  "
        f"H1 segment: {len(h1_seg)} samples  fs={fs:.0f}Hz")
    log(f"  L1 loaded: {len(l1_full)} samples  t0={t0_l1:.3f}")

    # Load off-source reference segments for ASD estimation (whitening ref)
    log("  Computing off-source reference ASDs...")
    h1_ref_s, _ = load_window(H1_PATH, TRIGGER_GPS - PSD_OFFSET_S,
                              16.0)[:2]
    l1_ref_s, _ = load_window(L1_PATH, TRIGGER_GPS - PSD_OFFSET_S,
                              16.0)[:2]
    if h1_ref_s is not None:
        h1_ref_freqs, h1_ref_asd = compute_psd_asd(h1_ref_s, fs)
        log(f"  H1 ref ASD: {len(h1_ref_s)} samples")
    else:
        h1_ref_freqs = h1_ref_asd = None
        log("  H1 ref ASD: FAILED — using per-segment")
    if l1_ref_s is not None:
        l1_ref_freqs, l1_ref_asd = compute_psd_asd(l1_ref_s, fs)
        log(f"  L1 ref ASD: {len(l1_ref_s)} samples")
    else:
        l1_ref_freqs = l1_ref_asd = None
        log("  L1 ref ASD: FAILED — using per-segment")

    all_rows = []

    for tag, t_c in [("TRIGGER", TRIGGER_GPS),
                     ("OFF_m500", TRIGGER_GPS - 500.0)]:
        log(f"\n{'='*60}")
        log(f"WINDOW: {tag}")
        log(f"{'='*60}")

        # For off-source, reload H1 segment too
        if tag == "TRIGGER":
            h1_s = h1_seg
        else:
            h1_off_data = load_window(H1_PATH, t_c, WIN_S)
            if h1_off_data[0] is None:
                log("  H1 off-source load failed")
                continue
            h1_off_full, _, _ = h1_off_data
            n_s = int(WIN_S * fs)
            ci = (len(h1_off_full) - n_s) // 2
            h1_s = h1_off_full[ci:ci + n_s]

        if len(h1_s) < n_seg // 2:
            log("  H1 segment too short")
            continue

        # Load L1 for this window
        l1_win_data = load_window(L1_PATH, t_c, WIN_S)
        if l1_win_data[0] is None:
            log("  L1 load failed")
            continue
        l1_w_full, _, t0_l1_w = l1_win_data

        shifts, xcorr_vals, coh_vals = xcorr_scan(
            h1_s, l1_w_full, fs, t0_l1_w, t_c,
            h1_ref_asd=h1_ref_asd, l1_ref_asd=l1_ref_asd,
            h1_ref_freqs=h1_ref_freqs, l1_ref_freqs=l1_ref_freqs)

        valid = np.isfinite(xcorr_vals)
        if not valid.any():
            log("  No valid shifts")
            continue

        xc_v = xcorr_vals[valid]
        sh_v = shifts[valid]
        coh_v = coh_vals[valid]

        best_xc_idx = int(np.argmax(np.abs(xc_v)))
        best_shift = float(sh_v[best_xc_idx])
        best_xc = float(xc_v[best_xc_idx])
        best_coh = float(coh_v[best_xc_idx])

        zero_idx = int(np.argmin(np.abs(sh_v)))
        zero_xc = float(xc_v[zero_idx])
        zero_coh = float(coh_v[zero_idx])

        log(f"  Zero-lag:   xcorr={zero_xc:+.5f}  coh={zero_coh:.4f}")
        log(f"  Best shift: dt={best_shift*1000:+.3f}ms  "
            f"xcorr={best_xc:+.5f}  coh={best_coh:.4f}")

        physical = abs(best_shift) <= MAX_LIGHT_TRAVEL_S
        log(f"  Physical shift (|dt|<={MAX_LIGHT_TRAVEL_S*1000:.0f}ms): "
            f"{'YES' if physical else 'NO'}")

        # Is the peak sharper than noise floor?
        noise_xc_std = float(np.std(xc_v))
        snr_peak = abs(best_xc) / (noise_xc_std + 1e-300)
        log(f"  XCorr noise std: {noise_xc_std:.5f}  "
            f"peak SNR: {snr_peak:.2f}")

        if snr_peak > 5 and physical:
            td_verdict = "PHYSICAL_PEAK_INVESTIGATE"
        elif snr_peak > 5 and not physical:
            td_verdict = "NON_PHYSICAL_PEAK"
        elif snr_peak < 2:
            td_verdict = "NO_PEAK_CONSISTENT_WITH_NOISE"
        else:
            td_verdict = "WEAK_PEAK_INCONCLUSIVE"

        log(f"  -> TIME_DELAY_VERDICT: {td_verdict}")

        for i, (sh, xc, ch) in enumerate(zip(sh_v, xc_v, coh_v)):
            all_rows.append({
                "tag": tag,
                "shift_ms": round(sh * 1000, 4),
                "xcorr": round(float(xc), 7),
                "coh": round(float(ch), 6),
                "is_physical": abs(sh) <= MAX_LIGHT_TRAVEL_S,
            })

    # ---------------------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------------------
    csv_path = MANIFEST / "h1l1_time_delay_scan.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        if all_rows:
            w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)

    md = [
        "# H1/L1 Time-Delay Scan Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Scan: +/-{MAX_DELAY_S*1000:.0f}ms "
        f"step={DELAY_STEP_S*1000:.3f}ms",
        f"- Physical range: |dt| <= {MAX_LIGHT_TRAVEL_S*1000:.0f}ms",
        f"- Band: {F_LOW}-{F_HIGH} Hz",
        "- Whitened + bandpassed before cross-correlation",
        "",
        "## Interpretation",
        "- SNR > 5 at physical shift -> investigate further",
        "- Broad/flat xcorr -> uncorrelated noise",
        "- Peak at non-physical shift -> systematic/artifact",
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "H1L1_TIME_DELAY_SCAN_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    flush_log()


if __name__ == "__main__":
    run()
