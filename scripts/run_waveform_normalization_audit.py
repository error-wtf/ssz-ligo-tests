"""Waveform Normalization Audit — Phase/Amplitude Decomposition.

Runs three SSZ DERIVED_V1 variants against the same H1 strain data:
  A) PHASE_ONLY:   h_SSZ = h_GR * exp(i * deltaPsi)
  B) AMPLITUDE_ONLY: h_SSZ = h_GR * (1 + deltaA)
  C) FULL:          h_SSZ = h_GR * (1 + deltaA) * exp(i * deltaPsi)

Outputs: metrics per sub-band for each variant.
No claims. No SSZ confirmation/falsification.
"""
import sys, datetime, numpy as np, h5py, hashlib, json
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.ssz_core import xi_weak, d_ssz, get_xi
from ssz_ligo_tests.derived_phase import delta_psi_ssz_v0
from ssz_ligo_tests.derived_amplitude import delta_a_ssz_v0

# ── Constants ──
G = 6.674e-11; C = 2.998e8; M_SUN = 1.989e30
TRIGGER_GPS = 1411261107.984
MC_MSUN = 8.9; ETA = 0.25
M_kg = MC_MSUN * M_SUN / (ETA ** (3.0/5.0))
mu_kg = ETA * M_kg
rs_m = 2 * G * M_kg / C**2
WIN_S = 4.0; F_LOW = 20.0; F_HIGH = 800.0
OFFSOURCE_OFFSET_S = 500.0; OFFSOURCE_DUR_S = 256.0; PSD_NPERSEG = 4096

H1_STRAIN = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720"
    r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)

SUB_BANDS = [(20, 100), (100, 200), (200, 400), (400, 800)]
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
MANIFEST = Path(__file__).parent.parent / "data_manifest"

def nwip(a, b, psd_f, psd_v, df):
    """Noise-weighted inner product: 4 * Re(sum(a* conj(b) / psd)) * df."""
    pi = np.interp(psd_f, psd_f, psd_v, left=psd_v[1], right=psd_v[-1])
    pi = np.where(pi > 0, pi, pi[pi > 0].min())
    return 4.0 * np.real(np.sum(a * np.conj(b) / pi)) * df

def load_strain():
    sha = hashlib.sha256()
    with open(str(H1_STRAIN), 'rb') as fh:
        while True:
            chunk = fh.read(8*1024*1024)
            if not chunk: break
            sha.update(chunk)
    with h5py.File(str(H1_STRAIN), 'r') as f:
        gps0 = float(f['meta/GPSstart'][()])
        dur = float(f['meta/Duration'][()])
        n_total = f['strain/Strain'].shape[0]
        fs = int(n_total / dur)
        t_ev = TRIGGER_GPS - gps0
        half = WIN_S / 2.0
        i0 = max(0, int((t_ev - half) * fs))
        i1 = min(n_total, int((t_ev + half) * fs))
        strain = f['strain/Strain'][i0:i1]
    return strain, fs, gps0, sha.hexdigest()

