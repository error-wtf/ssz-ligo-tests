"""
Echte Datei-Inspektion - alle Unterordner von 18600070
"""
import h5py
import csv
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/18600070")
OUTPUT_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")

print("="*80)
print(f"ECHTE DATEI-INPEKTION")
print(f"Root: {ROOT_DIR}")
print(f"Zeit: {datetime.now()}")
print("="*80)

# Finde ALLE HDF5-Dateien rekursiv
print("\n[1] Suche alle HDF5-Dateien...")
h5_files = []
for ext in ['*.hdf5', '*.h5', '*.H5', '*.HDF5']:
    h5_files.extend(ROOT_DIR.rglob(ext))

print(f"Gefunden: {len(h5_files)} HDF5-Dateien")

# Prüfe jede Datei
results = []
usable_count = 0
broken_count = 0
symlink_count = 0

print("\n[2] Prüfe jede Datei mit h5py...")
for idx, h5_path in enumerate(h5_files, 1):
    rel_path = h5_path.relative_to(ROOT_DIR)
    print(f"\n[{idx}/{len(h5_files)}] {rel_path}")
    
    result = {
        'rel_path': str(rel_path),
        'full_path': str(h5_path),
        'exists': h5_path.exists(),
        'is_symlink': False,
        'size_mb': 0,
        'h5py_open': False,
        'error': '',
        'top_groups': '',
        'total_items': 0,
        'has_posterior': False,
        'has_ringdown': False,
        'has_strain': False
    }
    
    # Prüfe auf Symlink
    try:
        result['is_symlink'] = h5_path.is_symlink()
        if result['is_symlink']:
            symlink_count += 1
            try:
                target = h5_path.readlink()
                print(f"  -> Symlink zu: {target}")
                result['error'] = f"Symlink: {target}"
            except:
                result['error'] = "Symlink (Ziel unlesbar)"
            results.append(result)
            continue
    except:
        pass
    
    # Dateigröße
    try:
        size = h5_path.stat().st_size
        result['size_mb'] = round(size / 1024 / 1024, 2)
        print(f"  Größe: {result['size_mb']} MB")
    except Exception as e:
        print(f"  Größe: FEHLER - {e}")
        result['error'] = f"Size error: {e}"
        broken_count += 1
        results.append(result)
        continue
    
    # h5py Test
    try:
        with h5py.File(h5_path, 'r') as f:
            result['h5py_open'] = True
            usable_count += 1
            print(f"  -> h5py: OK")
            
            # Top-Level
            top = list(f.keys())
            result['top_groups'] = ';'.join(top[:10])
            print(f"  Top-Level: {len(top)} items")
            
            # Zähle Items
            count = [0]
            def cnt(name, obj):
                count[0] += 1
            f.visititems(cnt)
            result['total_items'] = count[0]
            
            # Suche nach Keywords
            content = ' '.join(top).lower()
            result['has_posterior'] = any(x in content for x in ['posterior', 'samples', 'mass', 'spin'])
            result['has_ringdown'] = any(x in content for x in ['ringdown', 'qnm', 'frequency'])
            result['has_strain'] = any(x in content for x in ['strain', 'h1', 'l1', 'v1', 'gwosc'])
            
            if result['has_posterior']:
                print(f"  -> Enthält Posterior-Daten")
            if result['has_ringdown']:
                print(f"  -> Enthält Ringdown/QNM")
            if result['has_strain']:
                print(f"  -> Enthält Strain-Daten")
                
    except Exception as e:
        result['error'] = str(e)[:100]
        print(f"  -> h5py FEHLER: {e}")
        broken_count += 1
    
    results.append(result)

# Zusammenfassung
print("\n" + "="*80)
print("ZUSAMMENFASSUNG")
print("="*80)
print(f"Gesamt HDF5-Dateien: {len(results)}")
print(f"Nutzbbar (h5py OK): {usable_count}")
print(f"Symlinks: {symlink_count}")
print(f"Defekt: {broken_count}")

# Nach Ordner gruppieren
by_folder = {}
for r in results:
    folder = str(Path(r['rel_path']).parent)
    if folder not in by_folder:
        by_folder[folder] = {'total': 0, 'usable': 0, 'size': 0}
    by_folder[folder]['total'] += 1
    if r['h5py_open']:
        by_folder[folder]['usable'] += 1
        by_folder[folder]['size'] += r['size_mb']

print("\n" + "="*80)
print("NACH ORDNER")
print("="*80)
for folder, stats in sorted(by_folder.items(), key=lambda x: -x[1]['size']):
    if stats['usable'] > 0:
        print(f"{folder:50s} | {stats['usable']:3d} Dateien | {stats['size']:8.1f} MB")

# Wichtige Dateien hervorheben
print("\n" + "="*80)
print(" WICHTIGE DATEIEN (mit Posterior/Ringdown/Strain)")
print("="*80)
for r in results:
    if r['h5py_open'] and (r['has_posterior'] or r['has_ringdown'] or r['has_strain']):
        typ = []
        if r['has_posterior']: typ.append("POSTERIOR")
        if r['has_ringdown']: typ.append("RINGDOWN")
        if r['has_strain']: typ.append("STRAIN")
        print(f"{r['rel_path'][:60]:60s} | {r['size_mb']:8.1f} MB | {','.join(typ)}")

# CSV Export
csv_path = OUTPUT_DIR / "ECHTE_HDF5_DATEIEN_ALLE_ORDNER.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['rel_path', 'size_mb', 'h5py_open', 'is_symlink', 'error',
                  'total_items', 'has_posterior', 'has_ringdown', 'has_strain']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        writer.writerow({k: r[k] for k in fieldnames})

print(f"\nCSV gespeichert: {csv_path}")
print("="*80)
