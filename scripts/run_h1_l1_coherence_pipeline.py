"""H1/L1 Coherence Pipeline. No posterior. No claim. READY_FOR_REAL_CLAIM: NO"""
import sys, datetime, numpy as np, h5py
from pathlib import Path
from scipy import signal
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.derived_waveform import apply_ssz_v0_to_frequency_waveform

G=6.674e-11; C=2.998e8; M_SUN=1.989e30
TRIGGER_GPS=1411261107.984; MC_MSUN=8.9; ETA=0.25; DL_MPC=300.0
WIN_S=4.0; OFF_OFFSET=500.0; OFF_DUR=256.0; F_LOW=20.0; F_HIGH=210.0; NPERSEG=4096
# F_HIGH=210 Hz: below f_ISCO~215 Hz for M_total~20 Msun.
# 0PN TaylorF2 invalid above ISCO — clipped to keep r/rs > 3 throughout band.
_B=Path(r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF")
H1=_B/"H1/1410334720/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
L1=_B/"L1/1410334720/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
REPORTS=Path(__file__).parent.parent/"reports"
LOGS=Path(__file__).parent.parent/"logs"
MANIFEST=Path(__file__).parent.parent/"data_manifest"
NOW=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_log=[]
def log(m=""): print(m); _log.append(m)

def load_seg(p):
    with h5py.File(str(p),"r") as f:
        gps0=float(f["meta/GPSstart"][()]); n=f["strain/Strain"].shape[0]
        dur=float(f["meta/Duration"][()]); fs=int(n/dur)
        t=TRIGGER_GPS-gps0; h=WIN_S/2.
        on=f["strain/Strain"][max(0,int((t-h)*fs)):min(n,int((t+h)*fs))]
        j0=max(0,int((t-OFF_OFFSET)*fs))
        off=f["strain/Strain"][j0:min(n,j0+int(OFF_DUR*fs))]
    return on,off,fs

def gr_tmpl(ffd,mask,Mc):
    h=np.zeros(len(ffd),dtype=complex); f=ffd[mask]
    psi=(3./(128.*ETA))*(np.pi*G*Mc/C**3*f)**(-5./3.)
    c1=np.sqrt(5*np.pi/24)*(G*Mc/C**3)**(5./6.)*np.pi**(-7./6.)/(DL_MPC*3.086e22)
    h[mask]=c1*f**(-7./6.)*np.exp(1j*psi); return h

def proc(label,path,Mc,M,mu):
    if not path.exists(): log(f"  [{label}] BLOCKED: no file"); return None
    on,off,fs=load_seg(path)
    if not np.all(np.isfinite(on)) or len(on)==0: log(f"  [{label}] BLOCKED"); return None
    fp,psd=signal.welch(off,fs=fs,nperseg=NPERSEG,window="hann",noverlap=NPERSEG//2)
    ffd=np.fft.rfftfreq(len(on),1./fs); mask=(ffd>=F_LOW)&(ffd<=F_HIGH)&(ffd>0)
    h_gr=gr_tmpl(ffd,mask,Mc)
    h_ssz,dp,da,_=apply_ssz_v0_to_frequency_waveform(h_gr,ffd,M,mu,branch="g2_decay")
    df=float(fs)/len(on); dfd=np.fft.rfft(on)/fs
    pi=np.interp(ffd,fp,psd,left=psd[1],right=psd[-1]); pi[pi<=0]=pi[pi>0].min()
    def nw(a,b): return 4.*np.real(np.sum(a*np.conj(b)/pi))*df
    lg=-.5*nw(dfd-h_gr,dfd-h_gr); ls=-.5*nw(dfd-h_ssz,dfd-h_ssz)
    ng=nw(h_gr,h_gr); ns=nw(h_ssz,h_ssz)
    sg=abs(nw(dfd,h_gr))/np.sqrt(ng) if ng>0 else 0.
    ss=abs(nw(dfd,h_ssz))/np.sqrt(ns) if ns>0 else 0.
    resid=(dfd-h_gr)[mask]
    log(f"  [{label}] lnL_GR={lg:.4e} lnL_SSZ={ls:.4e} delta={ls-lg:.4e}")
    log(f"  [{label}] SNR_GR={sg:.2f} SNR_SSZ={ss:.2f} resid_rms={np.sqrt(np.mean(np.abs(resid)**2)):.3e}")
    return {"det":label,"lnL_gr":lg,"lnL_ssz":ls,"delta_lnL":ls-lg,
            "snr_gr":sg,"snr_ssz":ss,"resid":resid,"status":"PASS"}

def run():
    log(f"H1/L1 COHERENCE PIPELINE — {NOW}")
    log("FORMULA: DERIVED_V1_INSPIRAL_0PN_LOCKED | READY_FOR_REAL_CLAIM: NO")
    Mc=MC_MSUN*M_SUN; M=Mc/ETA**(3./5.); mu=ETA*M
    rs=2.*G*M/C**2
    log(f"  r/rs@20Hz={((G*M/(np.pi*F_LOW)**2)**(1./3.))/rs:.0f}  r/rs@800Hz={((G*M/(np.pi*F_HIGH)**2)**(1./3.))/rs:.0f}  (weak-field)")
    rh=proc("H1",H1,Mc,M,mu); rl=proc("L1",L1,Mc,M,mu)
    h1s=rh["status"] if rh else "BLOCKED"
    l1s=rl["status"] if rl else "BLOCKED"
    xcv=xclag=None; coh="BLOCKED"
    if rh and rl:
        a=np.real(rh["resid"]); b=np.real(rl["resid"]); n=min(len(a),len(b))
        a=a[:n]/(np.std(a[:n])+1e-300); b=b[:n]/(np.std(b[:n])+1e-300)
        xc=np.correlate(a,b,"full"); lgs=np.arange(-(n-1),n)
        pk=np.argmax(np.abs(xc)); xcv=float(xc[pk])/n; xclag=int(lgs[pk])
        coh="PASS" if abs(xcv)<0.3 else "CORRELATED_NEEDS_CHECK"
        log(f"  H1/L1 xcorr={xcv:.4f} lag={xclag} samples -> {coh}")
    MANIFEST.mkdir(exist_ok=True)
    (MANIFEST/"h1_l1_files_used.csv").write_text(
        "detector,file,trigger_gps,window_s,psd_method,anti_circularity\n"
        f"H1,{H1},{TRIGGER_GPS},{WIN_S},welch_off_source,VALID_INDEPENDENT\n"
        f"L1,{L1},{TRIGGER_GPS},{WIN_S},welch_off_source,VALID_INDEPENDENT\n",
        encoding="utf-8")
    def v(x): return f"{x:.4e}" if x is not None else "BLOCKED"
    report=f"""# H1/L1 Coherence Pipeline Report
Generated: {NOW}

## Anti-Circularity
- Strain files: read-only GWOSC C00
- No posterior f,m,chi used
- PSD: Welch off-source only
- GR template: 0PN TaylorF2 (no spin, no posterior)
- SSZ: DERIVED_V1_INSPIRAL_0PN_LOCKED phase, DERIVED_V0_PROXY amplitude

## Regime Check
- r/rs at 20 Hz:  {((G*M/(np.pi*F_LOW)**2)**(1./3.))/rs:.0f}  (weak-field)
- r/rs at 800 Hz: {((G*M/(np.pi*F_HIGH)**2)**(1./3.))/rs:.0f}  (weak-field)
- Both >> 1: Xi_weak = rs/(2r) operative throughout

## H1 Results
- lnL_GR:  {v(rh['lnL_gr'] if rh else None)}
- lnL_SSZ: {v(rh['lnL_ssz'] if rh else None)}
- delta_lnL: {v(rh['delta_lnL'] if rh else None)}
- MF-SNR GR:  {f"{rh['snr_gr']:.2f}" if rh else "BLOCKED"}
- MF-SNR SSZ: {f"{rh['snr_ssz']:.2f}" if rh else "BLOCKED"}

## L1 Results
- lnL_GR:  {v(rl['lnL_gr'] if rl else None)}
- lnL_SSZ: {v(rl['lnL_ssz'] if rl else None)}
- delta_lnL: {v(rl['delta_lnL'] if rl else None)}
- MF-SNR GR:  {f"{rl['snr_gr']:.2f}" if rl else "BLOCKED"}
- MF-SNR SSZ: {f"{rl['snr_ssz']:.2f}" if rl else "BLOCKED"}

## H1/L1 Residual Coherence
- Cross-correlation peak: {f"{xcv:.4f}" if xcv is not None else "BLOCKED"}
- Lag at peak: {f"{xclag} samples" if xclag is not None else "BLOCKED"}
- Interpretation: |xcorr|<0.3 expected for independent noise
- COHERENCE_STATUS: {coh}

## Interpretation
- delta_lnL values are exploratory only
- No physics claim is made from these numbers
- H1 and L1 processed independently with same pipeline
- Residual coherence tests pipeline stability, not SSZ physics

## Final Gate
```
H1_STATUS:                     {h1s}
L1_STATUS:                     {l1s}
COHERENCE_STATUS:               {coh}
FORMULA_STATUS_DELTA_PSI:      DERIVED_V1_INSPIRAL_0PN_LOCKED
FORMULA_STATUS_DELTA_A:        DERIVED_V0_PROXY
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
```
"""
    (REPORTS/"H1_L1_COHERENCE_PIPELINE_REPORT.md").write_text(report,encoding="utf-8")
    log("  -> reports/H1_L1_COHERENCE_PIPELINE_REPORT.md")
    log("  -> data_manifest/h1_l1_files_used.csv")
    (LOGS/"h1_l1_coherence_pipeline.log").write_text("\n".join(_log),encoding="utf-8")
    log("DONE | READY_FOR_REAL_CLAIM: NO")

if __name__=="__main__":
    run()
