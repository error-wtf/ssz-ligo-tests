"""Unit & Normalization Audit — Test 71.

Verifies that the pipeline's FFT normalization, PSD units, ASD vs PSD,
one-sided vs two-sided PSD, df factors, and window power correction are
all consistent and correctly calibrated.

Method:
  1. Inject a synthetic sine wave with known amplitude A and frequency f0.
  2. Compute PSD via Welch.
  3. Verify: PSD peak height = A^2 / (2 * df) for one-sided PSD.
  4. Verify: integrated bandpower recovers A^2 / 2 (energy of sine wave).
  5. Verify: ASD peak = sqrt(PSD peak) = A / sqrt(2 * df).
  6. Check window power correction factor.
  7. Verify bandpower integration with known analytic result.
  8. Run on real H1 strain: confirm PSD units are strain^2/Hz.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import datetime
import numpy as np
import csv
from pathlib import Path
from scipy import signal
import h5py

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for _d in (REPORTS, LOGS, MANIFEST):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "unit_normalization_audit.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
FS = 4096.0           # sample rate Hz
DUR = 16.0            # duration s
NPERSEG = 4096        # Welch segment = 1s -> df = 1 Hz
F0 = 100.0            # injection frequency Hz
A = 1e-21             # injection amplitude (strain units)
WINDOW = "hann"

H1_PATH = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
    r"\H1\1410334720"
    r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
TRIGGER_GPS = 1411261107.984

PASS_TOL = 0.05   # 5% tolerance for normalization checks


# ---------------------------------------------------------------------------
# SYNTHETIC SIGNAL TESTS
# ---------------------------------------------------------------------------
def test_psd_peak_normalization():
    """
    Sine wave with amplitude A at f0.
    Expected one-sided Welch PSD peak at f0: A^2 / 2 (for Hann window
    with correct power normalization).
    More precisely for Welch with Hann window:
      S(f0) * df = A^2 / 2
      S(f0) = A^2 / (2 * df)   where df = fs / nperseg
    """
    log("[TEST 1] PSD peak normalization (sine injection)")
    n = int(FS * DUR)
    t = np.arange(n) / FS
    x = A * np.sin(2 * np.pi * F0 * t)

    nps = NPERSEG
    df = FS / nps
    freqs, psd = signal.welch(x, fs=FS, nperseg=nps,
                              noverlap=nps // 2, window=WINDOW)

    # Find peak
    # Hann window equivalent noise bandwidth (ENB)
    # ENB = (sum(w^2)/N) / (sum(w)/N)^2  -- for density-mode PSD
    # Welch density PSD peak = A^2 / (2 * df * ENB)
    w_hann = signal.windows.hann(nps)
    S1 = float(np.mean(w_hann))           # sum(w)/N
    S2 = float(np.mean(w_hann**2))        # sum(w^2)/N
    enb = S2 / (S1**2)                    # equivalent noise bandwidth

    i0 = np.argmin(np.abs(freqs - F0))
    psd_peak = psd[i0]
    expected_peak = A**2 / (2 * df * enb)

    ratio = psd_peak / expected_peak
    err_pct = abs(ratio - 1.0) * 100
    passed = err_pct < PASS_TOL * 100

    log(f"  f0={F0} Hz  A={A:.3e}  df={df:.4f} Hz")
    log(f"  Hann ENB: {enb:.4f}  (S2/S1^2, theoretical=1.5)")
    log(f"  PSD peak at f0:           {psd_peak:.6e} strain^2/Hz")
    log(f"  Expected (A^2/(2*df*ENB)): {expected_peak:.6e} strain^2/Hz")
    log(f"  Ratio: {ratio:.6f}  Error: {err_pct:.3f}%  "
        f"PASS={passed}")
    log("  Note: Peak height depends on ENB. Bandpower integral "
        "(Test 2) is the reliable normalization check.")

    return {
        "test": "psd_peak_normalization",
        "psd_peak": psd_peak,
        "expected_peak": expected_peak,
        "ratio": ratio,
        "error_pct": err_pct,
        "passed": passed,
    }


def test_bandpower_integration():
    """
    Sine wave: bandpower integral over [f0-5, f0+5] Hz should = A^2 / 2.
    """
    log("\n[TEST 2] Bandpower integration (sine injection)")
    n = int(FS * DUR)
    t = np.arange(n) / FS
    x = A * np.sin(2 * np.pi * F0 * t)

    nps = NPERSEG
    freqs, psd = signal.welch(x, fs=FS, nperseg=nps,
                              noverlap=nps // 2, window=WINDOW)

    mask = (freqs >= F0 - 5) & (freqs <= F0 + 5)
    bp = float(np.trapezoid(psd[mask], freqs[mask]))
    expected_bp = A**2 / 2.0

    ratio = bp / expected_bp
    err_pct = abs(ratio - 1.0) * 100
    passed = err_pct < PASS_TOL * 100

    log(f"  Bandpower [{F0-5}-{F0+5} Hz]: {bp:.6e} strain^2")
    log(f"  Expected (A^2/2):              {expected_bp:.6e} strain^2")
    log(f"  Ratio: {ratio:.6f}  Error: {err_pct:.3f}%  PASS={passed}")

    return {
        "test": "bandpower_integration",
        "bandpower": bp,
        "expected_bp": expected_bp,
        "ratio": ratio,
        "error_pct": err_pct,
        "passed": passed,
    }


def test_asd_normalization():
    """ASD = sqrt(PSD). Peak ASD at f0 should = A / sqrt(2 * df)."""
    log("\n[TEST 3] ASD normalization")
    n = int(FS * DUR)
    t = np.arange(n) / FS
    x = A * np.sin(2 * np.pi * F0 * t)

    nps = NPERSEG
    df = FS / nps
    freqs, psd = signal.welch(x, fs=FS, nperseg=nps,
                              noverlap=nps // 2, window=WINDOW)
    asd = np.sqrt(psd)

    w_hann = signal.windows.hann(nps)
    S1 = float(np.mean(w_hann))
    S2 = float(np.mean(w_hann**2))
    enb = S2 / (S1**2)

    i0 = np.argmin(np.abs(freqs - F0))
    asd_peak = asd[i0]
    expected_asd = A / np.sqrt(2 * df * enb)  # ENB-corrected

    ratio = asd_peak / expected_asd
    err_pct = abs(ratio - 1.0) * 100
    passed = err_pct < PASS_TOL * 100

    log(f"  Hann ENB: {enb:.4f}")
    log(f"  ASD peak at f0:              {asd_peak:.6e} strain/sqrt(Hz)")
    log(f"  Expected (A/sqrt(2*df*ENB)): {expected_asd:.6e} strain/sqrt(Hz)")
    log(f"  Ratio: {ratio:.6f}  Error: {err_pct:.3f}%  PASS={passed}")

    return {
        "test": "asd_normalization",
        "asd_peak": asd_peak,
        "expected_asd": expected_asd,
        "ratio": ratio,
        "error_pct": err_pct,
        "passed": passed,
    }


def test_window_power_correction():
    """
    Hann window power correction factor should be sum(w^2)/N.
    scipy.signal.welch uses 'density' scaling which corrects for this.
    Verify the correction is applied.
    """
    log("\n[TEST 4] Window power correction factor")
    w = signal.windows.hann(NPERSEG)
    # Power correction factor for Welch PSD (density mode)
    # scipy divides by fs * sum(w^2)
    S2 = float(np.sum(w**2))
    correction = S2 / NPERSEG   # relative to rectangular window
    expected_correction = 0.375  # Hann window theoretical

    err_pct = abs(correction - expected_correction) / expected_correction * 100
    passed = err_pct < 1.0  # 1% tolerance

    log(f"  sum(w^2)/N (Hann): {correction:.6f}")
    log(f"  Expected (Hann):   {expected_correction:.6f}")
    log(f"  Error: {err_pct:.4f}%  PASS={passed}")

    return {
        "test": "window_power_correction",
        "computed": correction,
        "expected": expected_correction,
        "error_pct": err_pct,
        "passed": passed,
    }


def test_onesided_vs_twosided():
    """
    Welch default is one-sided (density) for real signals.
    One-sided PSD integral = total signal power (variance for zero-mean).
    Two-sided PSD integral = same total power.
    Verify: sum(psd * df) = var(x) for one-sided Welch.
    """
    log("\n[TEST 5] One-sided vs two-sided PSD consistency")
    n = int(FS * DUR)
    t = np.arange(n) / FS
    x = A * np.sin(2 * np.pi * F0 * t)

    nps = NPERSEG
    df = FS / nps

    freqs_1s, psd_1s = signal.welch(
        x, fs=FS, nperseg=nps, noverlap=nps // 2,
        window=WINDOW, return_onesided=True)
    freqs_2s, psd_2s = signal.welch(
        x, fs=FS, nperseg=nps, noverlap=nps // 2,
        window=WINDOW, return_onesided=False)

    power_1s = float(np.trapezoid(psd_1s, freqs_1s))
    power_2s = float(np.sum(psd_2s) * df)
    var_x = float(np.var(x))

    err_1s = abs(power_1s - var_x) / (var_x + 1e-300) * 100
    err_2s = abs(power_2s - var_x) / (var_x + 1e-300) * 100
    passed_1s = err_1s < PASS_TOL * 100
    passed_2s = err_2s < PASS_TOL * 100

    log(f"  var(x):         {var_x:.6e}")
    log(f"  one-sided power: {power_1s:.6e}  err={err_1s:.3f}%  "
        f"PASS={passed_1s}")
    log(f"  two-sided power: {power_2s:.6e}  err={err_2s:.3f}%  "
        f"PASS={passed_2s}")

    return {
        "test": "onesided_vs_twosided",
        "var_x": var_x,
        "power_1s": power_1s,
        "power_2s": power_2s,
        "err_1s_pct": err_1s,
        "err_2s_pct": err_2s,
        "passed_1s": passed_1s,
        "passed_2s": passed_2s,
        "passed": passed_1s and passed_2s,
    }


def test_rfft_normalization():
    """
    np.fft.rfft normalization convention.
    For x = A*cos(2*pi*f0*t) with n samples:
      |rfft(x)[k]|^2 = (A*n/2)^2 * 2  (for non-DC, non-Nyquist bin k>0)
    PSD from rfft: S(f) = 2 * |X(f)|^2 / (n * fs)   [one-sided]
    """
    log("\n[TEST 6] rfft normalization convention")
    n = int(FS * DUR)
    t = np.arange(n) / FS
    x = A * np.cos(2 * np.pi * F0 * t)

    X = np.fft.rfft(x)
    k = int(round(F0 * DUR))  # bin index for f0
    Xk = X[k]

    # Expected: |X[k]| = A * n / 2  (for cosine, non-DC)
    expected_mag = A * n / 2
    actual_mag = abs(Xk)
    ratio = actual_mag / expected_mag
    err_pct = abs(ratio - 1.0) * 100
    passed = err_pct < PASS_TOL * 100

    # PSD from rfft (one-sided, no window)
    psd_from_rfft = 2.0 * np.abs(X)**2 / (n * FS)
    psd_peak_rfft = psd_from_rfft[k]
    df = FS / n
    expected_psd = A**2 / (2 * df)
    ratio_psd = psd_peak_rfft / expected_psd
    err_psd = abs(ratio_psd - 1.0) * 100
    passed_psd = err_psd < PASS_TOL * 100

    log(f"  rfft magnitude at f0: {actual_mag:.6e}")
    log(f"  Expected (A*n/2):     {expected_mag:.6e}")
    log(f"  Ratio: {ratio:.6f}  Error: {err_pct:.3f}%  PASS={passed}")
    log(f"  PSD from rfft peak: {psd_peak_rfft:.6e}")
    log(f"  Expected PSD peak:  {expected_psd:.6e}")
    log(f"  Ratio: {ratio_psd:.6f}  Error: {err_psd:.3f}%  PASS={passed_psd}")

    return {
        "test": "rfft_normalization",
        "rfft_mag": actual_mag,
        "expected_mag": expected_mag,
        "ratio_mag": ratio,
        "error_mag_pct": err_pct,
        "psd_from_rfft": psd_peak_rfft,
        "expected_psd": expected_psd,
        "ratio_psd": ratio_psd,
        "error_psd_pct": err_psd,
        "passed": passed and passed_psd,
    }


def test_real_strain_units():
    """
    Load real H1 strain and verify PSD is in plausible strain^2/Hz range.
    H1 ASD near 100 Hz should be ~3e-24 to 5e-23 strain/sqrt(Hz) in O4.
    """
    log("\n[TEST 7] Real H1 strain PSD units check")
    if not H1_PATH.exists():
        log("  SKIP: H1 file not found")
        return {"test": "real_strain_units", "passed": None,
                "skipped": True}

    with h5py.File(H1_PATH, "r") as f:
        gps0 = float(f["meta"]["GPSstart"][()])
        dur_file = float(f["meta"]["Duration"][()])
        n_total = f["strain/Strain"].shape[0]
        fs = n_total / dur_file
        t_c = TRIGGER_GPS - gps0
        i0 = max(0, int((t_c - 8.0) * fs))
        i1 = min(n_total, int((t_c + 8.0) * fs))
        strain = f["strain/Strain"][i0:i1].astype(float)

    nps = min(4096, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window=WINDOW)
    asd = np.sqrt(psd)

    i100 = np.argmin(np.abs(freqs - 100.0))
    asd_100 = float(asd[i100])
    # O4 design ASD at 100 Hz: ~3e-24 to 3e-23 strain/sqrt(Hz)
    in_range = 1e-25 < asd_100 < 1e-21

    i60 = np.argmin(np.abs(freqs - 60.0))
    asd_60 = float(asd[i60])

    log(f"  ASD at 100 Hz: {asd_100:.4e} strain/sqrt(Hz)  "
        f"in_range={in_range}")
    log(f"  ASD at  60 Hz: {asd_60:.4e} strain/sqrt(Hz)  "
        f"(60Hz line, should be elevated)")
    log(f"  60/100 ASD ratio: {asd_60/asd_100:.2f}  "
        f"(>1 expected for 60Hz line)")
    log(f"  Sample rate: {fs:.0f} Hz  n_samples: {len(strain)}")

    return {
        "test": "real_strain_units",
        "asd_at_100hz": asd_100,
        "asd_at_60hz": asd_60,
        "asd_60_100_ratio": asd_60 / asd_100,
        "in_expected_range": in_range,
        "passed": in_range,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"UNIT & NORMALIZATION AUDIT -- {NOW}")
    log(f"FS={FS} Hz  DUR={DUR}s  NPERSEG={NPERSEG}  "
        f"df={FS/NPERSEG:.4f} Hz")
    log(f"Injection: A={A:.3e} strain  f0={F0} Hz  window={WINDOW}")
    log(f"Tolerance: {PASS_TOL*100:.0f}%")
    log()

    results = [
        test_psd_peak_normalization(),
        test_bandpower_integration(),
        test_asd_normalization(),
        test_window_power_correction(),
        test_onesided_vs_twosided(),
        test_rfft_normalization(),
        test_real_strain_units(),
    ]

    log(f"\n{'='*60}")
    log("AUDIT SUMMARY")
    log(f"{'='*60}")

    all_passed = True
    for r in results:
        p = r.get("passed")
        if p is None:
            status = "SKIP"
        elif p:
            status = "PASS"
        else:
            status = "FAIL"
            all_passed = False
        name = r["test"]
        log(f"  {status:4s}  {name}")

    log()
    if all_passed:
        log("OVERALL: ALL NORMALIZATION CHECKS PASSED")
        log("Pipeline FFT/PSD/ASD units are consistent.")
    else:
        log("OVERALL: ONE OR MORE CHECKS FAILED")
        log("Review failed tests before trusting bandpower values.")

    # CSV
    csv_path = MANIFEST / "unit_normalization_audit.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        fields = ["test", "passed", "error_pct", "ratio"]
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                           restval="N/A")
        w.writeheader()
        w.writerows(results)

    # Markdown
    md = [
        "# Unit & Normalization Audit",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- FS={FS} Hz  DUR={DUR}s  NPERSEG={NPERSEG}  df={FS/NPERSEG:.4f} Hz",
        f"- Injection: A={A:.3e} strain  f0={F0} Hz  window={WINDOW}",
        f"- Tolerance: {PASS_TOL*100:.0f}%",
        "",
        "## Results",
        "",
        "| Test | Status | Error % | Ratio |",
        "|------|--------|---------|-------|",
    ]
    for r in results:
        p = r.get("passed")
        status = "SKIP" if p is None else ("PASS" if p else "FAIL")
        err = r.get("error_pct", r.get("err_1s_pct", "N/A"))
        ratio = r.get("ratio", r.get("ratio_mag", "N/A"))
        err_str = f"{err:.3f}" if isinstance(err, float) else str(err)
        ratio_str = (f"{ratio:.6f}" if isinstance(ratio, float)
                     else str(ratio))
        md.append(f"| {r['test']} | {status} | {err_str} | {ratio_str} |")

    md += [
        "",
        "## Normalization Conventions Used",
        "- `scipy.signal.welch`: one-sided, density scaling",
        "  `S(f) * df = power in bin`, `integral = var(x)`",
        "- `np.fft.rfft`: `X[k] = sum(x * exp(-2pi*i*k*n/N))`",
        "  one-sided PSD: `S(f) = 2|X(f)|^2 / (N * fs)`",
        "- Hann window power correction: `sum(w^2)/N = 0.375`",
        "  Applied automatically by scipy.welch in density mode.",
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
    ]
    rpath = REPORTS / "UNIT_NORMALIZATION_AUDIT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    flush_log()


if __name__ == "__main__":
    run()
