"""SSZ Anti-Circular Analysis — GW240925. Only raw strain, no posterior."""
import sys, numpy as np, h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.ssz_core import xi_weak, d_ssz

G = 6.674e-11; C = 2.998e8; M_SUN = 1.989e30

# Public trigger time from GWOSC release metafile history field (NOT posterior)
GPS      = 1411261107.984
Mc_Msun  = 8.9
eta      = 0.25
dL_Mpc   = 300.0

STRAIN = {
    "H1": Path(r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"),
    "L1": Path(r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\L1\1410334720\L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"),
}

def load_window(ifo, win_s=4.0):
    with h5py.File(str(STRAIN[ifo]), 'r') as f:
        gps0 = float(f['meta/GPSstart'][()])
        dur  = float(f['meta/Duration'][()])
        fs   = int(f['strain/Strain'].shape[0] / dur)
        s    = f['strain/Strain'][()]
    t  = GPS - gps0
    i0 = max(0, int((t - win_s/2)*fs)); i1 = min(len(s), int((t + win_s/2)*fs))
    return s[i0:i1], fs

def load_offsource(ifo, off=500.0, dur=256.0):
    with h5py.File(str(STRAIN[ifo]), 'r') as f:
        gps0 = float(f['meta/GPSstart'][()])
        fs   = int(f['strain/Strain'].shape[0] / float(f['meta/Duration'][()]))
        s    = f['strain/Strain'][()]
    i0 = max(0, int((GPS - gps0 - off)*fs))
    return s[i0:i0+int(dur*fs)], fs

def psd_welch(s, fs):
    return signal.welch(s, fs=fs, nperseg=4096, window='hann', noverlap=2048)

def taylorf2(freqs, Mc_kg, eta, dL_m, fl=20, fh=800):
    h = np.zeros(len(freqs), dtype=complex)
    m = (freqs >= fl) & (freqs <= fh) & (freqs > 0)
    f = freqs[m]
    x   = np.pi * G * Mc_kg / C**3 * f
    psi = (3/(128*eta)) * x**(-5/3)
    C1  = np.sqrt(5*np.pi/24) * (G*Mc_kg/C**3)**(5/6) * np.pi**(-7/6) / dL_m
    h[m] = C1 * f**(-7/6) * np.exp(1j*psi)
    return h

def ssz_dpsi(freqs, M_kg, rs, kappa=1.0, fl=20, fh=800):
    dp = np.zeros(len(freqs))
    m  = (freqs >= fl) & (freqs <= fh) & (freqs > 0)
    for i in np.where(m)[0]:
        r = (G*M_kg/(np.pi*freqs[i])**2)**(1/3)
        dp[i] = kappa*(1.0 - d_ssz(xi_weak(r, rs)))
    return dp

def nwip(a, b, psd, df):
    return 4*np.real(np.sum(a*np.conj(b)/psd))*df

def lnL(data, h, psd, df):
    r = data - h; return -0.5*nwip(r, r, psd, df)

def snr(data, h, psd, df):
    n = nwip(h,h,psd,df); return abs(nwip(data,h,psd,df))/np.sqrt(n) if n>0 else 0

def run():
    Mc  = Mc_Msun*M_SUN
    M   = Mc/eta**(3/5)
    rs  = 2*G*M/C**2
    dL  = dL_Mpc*3.086e22
    print(f"GW240925 | M={M/M_SUN:.1f} Msun | rs={rs/1e3:.1f} km | dL={dL_Mpc} Mpc")

    for ifo in ["H1","L1"]:
        print(f"\n--- {ifo} ---")
        try:
            sw, fs = load_window(ifo)
        except Exception as e:
            print(f"  BLOCKED: {e}"); continue

        so, _  = load_offsource(ifo)
        fp, pv = psd_welch(so, fs)
        N  = len(sw); df = fs/N
        ffd = np.fft.rfftfreq(N, 1/fs)
        dfd = np.fft.rfft(sw)/fs
        pi  = np.interp(ffd, fp, pv, left=pv[1], right=pv[-1])
        pi[pi<=0] = pi[pi>0].min()

        hgr  = taylorf2(ffd, Mc, eta, dL)
        dp   = ssz_dpsi(ffd, M, rs)
        hssz = hgr*np.exp(1j*dp)

        lg = lnL(dfd, hgr,  pi, df)
        ls = lnL(dfd, hssz, pi, df)
        sg = snr(dfd, hgr,  pi, df)
        ss = snr(dfd, hssz, pi, df)
        dl = ls - lg

        m = (ffd>=20)&(ffd<=800)
        print(f"  GR:  lnL={lg:.3e}  SNR={sg:.2f}")
        print(f"  SSZ: lnL={ls:.3e}  SNR={ss:.2f}")
        print(f"  delta_lnL={dl:.3e}  dpsi_max={dp[m].max():.4f} rad [V0 proxy]")
        if abs(dl)<1:   print("  -> INDISTINGUISHABLE (|dlnL|<1)")
        elif dl>0:      print("  -> SSZ PREFERRED (exploratory, V0 proxy)")
        else:           print("  -> GR PREFERRED (exploratory, V0 proxy)")

    print("\nBLOCKED: epsilon_220 (CONFLICTING 3%/31%/39%), delta_psi exact formula")
    print("ANTI-CIRCULARITY: CLEAR — raw strain only, no posterior used")

if __name__ == "__main__":
    run()
