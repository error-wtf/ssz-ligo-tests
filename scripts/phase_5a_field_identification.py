"""
Phase 5A: Field Identification Lock
Task ID: LIGO_PHASE_5_PREREGISTERED_QNM_RF_TEST

Suche nach QNM-relevanten Feldern in den zugänglichen HDF5-Dateien.
NUR IDENTIFIZIEREN - NICHT BERECHNEN!
"""
import h5py
import csv
from pathlib import Path
from datetime import datetime

PRIMARY_ROOT = Path("E:/clone/ligo-gw240925-gw250207-release/18600070")
OUTPUT_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")

print("="*80)
print("PHASE 5A: FIELD IDENTIFICATION LOCK")
print("="*80)
print(f"Start: {datetime.now()}")
print("NUR IDENTIFIKATION - KEINE BERECHNUNG")
print()

# Zieldateien
TARGET_FILES = [
    PRIMARY_ROOT / "GW240925_combinedPHM_envcalC01_metafile.hdf5",
    PRIMARY_ROOT / "GW250207_combinedPHM_cal_metafile.hdf5",
]

# Suche auch in ringdown und qnmrf
TARGET_FILES.extend(list((PRIMARY_ROOT / "ringdown").rglob("*.hdf5")))
TARGET_FILES.extend(list((PRIMARY_ROOT / "ringdown").rglob("*.h5")))
TARGET_FILES.extend(list((PRIMARY_ROOT / "qnmrf").rglob("*.hdf5")))
TARGET_FILES.extend(list((PRIMARY_ROOT / "qnmrf").rglob("*.h5")))

# Entferne Duplikate und nicht-existierende
TARGET_FILES = [f for f in TARGET_FILES if f.exists()]

print(f"Zu untersuchende Dateien: {len(TARGET_FILES)}")
for f in TARGET_FILES:
    print(f"  - {f.name}")
print()

# Schlüsselwörter für die Suche
SEARCH_TERMS = {
    'final_mass': ['final_mass', 'remnant_mass', 'mass_final', 'm_final'],
    'final_spin': ['final_spin', 'remnant_spin', 'spin_final', 'chi_final', 'a_final'],
    'qnm_freq': ['f_220', 'f220', 'freq_220', 'frequency_220', 'omega_220', 'f_qnm', 'f_ringdown'],
    'qnm_damping': ['tau_220', 'tau220', 'damping_220', 'tau_qnm', 'quality_factor', 'Q_220'],
    'mass_1': ['mass_1', 'm1', 'mass1'],
    'mass_2': ['mass_2', 'm2', 'mass2'],
    'calibration': ['C00', 'C01', 'cal', 'envcal', 'widecal'],
}

found_fields = []

for file_idx, file_path in enumerate(TARGET_FILES, 1):
    print(f"\n[{file_idx}/{len(TARGET_FILES)}] {file_path.name}")
    print(f"  Pfad: {file_path}")
    
    try:
        with h5py.File(file_path, 'r') as f:
            # Durchlaufe alle Objekte
            def scan_object(name, obj):
                # Prüfe auf Keywords im Namen
                name_lower = name.lower()
                
                for category, terms in SEARCH_TERMS.items():
                    for term in terms:
                        if term.lower() in name_lower:
                            # Gefunden!
                            item_type = 'dataset' if isinstance(obj, h5py.Dataset) else 'group'
                            shape = str(obj.shape) if isinstance(obj, h5py.Dataset) else 'N/A'
                            dtype = str(obj.dtype) if isinstance(obj, h5py.Dataset) else 'N/A'
                            
                            # Versuche Attribute zu lesen
                            attrs = {}
                            if hasattr(obj, 'attrs'):
                                for key in obj.attrs.keys():
                                    try:
                                        attrs[key] = str(obj.attrs[key])[:100]
                                    except:
                                        attrs[key] = 'UNREADABLE'
                            
                            found_fields.append({
                                'file_path': str(file_path),
                                'file_name': file_path.name,
                                'hdf5_path': name,
                                'category': category,
                                'matched_term': term,
                                'item_type': item_type,
                                'shape': shape,
                                'dtype': dtype,
                                'attributes': str(attrs)[:200],
                                'confidence': 'HIGH' if term.lower() == name_lower else 'MEDIUM'
                            })
                            
                            print(f"    FOUND [{category}]: {name}")
                            if isinstance(obj, h5py.Dataset):
                                print(f"      Shape: {shape}, Dtype: {dtype}")
                            break
            
            f.visititems(scan_object)
            
    except Exception as e:
        print(f"    ERROR: {e}")

print(f"\n{'='*80}")
print(f"GESAMT GEFUNDEN: {len(found_fields)} Felder")
print(f"{'='*80}")

# Gruppiere nach Kategorie
by_category = {}
for field in found_fields:
    cat = field['category']
    if cat not in by_category:
        by_category[cat] = []
    by_category[cat].append(field)

print("\nZusammenfassung nach Kategorie:")
for cat, fields in sorted(by_category.items()):
    print(f"\n{cat.upper()} ({len(fields)}):")
    for f in fields[:5]:  # Zeige max 5 pro Kategorie
        print(f"  - {f['file_name'][:30]:30} | {f['hdf5_path'][:50]:50}")

# Speichere als CSV
print("\nSpeichere Field Lock Report...")
csv_path = OUTPUT_DIR / "PHASE_5_FIELD_LOCK_CANDIDATES.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['file_path', 'file_name', 'hdf5_path', 'category', 'matched_term', 
                  'item_type', 'shape', 'dtype', 'attributes', 'confidence']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for field in found_fields:
        writer.writerow({k: field[k] for k in fieldnames})

print(f"  CSV: {csv_path}")

# Erstelle Markdown Report
report_path = OUTPUT_DIR / "PHASE_5_FIELD_LOCK_REPORT.md"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 5A: Field Identification Lock Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("**Status:** FIELD IDENTIFICATION ONLY - NO COMPUTATION\n\n")
    f.write(f"**Files scanned:** {len(TARGET_FILES)}\n\n")
    f.write(f"**Total candidate fields found:** {len(found_fields)}\n\n")
    
    f.write("## Candidate Fields by Category\n\n")
    
    for cat, fields in sorted(by_category.items()):
        f.write(f"### {cat.upper()}\n\n")
        f.write("| File | HDF5 Path | Type | Shape | Dtype | Confidence |\n")
        f.write("|------|-----------|------|-------|-------|------------|\n")
        for field in fields:
            f.write(f"| {field['file_name'][:25]} | {field['hdf5_path'][:40]} | {field['item_type']} | {field['shape']} | {field['dtype']} | {field['confidence']} |\n")
        f.write("\n")
    
    f.write("## Files Examined\n\n")
    for fp in TARGET_FILES:
        f.write(f"- `{fp}`\n")
    
    f.write("\n## Next Step\n\n")
    f.write("Proceed to Phase 5B: Anti-Circularity Check.\n")
    f.write("Select specific fields from candidates above for R_f computation.\n")

print(f"  Report: {report_path}")
print(f"\n{'='*80}")
print("PHASE 5A COMPLETE")
print(f"{'='*80}")
print(f"Gefundene Kandidaten:")
for cat, fields in sorted(by_category.items()):
    print(f"  {cat}: {len(fields)}")
