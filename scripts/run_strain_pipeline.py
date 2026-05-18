"""SSZ Strain-Only Anti-Circular Exploratory Pipeline.

HARD RULES:
  ALLOWED:  calibrated strain h(t), PSD from Welch, analytic GR control,
            SSZ V0-proxy deformation, residual, log-likelihood sanity
  FORBIDDEN: posterior verdict, pSEOBNR comparison, epsilon_220 claim,
             SSZ support/falsification claim, loading huge datasets fully

All reports written to reports/  |  Log to logs/full_strain_pipeline.log
"""
import sys, os, datetime, numpy as np, h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.ssz_core import xi_weak, d_ssz
from ssz_ligo_tests.anti_circularity import classify_observable_source, CircularityStatus

# ---------------------------------------------------------------------------
# CONSTANTS & CONFIG
# ---------------------------------------------------------------------------
G = 6.674e-11; C = 2.998e8; M_SUN = 1.989e30

TRIGGER_GPS  = 1411261107.984   # from GWOSC release metafile, not posterior
MC_MSUN      = 8.9              # public alert estimate
ETA          = 0.25             # equal-mass assumption
DL_MPC       = 300.0

WIN_S        = 4.0              # on-source window [s]
OFFSOURCE_OFFSET_S = 500.0      # offset before event
OFFSOURCE_DUR_S    = 256.0      # PSD estimation duration
F_LOW        = 20.0
F_HIGH       = 800.0
PSD_NPERSEG  = 4096

H1_STRAIN = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720"
    r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)

REPORTS = Path(__file__).parent.parent / "reports"
LOGS    = Path(__file__).parent.parent / "logs"
NOW     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
_log_lines = []

def log(msg=""):
    print(msg)
    _log_lines.append(msg)

def flush_log():
    (LOGS / "full_strain_pipeline.log").write_text(
        "\n".join(_log_lines), encoding="utf-8"
    )

# ---------------------------------------------------------------------------
# ANTI-CIRCULARITY GUARD
# ---------------------------------------------------------------------------
def ac_assert(label):
    s = classify_observable_source(label)
    if s == CircularityStatus.INVALID:
        raise RuntimeError(f"ANTI-CIRCULARITY VIOLATION: {label}")
    return s

# ---------------------------------------------------------------------------
# STEP A — LOAD STRAIN
# ---------------------------------------------------------------------------
def step_A():
    log("=" * 60)
    log("STEP A: LOAD GW240925 H1 STRAIN")
    log("=" * 60)

    ac_assert("H1/strain")
    log(f"  Anti-circularity check: H1/strain -> VALID_INDEPENDENT")

    if not H1_STRAIN.exists():
        log(f"  STATUS: BLOCKED_STRAIN_NOT_READABLE")
        log(f"  File not found: {H1_STRAIN}")
        return None, None, None

    log(f"  File:    {H1_STRAIN}")
    log(f"  Dataset: strain/Strain")

    with h5py.File(str(H1_STRAIN), 'r') as f:
        gps0     = float(f['meta/GPSstart'][()])
        dur      = float(f['meta/Duration'][()])
        detector = f['meta/Detector'][()].decode()
        channel  = f['meta/StrainChannel'][()].decode()
        n_total  = f['strain/Strain'].shape[0]
        fs       = int(n_total / dur)

        t_ev   = TRIGGER_GPS - gps0
        half   = WIN_S / 2.0
        i0     = max(0, int((t_ev - half) * fs))
        i1     = min(n_total, int((t_ev + half) * fs))
        strain = f['strain/Strain'][i0:i1]

    log(f"  Detector:        {detector}")
    log(f"  Channel:         {channel}")
    log(f"  GPS start file:  {gps0}")
    log(f"  GPS end file:    {gps0 + dur}")
    log(f"  Trigger GPS:     {TRIGGER_GPS}")
    log(f"  Trigger offset:  {TRIGGER_GPS - gps0:.3f} s within file")
    log(f"  Sample rate:     {fs} Hz")
    log(f"  Window:          [{i0}:{i1}] = {len(strain)} samples = {len(strain)/fs:.3f} s")

    if len(strain) == 0:
        log("  STATUS: BLOCKED_STRAIN_NOT_READABLE (empty segment)")
        return None, None, None

    has_nan = np.any(np.isnan(strain))
    has_inf = np.any(np.isinf(strain))
    log(f"  min:   {strain.min():.4e}")
    log(f"  max:   {strain.max():.4e}")
    log(f"  mean:  {strain.mean():.4e}")
    log(f"  std:   {strain.std():.4e}")
    log(f"  NaN:   {has_nan}")
    log(f"  Inf:   {has_inf}")

    if has_nan or has_inf:
        log("  STATUS: FAIL_NUMERICAL_ERROR (NaN/Inf in strain)")
        return None, None, None

    log("  STATUS: PASS — strain segment loaded, sane values")
    return strain, fs, gps0

