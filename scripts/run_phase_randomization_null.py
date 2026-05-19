"""Phase Randomization Null Test.

Control test: if the L1 broadband excess is due to coherent spectral
structure (real signal or persistent lines), it should disappear when
phases are randomized while keeping the amplitude spectrum identical.

Method:
  1. Take L1 trigger strain.
  2. Compute FFT.
  3. Randomize phases (keep |FFT|, replace angle with uniform random).
  4. IFFT -> surrogate time series with same power spectrum, random phase.
  5. Run same bandpower, Gaussianity, and coherence tests on N surrogates.
  6. Compare surrogate distribution to original L1 trigger values.

If L1 excess persists in surrogates: excess is in the power spectrum (PSD),
  not in phase structure -> PSD/spectral artifact, not coherent signal.
If L1 excess disappears in surrogates: original signal has phase structure
  beyond what the PSD alone contains.

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

LOG_PATH = LOGS / "phase_randomization_null.log"
_log_lines = []
RNG = np.random.default_rng(seed=42)


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
PSD_REF_DUR_S = 64.0
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 512
N_SURROGATES = 200   # number of phase-randomized surrogates
FILTER_ORDER = 6

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
# SIGNAL PROCESSING
# ---------------------------------------------------------------------------
def phase_randomize(strain):
    """Return surrogate with same amplitude spectrum, randomized phases."""
    n = len(strain)
    S = np.fft.rfft(strain)
    mag = np.abs(S)
    # Random phases, preserving DC and Nyquist as real
    phases = RNG.uniform(0, 2 * np.pi, len(S))
    phases[0] = 0.0
    if n % 2 == 0:
        phases[-1] = 0.0
    S_rand = mag * np.exp(1j * phases)
    return np.fft.irfft(S_rand, n=n)


def bandpass_filter(strain, fs, f_lo=F_LOW, f_hi=F_HIGH,
                    order=FILTER_ORDER):
    nyq = fs / 2
    lo = max(f_lo / nyq, 1e-4)
    hi = min(f_hi / nyq, 0.9999)
    sos = signal.butter(order, [lo, hi], btype="bandpass", output="sos")
    return signal.sosfiltfilt(sos, strain)


def compute_ref_asd(strain, fs, nperseg=NPERSEG):
    nps = min(nperseg, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window="hann")
    return freqs, np.sqrt(psd)


def whiten_with_asd(strain, fs, ref_freqs, ref_asd):
    n = len(strain)
    fft_freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    asd_i = np.interp(fft_freqs, ref_freqs, ref_asd + 1e-300)
    S = np.fft.rfft(strain)
    return np.fft.irfft(S / asd_i, n=n)


def bandpower_from_strain(strain, fs, f_lo=F_LOW, f_hi=F_HIGH,
                          nperseg=NPERSEG):
    nps = min(nperseg, len(strain) // 4)
    freqs, psd = signal.welch(strain, fs=fs, nperseg=nps,
                              noverlap=nps // 2, window="hann")
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    return float(np.trapezoid(psd[mask], freqs[mask]))


def excess_kurtosis(x):
    return float(stats.kurtosis(x, fisher=True))  # Fisher=True -> normal=0


# ---------------------------------------------------------------------------
# SURROGATE TEST
# ---------------------------------------------------------------------------
def run_surrogate_test(det, strain, fs, ref_freqs, ref_asd, label):
    """
    Compute original stats and surrogate distribution.
    Returns dict of original values + surrogate quantile.
    """
    # Original: whiten + bandpass
    strain_w = whiten_with_asd(strain, fs, ref_freqs, ref_asd)
    strain_bp = bandpass_filter(strain_w, fs)

    orig_bp = bandpower_from_strain(strain, fs)
    orig_ex_k = excess_kurtosis(strain_bp)
    orig_n4 = int(np.sum(
        np.abs((strain_bp - np.mean(strain_bp))
               / (np.std(strain_bp) + 1e-300)) > 4))

    log(f"\n  [{label}] Original:")
    log(f"    Bandpower:      {orig_bp:.4e}")
    log(f"    Excess kurtosis: {orig_ex_k:+.4f}")
    log(f"    |z|>4 count:    {orig_n4}")

    # Surrogate distribution
    surr_bp = []
    surr_ex_k = []
    surr_n4 = []

    for _ in range(N_SURROGATES):
        s_rand = phase_randomize(strain)
        surr_bp.append(bandpower_from_strain(s_rand, fs))
        s_rand_w = whiten_with_asd(s_rand, fs, ref_freqs, ref_asd)
        s_rand_bp = bandpass_filter(s_rand_w, fs)
        surr_ex_k.append(excess_kurtosis(s_rand_bp))
        surr_n4.append(int(np.sum(
            np.abs((s_rand_bp - np.mean(s_rand_bp))
                   / (np.std(s_rand_bp) + 1e-300)) > 4)))

    surr_bp = np.array(surr_bp)
    surr_ex_k = np.array(surr_ex_k)
    surr_n4 = np.array(surr_n4)

    q_bp = float(stats.percentileofscore(surr_bp, orig_bp) / 100)
    q_ek = float(stats.percentileofscore(
        np.abs(surr_ex_k), abs(orig_ex_k)) / 100)
    q_n4 = float(stats.percentileofscore(surr_n4, orig_n4) / 100)

    log(f"  [{label}] Surrogate distribution (N={N_SURROGATES}):")
    log(f"    Bandpower:  surr_mean={surr_bp.mean():.4e}  "
        f"orig_quantile={q_bp*100:.1f}%")
    log(f"    |ex_kurtosis|: surr_mean={np.abs(surr_ex_k).mean():.3f}  "
        f"orig_quantile={q_ek*100:.1f}%")
    log(f"    |z|>4 count: surr_mean={surr_n4.mean():.2f}  "
        f"orig_quantile={q_n4*100:.1f}%")

    # Verdict
    if q_bp > 0.95:
        bp_verdict = "BP_EXCEEDS_SURROGATES"
    else:
        bp_verdict = "BP_CONSISTENT_WITH_SURROGATES"

    if q_ek > 0.95:
        ek_verdict = "KURTOSIS_EXCEEDS_SURROGATES"
    else:
        ek_verdict = "KURTOSIS_CONSISTENT_WITH_SURROGATES"

    if bp_verdict == "BP_EXCEEDS_SURROGATES":
        interp = ("Bandpower excess is NOT explained by phase randomization. "
                  "Excess is in the amplitude spectrum (PSD), not phase.")
    else:
        interp = ("Bandpower consistent with surrogates. "
                  "Excess may be explained by spectral content alone.")

    log(f"  -> BP_VERDICT: {bp_verdict}")
    log(f"  -> EK_VERDICT: {ek_verdict}")
    log(f"  -> {interp}")

    return {
        "det": det, "label": label,
        "orig_bp": round(orig_bp, 8),
        "orig_ex_k": round(orig_ex_k, 5),
        "orig_n4": orig_n4,
        "surr_bp_mean": round(float(surr_bp.mean()), 8),
        "surr_bp_std": round(float(surr_bp.std()), 8),
        "surr_ex_k_mean": round(float(surr_ex_k.mean()), 5),
        "q_bp": round(q_bp, 4),
        "q_ex_k": round(q_ek, 4),
        "q_n4": round(q_n4, 4),
        "bp_verdict": bp_verdict,
        "ek_verdict": ek_verdict,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"PHASE RANDOMIZATION NULL TEST -- {NOW}")
    log(f"Trigger: {TRIGGER_GPS}  Win: {WIN_S}s  "
        f"Band: {F_LOW}-{F_HIGH}Hz  N_surrogates: {N_SURROGATES}")

    # Load reference ASDs
    h1_ref_s, fs_h = load_window(H1_PATH,
                                  TRIGGER_GPS - PSD_OFFSET_S, PSD_REF_DUR_S)
    l1_ref_s, fs_l = load_window(L1_PATH,
                                  TRIGGER_GPS - PSD_OFFSET_S, PSD_REF_DUR_S)

    if h1_ref_s is None or l1_ref_s is None:
        log("ERROR: Reference segments failed to load")
        flush_log()
        return

    h1_ref_freqs, h1_ref_asd = compute_ref_asd(h1_ref_s, fs_h)
    l1_ref_freqs, l1_ref_asd = compute_ref_asd(l1_ref_s, fs_l)
    log(f"Reference ASD: H1 {len(h1_ref_s)} samples  "
        f"L1 {len(l1_ref_s)} samples")

    all_rows = []

    for det, path, ref_freqs, ref_asd, fs in [
        ("H1", H1_PATH, h1_ref_freqs, h1_ref_asd, fs_h),
        ("L1", L1_PATH, l1_ref_freqs, l1_ref_asd, fs_l),
    ]:
        log(f"\n{'='*60}")
        log(f"DETECTOR: {det}")
        log(f"{'='*60}")

        for tag, offset in [("TRIGGER", 0.0), ("OFF_m500", -500.0)]:
            strain, _ = load_window(path, TRIGGER_GPS + offset, WIN_S)
            if strain is None:
                log(f"  [{det} {tag}] load failed")
                continue
            label = f"{det}_{tag}"
            result = run_surrogate_test(det, strain, fs,
                                        ref_freqs, ref_asd, label)
            result["tag"] = tag
            all_rows.append(result)

    # ---------------------------------------------------------------------------
    # OVERALL VERDICT
    # ---------------------------------------------------------------------------
    log(f"\n{'='*60}")
    log("OVERALL PHASE-RANDOMIZATION VERDICT")
    log(f"{'='*60}")

    l1_trig = next((r for r in all_rows
                    if r["det"] == "L1" and r["tag"] == "TRIGGER"), None)
    h1_trig = next((r for r in all_rows
                    if r["det"] == "H1" and r["tag"] == "TRIGGER"), None)

    if l1_trig and h1_trig:
        log(f"  H1 trigger BP quantile vs surrogates: "
            f"{h1_trig['q_bp']*100:.1f}%  -> {h1_trig['bp_verdict']}")
        log(f"  L1 trigger BP quantile vs surrogates: "
            f"{l1_trig['q_bp']*100:.1f}%  -> {l1_trig['bp_verdict']}")

        if (l1_trig["bp_verdict"] == "BP_EXCEEDS_SURROGATES"
                and h1_trig["bp_verdict"] != "BP_EXCEEDS_SURROGATES"):
            final = "L1_HAS_ASD_EXCESS_H1_NORMAL"
        elif (l1_trig["bp_verdict"] == "BP_CONSISTENT_WITH_SURROGATES"):
            final = "L1_EXCESS_IN_PHASE_STRUCTURE_NOT_ASD"
        else:
            final = "INCONCLUSIVE"
        log(f"  -> FINAL_PHASE_RAND_VERDICT: {final}")

    # ---------------------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------------------
    csv_path = MANIFEST / "phase_randomization_null.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        if all_rows:
            fields = list(all_rows[0].keys())
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)

    md = [
        "# Phase Randomization Null Test Report",
        f"Generated: {NOW}",
        "",
        "## Configuration",
        f"- N surrogates: {N_SURROGATES}",
        f"- Trigger GPS: {TRIGGER_GPS}",
        f"- Window: {WIN_S}s  Band: {F_LOW}-{F_HIGH}Hz",
        f"- Random seed: 42",
        "",
        "## Interpretation",
        "- BP_EXCEEDS_SURROGATES (>95th pctile): excess is in the ASD/PSD,",
        "  not in phase structure. Consistent with spectral noise artifact.",
        "- BP_CONSISTENT_WITH_SURROGATES: excess might have phase structure",
        "  beyond what PSD alone contains.",
        "",
        "## Results",
        "",
        "| Det | Tag | Orig BP | Surr mean | BP quantile | BP Verdict |",
        "|-----|-----|---------|-----------|-------------|------------|",
    ]
    for r in all_rows:
        md.append(
            f"| {r['det']} | {r['tag']} | {r['orig_bp']:.3e} "
            f"| {r['surr_bp_mean']:.3e} | {r['q_bp']*100:.1f}% "
            f"| {r['bp_verdict']} |"
        )
    md += [
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]
    rpath = REPORTS / "PHASE_RANDOMIZATION_NULL_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("\nOutputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    flush_log()


if __name__ == "__main__":
    run()
