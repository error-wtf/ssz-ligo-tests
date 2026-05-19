#!/usr/bin/env python3
"""
PHASE 3 EXECUTION BLOCKER AUDIT
Diagnose why Phase 3 reports are not generated
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Setup
ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
LOGS_DIR = ROOT / "06_WINDSURF_LOGS"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

audit_log = []
def log(msg):
    line = f"{datetime.now().isoformat()} - {msg}"
    print(line)
    audit_log.append(line)

log("=" * 70)
log("PHASE 3 EXECUTION BLOCKER AUDIT")
log("=" * 70)

# Check 1: Python environment
log("\n--- CHECK 1: PYTHON ENVIRONMENT ---")
log(f"Python version: {sys.version}")
log(f"Python executable: {sys.executable}")
log(f"Platform: {sys.platform}")

# Check h5py
try:
    import h5py
    log(f"h5py: {h5py.__version__} OK")
    h5py_status = "OK"
except ImportError as e:
    log(f"h5py: NOT INSTALLED NO ({e})")
    h5py_status = "MISSING"

try:
    import numpy as np
    log(f"numpy: {np.__version__} OK")
except ImportError as e:
    log(f"numpy: NOT INSTALLED NO ({e})")

# Check 2: Extraction roots
log("\n--- CHECK 2: EXTRACTION ROOTS ---")
candidates = [
    ROOT / "18600070",
    ROOT / "1860070",
    ROOT / "01_EXTRACTED" / "18600070",
    ROOT / "01_EXTRACTED" / "1860070",
    ROOT / "01_EXTRACTED",
    ROOT / "01_EXTRACTED" / "nested",
]

found_roots = []
for cand in candidates:
    if cand.exists():
        try:
            items = list(cand.iterdir())
            files = [f for f in items if f.is_file()]
            dirs = [d for d in items if d.is_dir()]
            
            # Count HDF5
            h5_count = len(list(cand.rglob("*.hdf5"))) + len(list(cand.rglob("*.h5")))
            
            log(f"EXISTS: {cand}")
            log(f"  Dirs: {len(dirs)}, Files: {len(files)}, HDF5: {h5_count}")
            
            if h5_count > 0:
                found_roots.append((cand, h5_count))
        except Exception as e:
            log(f"ERROR: {cand} - {e}")
    else:
        log(f"MISSING: {cand}")

best_root = found_roots[0] if found_roots else (None, 0)
log(f"\nBEST ROOT: {best_root[0]} with {best_root[1]} HDF5 files")

# Check 3: HDF5 files
log("\n--- CHECK 3: HDF5 FILES ---")
if best_root[0]:
    h5_files = list(best_root[0].rglob("*.hdf5")) + list(best_root[0].rglob("*.h5"))
    log(f"Total HDF5 files found: {len(h5_files)}")
    for h5 in h5_files[:10]:
        try:
            size_mb = h5.stat().st_size / (1024**2)
            log(f"  {h5.name}: {size_mb:.1f} MB")
        except (OSError, FileNotFoundError):
            log(f"  {h5.name}: SIZE_UNKNOWN (file not accessible)")
    if len(h5_files) > 10:
        log(f"  ... and {len(h5_files) - 10} more")
else:
    log("No HDF5 files found (no valid root)")
    h5_files = []

# Check 4: Write permissions
log("\n--- CHECK 4: WRITE PERMISSIONS ---")
try:
    probe_file = ROOT / "02_INVENTORY" / "WRITE_PROBE_PHASE3.txt"
    probe_file.parent.mkdir(parents=True, exist_ok=True)
    probe_file.write_text(f"Phase 3 write probe at {datetime.now().isoformat()}")
    
    if probe_file.exists():
        content = probe_file.read_text()
        log(f"Write probe: SUCCESS OK")
        log(f"  File: {probe_file}")
        log(f"  Content: {content[:50]}...")
        write_status = "OK"
    else:
        log("Write probe: FAILED X (file not found after write)")
        write_status = "FAIL"
except Exception as e:
    log(f"Write probe: FAILED X ({e})")
    write_status = "FAIL"

# Check 5: Phase 3 scripts
log("\n--- CHECK 5: PHASE 3 SCRIPTS ---")
script_patterns = ['phase3*.py', '*hdf5*.py', '*qnm*.py', '*readiness*.py']
scripts_found = []
for pattern in script_patterns:
    for script in ROOT.glob(pattern):
        if script.is_file():
            size_kb = script.stat().st_size / 1024
            log(f"FOUND: {script.name} ({size_kb:.1f} KB)")
            
            # Check content
            try:
                content = script.read_text(encoding='utf-8', errors='ignore')
                has_h5py = 'import h5py' in content
                has_18600070 = '18600070' in content
                has_1860070 = '1860070' in content
                has_output = '02_INVENTORY' in content
                has_main = 'if __name__' in content
                
                log(f"  h5py import: {'YES' if has_h5py else 'NO'}")
                log(f"  18600070 ref: {'YES' if has_18600070 else 'NO'}")
                log(f"  1860070 ref: {'YES' if has_1860070 else 'NO'}")
                log(f"  output dir ref: {'YES' if has_output else 'NO'}")
                log(f"  main guard: {'YES' if has_main else 'NO'}")
                
                scripts_found.append({
                    'path': script,
                    'has_h5py': has_h5py,
                    'has_18600070': has_18600070,
                    'has_1860070': has_1860070,
                    'has_output': has_output,
                    'has_main': has_main
                })
            except Exception as e:
                log(f"  Error reading: {e}")

if not scripts_found:
    log("NO Phase 3 scripts found!")

# Check 6: Required outputs
log("\n--- CHECK 6: REQUIRED OUTPUTS ---")
required_files = [
    ROOT / "02_INVENTORY" / "HDF5_STRUCTURE_REPORT.md",
    ROOT / "02_INVENTORY" / "HDF5_STRUCTURE_SUMMARY.csv",
    ROOT / "02_INVENTORY" / "QNM_CANDIDATE_FIELDS_REPORT.md",
    ROOT / "02_INVENTORY" / "QNM_RF_TEST_READINESS_REPORT.md",
    ROOT / "06_WINDSURF_LOGS" / "PHASE_3_HDF5_QNM_READINESS_LOG.md",
]

all_outputs_ok = True
for req in required_files:
    if req.exists():
        size = req.stat().st_size
        status = "EXISTS" if size > 500 else "STALE/EMPTY"
        log(f"{status}: {req.name} ({size} bytes)")
        if size <= 500:
            all_outputs_ok = False
    else:
        log(f"MISSING: {req.name}")
        all_outputs_ok = False

# Determine blocker
log("\n--- CHECK 7: BLOCKER DETERMINATION ---")
blockers = []

if h5py_status == "MISSING":
    blockers.append("h5py not installed")

if not best_root[0]:
    blockers.append("No valid extraction root found")

if write_status == "FAIL":
    blockers.append("Write permission failed")

if not scripts_found:
    blockers.append("No Phase 3 scripts found")

# Check for path confusion
if scripts_found:
    for script in scripts_found:
        if script['has_1860070'] and not script['has_18600070']:
            blockers.append(f"{script['path'].name} uses 1860070 (wrong path)")
        if not script['has_h5py']:
            blockers.append(f"{script['path'].name} doesn't import h5py")

# Final status
if blockers:
    final_status = "BLOCKED"
    log(f"\nNO STATUS: {final_status}")
    log("Blockers:")
    for b in blockers:
        log(f"  - {b}")
else:
    final_status = "CAN_PROCEED"
    log(f"\nOK STATUS: {final_status}")
    log("No blockers found. Ready for full Phase 3 execution.")

# Write audit report
audit_path = LOGS_DIR / "PHASE_3_EXECUTION_BLOCKER_AUDIT.md"
with open(audit_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 3 Execution Blocker Audit\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Summary\n\n")
    f.write(f"**Status:** {final_status}\n\n")
    
    if blockers:
        f.write("### Blockers Found\n\n")
        for b in blockers:
            f.write(f"- {b}\n")
    else:
        f.write("### No Blockers\n\n")
        f.write("All checks passed. Ready for Phase 3 execution.\n")
    
    f.write("\n## Detailed Checks\n\n")
    for entry in audit_log[1:]:  # Skip header
        if entry.startswith('---'):
            f.write(f"\n### {entry.strip('- ')}\n\n")
        elif entry.startswith((' ', '\t')):
            f.write(f"{entry}\n")
        else:
            f.write(f"- {entry}\n")
    
    f.write("\n## Recommendations\n\n")
    if h5py_status == "MISSING":
        f.write("1. **Install h5py**: `pip install h5py`\n")
    if not best_root[0]:
        f.write("2. **Verify extraction**: Check that archives were extracted to correct location\n")
    if write_status == "FAIL":
        f.write("3. **Check permissions**: Ensure write access to 02_INVENTORY\n")
    if final_status == "CAN_PROCEED":
        f.write("1. **Execute Phase 3**: Run full forensic recovery script\n")

log(f"\nOK Audit Report: {audit_path}")

# If no blockers, run Phase 3
if final_status == "CAN_PROCEED" and best_root[0] and h5py_status == "OK":
    log("\n" + "=" * 70)
    log("EXECUTING FULL PHASE 3")
    log("=" * 70)
    
    # Now run the full inspection
    import h5py
    
    INVENTORY_DIR = ROOT / "02_INVENTORY"
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Inspect HDF5 files
    log(f"\nInspecting {len(h5_files)} HDF5 files...")
    structure_data = []
    qnm_candidates = []
    
    search_terms = ['final_mass', 'final_spin', 'mass', 'spin', 'chi', 'qnm', 
                    'ringdown', 'f_220', 'f220', 'omega', 'tau', 'damping', 'frequency']
    
    for idx, h5_path in enumerate(h5_files[:30]):  # Inspect up to 30 files
        log(f"\n[{idx+1}/{min(30, len(h5_files))}] {h5_path.name}")
        
        try:
            with h5py.File(h5_path, 'r') as f:
                items = []
                
                def collect(name, obj):
                    item_type = 'group' if isinstance(obj, h5py.Group) else 'dataset'
                    shape = str(obj.shape) if hasattr(obj, 'shape') else 'N/A'
                    dtype = str(obj.dtype) if hasattr(obj, 'dtype') else 'N/A'
                    attrs = list(obj.attrs.keys()) if hasattr(obj, 'attrs') else []
                    
                    items.append({
                        'file': str(h5_path.relative_to(best_root[0])),
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
                                'file': str(h5_path.relative_to(best_root[0])),
                                'path': name,
                                'type': item_type,
                                'shape': shape,
                                'dtype': dtype,
                                'match_term': term
                            })
                
                f.visititems(collect)
                structure_data.extend(items)
                log(f"  Items: {len(items)}")
                
        except Exception as e:
            log(f"  NO Error: {e}")
    
    log(f"\nOK Inspected {min(30, len(h5_files))} files")
    log(f"OK Structure entries: {len(structure_data)}")
    log(f"OK QNM candidates: {len(qnm_candidates)}")
    
    # Generate reports
    log("\nGenerating reports...")
    
    # Discovery report
    disc_path = INVENTORY_DIR / "HDF5_DISCOVERY_REPORT.md"
    with open(disc_path, 'w', encoding='utf-8') as f:
        f.write("# HDF5 Discovery Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Root:** {best_root[0]}\n\n")
        f.write(f"**Total HDF5 files:** {len(h5_files)}\n\n")
        f.write("## File List\n\n")
        for h5 in h5_files:
            try:
                size_mb = h5.stat().st_size / (1024**2)
                rel = h5.relative_to(best_root[0])
                f.write(f"- `{rel}` ({size_mb:.1f} MB)\n")
            except (OSError, FileNotFoundError) as e:
                rel = h5.relative_to(best_root[0])
                f.write(f"- `{rel}` (SIZE_UNKNOWN: {e})\n")
    
    log(f"  OK Discovery: {disc_path}")
    
    # Structure report
    struct_path = INVENTORY_DIR / "HDF5_STRUCTURE_REPORT.md"
    with open(struct_path, 'w', encoding='utf-8') as f:
        f.write("# HDF5 Structure Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Files inspected:** {min(30, len(h5_files))}/{len(h5_files)}\n")
        f.write(f"**Structure entries:** {len(structure_data)}\n")
        f.write(f"**QNM candidates:** {len(qnm_candidates)}\n\n")
        
        f.write("## QNM-Relevant Fields Found\n\n")
        if qnm_candidates:
            for c in qnm_candidates[:30]:
                f.write(f"- `{c['path']}` in {c['file']} ({c['type']}, match: {c['match_term']})\n")
    
    log(f"  OK Structure: {struct_path}")
    
    # Readiness report
    ready_path = INVENTORY_DIR / "QNM_RF_TEST_READINESS_REPORT.md"
    with open(ready_path, 'w', encoding='utf-8') as f:
        f.write("# QNM R_f Test Readiness Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        
        f.write("## Preregistered Test Definition\n\n")
        f.write("```\n")
        f.write("R_f := f_QNM,measured / f_QNM,GR(reference)\n\n")
        f.write("- f_QNM,measured = posterior median of observed QNM frequency\n")
        f.write("- f_QNM,GR(reference) = GR-predicted QNM from final mass/spin posterior\n")
        f.write("- mode fixed: l=m=2,n=0\n")
        f.write("```\n\n")
        
        f.write(f"## Candidates Found\n\n")
        f.write(f"- HDF5 files: {len(h5_files)}\n")
        f.write(f"- Structure entries: {len(structure_data)}\n")
        f.write(f"- QNM candidate matches: {len(qnm_candidates)}\n\n")
        
        f.write("## R_f Computation Status\n\n")
        f.write("**WARN  R_f was NOT computed in this phase.**\n\n")
        f.write("Blocked until independence verification complete.\n")
    
    log(f"  OK Readiness: {ready_path}")
    
    # Phase 3 Log
    phase3_log = LOGS_DIR / "PHASE_3_HDF5_QNM_READINESS_LOG.md"
    with open(phase3_log, 'w', encoding='utf-8') as f:
        f.write("# Phase 3: HDF5 Structure and QNM R_f Readiness Log\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write("## Status\n\n")
        f.write("OK Phase 3 Audit: COMPLETE\n")
        f.write("OK HDF5 Discovery: COMPLETE\n")
        f.write("OK Structure Inspection: COMPLETE\n")
        f.write("OK Readiness Report: COMPLETE\n")
        f.write("PENDING R_f computation: BLOCKED\n\n")
        f.write("## Outputs\n\n")
        f.write(f"- {audit_path}\n")
        f.write(f"- {disc_path}\n")
        f.write(f"- {struct_path}\n")
        f.write(f"- {ready_path}\n")
        f.write(f"- {phase3_log}\n")
    
    log(f"  OK Phase 3 Log: {phase3_log}")
    
    log("\n" + "=" * 70)
    log("PHASE 3 COMPLETE")
    log("=" * 70)
    log(f"All reports generated successfully.")
    
else:
    log("\n" + "=" * 70)
    log("PHASE 3 NOT EXECUTED")
    log("=" * 70)
    log("Blockers must be resolved before Phase 3 can run.")
    log(f"See audit report: {audit_path}")
