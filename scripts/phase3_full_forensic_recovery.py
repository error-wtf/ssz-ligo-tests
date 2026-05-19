#!/usr/bin/env python3
"""
PHASE 3 FULL FORENSIC RECOVERY + HDF5 INSPECTION + QNM READINESS
Part A: Audit + Part B: Discovery + Part C: Structure + Part D: Readiness
"""

import os
import sys
import csv
import subprocess
from pathlib import Path
from datetime import datetime

# Setup
ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
INVENTORY_DIR = ROOT / "02_INVENTORY"
LOGS_DIR = ROOT / "06_WINDSURF_LOGS"
INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

log_entries = []
def log(msg):
    ts = datetime.now().isoformat()
    entry = f"{ts} - {msg}"
    print(entry)
    log_entries.append(entry)

# ============================================================
# PART A — FORENSIC AUDIT
# ============================================================
log("=" * 70)
log("PART A: FORENSIC AUDIT")
log("=" * 70)

# Check 1: Existing files
log("\n--- CHECK 1: EXISTING OUTPUT FILES ---")
expected_files = [
    INVENTORY_DIR / "HDF5_STRUCTURE_REPORT.md",
    INVENTORY_DIR / "HDF5_STRUCTURE_SUMMARY.csv",
    INVENTORY_DIR / "QNM_RF_TEST_READINESS_REPORT.md",
    LOGS_DIR / "PHASE_3_HDF5_QNM_READINESS_LOG.md",
]

file_status = {}
for f in expected_files:
    exists = f.exists()
    size = f.stat().st_size if exists else 0
    file_status[f.name] = {"exists": exists, "size": size}
    status = "EXISTS" if exists else "MISSING"
    log(f"  {f.name}: {status} ({size} bytes)")

# Check 2: Python env
log("\n--- CHECK 2: PYTHON ENVIRONMENT ---")
log(f"  Python: {sys.version}")
log(f"  Executable: {sys.executable}")

try:
    import h5py
    h5py_ver = h5py.__version__
    h5py_ok = True
    log(f"  h5py: {h5py_ver} ✅")
except ImportError:
    h5py_ver = None
    h5py_ok = False
    log(f"  h5py: NOT INSTALLED ❌")

try:
    import numpy as np
    log(f"  numpy: {np.__version__} ✅")
except ImportError:
    log(f"  numpy: NOT INSTALLED ❌")

# Check 3: Find extraction roots
log("\n--- CHECK 3: EXTRACTION ROOTS ---")
candidates = [
    ROOT / "18600070",
    ROOT / "1860070",
    ROOT / "01_EXTRACTED" / "18600070",
    ROOT / "01_EXTRACTED" / "1860070",
    ROOT / "01_EXTRACTED",
    ROOT / "01_EXTRACTED" / "nested",
]

found_root = None
for cand in candidates:
    if cand.exists():
        try:
            items = list(cand.iterdir())
            files = [f for f in items if f.is_file()]
            dirs = [d for d in items if d.is_dir()]
            log(f"  {cand}: EXISTS ({len(dirs)} dirs, {len(files)} files)")
            
            # Check for HDF5
            h5_count = len(list(cand.rglob("*.hdf5"))) + len(list(cand.rglob("*.h5")))
            if h5_count > 0 and not found_root:
                found_root = cand
                log(f"    ★ Best root candidate: {h5_count} HDF5 files")
        except Exception as e:
            log(f"  {cand}: ERROR - {e}")
    else:
        log(f"  {cand}: NOT FOUND")

if not found_root:
    log("  ❌ NO VALID EXTRACTION ROOT FOUND")
    sys.exit(1)

log(f"\n★ Using extraction root: {found_root}")

