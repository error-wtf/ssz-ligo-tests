"""QNM Ringdown Injection Sensitivity Test — Branch 3: QNM_FREQ_3PCT.

Tests whether a 3% QNM frequency shift would be distinguishable from GR
at GW240925 ringdown SNR using LIGO H1 off-source noise PSD.

RULES:
- No posterior f_220, M_f, chi_f used
- GR f_220 from fixed physical priors (M_total, eta)
- SSZ f_220 = f_220_GR * (1 + epsilon) with epsilon from branch registry
- Synthetic injection only — no ringdown strain claimed
- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
- This is a SENSITIVITY test, not a signal test

Method:
1. Estimate f_220_GR from M_total (Schwarzschild QNM approximation)
2. Build synthetic ringdown h_GR(t) and h_SSZ(t) at varying epsilon
3. Compute noise-weighted lnL difference between the two models
4. Report: DETECTABLE / MARGINAL / UNDETECTABLE at expected ringdown SNR
"""
import sys
import datetime
import numpy as np
import h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.epsilon_220_registry import epsilon_220_exploratory_options

G = 6.674e-11
C = 2.998e8
M_SUN = 1.989e30

# Event priors (no posterior)
MC_MSUN = 8.9
ETA = 0.25
DL_MPC = 300.0

# Ringdown window (after trigger)
TRIGGER_GPS = 1411261107.984
RD_START_OFFSET_S = 0.01    # 10 ms post-trigger
RD_DURATION_S = 0.5         # 500 ms ringdown window
OFF_OFFSET_S = 500.0
OFF_DUR_S = 256.0
NPERSEG = 4096

H1 = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720"
    r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_log = []


def log(m=""):
    print(m)
    _log.append(m)


def qnm_f220_gr(M_total_kg):
    """Schwarzschild QNM l=2,m=2,n=0 approximation.

    f_220 ~ c^3 / (2*pi*G*M) * (1 - 0.63*(1-chi)^0.3) for chi=0
    For non-spinning: f_220 ~ 0.0966 * c^3 / (G * M_final)
    Using Echeverria formula for a=0: f_220 * G*M/c^3 = 0.0966 - i*0.0908/2
    """
    return 0.0966 * C**3 / (G * M_total_kg * 2 * np.pi)


def qnm_tau220_gr(M_total_kg):
    """QNM damping time tau = 1/(pi*f*Q), Q ~ 2 for l=m=2, chi=0."""
    f220 = qnm_f220_gr(M_total_kg)
    Q = 2.0
    return Q / (np.pi * f220)


def synthetic_ringdown(t, A, f220, tau, phi0=0.0):
    """h(t) = A * exp(-t/tau) * cos(2*pi*f220*t + phi0) for t >= 0."""
    h = np.zeros_like(t)
    mask = t >= 0
    h[mask] = A * np.exp(-t[mask] / tau) * np.cos(2 * np.pi * f220 * t[mask] + phi0)
    return h