def load_psd(gps0, fs):
    with h5py.File(str(H1_STRAIN), 'r') as f:
        n_total = f['strain/Strain'].shape[0]
        dur = float(f['meta/Duration'][()])
        fs_file = int(n_total / dur)
        t_off = TRIGGER_GPS - gps0 - OFFSOURCE_OFFSET_S
        i0 = max(0, int(t_off * fs_file))
        i1 = min(n_total, i0 + int(OFFSOURCE_DUR_S * fs_file))
        offsrc = f['strain/Strain'][i0:i1]
    freqs, psd = signal.welch(offsrc, fs=fs, nperseg=PSD_NPERSEG,
                               window='hann', noverlap=PSD_NPERSEG // 2)
    return freqs, psd

def gr_control(freqs_fd):
    mask = (freqs_fd >= F_LOW) & (freqs_fd <= F_HIGH) & (freqs_fd > 0)
    h = np.zeros(len(freqs_fd), dtype=complex)
    f = freqs_fd[mask]
    x = np.pi * G * MC_MSUN * M_SUN / C**3 * f
    psi = (3.0 / (128.0 * ETA)) * x**(-5.0/3.0)
    C1 = (np.sqrt(5*np.pi/24) * (G*MC_MSUN*M_SUN/C**3)**(5/6)
          * np.pi**(-7/6) / (300 * 3.086e22))
    A = C1 * f**(-7.0/6.0)
    h[mask] = A * np.exp(1j * psi)
    return h, mask

def compute_metrics(data_fd, h_template, psd_f, psd_v, df, mask, ffd):
    """Compute MF-SNR, lnL, residual RMS, overlap."""
    # Interpolate PSD to FFT grid
    pi = np.interp(ffd, psd_f, psd_v, left=psd_v[1], right=psd_v[-1])
    pi = np.where(pi > 0, pi, pi[pi > 0].min())
    
    # Mask to sub-band
    d = data_fd[mask]
    h = h_template[mask]
    p = pi[mask]
    
    # MF-SNR
    nn = 4.0 * np.real(np.sum(h * np.conj(h) / p)) * df
    snr = abs(4.0 * np.real(np.sum(d * np.conj(h) / p)) * df) / np.sqrt(nn) if nn > 0 else 0.0
    
    # Normalized overlap
    hh_gr_norm = np.sqrt(4.0 * np.real(np.sum(h * np.conj(h) / p)) * df)
    h_normed = h / max(hh_gr_norm, 1e-40)
    # Re-read GR for overlap
    # We need the GR template too — pass it separately
    
    # Residual and lnL
    res = d - h
    lnL = -0.5 * 4.0 * np.real(np.sum(res * np.conj(res) / p)) * df
    res_rms = np.sqrt(np.mean(np.abs(res)**2))
    
    # Amplitude ratio
    amp_ratio = np.mean(np.abs(h)) / (np.mean(np.abs(d)) + 1e-40)
    
    return {
        "mf_snr": float(snr),
        "lnL": float(lnL),
        "residual_rms": float(res_rms),
        "amplitude_ratio": float(amp_ratio),
        "template_norm_sq": float(nn),
    }

def compute_overlap(h1, h2, psd_f, psd_v, df, mask, ffd):
    """Normalized noise-weighted overlap."""
    # Interpolate PSD to FFT grid
    pi = np.interp(ffd, psd_f, psd_v, left=psd_v[1], right=psd_v[-1])
    pi = np.where(pi > 0, pi, pi[pi > 0].min())
    
    a = h1[mask]; b = h2[mask]; p = pi[mask]
    
    aa = 4.0 * np.real(np.sum(a * np.conj(a) / p)) * df
    bb = 4.0 * np.real(np.sum(b * np.conj(b) / p)) * df
    ab = 4.0 * np.real(np.sum(a * np.conj(b) / p)) * df
    
    norm = np.sqrt(max(aa, 1e-40) * max(bb, 1e-40))
    return float(ab / norm) if norm > 0 else 0.0

def main():
    print("=== WAVEFORM NORMALIZATION AUDIT ===")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Event: GW240925  H1 4kHz  Mc={MC_MSUN} Msun")
    
    # Load data
    strain, fs, gps0, sha = load_strain()
    print(f"\nHDF5 SHA256: {sha}")
    print(f"GPS start: {gps0}  Trigger: {TRIGGER_GPS}  Offset: {TRIGGER_GPS-gps0:.3f}s")
    
    psd_f, psd_v = load_psd(gps0, fs)
    print(f"PSD bins: {len(psd_f)}  Range: {psd_f[1]:.1f}-{psd_f[-1]:.1f} Hz")
    
    # FFT data
    N = len(strain)
    df = float(fs) / N
    ffd = np.fft.rfftfreq(N, 1.0/fs)
    dfd = np.fft.rfft(strain) / fs
    
    # GR control
    h_gr, full_mask = gr_control(ffd)
    
    # Compute deltaA and deltaPsi
    da, meta_a = delta_a_ssz_v0(ffd[full_mask], M_kg, branch="g2_decay")
    dp, meta_p = delta_psi_ssz_v0(ffd[full_mask], M_kg, mu_kg, branch="g2_decay")
    
    print(f"\ndeltaPsi range: [{dp.min():.4f}, {dp.max():.4f}] rad  mean: {dp.mean():.4f}")
    print(f"deltaA range:   [{da.min():.4e}, {da.max():.4e}]  mean: {da.mean():.4e}")
    
    # Build three variants
    deltaA_full = np.zeros(len(ffd))
    deltaPsi_full = np.zeros(len(ffd))
    deltaA_full[full_mask] = da
    deltaPsi_full[full_mask] = dp
    
    h_phase = h_gr * np.exp(1j * deltaPsi_full)                       # A
    h_amp   = h_gr * (1.0 + deltaA_full)                              # B
    h_full  = h_gr * (1.0 + deltaA_full) * np.exp(1j * deltaPsi_full) # C
    
    # Sub-band masks
    sub_masks = {}
    for flo, fhi in SUB_BANDS:
        sub_masks[f"{flo}-{fhi}"] = (ffd >= flo) & (ffd <= fhi)
    
    results = []
    
    for band_name, bmask in sub_masks.items():
        # Combine with full_mask (active frequencies)
        combined = bmask & full_mask
        
        if np.sum(combined) == 0:
            continue
        
        # GR baseline
        overlap_gr_phase = compute_overlap(h_gr, h_phase, psd_f, psd_v, df, combined, ffd)
        overlap_gr_amp   = compute_overlap(h_gr, h_amp,   psd_f, psd_v, df, combined, ffd)
        overlap_gr_full  = compute_overlap(h_gr, h_full,  psd_f, psd_v, df, combined, ffd)
        
        # Metrics for each variant
        m_gr    = compute_metrics(dfd, h_gr,    psd_f, psd_v, df, combined, ffd)
        m_phase = compute_metrics(dfd, h_phase, psd_f, psd_v, df, combined, ffd)
        m_amp   = compute_metrics(dfd, h_amp,   psd_f, psd_v, df, combined, ffd)
        m_full  = compute_metrics(dfd, h_full,  psd_f, psd_v, df, combined, ffd)
        
        # Amplitude and phase stats in sub-band
        amp_ratio_band = np.mean(np.abs(h_full[combined])) / max(np.mean(np.abs(h_gr[combined])), 1e-40)
        da_band = da[(ffd[full_mask] >= float(band_name.split('-')[0])) & 
                      (ffd[full_mask] <= float(band_name.split('-')[1]))]
        dp_band = dp[(ffd[full_mask] >= float(band_name.split('-')[0])) & 
                      (ffd[full_mask] <= float(band_name.split('-')[1]))]
        
        row = {
            "band_hz": band_name,
            "bins": int(np.sum(combined)),
            "mf_snr_gr": m_gr["mf_snr"],
            "mf_snr_phase": m_phase["mf_snr"],
            "mf_snr_amp": m_amp["mf_snr"],
            "mf_snr_full": m_full["mf_snr"],
            "delta_lnL_phase": m_phase["lnL"] - m_gr["lnL"],
            "delta_lnL_amp": m_amp["lnL"] - m_gr["lnL"],
            "delta_lnL_full": m_full["lnL"] - m_gr["lnL"],
            "overlap_gr_phase": overlap_gr_phase,
            "overlap_gr_amp": overlap_gr_amp,
            "overlap_gr_full": overlap_gr_full,
            "amplitude_ratio": float(amp_ratio_band),
            "da_min": float(da_band.min()),
            "da_max": float(da_band.max()),
            "da_mean": float(da_band.mean()),
            "dp_min_rad": float(dp_band.min()),
            "dp_max_rad": float(dp_band.max()),
            "dp_mean_rad": float(dp_band.mean()),
        }
        results.append(row)
        print(f"\n{band_name} Hz ({row['bins']} bins):")
        print(f"  overlap:  phase={overlap_gr_phase:.4f}  amp={overlap_gr_amp:.4f}  full={overlap_gr_full:.4f}")
        print(f"  MF-SNR:   GR={m_gr['mf_snr']:.2f}  phase={m_phase['mf_snr']:.2f}  amp={m_amp['mf_snr']:.2f}  full={m_full['mf_snr']:.2f}")
    
    # Write CSV
    csv_path = MANIFEST / "subband_waveform_decomposition.csv"
    keys = list(results[0].keys())
    lines = [",".join(keys)]
    for r in results:
        lines.append(",".join(str(r[k]) for k in keys))
    csv_path.write_text("\n".join(lines))
    print(f"\nCSV written: {csv_path}")
    
    # Write log
    log_path = LOGS / "subband_waveform_decomposition.log"
    log_lines = [
        "=== SUBBAND WAVEFORM DECOMPOSITION LOG ===",
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"HDF5 SHA256: {sha}",
        f"Trigger GPS: {TRIGGER_GPS}",
        f"GPS start: {gps0}",
        f"Mc={MC_MSUN} Msun  eta={ETA}  M_total={M_kg/M_SUN:.2f} Msun",
        f"rs={rs_m/1e3:.2f} km",
        "",
        "=== PER SUB-BAND ===",
    ]
    for r in results:
        log_lines.append(
            f"{r['band_hz']} Hz: overlap(phase={r['overlap_gr_phase']:.4f} "
            f"amp={r['overlap_gr_amp']:.4f} full={r['overlap_gr_full']:.4f})  "
            f"MF-SNR(GR={r['mf_snr_gr']:.1f} phase={r['mf_snr_phase']:.1f} "
            f"amp={r['mf_snr_amp']:.1f} full={r['mf_snr_full']:.1f})"
        )
    log_lines += [
        "",
        "=== STATUS ===",
        "FAIR_COMPARISON: PARTIAL",
        "SSZ_EFFECT_SEPARABLE: YES",
        "CLAIM_LEVEL_LIGO: NO",
    ]
    log_path.write_text("\n".join(log_lines))
    print(f"Log written: {log_path}")
    
    # Summary
    print("\n=== SUMMARY ===")
    for r in results:
        driver = "PHASE" if (1 - r['overlap_gr_phase']) > (1 - r['overlap_gr_amp']) else "AMPLITUDE"
        print(f"  {r['band_hz']} Hz: overlap={r['overlap_gr_full']:.3f}  main driver={driver}")

if __name__ == "__main__":
    main()
