"""
Werte-Prüfung der QNM-Felder
"""
import h5py
import numpy as np
from pathlib import Path

ringdown_file = Path("E:/clone/ligo-gw240925-gw250207-release/18600070/ringdown/ringdown/rd_GW250207_Kerr220_8M_singleIFO_prod_2048Hz_evol_20Ksamps.hdf5")

print("="*80)
print("QNM FELD-WERTE")
print("="*80)

with h5py.File(ringdown_file, 'r') as f:
    for ifo in ['H1_only', 'L1_only']:
        print(f"\n{'='*40}")
        print(f"{ifo}")
        print(f"{'='*40}")
        
        for field in ['f', 'chi', 'm', 'g']:
            path = f"{ifo}/{field}"
            if path in f:
                data = f[path][()]
                print(f"\n{field}:")
                print(f"  Shape: {data.shape}")
                print(f"  Dtype: {data.dtype}")
                
                if data.size < 20:
                    print(f"  Werte: {data}")
                else:
                    print(f"  Min: {np.min(data)}")
                    print(f"  Max: {np.max(data)}")
                    print(f"  Mean: {np.mean(data)}")
                    print(f"  Median: {np.median(data)}")
                    
                # Prüfe auf NaN oder Inf
                if np.isnan(data).any():
                    print(f"  WARNING: Contains NaN!")
                if np.isinf(data).any():
                    print(f"  WARNING: Contains Inf!")

print("\n" + "="*80)
print("INTERPRETATION")
print("="*80)
print("""
Feld 'f' = QNM Frequenz (in Hz oder rad/s?)
Feld 'chi' = dimensionloser Spin-Parameter (0-1)
Feld 'm' = Masse (in M_sun?)
Feld 'g' = unklar, evtl. Dämpfung oder Amplitude

Wichtig: Einheit von 'f' muss geklärt werden!
- Wenn in Hz: f ~ 100-1000 Hz für BH-Ringdown
- Wenn in rad/s: omega ~ 600-6000 rad/s
- Umrechnung: omega = 2*pi*f
""")
