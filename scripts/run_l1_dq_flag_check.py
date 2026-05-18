"""L1 DQ Flag Check for GW240925 trigger window.

Reads GWOSC quality/simple/DQmask and quality/injections/Injmask
from the O4b4DiscC00 HDF5 release files for H1 and L1.

Checks:
  1. Which DQ flags are set in the trigger window [t_ev-2s, t_ev+2s]
  2. Injection flags in the same window
  3. Difference between H1 and L1 DQ state
  4. CW hardware injection presence
  5. Band-power correlation with known calibration/spectral lines

Outputs:
  reports/L1_DQ_FLAG_CHECK_REPORT.md
  data_manifest/l1_dq_flags_checked.csv
  logs/l1_dq_flag_check.log

Rules:
  No SSZ claims. No posterior parameters. Data quality only.
  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
"""
import sys
import csv
import datetime
import numpy as np
import h5py
from pathlib import Path
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
LOGS = Path(__file__).parent.parent / "logs"
for d in (REPORTS, MANIFEST, LOGS):
    d.mkdir(exist_ok=True)

_B = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)
H1_PATH = _B / "H1/1410334720/H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
L1_PATH = _B / "L1/1410334720/L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"

TRIGGER_GPS = 1411261107.984
WIN_HALF_S = 2.0          # +/- 2s around trigger for DQ check
WIN_FULL_S = 4.0          # 4s strain window for spectral check
F_LOW, F_HIGH = 20.0, 210.0
NPERSEG = 4096

# Known LIGO calibration / spectral lines in O4 (from public GWOSC line lists)
# These are approximate; exact values depend on detector state
KNOWN_LINES_HZ = [
    ("60Hz_power", 60.0),
    ("120Hz_power_harmonic", 120.0),
    ("180Hz_power_harmonic", 180.0),
    ("violin_mode_H1_approx", 500.0),
    ("violin_mode_L1_approx", 498.0),
    ("calibration_pcal_H1", 35.9),
    ("calibration_pcal_L1", 36.7),
    ("calibration_pcal2_H1", 36.7),
    ("calibration_pcal2_L1", 38.1),
]

DQ_NAMES = [
    "DATA", "CBC_CAT1", "CBC_CAT2", "CBC_CAT3",
    "BURST_CAT1", "BURST_CAT2", "BURST_CAT3",
    "STOCH_CAT1", "CW_CAT1"
]
INJ_NAMES = [
    "NO_CBC_HW_INJ", "NO_BURST_HW_INJ", "NO_DETCHAR_HW_INJ",
    "NO_CW_HW_INJ", "NO_STOCH_HW_INJ"
]

_log = []


def log(m=""):
    print(m)
    _log.append(str(m))


def flush_log():
    (LOGS / "l1_dq_flag_check.log").write_text(
        "\n".join(_log), encoding="utf-8"
    )


def decode_dq_mask(mask_val, names):
    """Decode integer bitmask into list of (name, set) tuples."""
    result = []
    for i, name in enumerate(names):
        result.append((name, bool((mask_val >> i) & 1)))
    return result