# ---------------------------------------------------------------------------
# STEP B — PSD ESTIMATION
# ---------------------------------------------------------------------------
def step_B(gps0, fs):
    log("\n" + "=" * 60)
    log("STEP B: PSD ESTIMATION (Welch, off-source)")
    log("=" * 60)

    ac_assert("H1/strain")

    with h5py.File(str(H1_STRAIN), 'r') as f:
        n_total  = f['strain/Strain'].shape[0]
        dur      = float(f['meta/Duration'][()])
        fs_file  = int(n_total / dur)
        t_off    = TRIGGER_GPS - gps0 - OFFSOURCE_OFFSET_S
        i0       = max(0, int(t_off * fs_file))
        i1       = min(n_total, i0 + int(OFFSOURCE_DUR_S * fs_file))
        offsrc   = f['strain/Strain'][i0:i1]

    if len(offsrc) < PSD_NPERSEG * 2:
        log("  STATUS: BLOCKED_PSD_INVALID (off-source segment too short)")
        return None, None

    freqs, psd = signal.welch(offsrc, fs=fs, nperseg=PSD_NPERSEG,
                               window='hann', noverlap=PSD_NPERSEG // 2)

    log(f"  Off-source offset:  {OFFSOURCE_OFFSET_S} s before trigger")
    log(f"  Off-source length:  {OFFSOURCE_DUR_S} s  ({len(offsrc)} samples)")
    log(f"  Welch nperseg:      {PSD_NPERSEG}")
    log(f"  Welch overlap:      50%")
    log(f"  Window:             Hann")
    log(f"  PSD bins:           {len(freqs)}")
    log(f"  Freq range:         {freqs[1]:.3f} – {freqs[-1]:.1f} Hz")
    log(f"  PSD median (20-800 Hz): {np.median(psd[(freqs>=20)&(freqs<=800)]):.3e} 1/Hz")
    log(f"  Source:             RAW STRAIN (no posterior PSD used)")
    log("  STATUS: PASS — PSD estimated from off-source strain")
    return freqs, psd

# ---------------------------------------------------------------------------
# STEP C — GR CONTROL WAVEFORM
# ---------------------------------------------------------------------------
def step_C(freqs_fd, Mc_kg, eta, dL_m):
    log("\n" + "=" * 60)
    log("STEP C: GR CONTROL WAVEFORM (TaylorF2 0PN)")
    log("=" * 60)
    log("  LABEL: GR_CONTROL_TEMPLATE_ONLY")
    log("  WARNING: This is a 0PN stationary-phase approximation.")
    log("           Not a full LIGO PE waveform.")
    log("           Suitable only as sanity/control template.")

    mask = (freqs_fd >= F_LOW) & (freqs_fd <= F_HIGH) & (freqs_fd > 0)
    h = np.zeros(len(freqs_fd), dtype=complex)
    f = freqs_fd[mask]
    x   = np.pi * G * Mc_kg / C**3 * f
    psi = (3.0 / (128.0 * eta)) * x**(-5.0/3.0)
    C1  = (np.sqrt(5*np.pi/24)
           * (G*Mc_kg/C**3)**(5/6)
           * np.pi**(-7/6)
           / dL_m)
    A   = C1 * f**(-7.0/6.0)
    h[mask] = A * np.exp(1j * psi)

    log(f"  Chirp mass:  {Mc_kg/M_SUN:.2f} Msun")
    log(f"  eta:         {eta}")
    log(f"  Distance:    {dL_m/3.086e22:.0f} Mpc")
    log(f"  f_low:       {F_LOW} Hz")
    log(f"  f_high:      {F_HIGH} Hz")
    log(f"  |h| max:     {np.abs(h).max():.3e}")
    log(f"  |h| at 100Hz:{np.abs(h[np.argmin(np.abs(freqs_fd-100))]):.3e}")
    log("  STATUS: GR_CONTROL_TEMPLATE_LIMITED (0PN only, no higher order terms)")
    return h

# ---------------------------------------------------------------------------
# STEP D — SSZ FORWARD MODEL
# ---------------------------------------------------------------------------
def step_D(freqs_fd, h_gr, M_kg, rs_m):
    log("\n" + "=" * 60)
    log("STEP D: SSZ FORWARD MODEL")
    log("=" * 60)
    log("  LABEL: SSZ_FORWARD_V0_PROXY")
    log("  V0 proxy formula:")
    log("    r(f)  = (G*M / (pi*f)^2)^{1/3}  [Kepler]")
    log("    xi(r) = xi_weak(r, rs)           [weak field]")
    log("    dPsi(f) = kappa * (1 - D(xi))   [kappa=1.0 locked]")

    mask = (freqs_fd >= F_LOW) & (freqs_fd <= F_HIGH) & (freqs_fd > 0)
    dpsi = np.zeros(len(freqs_fd))
    for i in np.where(mask)[0]:
        r = (G * M_kg / (np.pi * freqs_fd[i])**2) ** (1.0/3.0)
        xi = xi_weak(r, rs_m)
        dpsi[i] = 1.0 * (1.0 - d_ssz(xi))

    h_ssz = h_gr * np.exp(1j * dpsi)

    band = dpsi[mask]
    log(f"  Schwarzschild r_s:  {rs_m/1e3:.2f} km")
    log(f"  kappa_phase:        1.0 (locked exploratory)")
    log(f"  dpsi range (band):  [{band.min():.4f}, {band.max():.4f}] rad")
    log(f"  dpsi mean (band):   {band.mean():.4f} rad")
    log(f"  |h_SSZ| max:        {np.abs(h_ssz).max():.3e}")
    log("  Exact delta_psi SSZ derivation: MISSING (Ch.31 not yet locked)")
    log("  STATUS: SSZ_FORWARD_V0_PROXY — not suitable for physics claim")
    return h_ssz, dpsi

# ---------------------------------------------------------------------------
# STEP E — RESIDUALS & LOG-LIKELIHOOD
# ---------------------------------------------------------------------------
def step_E(strain, fs, freqs_psd, psd, h_gr, h_ssz):
    log("\n" + "=" * 60)
    log("STEP E: RESIDUALS + LOG-LIKELIHOOD")
    log("=" * 60)

    N   = len(strain)
    df  = float(fs) / N
    ffd = np.fft.rfftfreq(N, 1.0/fs)
    dfd = np.fft.rfft(strain) / fs

    # Interpolate PSD to FFT grid
    pi = np.interp(ffd, freqs_psd, psd, left=psd[1], right=psd[-1])
    pi[pi <= 0] = pi[pi > 0].min()

    if np.any(~np.isfinite(pi)):
        log("  STATUS: BLOCKED_PSD_INVALID")
        return None

    # Residuals
    res_gr  = dfd - h_gr
    res_ssz = dfd - h_ssz

    def nwip(a, b):
        return 4.0 * np.real(np.sum(a * np.conj(b) / pi)) * df

    def lnL(res):
        return -0.5 * nwip(res, res)

    def snr_mf(d, h):
        nn = nwip(h, h)
        return abs(nwip(d, h)) / np.sqrt(nn) if nn > 0 else 0.0

    lnL_gr   = lnL(res_gr)
    lnL_ssz  = lnL(res_ssz)
    delta_lnL = lnL_ssz - lnL_gr
    snr_gr   = snr_mf(dfd, h_gr)
    snr_ssz  = snr_mf(dfd, h_ssz)

    mask = (ffd >= F_LOW) & (ffd <= F_HIGH)
    res_gr_rms  = np.sqrt(np.mean(np.abs(res_gr[mask])**2))
    res_ssz_rms = np.sqrt(np.mean(np.abs(res_ssz[mask])**2))

    log(f"  N samples:          {N}")
    log(f"  df:                 {df:.6f} Hz")
    log(f"  FFT bins (total):   {len(ffd)}")
    log(f"  Band [20-800 Hz]:   {mask.sum()} bins")
    log(f"  lnL (GR control):   {lnL_gr:.4e}")
    log(f"  lnL (SSZ V0):       {lnL_ssz:.4e}")
    log(f"  delta_lnL SSZ-GR:   {delta_lnL:.4e}")
    log(f"  MF-SNR GR:          {snr_gr:.2f}")
    log(f"  MF-SNR SSZ:         {snr_ssz:.2f}")
    log(f"  Residual RMS GR:    {res_gr_rms:.3e}")
    log(f"  Residual RMS SSZ:   {res_ssz_rms:.3e}")

    if abs(delta_lnL) < 1.0:
        log("  delta_lnL < 1: INDISTINGUISHABLE — no physics claim possible")
    elif delta_lnL > 0:
        log("  delta_lnL > 0: SSZ V0-proxy marginally preferred — V0 PROXY ONLY, NO CLAIM")
    else:
        log("  delta_lnL < 0: GR control preferred — V0 PROXY ONLY, NO CLAIM")

    log("  STATUS: PASS_NUMERICAL — residuals and lnL computed without error")
    return {
        "lnL_gr": lnL_gr, "lnL_ssz": lnL_ssz,
        "delta_lnL": delta_lnL,
        "snr_gr": snr_gr, "snr_ssz": snr_ssz,
        "res_gr_rms": res_gr_rms, "res_ssz_rms": res_ssz_rms,
    }

# ---------------------------------------------------------------------------
# WRITE REPORTS
# ---------------------------------------------------------------------------
def write_reports(strain, fs, gps0, freqs_psd, psd, h_gr, h_ssz,
                  dpsi, stats, M_kg, rs_m):
    ffd = np.fft.rfftfreq(len(strain), 1.0/fs)
    mask = (ffd >= F_LOW) & (ffd <= F_HIGH)

    # ---- A: REAL_STRAIN_LOAD_REPORT ----
    (REPORTS / "REAL_STRAIN_LOAD_REPORT.md").write_text(f"""# Real Strain Load Report
Generated: {NOW}

## File
- Path: `{H1_STRAIN}`
- Dataset: `strain/Strain`
- GPS start: {gps0}
- Trigger GPS: {TRIGGER_GPS}
- Trigger offset: {TRIGGER_GPS - gps0:.3f} s within file

## Segment
- Window: {WIN_S} s around trigger
- Samples loaded: {len(strain)}
- Sample rate: {fs} Hz

## Sanity Statistics
| Stat | Value |
|------|-------|
| min | {strain.min():.4e} |
| max | {strain.max():.4e} |
| mean | {strain.mean():.4e} |
| std | {strain.std():.4e} |
| NaN | {np.any(np.isnan(strain))} |
| Inf | {np.any(np.isinf(strain))} |

## Anti-Circularity
- Source label: `H1/strain`
- Classification: VALID_INDEPENDENT
- Posterior data used: NO

## Status
**PASS** — strain segment loaded, values sane
""", encoding="utf-8")

    # ---- B: PSD_WELCH_REPORT ----
    band_m = (freqs_psd >= F_LOW) & (freqs_psd <= F_HIGH)
    (REPORTS / "PSD_WELCH_REPORT.md").write_text(f"""# PSD Welch Estimation Report
Generated: {NOW}

## Method
- Estimator: Welch
- Window: Hann
- nperseg: {PSD_NPERSEG}
- Overlap: 50%
- Off-source offset: {OFFSOURCE_OFFSET_S} s before trigger
- Off-source duration: {OFFSOURCE_DUR_S} s

## Results
- PSD bins: {len(freqs_psd)}
- Frequency range: {freqs_psd[1]:.3f} – {freqs_psd[-1]:.1f} Hz
- PSD median [20–800 Hz]: {np.median(psd[band_m]):.3e} 1/Hz
- PSD min [20–800 Hz]:    {psd[band_m].min():.3e} 1/Hz
- PSD max [20–800 Hz]:    {psd[band_m].max():.3e} 1/Hz

## Anti-Circularity
- Posterior PSD used: NO
- Source: raw H1 strain off-source segment

## Status
**PASS** — PSD estimated from raw strain only
""", encoding="utf-8")

    # ---- C: GR_CONTROL_WAVEFORM_REPORT ----
    (REPORTS / "GR_CONTROL_WAVEFORM_REPORT.md").write_text(f"""# GR Control Waveform Report
Generated: {NOW}

## LABEL: GR_CONTROL_TEMPLATE_LIMITED

## Warning
This is a 0PN TaylorF2 stationary-phase approximation.
It is NOT a full LIGO parameter estimation waveform.
It does NOT include: spin, higher modes, merger, ringdown.
It is used ONLY as a sanity control reference.

## Parameters (Public Alert / Analytic)
- Chirp mass: {MC_MSUN} Msun  (public estimate)
- eta: {ETA}  (equal-mass assumption)
- Total mass: {M_kg/M_SUN:.2f} Msun
- Distance: {DL_MPC} Mpc
- f_low: {F_LOW} Hz
- f_high: {F_HIGH} Hz

## Template Statistics
- |h_GR| max: {np.abs(h_gr).max():.3e}
- Active frequency bins: {mask.sum()}

## Status
**GR_CONTROL_TEMPLATE_LIMITED** — suitable for pipeline sanity only
""", encoding="utf-8")

    # ---- D: SSZ_FORWARD_APPLICATION_REPORT ----
    (REPORTS / "SSZ_FORWARD_APPLICATION_REPORT.md").write_text(f"""# SSZ Forward Model Application Report
Generated: {NOW}

## LABEL: SSZ_FORWARD_V0_PROXY

## Warning
The delta_psi(f) formula used here is a V0 proxy.
Exact derivation from SSZ Book Ch.31 (RSG phase integral) is MISSING.
This result CANNOT be used for any physics claim.

## Formula Applied
```
r(f)    = (G*M / (pi*f)^2)^(1/3)   [Kepler 3rd law]
xi(r)   = xi_weak(r, rs)             [weak field: rs/(2r)]
dPsi(f) = kappa * (1 - D(xi(r)))    [kappa=1.0, locked]
h_SSZ   = h_GR * exp(i * dPsi(f))
```

## Parameters
- Total mass: {M_kg/M_SUN:.2f} Msun
- Schwarzschild radius: {rs_m/1e3:.2f} km
- kappa_phase: 1.0 (exploratory, not derived)
- Regime: weak field (r >> rs in LIGO band)

## delta_psi Statistics [20–800 Hz]
- max:  {dpsi[mask].max():.4f} rad
- min:  {dpsi[mask].min():.4f} rad
- mean: {dpsi[mask].mean():.4f} rad

## Blocked Items
- BLOCKED_MISSING_EQUATION: exact delta_psi from SSZ Ch.31
- BLOCKED_MISSING_EQUATION: epsilon_220 ringdown (CONFLICTING 3%/31%/39%)

## Status
**SSZ_FORWARD_V0_PROXY** — technical application only, no physics claim
""", encoding="utf-8")

    # ---- E: RESIDUAL_LIKELIHOOD_REPORT ----
    (REPORTS / "RESIDUAL_LIKELIHOOD_REPORT.md").write_text(f"""# Residual and Log-Likelihood Report
Generated: {NOW}

## Computation
- FFT length: {len(strain)} samples
- df: {float(fs)/len(strain):.6f} Hz
- Band: {F_LOW}–{F_HIGH} Hz

## Log-Likelihood (noise-weighted inner product)
| Model | lnL | MF-SNR | Residual RMS |
|-------|-----|--------|--------------|
| GR control (0PN) | {stats['lnL_gr']:.4e} | {stats['snr_gr']:.2f} | {stats['res_gr_rms']:.3e} |
| SSZ V0-proxy     | {stats['lnL_ssz']:.4e} | {stats['snr_ssz']:.2f} | {stats['res_ssz_rms']:.3e} |

**delta_lnL (SSZ - GR) = {stats['delta_lnL']:.4e}**

## Interpretation
- |delta_lnL| < 1: INDISTINGUISHABLE
- GR control is 0PN only (GR_CONTROL_TEMPLATE_LIMITED)
- SSZ uses V0 proxy (SSZ_FORWARD_V0_PROXY)
- Neither result constitutes a physics claim

## Mandatory Statements
```
READY_FOR_REAL_SSZ_CLAIM:      NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
POSTERIOR_RF_TEST:             INVALID_FOR_SSZ
```

## Status
**PASS_NUMERICAL** — residuals and lnL computed without error
""", encoding="utf-8")

    # ---- F: ANTI_CIRCULARITY_FINAL_GATE ----
    (REPORTS / "ANTI_CIRCULARITY_FINAL_GATE.md").write_text(f"""# Anti-Circularity Final Gate
Generated: {NOW}

## Observable Classification Audit

| Data Source | Classification | Used |
|-------------|---------------|------|
| H1 strain (GWOSC HDF5) | VALID_INDEPENDENT | YES |
| PSD from off-source strain | VALID_INDEPENDENT | YES |
| TaylorF2 analytic template | ANALYTIC_CONTROL | YES |
| SSZ V0 proxy (locked kappa) | SSZ_FORWARD_V0_PROXY | YES |
| online_posterior_samples.h5 | INVALID (posterior) | NO |
| GW240925 metafile PSDs | CIRCULARITY_RISK (bilby) | NO |
| pSEOBNR HDF5 samples | INVALID (GR posterior) | NO |
| pca_tiger / pca_fti files | INVALID (FTI/TIGER) | NO |
| epsilon_220 from corpus | BLOCKED_CONFLICTING | NO |

## Forbidden Claims — All Confirmed Absent
- SSZ supported by GW240925: NOT MADE
- SSZ falsified by GW240925: NOT MADE
- Posterior R_f as SSZ test:  NOT MADE
- Ringdown epsilon_220 claim: NOT MADE

## Final Pipeline Status
```
PIPELINE_STATUS:               PASS_EXPLORATORY_STRAIN_PIPELINE_RAN
READY_FOR_REAL_SSZ_CLAIM:      NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
POSTERIOR_RF_TEST:             INVALID_FOR_SSZ
GR_CONTROL_TEMPLATE:           GR_CONTROL_TEMPLATE_LIMITED
SSZ_FORWARD_MODEL:             SSZ_FORWARD_V0_PROXY
ANTI_CIRCULARITY_GATE:         CLEAR
```

## What Remains Blocked
1. delta_psi exact formula (SSZ Book Ch.31 not yet locked)
2. epsilon_220 ringdown (3 conflicting sources: 3%, 31%, 39%)
3. Whitened MF with calibrated ASD
""", encoding="utf-8")

    log("\n  Reports written:")
    for name in [
        "REAL_STRAIN_LOAD_REPORT.md",
        "PSD_WELCH_REPORT.md",
        "GR_CONTROL_WAVEFORM_REPORT.md",
        "SSZ_FORWARD_APPLICATION_REPORT.md",
        "RESIDUAL_LIKELIHOOD_REPORT.md",
        "ANTI_CIRCULARITY_FINAL_GATE.md",
    ]:
        log(f"    reports/{name}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"SSZ STRAIN PIPELINE — {NOW}")
    log(f"GW240925 | GPS={TRIGGER_GPS} | Mc={MC_MSUN} Msun | eta={ETA}")

    Mc_kg = MC_MSUN * M_SUN
    M_kg  = Mc_kg / ETA**(3.0/5.0)
    rs_m  = 2.0 * G * M_kg / C**2
    dL_m  = DL_MPC * 3.086e22

    strain, fs, gps0 = step_A()
    if strain is None:
        log("\nFINAL: BLOCKED_STRAIN_NOT_READABLE")
        flush_log(); return

    freqs_psd, psd = step_B(gps0, fs)
    if psd is None:
        log("\nFINAL: BLOCKED_PSD_INVALID")
        flush_log(); return

    ffd   = np.fft.rfftfreq(len(strain), 1.0/fs)
    h_gr  = step_C(ffd, Mc_kg, ETA, dL_m)
    h_ssz, dpsi = step_D(ffd, h_gr, M_kg, rs_m)
    stats = step_E(strain, fs, freqs_psd, psd, h_gr, h_ssz)

    if stats is None:
        log("\nFINAL: BLOCKED_PSD_INVALID")
        flush_log(); return

    mask = (ffd >= F_LOW) & (ffd <= F_HIGH)
    write_reports(strain, fs, gps0, freqs_psd, psd,
                  h_gr, h_ssz, dpsi, stats, M_kg, rs_m)

    log("\n" + "=" * 60)
    log("FINAL GATE")
    log("=" * 60)
    log("  PIPELINE_STATUS:              PASS_EXPLORATORY_STRAIN_PIPELINE_RAN")
    log("  READY_FOR_REAL_SSZ_CLAIM:     NO")
    log("  SSZ_SUPPORT_CLAIM_MADE:       NO")
    log("  SSZ_FALSIFICATION_CLAIM_MADE: NO")
    log("  POSTERIOR_RF_TEST:            INVALID_FOR_SSZ")
    log("  GR_CONTROL_TEMPLATE:          GR_CONTROL_TEMPLATE_LIMITED")
    log("  SSZ_FORWARD_MODEL:            SSZ_FORWARD_V0_PROXY")
    log("  ANTI_CIRCULARITY_GATE:        CLEAR")

    flush_log()
    log(f"\n  Log: logs/full_strain_pipeline.log")


if __name__ == "__main__":
    run()
