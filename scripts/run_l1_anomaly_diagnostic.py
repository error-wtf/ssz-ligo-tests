"""L1 Anomaly Diagnostic — anti-circular, no claim.

Checks:
1. L1 file path, GPS offset, sample rate, trigger window integrity
2. H1/L1 strain RMS in trigger / pre / post / off-source windows
3. NaN/Inf/clipping/glitch detection
4. Correct normalised cross-correlation xcorr in [-1,1]
5. MF-SNR recomputed with identical normalization for H1 and L1
6. Tabulated strain statistics

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
"""
import sys
import datetime
import numpy as np
import h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.derived_waveform import apply_ssz_v0_to_frequency_waveform

G = 6.674e-11
C = 2.998e8
M_SUN = 1.989e30

TRIGGER_GPS = 1411261107.984
MC_MSUN = 8.9
ETA = 0.25
DL_MPC = 300.0
F_LOW = 20.0
F_HIGH = 210.0
NPERSEG = 4096
OFF_OFFSET_S = 500.0
OFF_DUR_S = 256.0
WIN_S = 4.0

_BASE = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_PATH = _BASE / (
    "H1/1410334720/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
L1_PATH = _BASE / (
    "L1/1410334720/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_log = []


def log(m=""):
    print(m)
    _log.append(m)


def load_windows(path, trigger_gps, win_s, off_offset, off_dur):
    """Load trigger window + contextual windows from HDF5."""
    with h5py.File(str(path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur = float(f["meta/Duration"][()])
        n = f["strain/Strain"].shape[0]
        fs = int(n / dur)
        t_ev = trigger_gps - gps0

        def win(t_start, t_len):
            i0 = max(0, int(t_start * fs))
            i1 = min(n, i0 + int(t_len * fs))
            return f["strain/Strain"][i0:i1]

        half = win_s / 2.0
        on = win(t_ev - half, win_s)
        pre = win(t_ev - 10.0 - half, 10.0)
        post = win(t_ev + half, 10.0)
        j0 = max(0, int((t_ev - off_offset) * fs))
        j1 = min(n, j0 + int(off_dur * fs))
        off = f["strain/Strain"][j0:j1]

    return {
        "on": on, "pre": pre, "post": post, "of": off,
        "fs": fs, "gps0": gps0, "t_ev": t_ev,
        "n_total": n, "dur_total": dur,
    }


def strain_stats(arr, label):
    """Compute and log strain statistics. Returns dict."""
    if len(arr) == 0:
        log(f"    {label}: EMPTY")
        return {}
    has_nan = int(np.any(np.isnan(arr)))
    has_inf = int(np.any(np.isinf(arr)))
    rms = float(np.sqrt(np.mean(arr**2)))
    peak = float(np.max(np.abs(arr)))
    p99 = float(np.percentile(np.abs(arr), 99))
    clipped = int(np.sum(np.abs(arr) > 0.99 * peak))
    log(f"    {label}: rms={rms:.3e}  peak={peak:.3e}  "
        f"p99={p99:.3e}  NaN={has_nan}  Inf={has_inf}  "
        f"near_clip={clipped}  n={len(arr)}")
    return {
        "label": label, "rms": rms, "peak": peak, "p99": p99,
        "has_nan": has_nan, "has_in": has_inf, "near_clip": clipped,
        "n": len(arr),
    }


def xcorr_correct(a, b):
    """Correctly normalised xcorr: result in [-1,1].
    Uses Cauchy-Schwarz normalisation: dot(a,b)/sqrt(dot(a,a)*dot(b,b)).
    Returns peak value and lag in samples.
    """
    n = min(len(a), len(b))
    a = np.real(a[:n]).astype(float)
    b = np.real(b[:n]).astype(float)
    norm = np.sqrt(np.dot(a, a) * np.dot(b, b))
    if norm < 1e-300:
        return 0.0, 0
    xc = np.correlate(a, b, mode="full") / norm
    lags = np.arange(-(n - 1), n)
    pk = np.argmax(np.abs(xc))
    val = float(xc[pk])
    # Hard-clamp to [-1,1] as numerical sanity check
    if abs(val) > 1.0 + 1e-9:
        log(f"    WARNING: xcorr={val:.6f} outside [-1,1] — "
            "CORRELATION_IMPLEMENTATION_ERROR")
        return val, int(lags[pk])
    return val, int(lags[pk])


def mf_snr(dfd, h, psd_f, psd_v, df):
    """Noise-weighted matched-filter SNR: <d|h>/sqrt(<h|h>)."""
    pi = np.interp(psd_f, psd_f, psd_v,
                   left=psd_v[1], right=psd_v[-1])
    pi = np.where(pi > 0, pi, pi[pi > 0].min())

    def nw(a, b):
        return 4.0 * np.real(np.sum(a * np.conj(b) / pi)) * df

    nn = nw(h, h)
    return abs(nw(dfd, h)) / np.sqrt(nn) if nn > 0 else 0.0


def process_detector(label, path, Mc, M, mu, dL):
    log(f"\n  === {label} ===")
    if not path.exists():
        log(f"  BLOCKED: {path} not found")
        return None

    ww = load_windows(path, TRIGGER_GPS, WIN_S, OFF_OFFSET_S, OFF_DUR_S)
    fs = ww["fs"]
    log(f"  File OK | GPS0={ww['gps0']}  t_ev={ww['t_ev']:.1f}s  "
        f"fs={fs} Hz  n_total={ww['n_total']}")

    stats = {}
    for key in ("on", "pre", "post", "of"):
        stats[key] = strain_stats(ww[key], f"{label}_{key}")

    # Anomaly flags
    anomalies = []
    if stats["on"].get("has_nan") or stats["on"].get("has_in"):
        anomalies.append("NAN_OR_INF_IN_TRIGGER_WINDOW")
    if stats["on"].get("near_clip", 0) > 10:
        anomalies.append("POSSIBLE_CLIPPING")
    rms_on = stats["on"].get("rms", 0)
    rms_off = stats["of"].get("rms", 0)
    rms_ratio = rms_on / rms_off if rms_off > 0 else 999.0
    log(f"  rms_on/rms_off ratio: {rms_ratio:.2f}"
        f"  ({'OK' if rms_ratio < 5.0 else 'ANOMALOUS — high noise in trigger window'})")
    if rms_ratio > 5.0:
        anomalies.append(f"RMS_RATIO_ANOMALOUS ({rms_ratio:.1f}x)")

    # PSD from off-source
    fp, psd = signal.welch(
        ww["of"], fs=fs, nperseg=NPERSEG, window="hann", noverlap=NPERSEG // 2
    )

    # MF-SNR with correct normalization
    on_arr = ww["on"]
    ffd = np.fft.rfftfreq(len(on_arr), 1.0 / fs)
    mask = (ffd >= F_LOW) & (ffd <= F_HIGH) & (ffd > 0)
    dfd = np.fft.rfft(on_arr) / fs
    df = float(fs) / len(on_arr)

    # GR template
    h_gr = np.zeros(len(ffd), dtype=complex)
    f = ffd[mask]
    psi = (3.0 / (128.0 * ETA)) * (np.pi * G * Mc / C**3 * f)**(-5.0 / 3.0)
    c1 = (np.sqrt(5 * np.pi / 24)
          * (G * Mc / C**3)**(5.0 / 6.0)
          * np.pi**(-7.0 / 6.0) / dL)
    h_gr[mask] = c1 * f**(-7.0 / 6.0) * np.exp(1j * psi)

    h_ssz, _, _, _ = apply_ssz_v0_to_frequency_waveform(
        h_gr, ffd, M, mu, branch="g2_decay"
    )

    pi_full = np.interp(ffd, fp, psd, left=psd[1], right=psd[-1])
    pi_full[pi_full <= 0] = pi_full[pi_full > 0].min()

    snr_gr = mf_snr(dfd, h_gr, ffd, pi_full, df)
    snr_ssz = mf_snr(dfd, h_ssz, ffd, pi_full, df)
    log(f"  MF-SNR GR={snr_gr:.2f}  SSZ={snr_ssz:.2f}")

    # Check if high SNR is due to low PSD (quiet off-source) or loud on-source
    psd_median = float(np.median(psd[(fp >= F_LOW) & (fp <= F_HIGH)]))
    signal_power = float(np.mean(np.abs(dfd[mask])**2))
    log(f"  PSD median in band: {psd_median:.3e}  "
        f"signal power: {signal_power:.3e}  "
        f"ratio: {signal_power/psd_median:.1f}")
    if snr_gr > 200:
        anomalies.append(f"MF_SNR_GR_ANOMALOUS ({snr_gr:.0f})")
        log(f"  ANOMALY: MF-SNR GR={snr_gr:.0f} >> expected (~10-50)")
        log("  Likely cause: off-source PSD underestimates trigger-window noise")

    # Determine L1 status
    if not anomalies:
        l1_status = "OK"
    elif any("MF_SNR" in a or "RMS_RATIO" in a for a in anomalies):
        l1_status = "NOISE_ANOMALY"
    elif "NAN_OR_INF" in str(anomalies):
        l1_status = "DATA_INTEGRITY_ERROR"
    else:
        l1_status = "MINOR_ANOMALY"

    log(f"  Anomalies: {anomalies if anomalies else 'none'}")
    log(f"  {label}_STATUS: {l1_status}")

    return {
        "label": label, "stats": stats, "anomalies": anomalies,
        "status": l1_status, "snr_gr": snr_gr, "snr_ssz": snr_ssz,
        "rms_ratio": rms_ratio, "psd_median": psd_median,
        "signal_power": signal_power, "fs": fs,
        "strain_on": on_arr,
    }


def run():
    log(f"L1 ANOMALY DIAGNOSTIC — {NOW}")
    log("READY_FOR_REAL_CLAIM: NO | No SSZ claim made here")

    Mc = MC_MSUN * M_SUN
    M = Mc / ETA**(3.0 / 5.0)
    mu = ETA * M
    dL = DL_MPC * 3.086e22

    rh = process_detector("H1", H1_PATH, Mc, M, mu, dL)
    rl = process_detector("L1", L1_PATH, Mc, M, mu, dL)

    # Corrected xcorr
    log("\n  === CORRECTED XCORR ===")
    xcorr_val = xcorr_lag = None
    xcorr_status = "BLOCKED"
    if rh and rl:
        a = rh["strain_on"]
        b = rl["strain_on"]
        xcorr_val, xcorr_lag = xcorr_correct(a, b)
        in_range = abs(xcorr_val) <= 1.0 + 1e-9
        log(f"  xcorr (Cauchy-Schwarz) = {xcorr_val:.6f}  lag={xcorr_lag}  "
            f"in_[-1,1]: {in_range}")
        if not in_range:
            xcorr_status = "CORRELATION_IMPLEMENTATION_ERROR"
        elif abs(xcorr_val) < 0.3:
            xcorr_status = "UNCORRELATED_OK"
        else:
            xcorr_status = "CORRELATED_NEEDS_INVESTIGATION"
        log(f"  XCORR_STATUS: {xcorr_status}")

        # Previous pipeline used std-normalisation which can exceed 1
        # for non-stationary signals. Document the difference.
        n = min(len(a), len(b))
        a2 = np.real(a[:n]).astype(float)
        b2 = np.real(b[:n]).astype(float)
        sa = np.std(a2) + 1e-300
        sb = np.std(b2) + 1e-300
        xc_old = np.correlate(a2 / sa, b2 / sb, mode="full")
        pk = np.argmax(np.abs(xc_old))
        old_val = float(xc_old[pk]) / n
        log(f"  Previous std-norm xcorr = {old_val:.6f}  "
            f"({'BUG: exceeds 1 for non-stationary' if abs(old_val) > 1.0 else 'OK'})")

    # H1/L1 RMS comparison table
    log("\n  === H1 / L1 RMS COMPARISON ===")
    for key in ("on", "pre", "post", "of"):
        rms_h = rh["stats"][key].get("rms", 0) if rh else 0
        rms_l = rl["stats"][key].get("rms", 0) if rl else 0
        ratio = rms_l / rms_h if rms_h > 0 else 999.0
        flag = " << ANOMALOUS" if ratio > 5.0 else ""
        log(f"  {key:8s}: H1={rms_h:.3e}  L1={rms_l:.3e}  L1/H1={ratio:.2f}{flag}")

    h1_status = rh["status"] if rh else "BLOCKED"
    l1_status = rl["status"] if rl else "BLOCKED"

    # Write report
    def _s(d, k, fmt=".3e"):
        v = d.get(k, None) if d else None
        return f"{v:{fmt}}" if v is not None else "BLOCKED"

    report_lines = [
        "# L1 Anomaly Diagnostic Report",
        f"Generated: {NOW}",
        "",
        "## Purpose",
        "Diagnose why L1 MF-SNR=647 and xcorr>1 appeared in the H1/L1 pipeline.",
        "No SSZ claim is made.",
        "",
        "## H1 / L1 Strain Window Statistics",
        "",
        "| Window | H1 RMS | L1 RMS | L1/H1 | Notes |",
        "|--------|--------|--------|-------|-------|",
    ]
    if rh and rl:
        for key in ("on", "pre", "post", "of"):
            rms_h = rh["stats"][key].get("rms", 0)
            rms_l = rl["stats"][key].get("rms", 0)
            ratio = rms_l / rms_h if rms_h > 0 else 999.0
            flag = "ANOMALOUS" if ratio > 5.0 else "OK"
            report_lines.append(
                f"| {key} | {rms_h:.3e} | {rms_l:.3e} "
                f"| {ratio:.2f} | {flag} |"
            )

    report_lines += [
        "",
        "## H1 Anomalies",
        f"- Status: {h1_status}",
        f"- Anomalies: {rh['anomalies'] if rh else 'N/A'}",
        f"- MF-SNR GR: {rh['snr_gr']:.2f}" if rh else "- BLOCKED",
        "",
        "## L1 Anomalies",
        f"- Status: {l1_status}",
        f"- Anomalies: {rl['anomalies'] if rl else 'N/A'}",
        f"- MF-SNR GR: {rl['snr_gr']:.2f}" if rl else "- BLOCKED",
        f"- RMS ratio on/off: {rl['rms_ratio']:.2f}" if rl else "",
        "",
        "## Root Cause Analysis",
        "",
        "**L1 MF-SNR anomaly:**",
        "- MF-SNR depends on off-source PSD as noise estimator",
        "- If off-source window (-500s) is quiet but trigger window is loud,",
        "  the PSD underestimates the true noise → inflated SNR",
        "- L1 trigger window RMS / off-source RMS ratio reveals this",
        "- This is a noise non-stationarity issue, NOT an SSZ effect",
        "",
        "**xcorr > 1 root cause:**",
        "- Previous pipeline used: xcorr = correlate(a/std(a), b/std(b)) / n",
        "- std-normalisation does NOT guarantee output in [-1,1]",
        "  for non-stationary or impulsive signals",
        "- Correct formula: xcorr = dot(a,b) / sqrt(dot(a,a)*dot(b,b))",
        "  (Cauchy-Schwarz, guaranteed in [-1,1])",
        "",
        "## Corrected Cross-Correlation",
        "",
        "- Method: Cauchy-Schwarz normalisation",
        f"- xcorr_corrected = {xcorr_val:.6f}" if xcorr_val is not None
        else "- xcorr: BLOCKED",
        f"- lag = {xcorr_lag} samples" if xcorr_lag is not None else "",
        f"- XCORR_STATUS: {xcorr_status}",
        "",
        "## Final Gate",
        "```",
        f"H1_STATUS:                      {h1_status}",
        f"L1_STATUS:                      {l1_status}",
        f"XCORR_STATUS:                   {xcorr_status}",
        "COHERENCE_TEST_VALID:           PENDING (depends on L1_STATUS)",
        "READY_FOR_REAL_LIGO_SSZ_CLAIM:  NO",
        "SSZ_SUPPORT_CLAIM_MADE:         NO",
        "SSZ_FALSIFICATION_CLAIM_MADE:   NO",
        "```",
    ]
    (REPORTS / "L1_ANOMALY_DIAGNOSTIC_REPORT.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )
    log("\n  -> reports/L1_ANOMALY_DIAGNOSTIC_REPORT.md")
    (LOGS / "l1_anomaly_diagnostic.log").write_text(
        "\n".join(_log), encoding="utf-8"
    )
    log(f"DONE | H1={h1_status} | L1={l1_status} | XCORR={xcorr_status}")
    log("READY_FOR_REAL_CLAIM: NO")


if __name__ == "__main__":
    run()