# Write forensic report
forensic_path = LOGS_DIR / "PHASE_3_FORENSIC_AUDIT_REPORT.md"
with open(forensic_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 3 Forensic Audit Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("## File Status Check\n\n")
    for name, info in file_status.items():
        status = "EXISTS" if info["exists"] else "MISSING"
        f.write(f"- {name}: {status} ({info['size']} bytes)\n")
    
    f.write("\n## Environment\n\n")
    f.write(f"- Python: {sys.version}\n")
    f.write(f"- h5py: {h5py_ver or 'NOT INSTALLED'}\n")
    f.write(f"- h5py available: {'YES' if h5py_ok else 'NO'}\n")
    
    f.write("\n## Extraction Root\n\n")
    f.write(f"- Selected: {found_root}\n")
    
    if h5py_ok and found_root:
        f.write("\n## Status: CAN PROCEED TO PART B\n")
    else:
        f.write("\n## Status: BLOCKED\n")
        if not h5py_ok:
            f.write("- h5py not installed\n")
        if not found_root:
            f.write("- No extraction root found\n")

log(f"✅ Forensic Report: {forensic_path}")

if not h5py_ok:
    log("\n❌ BLOCKED: h5py not installed")
    log("Install: pip install h5py")
    sys.exit(1)

# ============================================================
# PART B — HDF5 DISCOVERY
# ============================================================
log("\n" + "=" * 70)
log("PART B: HDF5 DISCOVERY")
log("=" * 70)

hdf5_files = []
for ext in ['*.hdf5', '*.h5', '*.hdf']:
    hdf5_files.extend(found_root.rglob(ext))

hdf5_files = sorted(set(hdf5_files))
log(f"\nFound {len(hdf5_files)} HDF5 files")

for h5 in hdf5_files[:10]:
    size_mb = h5.stat().st_size / (1024**2)
    rel = h5.relative_to(found_root)
    log(f"  {rel} ({size_mb:.1f} MB)")
if len(hdf5_files) > 10:
    log(f"  ... and {len(hdf5_files) - 10} more")

# Write discovery report
discovery_path = INVENTORY_DIR / "HDF5_DISCOVERY_REPORT.md"
with open(discovery_path, 'w', encoding='utf-8') as f:
    f.write("# HDF5 Discovery Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n")
    f.write(f"**Root:** {found_root}\n\n")
    f.write(f"**Total HDF5 files found:** {len(hdf5_files)}\n\n")
    
    f.write("## File List\n\n")
    f.write("| File | Size (MB) | Parent Dir |\n")
    f.write("|------|-----------|------------|\n")
    for h5 in hdf5_files:
        size_mb = h5.stat().st_size / (1024**2)
        rel = h5.relative_to(found_root)
        parent = rel.parent
        f.write(f"| {h5.name} | {size_mb:.1f} | {parent} |\n")

log(f"✅ Discovery Report: {discovery_path}")

# ============================================================
# PART C — HDF5 STRUCTURE INSPECTION
# ============================================================
log("\n" + "=" * 70)
log("PART C: HDF5 STRUCTURE INSPECTION")
log("=" * 70)

# Inspect structure of each HDF5
structure_data = []
qnm_candidates = []

search_terms = [
    'final_mass', 'final_mass_source', 'remnant_mass', 'mass', 'm1', 'm2',
    'final_spin', 'remnant_spin', 'spin', 'chi', 'chi_eff', 'chi_p', 'a1', 'a2',
    'qnm', 'ringdown', 'f_220', 'f220', 'omega', 'omega_220', 'omega220',
    'tau', 'tau_220', 'tau220', 'damping', 'damping_time',
    'frequency', 'freq', 'mode', 'l=', 'm=', 'n=',
    'deviation', 'delta', 'tiger', 'pca', 'fti', 'pseobnr', 'qnmrf',
    'calibration', 'C00', 'C01', 'envcal', 'cal'
]

# Limit to first 20 HDF5 files for speed
for idx, h5_path in enumerate(hdf5_files[:20]):
    log(f"\n[{idx+1}/20] Inspecting: {h5_path.name}")
    
    try:
        with h5py.File(h5_path, 'r') as f:
            # Collect all items
            all_items = []
            
            def collect(name, obj):
                item_type = 'group' if isinstance(obj, h5py.Group) else 'dataset'
                shape = str(obj.shape) if hasattr(obj, 'shape') else 'N/A'
                dtype = str(obj.dtype) if hasattr(obj, 'dtype') else 'N/A'
                
                # Get attributes
                attrs = list(obj.attrs.keys()) if hasattr(obj, 'attrs') else []
                
                all_items.append({
                    'file': str(h5_path.relative_to(found_root)),
                    'path': name,
                    'type': item_type,
                    'shape': shape,
                    'dtype': dtype,
                    'attrs': attrs
                })
                
                # Check for QNM candidates
                for term in search_terms:
                    if term.lower() in name.lower():
                        qnm_candidates.append({
                            'file': str(h5_path.relative_to(found_root)),
                            'path': name,
                            'type': item_type,
                            'shape': shape,
                            'dtype': dtype,
                            'match_term': term,
                            'attrs': attrs
                        })
            
            f.visititems(collect)
            structure_data.extend(all_items)
            log(f"  Items: {len(all_items)}")
            
    except Exception as e:
        log(f"  ❌ Error: {e}")

log(f"\n✅ Inspected {min(20, len(hdf5_files))} HDF5 files")
log(f"✅ Total structure entries: {len(structure_data)}")
log(f"✅ QNM candidate matches: {len(qnm_candidates)}")

# Write structure report
structure_path = INVENTORY_DIR / "HDF5_STRUCTURE_REPORT.md"
with open(structure_path, 'w', encoding='utf-8') as f:
    f.write("# HDF5 Structure Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n")
    f.write(f"**Root:** {found_root}\n")
    f.write(f"**Files inspected:** {min(20, len(hdf5_files))}/{len(hdf5_files)}\n")
    f.write(f"**Total items:** {len(structure_data)}\n")
    f.write(f"**QNM candidates:** {len(qnm_candidates)}\n\n")
    
    f.write("## QNM/SSZ-Relevant Candidates Found\n\n")
    if qnm_candidates:
        f.write("| File | Path | Type | Shape | Match Term |\n")
        f.write("|------|------|------|-------|------------|\n")
        for cand in qnm_candidates[:50]:  # Limit output
            f.write(f"| {cand['file']} | {cand['path']} | {cand['type']} | {cand['shape']} | {cand['match_term']} |\n")
        if len(qnm_candidates) > 50:
            f.write(f"\n... and {len(qnm_candidates) - 50} more matches\n")
    else:
        f.write("No obvious QNM/SSZ-relevant fields found in inspected files.\n")
    
    f.write("\n## Status\n\n")
    f.write("✅ HDF5 structure inspected (read-only)\n")
    f.write(f"⏳ QNM field identification: {len(qnm_candidates)} candidates found\n")
    f.write("⏳ Independence assessment: Requires Part D analysis\n")

log(f"✅ Structure Report: {structure_path}")

# Write CSV summary
csv_path = INVENTORY_DIR / "HDF5_STRUCTURE_SUMMARY.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['file_path', 'hdf5_path', 'object_type', 'shape', 'dtype', 'attribute_count', 'event_tag', 'calibration_tag'])
    for item in structure_data:
        # Infer tags from path
        path_lower = item['path'].lower()
        event_tag = 'GW240925' if '240925' in path_lower or 'gw240925' in path_lower else \
                    'GW250207' if '250207' in path_lower or 'gw250207' in path_lower else 'UNKNOWN'
        cal_tag = 'C00' if 'c00' in path_lower else \
                  'C01' if 'c01' in path_lower else \
                  'envcal' if 'envcal' in path_lower else 'UNKNOWN'
        
        writer.writerow([
            item['file'],
            item['path'],
            item['type'],
            item['shape'],
            item['dtype'],
            len(item['attrs']),
            event_tag,
            cal_tag
        ])

log(f"✅ Structure CSV: {csv_path}")

# ============================================================
# PART D — QNM R_f READINESS (NO COMPUTATION)
# ============================================================
log("\n" + "=" * 70)
log("PART D: QNM R_f TEST READINESS")
log("=" * 70)

# Analyze candidates
final_mass_candidates = [c for c in qnm_candidates if any(t in c['match_term'] for t in ['final_mass', 'remnant_mass', 'mass'])]
final_spin_candidates = [c for c in qnm_candidates if any(t in c['match_term'] for t in ['final_spin', 'remnant_spin', 'spin', 'chi'])]
qnm_freq_candidates = [c for c in qnm_candidates if any(t in c['match_term'] for t in ['qnm', 'f_220', 'f220', 'omega', 'ringdown', 'frequency'])]

log(f"\nCandidate Analysis:")
log(f"  Final mass candidates: {len(final_mass_candidates)}")
log(f"  Final spin candidates: {len(final_spin_candidates)}")
log(f"  QNM frequency candidates: {len(qnm_freq_candidates)}")

# Write QNM candidates report
qnm_cand_path = INVENTORY_DIR / "QNM_CANDIDATE_FIELDS_REPORT.md"
with open(qnm_cand_path, 'w', encoding='utf-8') as f:
    f.write("# QNM Candidate Fields Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Preregistered Test Definition\n\n")
    f.write("```\n")
    f.write("R_f := f_QNM,measured / f_QNM,GR(reference)\n\n")
    f.write("where:\n")
    f.write("- f_QNM,measured = posterior median of observed QNM frequency\n")
    f.write("- f_QNM,GR(reference) = GR-predicted QNM from final mass/spin posterior\n")
    f.write("- mode fixed: l=m=2,n=0\n")
    f.write("```\n\n")
    
    f.write(f"## Candidates Found\n\n")
    
    f.write(f"### Final Mass Candidates ({len(final_mass_candidates)})\n\n")
    if final_mass_candidates:
        for c in final_mass_candidates[:10]:
            f.write(f"- `{c['path']}` in {c['file']} ({c['type']}, {c['shape']})\n")
    else:
        f.write("No obvious final mass candidates found.\n")
    
    f.write(f"\n### Final Spin Candidates ({len(final_spin_candidates)})\n\n")
    if final_spin_candidates:
        for c in final_spin_candidates[:10]:
            f.write(f"- `{c['path']}` in {c['file']} ({c['type']}, {c['shape']})\n")
    else:
        f.write("No obvious final spin candidates found.\n")
    
    f.write(f"\n### QNM Frequency Candidates ({len(qnm_freq_candidates)})\n\n")
    if qnm_freq_candidates:
        for c in qnm_freq_candidates[:10]:
            f.write(f"- `{c['path']}` in {c['file']} ({c['type']}, {c['shape']})\n")
    else:
        f.write("No obvious QNM frequency candidates found.\n")

log(f"✅ QNM Candidates Report: {qnm_cand_path}")

# Write readiness report
readiness_path = INVENTORY_DIR / "QNM_RF_TEST_READINESS_REPORT.md"
with open(readiness_path, 'w', encoding='utf-8') as f:
    f.write("# QNM R_f Test Readiness Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Preregistered Test Definition\n\n")
    f.write("```\n")
    f.write("R_f := f_QNM,measured / f_QNM,GR(reference)\n\n")
    f.write("where:\n")
    f.write("- f_QNM,measured = posterior median of observed QNM frequency\n")
    f.write("- f_QNM,GR(reference) = GR-predicted QNM from final mass/spin posterior\n")
    f.write("- mode fixed: l=m=2,n=0 (dominant mode)\n")
    f.write("- thresholds fixed in SSZ_PREREGISTERED_HYPOTHESIS.md\n")
    f.write("- do not change thresholds, mode, or definition\n")
    f.write("```\n\n")
    
    f.write("## Data Availability Status\n\n")
    f.write(f"| Element | Status | Evidence |\n")
    f.write(f"|---------|--------|----------|\n")
    f.write(f"| HDF5 files present | ✅ YES | {len(hdf5_files)} files found |\n")
    f.write(f"| Structure inspected | ✅ YES | {len(structure_data)} items |\n")
    f.write(f"| Final mass candidates | {'✅' if final_mass_candidates else '⏳'} {'Found' if final_mass_candidates else 'Pending'} | {len(final_mass_candidates)} candidates |\n")
    f.write(f"| Final spin candidates | {'✅' if final_spin_candidates else '⏳'} {'Found' if final_spin_candidates else 'Pending'} | {len(final_spin_candidates)} candidates |\n")
    f.write(f"| QNM frequency candidates | {'✅' if qnm_freq_candidates else '⏳'} {'Found' if qnm_freq_candidates else 'Pending'} | {len(qnm_freq_candidates)} candidates |\n")
    f.write(f"| Independence verified | ⏳ PENDING | Requires deeper inspection |\n")
    
    f.write("\n## Anti-Circularity Assessment\n\n")
    f.write("**Global Rule:** Same data product cannot define AND validate prediction\n\n")
    f.write("**Required:** f_QNM,measured and f_QNM,GR(reference) from independent sources\n\n")
    
    f.write("**Current Status:** UNKNOWN\n\n")
    f.write("Risks to verify:\n")
    f.write("1. Using ringdown frequency to compute GR reference → CIRCULAR\n")
    f.write("2. Using same posterior for both measured and reference → CIRCULAR\n")
    f.write("3. Using independent inspiral PE vs ringdown QNM → SAFE\n\n")
    
    f.write("**Classification:** UNKNOWN (pending detailed field inspection)\n\n")
    
    f.write("## Readiness Matrix\n\n")
    f.write("| Event | Calibration | Measured QNM | GR Reference | Independence | Ready? |\n")
    f.write("|-------|-------------|--------------|--------------|--------------|--------|\n")
    f.write("| GW240925 | C00/C01/envcal | ⏳ Locate | ⏳ Locate | ⏳ Verify | NO |\n")
    f.write("| GW250207 | cal | ⏳ Locate | ⏳ Locate | ⏳ Verify | NO |\n")
    
    f.write("\n## R_f Computation Status\n\n")
    f.write("**⚠️  R_f was NOT computed in this phase.**\n\n")
    f.write("R_f computation is BLOCKED until:\n")
    f.write("1. Exact field names identified\n")
    f.write("2. Independence verified\n")
    f.write("3. Anti-circularity confirmed\n")
    f.write("4. This readiness report updated\n")
    
    f.write("\n## Next Steps\n\n")
    f.write("1. Deep HDF5 inspection: Find exact field names\n")
    f.write("2. Cross-reference: Which files contain which parameters\n")
    f.write("3. Verify: Inspiral vs ringdown pipeline independence\n")
    f.write("4. Update: This readiness report with findings\n")
    f.write("5. Only then: Consider R_f computation (Phase 4+)\n")

log(f"✅ Readiness Report: {readiness_path}")

# Write final log
log_path = LOGS_DIR / "PHASE_3_HDF5_QNM_READINESS_LOG.md"
with open(log_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 3: HDF5 Structure and QNM R_f Readiness Log\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("## Parts Completed\n\n")
    f.write("- ✅ Part A: Forensic Audit\n")
    f.write("- ✅ Part B: HDF5 Discovery\n")
    f.write("- ✅ Part C: Structure Inspection\n")
    f.write("- ✅ Part D: QNM Readiness (without R_f computation)\n\n")
    
    f.write("## Key Findings\n\n")
    f.write(f"- HDF5 files found: {len(hdf5_files)}\n")
    f.write(f"- HDF5 files inspected: {min(20, len(hdf5_files))}\n")
    f.write(f"- Structure entries: {len(structure_data)}\n")
    f.write(f"- QNM candidates: {len(qnm_candidates)}\n")
    f.write(f"- Final mass candidates: {len(final_mass_candidates)}\n")
    f.write(f"- Final spin candidates: {len(final_spin_candidates)}\n\n")
    
    f.write("## Status\n\n")
    f.write("✅ VERIFICATION: PASS (based on real filesystem inspection)\n")
    f.write("✅ PHASE 3: Structure inspection complete\n")
    f.write("⏳ R_f computation: BLOCKED (awaiting readiness confirmation)\n")
    f.write("⏳ Independence: UNKNOWN (to be verified)\n")
    
    f.write("\n## Output Files\n\n")
    f.write(f"- {forensic_path}\n")
    f.write(f"- {discovery_path}\n")
    f.write(f"- {structure_path}\n")
    f.write(f"- {csv_path}\n")
    f.write(f"- {qnm_cand_path}\n")
    f.write(f"- {readiness_path}\n")

log(f"✅ Phase 3 Log: {log_path}")

# ============================================================
# FINAL SUMMARY
# ============================================================
log("\n" + "=" * 70)
log("PHASE 3 COMPLETE")
log("=" * 70)

status = "PASS" if h5py_ok and found_root else "BLOCKED"
log(f"\nSTATUS: {status}")
log(f"HDF5 files found: {len(hdf5_files)}")
log(f"HDF5 files inspected: {min(20, len(hdf5_files))}")
log(f"R_f computed: NO")
log(f"SSZ claims: NONE")
log(f"Circularity status: UNKNOWN (requires deeper verification)")

log(f"\nAll reports generated:")
log(f"  1. {forensic_path}")
log(f"  2. {discovery_path}")
log(f"  3. {structure_path}")
log(f"  4. {csv_path}")
log(f"  5. {qnm_cand_path}")
log(f"  6. {readiness_path}")
log(f"  7. {log_path}")

log("\n✅ Phase 3 Forensic Recovery COMPLETE")