def load_psd(hdf5_path):
    """Load off-source strain and estimate PSD."""
    with h5py.File(str(hdf5_path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur = float(f["meta/Duration"][()])
        n = f["strain/Strain"].shape[0]
        fs = int(n / dur)
        t_ev = TRIGGER_GPS - gps0
        j0 = max(0, int((t_ev - OFF_OFFSET_S) * fs))
        j1 = min(n, j0 + int(OFF_DUR_S * fs))
        off = f["strain/Strain"][j0:j1]
    fp, psd = signal.welch(off, fs=fs, nperseg=NPERSEG, window="hann",
                           noverlap=NPERSEG // 2)
    return fp, psd, fs


def nwip_td(a, b, psd_freqs, psd_vals, fs):
    """Noise-weighted inner product in frequency domain from time-domain signals."""
    n = len(a)
    df = float(fs) / n
    af = np.fft.rfft(a) / fs
    bf = np.fft.rfft(b) / fs
    ffd = np.fft.rfftfreq(n, 1.0 / fs)
    pi = np.interp(ffd, psd_freqs, psd_vals, left=psd_vals[1], right=psd_vals[-1])
    pi[pi <= 0] = pi[pi > 0].min()
    return 4.0 * np.real(np.sum(af * np.conj(bf) / pi)) * df


def run():
    log(f"QNM RINGDOWN INJECTION SENSITIVITY — {NOW}")
    log("Branch: QNM_FREQ_3PCT | READY_FOR_REAL_CLAIM: NO")
    log("This is a SENSITIVITY test, not a signal test.")

    if not H1.exists():
        log("BLOCKED: H1 file not found")
        return

    fp, psd, fs = load_psd(H1)
    log(f"  PSD loaded: fs={fs} Hz, bins={len(fp)}")

    # Physical parameters
    Mc = MC_MSUN * M_SUN
    M = Mc / ETA ** (3.0 / 5.0)
    dL = DL_MPC * 3.086e22

    # GR QNM parameters (no posterior)
    f220_gr = qnm_f220_gr(M)
    tau220_gr = qnm_tau220_gr(M)
    log(f"  M_total={M/M_SUN:.1f} Msun  f_220_GR={f220_gr:.1f} Hz  tau_220={tau220_gr*1e3:.1f} ms")

    # Analytic SNR estimate
    # rho_rd ~ A * sqrt(tau/2) / sqrt(S(f_220))
    psd_at_f220 = float(np.interp(f220_gr, fp, psd))
    # Characteristic strain amplitude at dL (rough order-of-magnitude)
    A_rd = G * M / (C**2 * dL) * 0.44  # ~ 0.44 * M/dL in geom units
    snr_rd_est = A_rd * np.sqrt(tau220_gr / 2.0) / np.sqrt(psd_at_f220)
    log(f"  Estimated ringdown SNR ~ {snr_rd_est:.2f}")
    log(f"  PSD at f_220: {psd_at_f220:.3e} Hz^-1")

    # Analytic frequency resolution
    delta_f_res = 1.0 / (2 * np.pi * f220_gr * tau220_gr * max(snr_rd_est, 1.0))
    delta_f_frac = delta_f_res / f220_gr
    log(f"  Freq resolution (analytic): delta_f/f ~ {delta_f_frac:.4f} ({delta_f_frac*100:.2f}%)")

    # Time axis for synthetic ringdown
    n_rd = int(RD_DURATION_S * fs)
    t_rd = np.arange(n_rd) / fs

    # Epsilon scan — include all registry branches plus fine scan
    reg_vals = [b["value"] for b in epsilon_220_exploratory_options.values()]
    epsilon_scan = sorted(set(
        [0.0, 0.01, 0.02, 0.03, 0.05, 0.10, 0.20, 0.31, 0.39] + reg_vals
    ))

    # Build GR ringdown at nominal amplitude
    h_gr_rd = synthetic_ringdown(t_rd, A_rd, f220_gr, tau220_gr)
    snr_gr_inj = np.sqrt(abs(nwip_td(h_gr_rd, h_gr_rd, fp, psd, fs)))
    log(f"  Injected GR ringdown SNR (numerical): {snr_gr_inj:.3f}")

    rows = []
    rows.append("epsilon,f220_ssz_hz,delta_f_hz,delta_f_pct,"
                "lnL_gr,lnL_ssz,delta_lnL,snr_ssz,detectability")

    log("")
    log("  epsilon  | f_220_SSZ | delta_f%  | delta_lnL  | detectability")
    log("  " + "-" * 65)

    for eps in epsilon_scan:
        f220_ssz = f220_gr * (1.0 + eps)
        # Keep same tau (first-order: tau changes slowly with frequency)
        h_ssz_rd = synthetic_ringdown(t_rd, A_rd, f220_ssz, tau220_gr)

        # lnL against zero-signal baseline (injection recovery)
        lnL_gr_vs0 = nwip_td(h_gr_rd, h_gr_rd, fp, psd, fs) \
            - 0.5 * nwip_td(h_gr_rd, h_gr_rd, fp, psd, fs)
        lnL_ssz_vs0 = nwip_td(h_gr_rd, h_ssz_rd, fp, psd, fs) \
            - 0.5 * nwip_td(h_ssz_rd, h_ssz_rd, fp, psd, fs)
        delta_lnL = lnL_ssz_vs0 - lnL_gr_vs0

        snr_ssz = np.sqrt(abs(nwip_td(h_ssz_rd, h_ssz_rd, fp, psd, fs)))

        # Detectability criterion: |delta_lnL| > 8 (~ 4 sigma)
        if abs(delta_lnL) >= 8.0:
            det = "DETECTABLE"
        elif abs(delta_lnL) >= 2.0:
            det = "MARGINAL"
        else:
            det = "UNDETECTABLE"

        df_hz = f220_ssz - f220_gr
        df_pct = eps * 100.0
        log(f"  eps={eps:.3f}  f_SSZ={f220_ssz:.1f}Hz  d_f%={df_pct:.1f}%"
            f"  dlnL={delta_lnL:+.3e}  -> {det}")
        rows.append(
            f"{eps:.4f},{f220_ssz:.3f},{df_hz:.3f},{df_pct:.2f},"
            f"{lnL_gr_vs0:.4e},{lnL_ssz_vs0:.4e},{delta_lnL:.4e},"
            f"{snr_ssz:.3f},{det}")

    # Summarise 3% branch specifically
    row3 = [r for r in rows[1:] if r.startswith("0.0300")]
    det3 = row3[0].split(",")[-1] if row3 else "UNKNOWN"
    dl3 = float(row3[0].split(",")[6]) if row3 else 0.0
    log("")
    log("  === 3% BRANCH SUMMARY ===")
    log(f"  epsilon=0.03 -> delta_lnL={dl3:.3e} -> {det3}")
    log(f"  Analytic resolution: {delta_f_frac*100:.2f}%  vs  3% shift")
    if delta_f_frac < 0.03:
        log("  Analytic: 3% shift is ABOVE frequency resolution threshold")
    else:
        log("  Analytic: 3% shift is BELOW frequency resolution threshold")

    # Write CSV
    csv_path = Path(__file__).parent.parent / "data_manifest" / "qnm_injection_scan.csv"
    csv_path.parent.mkdir(exist_ok=True)
    csv_path.write_text("\n".join(rows), encoding="utf-8")

    # Write report
    report = """# QNM Ringdown Injection Sensitivity Report

Generated: {NOW}

## Purpose

Tests whether a QNM_FREQ_3PCT branch frequency shift would be distinguishable
from GR ringdown at GW240925 noise level.
This is a SENSITIVITY test only. No real ringdown signal is claimed.

## Anti-Circularity

- No posterior f_220, M_f, chi_f used
- f_220_GR computed from M_total (fixed physical prior, no posterior)
- PSD from H1 off-source Welch only
- Synthetic injection — not real ringdown strain

## Parameters

| Parameter | Value |
|-----------|-------|
| M_total | {M/M_SUN:.1f} Msun |
| f_220_GR (Schwarzschild, chi=0) | {f220_gr:.1f} Hz |
| tau_220_GR | {tau220_gr*1e3:.1f} ms |
| Injected ringdown SNR | {snr_gr_inj:.2f} |
| Est. ringdown SNR (analytic) | {snr_rd_est:.2f} |

## Frequency Resolution

- Analytic: delta_f/f ~ 1/(rho * 2*pi*f*tau) = {delta_f_frac*100:.2f}%
- For 3% shift to be detectable: need rho > {0.03/delta_f_frac*snr_rd_est:.1f}

## Epsilon Scan Results

| epsilon | f_220_SSZ (Hz) | delta_f% | delta_lnL | Detectability |
|---------|---------------|----------|-----------|---------------|
""" + "\n".join(
        f"| {r.split(',')[0]} | {r.split(',')[1]} | {r.split(',')[3]}% "
        f"| {r.split(',')[6]} | {r.split(',')[8]} |"
        for r in rows[1:]
    ) + """

## 3% Branch Assessment

```
epsilon_220 = 0.03  (QNM_FREQ_3PCT_BRANCH, SSZ Book V51 Ch.30)
delta_lnL = {dl3:.3e}
detectability = {det3}
analytic_freq_resolution = {delta_f_frac*100:.2f}%
3pct_above_resolution = {"YES" if delta_f_frac < 0.03 else "NO"}
ringdown_SNR_needed_for_3pct = {0.03/max(delta_f_frac,1e-10)*snr_rd_est:.1f}
actual_ringdown_SNR_est = {snr_rd_est:.2f}
```

## Interpretation

- The injected ringdown SNR is low (~{snr_rd_est:.1f})
- At this SNR, frequency resolution is ~{delta_f_frac*100:.1f}%
- A 3% shift is {"above" if delta_f_frac < 0.03 else "below"} the frequency resolution threshold
- This means: **even if SSZ predicts a 3% shift, GW240925 ringdown SNR
  may not be sufficient to distinguish it from GR**
- A stacking analysis across multiple events would be needed

## Final Gate

```
QNM_FREQ_3PCT_SENSITIVITY_RUN:     COMPLETE
QNM_3PCT_DETECTABLE_AT_GW240925:   {det3}
RINGDOWN_STRAIN_OBSERVABLE_BUILT:  YES (synthetic injection only)
READY_FOR_REAL_RINGDOWN_TEST:      {"YES_IF_DETECTABLE" if det3 == "DETECTABLE" else "NO — insufficient SNR or MARGINAL"}
READY_FOR_REAL_LIGO_SSZ_CLAIM:     NO
SSZ_SUPPORT_CLAIM_MADE:            NO
SSZ_FALSIFICATION_CLAIM_MADE:      NO
```
"""
    (REPORTS / "QNM_RINGDOWN_INJECTION_SENSITIVITY_REPORT.md").write_text(
        report, encoding="utf-8")
    log("  -> reports/QNM_RINGDOWN_INJECTION_SENSITIVITY_REPORT.md")
    log("  -> data_manifest/qnm_injection_scan.csv")
    (LOGS / "qnm_ringdown_injection_sensitivity.log").write_text(
        "\n".join(_log), encoding="utf-8")
    log(f"DONE | 3% branch: {det3} | READY_FOR_REAL_CLAIM: NO")


if __name__ == "__main__":
    run()
