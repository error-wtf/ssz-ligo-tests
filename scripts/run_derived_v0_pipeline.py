"""SSZ Derived-V0 Strain Pipeline (DERIVED_V0_PROXY).
HARD RULES: no posterior, no fitting, no physics claim.
"""
import sys, datetime, numpy as np, h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.derived_waveform import apply_ssz_v0_to_frequency_waveform
from ssz_ligo_tests.anti_circularity import classify_observable_source, CircularityStatus

G=6.674e-11; C=2.998e8; M_SUN=1.989e30
TRIGGER_GPS=1411261107.984; MC_MSUN=8.9; ETA=0.25; DL_MPC=300.0
WIN_S=4.0; OFFSOURCE_OFFSET_S=500.0; OFFSOURCE_DUR_S=256.0
F_LOW=20.0; F_HIGH=800.0; PSD_NPERSEG=4096

H1_STRAIN = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720"
    r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)
REPORTS=Path(__file__).parent.parent/"reports"
LOGS=Path(__file__).parent.parent/"logs"
NOW=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_log=[]

def log(m=""): print(m); _log.append(m)
def flush(): (LOGS/"derived_v0_pipeline.log").write_text("\n".join(_log),encoding="utf-8")

def run():
    log(f"SSZ DERIVED-V0 PIPELINE — {NOW}")
    log("FORMULA_STATUS: DERIVED_V0_PROXY | READY_FOR_REAL_CLAIM: NO")

    s = classify_observable_source("H1/strain")
    if s == CircularityStatus.INVALID:
        log("BLOCKED: anti-circularity violation"); flush(); return

    if not H1_STRAIN.exists():
        log("BLOCKED: strain file not found"); flush(); return

    with h5py.File(str(H1_STRAIN),'r') as f:
        gps0=float(f['meta/GPSstart'][()]); dur=float(f['meta/Duration'][()])
        n=f['strain/Strain'].shape[0]; fs=int(n/dur)
        t_ev=TRIGGER_GPS-gps0; half=WIN_S/2.0
        i0=max(0,int((t_ev-half)*fs)); i1=min(n,int((t_ev+half)*fs))
        strain=f['strain/Strain'][i0:i1]
        t_off=TRIGGER_GPS-gps0-OFFSOURCE_OFFSET_S
        j0=max(0,int(t_off*fs)); j1=min(n,j0+int(OFFSOURCE_DUR_S*fs))
        offsrc=f['strain/Strain'][j0:j1]

    if not np.all(np.isfinite(strain)) or len(strain)==0:
        log("BLOCKED: strain not finite"); flush(); return

    freqs_psd,psd=signal.welch(offsrc,fs=fs,nperseg=PSD_NPERSEG,window='hann',noverlap=PSD_NPERSEG//2)
    log(f"  strain: {len(strain)} samples @ {fs} Hz | PSD bins: {len(freqs_psd)}")

    Mc_kg=MC_MSUN*M_SUN; M_kg=Mc_kg/ETA**(3./5.); mu_kg=ETA*M_kg
    dL_m=DL_MPC*3.086e22

    ffd=np.fft.rfftfreq(len(strain),1./fs)
    mask=(ffd>=F_LOW)&(ffd<=F_HIGH)&(ffd>0)
    h_gr=np.zeros(len(ffd),dtype=complex)
    f=ffd[mask]
    x=np.pi*G*Mc_kg/C**3*f
    psi=(3./(128.*ETA))*x**(-5./3.)
    c1=np.sqrt(5*np.pi/24)*(G*Mc_kg/C**3)**(5./6.)*np.pi**(-7./6.)/dL_m
    h_gr[mask]=c1*f**(-7./6.)*np.exp(1j*psi)

    h_ssz,dp,da,meta=apply_ssz_v0_to_frequency_waveform(h_gr,ffd,M_kg,mu_kg,branch="g2_decay")

    log(f"  deltaPsi band: min={dp[mask].min():.4e} max={dp[mask].max():.4e} median={np.median(dp[mask]):.4e} rad")
    log(f"  deltaA   band: min={da[mask].min():.4e} max={da[mask].max():.4e} median={np.median(da[mask]):.4e}")

    N=len(strain); df=float(fs)/N
    dfd_f=np.fft.rfft(strain)/fs
    pi=np.interp(ffd,freqs_psd,psd,left=psd[1],right=psd[-1])
    pi[pi<=0]=pi[pi>0].min()
    def nwip(a,b): return 4.*np.real(np.sum(a*np.conj(b)/pi))*df
    lnL_gr=-0.5*nwip(dfd_f-h_gr,dfd_f-h_gr)
    lnL_ssz=-0.5*nwip(dfd_f-h_ssz,dfd_f-h_ssz)
    delta_lnL=lnL_ssz-lnL_gr
    nn_gr=nwip(h_gr,h_gr); nn_ssz=nwip(h_ssz,h_ssz)
    snr_gr=abs(nwip(dfd_f,h_gr))/np.sqrt(nn_gr) if nn_gr>0 else 0.
    snr_ssz=abs(nwip(dfd_f,h_ssz))/np.sqrt(nn_ssz) if nn_ssz>0 else 0.

    log(f"  lnL_GR={lnL_gr:.4e}  lnL_SSZ={lnL_ssz:.4e}  delta_lnL={delta_lnL:.4e}")
    log(f"  MF-SNR GR={snr_gr:.2f}  MF-SNR SSZ={snr_ssz:.2f}")

    if abs(delta_lnL)<1.:
        interp="DERIVED_V0_PROXY_INDISTINGUISHABLE_FROM_GR_CONTROL"
    elif delta_lnL>0:
        interp="DERIVED_V0_PROXY_NUMERICALLY_DISTINCT_BUT_NO_PHYSICS_CLAIM"
    else:
        interp="DERIVED_V0_PROXY_NUMERICALLY_DISTINCT_BUT_NO_PHYSICS_CLAIM"
    log(f"  INTERPRETATION: {interp}")

    report="""# Derived-V0 Strain Pipeline Report
Generated: {NOW}

## Formula Status
- deltaPsi: DERIVED_V0_PROXY (rdot_SSZ=rdot_GR*D^2/s^4, SSZ Book Ch.31)
- deltaA:   DERIVED_V0_PROXY (D^2-1 from P_GW ratio)
- h_SSZ:    DERIVED_V0_PROXY = h_GR*(1+deltaA)*exp(i*deltaPsi)
- branch:   g2_decay (operative per formula_compendium.md)

## Parameters
- M_total: {M_kg/M_SUN:.2f} Msun | mu: {mu_kg/M_SUN:.2f} Msun | rs: {rs_m/1e3:.2f} km
- r/rs at 20 Hz: {((G*M_kg/(np.pi*F_LOW)**2)**(1./3.))/rs_m:.1f}
- r/rs at 800 Hz: {((G*M_kg/(np.pi*F_HIGH)**2)**(1./3.))/rs_m:.1f}

## deltaPsi [{F_LOW}-{F_HIGH} Hz]
- min: {dp[mask].min():.4e} rad
- max: {dp[mask].max():.4e} rad
- median: {np.median(dp[mask]):.4e} rad

## deltaA [{F_LOW}-{F_HIGH} Hz]
- min: {da[mask].min():.4e}
- max: {da[mask].max():.4e}
- median: {np.median(da[mask]):.4e}

## Likelihood
| Model | lnL | MF-SNR |
|-------|-----|--------|
| GR control (0PN) | {lnL_gr:.4e} | {snr_gr:.2f} |
| SSZ derived-V0   | {lnL_ssz:.4e} | {snr_ssz:.2f} |

delta_lnL = {delta_lnL:.4e}

## Interpretation
{interp}

## Final Gate
```
DELTA_PSI_STATUS: DERIVED_V0_PROXY
DELTA_A_STATUS: DERIVED_V0_PROXY
H_SSZ_STATUS: DERIVED_V0_PROXY
EPSILON_220_STATUS: BLOCKED_BRANCH_CONFLICT
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
```
"""
    (REPORTS/"DERIVED_V0_STRAIN_PIPELINE_REPORT.md").write_text(report,encoding="utf-8")
    log("  Report: reports/DERIVED_V0_STRAIN_PIPELINE_REPORT.md")
    log("FINAL: PASS_DERIVED_V0_PIPELINE | READY_FOR_REAL_CLAIM: NO")
    flush()

if __name__=="__main__":
    run()
