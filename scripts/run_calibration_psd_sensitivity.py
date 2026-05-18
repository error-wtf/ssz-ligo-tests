"""Calibration/PSD Sensitivity Check.
Tests whether the SSZ V1 effect is smaller than calibration uncertainty.
No posterior. No fitting. No claim. READY_FOR_REAL_CLAIM: NO
"""
import sys, datetime, numpy as np, h5py
from pathlib import Path
from scipy import signal
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssz_ligo_tests.derived_waveform import apply_ssz_v0_to_frequency_waveform

G=6.674e-11; C=2.998e8; M_SUN=1.989e30
TRIGGER_GPS=1411261107.984; MC_MSUN=8.9; ETA=0.25; DL_MPC=300.0
WIN_S=4.0; OFF_OFFSET=500.0; OFF_DUR=256.0; F_LOW=20.0; F_HIGH=800.0; NPERSEG=4096
H1=Path(r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain"
        r"\GW240925-C00-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720"
        r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5")
REPORTS=Path(__file__).parent.parent/"reports"
LOGS=Path(__file__).parent.parent/"logs"
NOW=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_log=[]
def log(m=""): print(m); _log.append(m)

AMP_ENVELOPES=[0.0, 0.03, 0.05]       # fractional amplitude cal uncertainty
PHASE_ENVELOPES=[0.0, 0.01, 0.05]     # radians phase cal uncertainty
PSD_NPERSEG_VARIANTS=[2048, 4096, 8192]

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

def nwip(a,b,pi,df): return 4.*np.real(np.sum(a*np.conj(b)/pi))*df
def lnl(dfd,h,pi,df): return -.5*nwip(dfd-h,dfd-h,pi,df)

def run():
    log(f"CALIBRATION/PSD SENSITIVITY — {NOW}")
    log("READY_FOR_REAL_CLAIM: NO | No physics claim from sensitivity scan")
    if not H1.exists(): log("BLOCKED: H1 file not found"); return
    on,off,fs=load_seg(H1)
    if not np.all(np.isfinite(on)) or len(on)==0: log("BLOCKED: strain bad"); return
    Mc=MC_MSUN*M_SUN; M=Mc/ETA**(3./5.); mu=ETA*M
    ffd=np.fft.rfftfreq(len(on),1./fs); mask=(ffd>=F_LOW)&(ffd<=F_HIGH)&(ffd>0)
    dfd=np.fft.rfft(on)/fs; df=float(fs)/len(on)
    h_gr=gr_tmpl(ffd,mask,Mc)
    h_ssz,dp,da,_=apply_ssz_v0_to_frequency_waveform(h_gr,ffd,M,mu,branch="g2_decay")
    # Nominal PSD
    fp,psd_nom=signal.welch(off,fs=fs,nperseg=NPERSEG,window="hann",noverlap=NPERSEG//2)
    pi_nom=np.interp(ffd,fp,psd_nom,left=psd_nom[1],right=psd_nom[-1]); pi_nom[pi_nom<=0]=pi_nom[pi_nom>0].min()
    lnl_gr_nom=lnl(dfd,h_gr,pi_nom,df); lnl_ssz_nom=lnl(dfd,h_ssz,pi_nom,df)
    dl_nom=lnl_ssz_nom-lnl_gr_nom
    log(f"  Nominal: lnL_GR={lnl_gr_nom:.4e} lnL_SSZ={lnl_ssz_nom:.4e} delta={dl_nom:.4e}")

    rows=[]; rows.append("scan_type,param,delta_lnL,delta_vs_nominal,interpretation")

    # 1. Amplitude calibration envelope
    log("  -- Amplitude calibration scan --")
    for amp_err in AMP_ENVELOPES:
        for sign in ([1.] if amp_err==0. else [1.,-1.]):
            h_cal=(1.+sign*amp_err)*h_ssz
            dl=lnl(dfd,h_cal,pi_nom,df)-lnl(dfd,h_gr,pi_nom,df)
            diff=dl-dl_nom
            interp="WITHIN_NOMINAL" if abs(diff)<abs(dl_nom)*10+1e-10 else "EXCEEDS_NOMINAL"
            log(f"    amp_cal={sign*amp_err:+.2f}: delta_lnL={dl:.4e} diff_vs_nom={diff:.4e} -> {interp}")
            rows.append(f"amp_cal,{sign*amp_err:+.3f},{dl:.6e},{diff:.6e},{interp}")

    # 2. Phase calibration envelope
    log("  -- Phase calibration scan --")
    for ph_err in PHASE_ENVELOPES:
        for sign in ([1.] if ph_err==0. else [1.,-1.]):
            h_cal=h_ssz*np.exp(1j*sign*ph_err)
            dl=lnl(dfd,h_cal,pi_nom,df)-lnl(dfd,h_gr,pi_nom,df)
            diff=dl-dl_nom
            interp="WITHIN_NOMINAL" if abs(diff)<abs(dl_nom)*10+1e-10 else "EXCEEDS_NOMINAL"
            log(f"    phase_cal={sign*ph_err:+.3f} rad: delta_lnL={dl:.4e} diff={diff:.4e} -> {interp}")
            rows.append(f"phase_cal,{sign*ph_err:+.3f},{dl:.6e},{diff:.6e},{interp}")

    # 3. PSD Welch setting variants
    log("  -- PSD Welch variant scan --")
    psd_results={}
    for nps in PSD_NPERSEG_VARIANTS:
        fp2,psd2=signal.welch(off,fs=fs,nperseg=nps,window="hann",noverlap=nps//2)
        pi2=np.interp(ffd,fp2,psd2,left=psd2[1],right=psd2[-1]); pi2[pi2<=0]=pi2[pi2>0].min()
        dl=lnl(dfd,h_ssz,pi2,df)-lnl(dfd,h_gr,pi2,df)
        diff=dl-dl_nom
        interp="WITHIN_NOMINAL" if abs(diff)<abs(dl_nom)*10+1e-10 else "EXCEEDS_NOMINAL"
        log(f"    nperseg={nps}: delta_lnL={dl:.4e} diff={diff:.4e} -> {interp}")
        rows.append(f"psd_welch,nperseg={nps},{dl:.6e},{diff:.6e},{interp}")
        psd_results[nps]=dl

    # 4. Assess SSZ effect vs calibration
    ssz_effect=abs(dl_nom)
    max_cal_spread=max(abs(float(r.split(",")[2])-dl_nom)
                       for r in rows[1:] if r.startswith("amp_cal") or r.startswith("phase_cal"))
    if ssz_effect<max_cal_spread:
        above="NO — SSZ effect smaller than calibration spread"
    elif ssz_effect>10*max_cal_spread:
        above="YES — SSZ effect exceeds calibration spread"
    else:
        above="UNKNOWN — SSZ effect comparable to calibration spread"
    log(f"  SSZ_EFFECT={ssz_effect:.4e} CAL_SPREAD={max_cal_spread:.4e}")
    log(f"  SSZ_EFFECT_ABOVE_CALIBRATION: {above}")

    (LOGS/"calibration_psd_sensitivity.log").write_text("\n".join(_log),encoding="utf-8")

    report=f"""# Calibration/PSD Sensitivity Report
Generated: {NOW}

## Purpose
Check whether the SSZ V1 inspiral effect is distinguishable from
calibration and PSD estimation uncertainty.
No physics claim is made. READY_FOR_REAL_CLAIM: NO

## Nominal Result
| Model | lnL | delta_lnL |
|-------|-----|-----------|
| GR control 0PN | {lnl_gr_nom:.4e} | — |
| SSZ V1 0PN | {lnl_ssz_nom:.4e} | {dl_nom:.4e} |

## Amplitude Calibration Scan (±3%, ±5%)
| amp_error | delta_lnL | diff_vs_nominal |
|-----------|-----------|-----------------|
""" + "\n".join(f"| {r.split(',')[1]} | {r.split(',')[2]} | {r.split(',')[3]} |"
                for r in rows[1:] if r.startswith("amp_cal")) + f"""

## Phase Calibration Scan (±0.01 rad, ±0.05 rad)
| phase_error | delta_lnL | diff_vs_nominal |
|-------------|-----------|-----------------|
""" + "\n".join(f"| {r.split(',')[1]} | {r.split(',')[2]} | {r.split(',')[3]} |"
                for r in rows[1:] if r.startswith("phase_cal")) + f"""

## PSD Welch Variant Scan
| nperseg | delta_lnL | diff_vs_nominal |
|---------|-----------|-----------------|
""" + "\n".join(f"| {r.split(',')[1]} | {r.split(',')[2]} | {r.split(',')[3]} |"
                for r in rows[1:] if r.startswith("psd_welch")) + f"""

## Sensitivity Assessment
- SSZ effect |delta_lnL|: {ssz_effect:.4e}
- Max calibration spread: {max_cal_spread:.4e}
- SSZ_EFFECT_ABOVE_CALIBRATION: {above}

## Final Gate
```
SSZ_EFFECT_ABOVE_CALIBRATION:  {above}
CALIBRATION_SCAN:              COMPLETE
PSD_VARIANT_SCAN:              COMPLETE
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE:        NO
SSZ_FALSIFICATION_CLAIM_MADE:  NO
```
"""
    (REPORTS/"CALIBRATION_PSD_SENSITIVITY_REPORT.md").write_text(report,encoding="utf-8")
    log("  -> reports/CALIBRATION_PSD_SENSITIVITY_REPORT.md")

if __name__=="__main__":
    run()