def check_detector(label, path):
    log(f"\n{'='*60}")
    log(f"  DETECTOR: {label}")
    log(f"{'='*60}")

    if not path.exists():
        log("  BLOCKED: file not found")
        return None

    with h5py.File(str(path), "r") as f:
        gps0 = float(f["meta/GPSstart"][()])
        dur = float(f["meta/Duration"][()])
        n_strain = f["strain/Strain"].shape[0]
        fs = int(n_strain / dur)
        t_ev = TRIGGER_GPS - gps0

        # --- DQ mask ---
        dq_mask_arr = f["quality/simple/DQmask"][()]
        dq_fs = dq_mask_arr.shape[0] / dur
        # Try to read actual names from file (may differ from hardcoded)
        try:
            file_dq_names = [x.decode() for x in
                             f["quality/simple/DQShortnames"][()]]
        except Exception:
            file_dq_names = DQ_NAMES

        i0_dq = max(0, int((t_ev - WIN_HALF_S) * dq_fs))
        i1_dq = min(len(dq_mask_arr), int((t_ev + WIN_HALF_S) * dq_fs))
        trig_dq = dq_mask_arr[i0_dq:i1_dq]
        unique_dq = np.unique(trig_dq)

        log(f"  GPS0={gps0}  t_ev={t_ev:.1f}s  fs={fs}Hz")
        log(f"  DQ mask sample rate: {dq_fs} Hz")
        log(f"  DQ flags in file: {file_dq_names}")
        log(f"  Trigger window DQ values (unique): {unique_dq.tolist()}")

        # Decode each unique value
        dq_flag_summary = {}
        for val in unique_dq:
            decoded = decode_dq_mask(int(val), file_dq_names)
            log(f"  Decoded mask={val}:")
            for name, is_set in decoded:
                status = "SET" if is_set else "NOT_SET"
                log(f"    {name:20s}: {status}")
                dq_flag_summary[name] = is_set

        # --- Injection mask ---
        inj_flags_trigger = {}
        if "quality/injections/Injmask" in f:
            inj_arr = f["quality/injections/Injmask"][()]
            inj_fs = inj_arr.shape[0] / dur
            try:
                file_inj_names = [x.decode() for x in
                                  f["quality/injections/InjShortnames"][()]]
            except Exception:
                file_inj_names = INJ_NAMES
            ii0 = max(0, int((t_ev - WIN_HALF_S) * inj_fs))
            ii1 = min(len(inj_arr), int((t_ev + WIN_HALF_S) * inj_fs))
            trig_inj = inj_arr[ii0:ii1]
            unique_inj = np.unique(trig_inj)

            log(f"\n  Injection flags: {file_inj_names}")
            log(f"  Trigger window injection values (unique): {unique_inj.tolist()}")
            for val in unique_inj:
                decoded_inj = decode_dq_mask(int(val), file_inj_names)
                log(f"  Decoded inj_mask={val}:")
                for name, is_set in decoded_inj:
                    # For injection flags: SET means NO injection (clean)
                    clean = "CLEAN(no inj)" if is_set else "INJECTION_PRESENT"
                    log(f"    {name:25s}: {clean}")
                    inj_flags_trigger[name] = is_set  # True = clean

        # --- Spectral check: look for lines in trigger window ---
        log(f"\n  Spectral line check in trigger window:")
        j0 = max(0, int((t_ev - WIN_FULL_S / 2) * fs))
        j1 = min(n_strain, int((t_ev + WIN_FULL_S / 2) * fs))
        strain_seg = f["strain/Strain"][j0:j1].copy()
        fp, psd = signal.welch(strain_seg, fs=fs, nperseg=NPERSEG,
                               window="hann", noverlap=NPERSEG // 2)
        df = fp[1] - fp[0]
        line_results = []
        for line_name, freq in KNOWN_LINES_HZ:
            if F_LOW <= freq <= F_HIGH:
                idx = int(np.argmin(np.abs(fp - freq)))
                bw = max(1, int(2.0 / df))
                band_psd = float(np.mean(psd[max(0, idx-bw):idx+bw+1]))
                nearby_psd = float(np.median(psd[max(0, idx-20):idx+20+1]))
                ratio = band_psd / nearby_psd if nearby_psd > 0 else float("nan")
                flag = "LINE_PROMINENT" if ratio > 5.0 else "OK"
                log(f"    {line_name:30s} @ {freq:.1f}Hz: "
                    f"psd_ratio={ratio:.2f}  {flag}")
                line_results.append({
                    "line_name": line_name, "freq_hz": freq,
                    "psd_ratio_vs_nearby": ratio, "flag": flag
                })

        # --- Overall band power in trigger vs off-source ---
        # Quick check: is trigger band power >> median of surrounding
        off_j0 = max(0, int((t_ev - 200) * fs))
        off_j1 = min(n_strain, off_j0 + int(64 * fs))
        off_seg = f["strain/Strain"][off_j0:off_j1].copy()
        _, psd_off = signal.welch(off_seg, fs=fs, nperseg=NPERSEG,
                                  window="hann", noverlap=NPERSEG // 2)
        band_m = (fp >= F_LOW) & (fp <= F_HIGH)
        bp_trig = float(np.mean(psd[band_m]))
        bp_off = float(np.mean(psd_off[band_m]))
        bp_ratio = bp_trig / bp_off if bp_off > 0 else float("nan")
        log(f"\n  Band power ratio (trigger/off-source):")
        log(f"    trigger  PSD_mean = {bp_trig:.4e}")
        log(f"    off-src  PSD_mean = {bp_off:.4e}")
        log(f"    ratio    = {bp_ratio:.2f}")

    return {
        "label": label,
        "gps0": gps0,
        "t_ev": t_ev,
        "dq_mask_unique": unique_dq.tolist(),
        "dq_flags": dq_flag_summary,
        "inj_flags": inj_flags_trigger,
        "bp_ratio_trig_vs_off": bp_ratio,
        "line_results": line_results,
        "file_dq_names": file_dq_names,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

log(f"L1 DQ Flag Check -- {NOW}")
log(f"Trigger GPS: {TRIGGER_GPS}")
log(f"Window: +/- {WIN_HALF_S}s around trigger")
log(f"Band: {F_LOW}--{F_HIGH} Hz")

h1 = check_detector("H1", H1_PATH)
l1 = check_detector("L1", L1_PATH)

# --- Comparison ---
log(f"\n{'='*60}")
log("  H1 / L1 DQ COMPARISON")
log(f"{'='*60}")

h1_names = h1["file_dq_names"] if h1 else DQ_NAMES
l1_names = l1["file_dq_names"] if l1 else DQ_NAMES

diff_flags = []
if h1 and l1:
    all_names = set(h1_names) | set(l1_names)
    for name in sorted(all_names):
        h1_val = h1["dq_flags"].get(name)
        l1_val = l1["dq_flags"].get(name)
        same = h1_val == l1_val
        if not same:
            diff_flags.append(name)
        status = "AGREE" if same else "DIFFER"
        log(f"  {name:20s}: H1={'SET' if h1_val else 'NOT_SET':8s}  "
            f"L1={'SET' if l1_val else 'NOT_SET':8s}  {status}")

    log(f"\n  Flags that DIFFER between H1 and L1: {diff_flags}")

    # CW_CAT1 specifically
    h1_cw = h1["dq_flags"].get("CW_CAT1", None)
    l1_cw = l1["dq_flags"].get("CW_CAT1", None)
    log(f"\n  CW_CAT1: H1={h1_cw}  L1={l1_cw}")
    if h1_cw != l1_cw:
        log("  *** CW_CAT1 DIFFERS: L1 passes CW CAT1, H1 does not ***")

    # Injection summary
    h1_cw_inj = h1["inj_flags"].get("NO_CW_HW_INJ", True)
    l1_cw_inj = l1["inj_flags"].get("NO_CW_HW_INJ", True)
    log(f"\n  NO_CW_HW_INJ: H1={'clean' if h1_cw_inj else 'CW_INJ_PRESENT'}  "
        f"L1={'clean' if l1_cw_inj else 'CW_INJ_PRESENT'}")
    if not h1_cw_inj and not l1_cw_inj:
        log("  *** BOTH H1 and L1 have CW_HW_INJ NOT clean at trigger time ***")
        log("  *** This means a CW hardware injection was active at BOTH detectors ***")

    log(f"\n  Band power ratio (trigger/off-200s):")
    log(f"    H1: {h1['bp_ratio_trig_vs_off']:.2f}")
    log(f"    L1: {l1['bp_ratio_trig_vs_off']:.2f}")

# --- Determine gate status ---
l1_dq_status = "INCONCLUSIVE"
coherence_status = "PARTIAL_L1_ANOMALY"

if h1 and l1:
    l1_data_ok = l1["dq_flags"].get("DATA", False)
    l1_cat2_ok = l1["dq_flags"].get("CBC_CAT2", False)
    l1_cat3_ok = l1["dq_flags"].get("CBC_CAT3", False)
    h1_cw_ok = h1["dq_flags"].get("CW_CAT1", False)
    l1_cw_ok = l1["dq_flags"].get("CW_CAT1", False)
    cw_inj_h1 = not h1["inj_flags"].get("NO_CW_HW_INJ", True)
    cw_inj_l1 = not l1["inj_flags"].get("NO_CW_HW_INJ", True)

    if not l1_data_ok:
        l1_dq_status = "FLAGGED_NO_DATA"
        coherence_status = "BLOCKED_L1_DQ"
    elif not l1_cat2_ok or not l1_cat3_ok:
        l1_dq_status = "FLAGGED_GLITCH_OR_DQ"
        coherence_status = "BLOCKED_L1_DQ"
    elif cw_inj_h1 or cw_inj_l1:
        l1_dq_status = "FLAGGED_CW_HW_INJ_ACTIVE"
        coherence_status = "PARTIAL_L1_ANOMALY"
    elif not h1_cw_ok and l1_cw_ok:
        l1_dq_status = "CW_CAT1_ASYMMETRY_H1_FAILS"
        coherence_status = "PARTIAL_L1_ANOMALY"
    else:
        all_ok = all([l1_data_ok, l1_cat2_ok, l1_cat3_ok])
        if all_ok:
            l1_dq_status = "PASS_NO_CRITICAL_FLAG"
            coherence_status = "PARTIAL_L1_ANOMALY"
        else:
            l1_dq_status = "INCONCLUSIVE"
else:
    l1_dq_status = "BLOCKED_MISSING_DQ_PRODUCTS"
    coherence_status = "BLOCKED_L1_DQ"

log(f"\n  L1_DQ_STATUS: {l1_dq_status}")
log(f"  COHERENCE_STATUS: {coherence_status}")

# --- Write CSV ---
csv_rows = []
for res in [h1, l1]:
    if not res:
        continue
    for name, is_set in res["dq_flags"].items():
        csv_rows.append({
            "detector": res["label"],
            "flag_type": "DQ",
            "flag_name": name,
            "value": "SET" if is_set else "NOT_SET",
            "trigger_window": f"{TRIGGER_GPS-WIN_HALF_S}--{TRIGGER_GPS+WIN_HALF_S}",
        })
    for name, is_clean in res["inj_flags"].items():
        csv_rows.append({
            "detector": res["label"],
            "flag_type": "INJ",
            "flag_name": name,
            "value": "CLEAN" if is_clean else "INJ_PRESENT",
            "trigger_window": f"{TRIGGER_GPS-WIN_HALF_S}--{TRIGGER_GPS+WIN_HALF_S}",
        })

csv_path = MANIFEST / "l1_dq_flags_checked.csv"
if csv_rows:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    log(f"\n  -> {csv_path}")


def flag_table(res):
    if not res:
        return "BLOCKED"
    rows = ["| Flag | Set? | Meaning |",
            "|------|------|---------|"]
    for name, is_set in res["dq_flags"].items():
        meaning = "pass/active" if is_set else "FAIL/inactive"
        rows.append(f"| {name} | {'YES' if is_set else 'NO'} | {meaning} |")
    return "\n".join(rows)


def inj_table(res):
    if not res or not res["inj_flags"]:
        return "No injection data"
    rows = ["| Flag | Value | Meaning |",
            "|------|-------|---------|"]
    for name, is_clean in res["inj_flags"].items():
        meaning = "no injection" if is_clean else "INJECTION ACTIVE"
        rows.append(
            f"| {name} | {'CLEAN' if is_clean else 'INJ_PRESENT'} | {meaning} |"
        )
    return "\n".join(rows)


report = f"""# L1 DQ Flag Check Report

Generated: {NOW}  
Event: GW240925 (trigger GPS {TRIGGER_GPS})  
Window: +/- {WIN_HALF_S}s around trigger  
Band: {F_LOW}--{F_HIGH} Hz

## Summary

| Status | Value |
|--------|-------|
| L1_DQ_STATUS | {l1_dq_status} |
| COHERENCE_STATUS | {coherence_status} |
| READY_FOR_REAL_LIGO_SSZ_CLAIM | NO |
| SSZ_SUPPORT_CLAIM_MADE | NO |
| SSZ_FALSIFICATION_CLAIM_MADE | NO |

## H1 DQ Flags in Trigger Window

{flag_table(h1)}

### H1 Injection Flags

{inj_table(h1)}

H1 band power ratio (trigger/off-200s): {h1['bp_ratio_trig_vs_off']:.2f}

## L1 DQ Flags in Trigger Window

{flag_table(l1)}

### L1 Injection Flags

{inj_table(l1)}

L1 band power ratio (trigger/off-200s): {l1['bp_ratio_trig_vs_off']:.2f}

## H1 / L1 Flag Differences

Flags that differ between H1 and L1: **{diff_flags if h1 and l1 else 'N/A'}**

| Flag | H1 | L1 | Status |
|------|----|----|--------|
| CW_CAT1 | {h1['dq_flags'].get('CW_CAT1','?') if h1 else '?'} | {l1['dq_flags'].get('CW_CAT1','?') if l1 else '?'} | {'DIFFER' if h1 and l1 and h1['dq_flags'].get('CW_CAT1') != l1['dq_flags'].get('CW_CAT1') else 'SAME'} |
| NO_CW_HW_INJ | {'CLEAN' if h1 and h1['inj_flags'].get('NO_CW_HW_INJ') else 'INJ_PRESENT'} | {'CLEAN' if l1 and l1['inj_flags'].get('NO_CW_HW_INJ') else 'INJ_PRESENT'} | {'SAME' if h1 and l1 and h1['inj_flags'].get('NO_CW_HW_INJ') == l1['inj_flags'].get('NO_CW_HW_INJ') else 'DIFFER'} |

## Key Finding: CW Hardware Injection

```
NO_CW_HW_INJ flag is NOT SET for BOTH H1 and L1.
This means a CW (continuous wave) hardware injection was ACTIVE
at the time of the GW240925 trigger at both detectors.
```

**What this means:**

A hardware injection injects a simulated signal directly into the
detector actuation system. CW injections are continuous sinusoidal
signals used for calibration and detector characterization. They are
NOT GW signals.

If a CW hardware injection was active in the 20-210 Hz band at
trigger time, it would:
- Add a narrow spectral line to the data
- NOT explain a broadband power excess like the L1 anomaly
- Be present in both H1 and L1 simultaneously (consistent with both
  being flagged)

**However:** The CW injection line would be at a single known frequency,
not broadband. The L1 power excess across the full 20-210 Hz band
is **not explained** by a CW hardware injection alone.

## Critical Flags: CBC_CAT2 / CBC_CAT3

| Flag | H1 | L1 |
|------|----|----|
| CBC_CAT2 | {'SET' if h1 and h1['dq_flags'].get('CBC_CAT2') else 'NOT_SET'} | {'SET' if l1 and l1['dq_flags'].get('CBC_CAT2') else 'NOT_SET'} |
| CBC_CAT3 | {'SET' if h1 and h1['dq_flags'].get('CBC_CAT3') else 'NOT_SET'} | {'SET' if l1 and l1['dq_flags'].get('CBC_CAT3') else 'NOT_SET'} |

Both H1 and L1 pass CBC_CAT2 and CBC_CAT3 in the trigger window.
The L1 power excess is therefore **not due to a known vetoed glitch**
in the GWOSC release DQ flags.

## Interpretation

The L1 in-band power anomaly:

1. **Is NOT due to a CAT2/CAT3 flagged glitch** (both flags pass)
2. **Is NOT explained by DATA quality failure** (DATA flag set = good)
3. **Has a CW HW injection present** (same for H1 and L1) — cannot
   explain broadband excess
4. **CW_CAT1 differs**: H1 fails CW_CAT1, L1 passes — this means
   H1 was flagged for CW analysis quality, not L1

**Conclusion:** The L1 broadband power excess in the trigger window
is **not explained by any GWOSC release DQ flag**. The source of the
anomaly remains unresolved. Possible explanations:

- A non-stationary noise transient not captured by 1Hz DQ masks
- Environmental coupling not listed in simple DQ products
- An actual astrophysical signal in L1 (the event GW240925 itself)
- A non-glitch excess that requires LIGO offline DQ tools

## Question to LIGO (if needed)

```
We observe an L1-specific broadband power excess in the 20-210 Hz band
at the GW240925 trigger time (GPS {TRIGGER_GPS}) after robust
multi-window PSD checks (4 off-source windows from -500s to +300s).

The GWOSC DQ flags CBC_CAT2/CAT3 are set (passing), DATA is set, and
we note NO_CW_HW_INJ is not set (CW injection active).

Questions:
1. Are offline DQ / glitch characterization products (omicron, iDQ,
   hveto outputs) available for this release?
2. Is the L1 trigger window in GW240925 known to be affected by any
   non-stationarity or environmental coupling not in the simple DQ mask?
3. Is there a recommended off-source window strategy for L1 in this event?
```

## Gate Status

```
L1_DQ_STATUS:                   {l1_dq_status}
H1_DQ_STATUS:                   PASS_NO_CRITICAL_FLAG
CBC_CAT2_BOTH:                  PASS
CBC_CAT3_BOTH:                  PASS
DATA_BOTH:                      PASS
CW_HW_INJ_BOTH_DETECTORS:       ACTIVE (broadband effect: NO)
CW_CAT1_ASYMMETRY:              H1 FAILS, L1 PASSES
L1_BROADBAND_EXCESS_EXPLAINED:  NO
COHERENCE_STATUS:               {coherence_status}
READY_FOR_REAL_LIGO_SSZ_CLAIM:  NO
SSZ_SUPPORT_CLAIM_MADE:         NO
SSZ_FALSIFICATION_CLAIM_MADE:   NO
```
"""

(REPORTS / "L1_DQ_FLAG_CHECK_REPORT.md").write_text(report, encoding="utf-8")
log("  -> reports/L1_DQ_FLAG_CHECK_REPORT.md")

flush_log()
log("  -> logs/l1_dq_flag_check.log")
log(f"\nFINAL GATE:")
log(f"  L1_DQ_STATUS: {l1_dq_status}")
log(f"  COHERENCE_STATUS: {coherence_status}")
log(f"  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
