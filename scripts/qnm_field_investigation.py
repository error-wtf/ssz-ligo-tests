"""
Dringende Nachuntersuchung: QNM-Felder in ringdown und qnmrf
"""
import h5py
from pathlib import Path

# Untersuche ringdown-Datei im Detail
ringdown_file = Path("E:/clone/ligo-gw240925-gw250207-release/18600070/ringdown/ringdown/rd_GW250207_Kerr220_8M_singleIFO_prod_2048Hz_evol_20Ksamps.hdf5")

print("="*80)
print("DRINGENDE NACHUNTERSUCHUNG: QNM-FELDER")
print("="*80)

print(f"\nDatei: {ringdown_file}")
print(f"Existiert: {ringdown_file.exists()}")

if ringdown_file.exists():
    with h5py.File(ringdown_file, 'r') as f:
        print("\n--- TOP-LEVEL STRUKTUR ---")
        for name in f.keys():
            obj = f[name]
            item_type = 'dataset' if isinstance(obj, h5py.Dataset) else 'group'
            if isinstance(obj, h5py.Dataset):
                print(f"  {name}: {item_type}, shape={obj.shape}, dtype={obj.dtype}")
            else:
                print(f"  {name}: {item_type}")
        
        print("\n--- ALLE Pfade (rekursiv) ---")
        all_paths = []
        def collect(name, obj):
            all_paths.append(name)
        f.visititems(collect)
        
        # Zeige alle Pfade
        for p in sorted(all_paths):
            print(f"  {p}")
        
        # Suche nach Frequenz-bezogenen Feldern
        print("\n--- FREQUENZ/OMEGA/QNM SUCHE ---")
        freq_keywords = ['freq', 'omega', 'f220', 'f_220', 'mode', 'qnm', 'ringdown', 'damping', 'tau']
        for p in all_paths:
            p_lower = p.lower()
            for kw in freq_keywords:
                if kw in p_lower:
                    print(f"  *** MATCH: {p}")
                    try:
                        obj = f[p]
                        if isinstance(obj, h5py.Dataset):
                            print(f"      Dataset: shape={obj.shape}, dtype={obj.dtype}")
                            if obj.size < 100:
                                print(f"      Werte: {obj[()]}")
                    except:
                        pass
                    break

# Untersuche QNMRF-Dateien
print("\n" + "="*80)
print("QNMRF-DATEIEN")
print("="*80)

qnmrf_files = [
    Path("E:/clone/ligo-gw240925-gw250207-release/18600070/qnmrf/qnmrf/QNMRF_GW250207_Hanford_220_t=8.0M.h5"),
    Path("E:/clone/ligo-gw240925-gw250207-release/18600070/qnmrf/qnmrf/QNMRF_GW250207_Livingston_220_t=8.0M.h5")
]

for qf in qnmrf_files:
    print(f"\n--- {qf.name} ---")
    if qf.exists():
        with h5py.File(qf, 'r') as f:
            print("Top-Level:")
            for name in f.keys():
                obj = f[name]
                if isinstance(obj, h5py.Dataset):
                    print(f"  {name}: shape={obj.shape}, dtype={obj.dtype}")
                else:
                    print(f"  {name}: group")
            
            # Alle Pfade
            all_paths = []
            def collect(name, obj):
                all_paths.append(name)
            f.visititems(collect)
            
            # Frequenz-Suche
            print("Frequenz/QNM-Suche:")
            for p in sorted(all_paths):
                p_lower = p.lower()
                for kw in freq_keywords:
                    if kw in p_lower:
                        print(f"  *** {p}")
                        break

print("\n" + "="*80)
print("KONKLUSION")
print("="*80)
