"""
Phase 5C: R_f Computation with Berti/Cardoso/Will Kerr QNM Formula
Task ID: LIGO_PHASE_5_PREREGISTERED_QNM_RF_TEST

Verwendet die korrekte Formel:
f_GR = (1 / (2*pi*M_seconds)) * (1.5251 - 1.1568*(1-chi)**0.1292)

wobei M_seconds = M_solar * 4.92549095e-6
"""
import h5py
import numpy as np
import csv
from pathlib import Path
from datetime import datetime

# Konstanten
G = 6.67430e-11  # m^3 kg^-1 s^-2
c = 299792458    # m/s
M_sun_kg = 1.98847e30  # kg
M_sun_seconds = G * M_sun_kg / c**3  # ~4.9255e-6 s

print("="*80)
print("PHASE 5C: R_f COMPUTATION")
print("="*80)
print(f"Start: {datetime.now()}")
print(f"M_sun_seconds = {M_sun_seconds:.10e} s")
print()

def compute_f_gr_kerr_220(m_solar, chi):
    """
    Berechne GR QNM Frequenz für l=m=2, n=0 Mode.
    Formel: Berti, Cardoso, Will (2009) - analytischer Fit
    f_GR = (1 / (2*pi*M_seconds)) * (1.5251 - 1.1568*(1-chi)**0.1292)
    """
    M_seconds = m_solar * M_sun_seconds
    
    # Dimensionlose Frequenz (omega * M)
    # Fit-Koeffizienten aus Berti et al. für (2,2,0) mode
    omega_m = 1.5251 - 1.1568 * (1 - chi)**0.1292
    
    # Umrechnung in Hz
    f_gr = omega_m / (2 * np.pi * M_seconds)
    
    return f_gr

# Test mit bekannten Werten
print("--- FORMEL VALIDATION ---")
test_cases = [
    (100, 0.0, "Schwarzschild"),
    (100, 0.7, "Kerr schnell"),
    (78, 0.8, "GW250207 H1-like"),
]
for m, chi, desc in test_cases:
    f = compute_f_gr_kerr_220(m, chi)
    print(f"{desc}: M={m}, chi={chi:.2f} → f_GR = {f:.1f} Hz")
print()

# Dateien laden
ringdown_file = Path("E:/clone/ligo-gw240925-gw250207-release/18600070/ringdown/ringdown/rd_GW250207_Kerr220_8M_singleIFO_prod_2048Hz_evol_20Ksamps.hdf5")
metafile = Path("E:/clone/ligo-gw240925-gw250207-release/18600070/GW250207_combinedPHM_cal_metafile.hdf5")

results = []

# --- H1 ANALYSIS ---
print("="*80)
print("GW250207 - H1 (Hanford)")
print("="*80)

with h5py.File(ringdown_file, 'r') as f:
    f_h1 = f['H1_only/f'][()]
    chi_h1 = f['H1_only/chi'][()]
    m_h1 = f['H1_only/m'][()]

print(f"f_H1 samples: {len(f_h1)}")
print(f"  Range: {f_h1.min():.1f} - {f_h1.max():.1f} Hz")
print(f"  Median: {np.median(f_h1):.1f} Hz")
print(f"  5/95 percentiles: {np.percentile(f_h1, 5):.1f} / {np.percentile(f_h1, 95):.1f}")

# Berechne f_GR aus H1's M und chi (dies ist die korrekte Paarung!)
f_gr_h1 = compute_f_gr_kerr_220(m_h1, chi_h1)
print(f"\nf_GR from H1 M/chi:")
print(f"  Range: {f_gr_h1.min():.1f} - {f_gr_h1.max():.1f} Hz")
print(f"  Median: {np.median(f_gr_h1):.1f} Hz")
print(f"  5/95 percentiles: {np.percentile(f_gr_h1, 5):.1f} / {np.percentile(f_gr_h1, 95):.1f}")

# Berechne R_f = f_measured / f_GR (sample-weise!)
R_f_h1 = f_h1 / f_gr_h1
print(f"\nR_f (H1, sample-weise):")
print(f"  Median: {np.median(R_f_h1):.4f}")
print(f"  16/84 percentiles: {np.percentile(R_f_h1, 16):.4f} / {np.percentile(R_f_h1, 84):.4f}")
print(f"  5/95 percentiles: {np.percentile(R_f_h1, 5):.4f} / {np.percentile(R_f_h1, 95):.4f}")

results.append({
    'event': 'GW250207',
    'ifo': 'H1',
    'f_measured_median': np.median(f_h1),
    'f_measured_p5': np.percentile(f_h1, 5),
    'f_measured_p95': np.percentile(f_h1, 95),
    'm_median': np.median(m_h1),
    'chi_median': np.median(chi_h1),
    'f_gr_median': np.median(f_gr_h1),
    'f_gr_p5': np.percentile(f_gr_h1, 5),
    'f_gr_p95': np.percentile(f_gr_h1, 95),
    'R_f_median': np.median(R_f_h1),
    'R_f_p16': np.percentile(R_f_h1, 16),
    'R_f_p84': np.percentile(R_f_h1, 84),
    'R_f_p5': np.percentile(R_f_h1, 5),
    'R_f_p95': np.percentile(R_f_h1, 95),
})

# --- L1 ANALYSIS ---
print(f"\n{'='*80}")
print("GW250207 - L1 (Livingston)")
print("="*80)

with h5py.File(ringdown_file, 'r') as f:
    f_l1 = f['L1_only/f'][()]
    chi_l1 = f['L1_only/chi'][()]
    m_l1 = f['L1_only/m'][()]

print(f"f_L1 samples: {len(f_l1)}")
print(f"  Range: {f_l1.min():.1f} - {f_l1.max():.1f} Hz")
print(f"  Median: {np.median(f_l1):.1f} Hz")

# Berechne f_GR aus L1's M und chi
f_gr_l1 = compute_f_gr_kerr_220(m_l1, chi_l1)
print(f"\nf_GR from L1 M/chi:")
print(f"  Median: {np.median(f_gr_l1):.1f} Hz")

# Berechne R_f
R_f_l1 = f_l1 / f_gr_l1
print(f"\nR_f (L1, sample-weise):")
print(f"  Median: {np.median(R_f_l1):.4f}")
print(f"  16/84 percentiles: {np.percentile(R_f_l1, 16):.4f} / {np.percentile(R_f_l1, 84):.4f}")
print(f"  5/95 percentiles: {np.percentile(R_f_l1, 5):.4f} / {np.percentile(R_f_l1, 95):.4f}")

results.append({
    'event': 'GW250207',
    'ifo': 'L1',
    'f_measured_median': np.median(f_l1),
    'f_measured_p5': np.percentile(f_l1, 5),
    'f_measured_p95': np.percentile(f_l1, 95),
    'm_median': np.median(m_l1),
    'chi_median': np.median(chi_l1),
    'f_gr_median': np.median(f_gr_l1),
    'f_gr_p5': np.percentile(f_gr_l1, 5),
    'f_gr_p95': np.percentile(f_gr_l1, 95),
    'R_f_median': np.median(R_f_l1),
    'R_f_p16': np.percentile(R_f_l1, 16),
    'R_f_p84': np.percentile(R_f_l1, 84),
    'R_f_p5': np.percentile(R_f_l1, 5),
    'R_f_p95': np.percentile(R_f_l1, 95),
})

# --- VERGLEICH MIT SSZ VORHERSAGE ---
print(f"\n{'='*80}")
print("VERGLEICH MIT SSZ VORHERSAGE")
print("="*80)
print(f"\nSSZ QNM-Vorhersage für R_f:")
print(f"  Erwarteter Shift: +39% → R_f ≈ 1.39")
print(f"  Untere Grenze (typisch): +10% → R_f ≈ 1.10")
print()
print(f"Gemessene R_f Werte:")
print(f"  H1: R_f = {np.median(R_f_h1):.3f} [{np.percentile(R_f_h1, 16):.3f}, {np.percentile(R_f_h1, 84):.3f}]")
print(f"  L1: R_f = {np.median(R_f_l1):.3f} [{np.percentile(R_f_l1, 16):.3f}, {np.percentile(R_f_l1, 84):.3f}]")
print()

# Prüfe gegen preregisterierte Schwellen
print(f"Preregisterierte Schwellenprüfung:")
print(f"  R_f < 1.10: SSZ falsifiziert für diesen Test")
print(f"  R_f > 1.10: SSZ nicht falsifiziert")
print()

h1_below = np.percentile(R_f_h1, 95) < 1.10
l1_below = np.percentile(R_f_l1, 95) < 1.10
print(f"  H1 95%-CI < 1.10? {h1_below} ({np.percentile(R_f_h1, 95):.3f})")
print(f"  L1 95%-CI < 1.10? {l1_below} ({np.percentile(R_f_l1, 95):.3f})")

if h1_below and l1_below:
    print(f"\n  → BEIDE unter 1.10: SSZ QNM-Shift NICHT unterstützt")
else:
    print(f"\n  → Mindestens einer über 1.10: Keine klare Falsifikation")

# Speichere Ergebnisse
output_dir = Path("E:/clone/ligo-gw240925-gw250207-release/05_RESULTS")
output_dir.mkdir(parents=True, exist_ok=True)

csv_path = output_dir / "PHASE_5C_RF_COMPUTATION_RESULTS.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['event', 'ifo', 'f_measured_median', 'f_measured_p5', 'f_measured_p95',
                  'm_median', 'chi_median', 'f_gr_median', 'f_gr_p5', 'f_gr_p95',
                  'R_f_median', 'R_f_p16', 'R_f_p84', 'R_f_p5', 'R_f_p95']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        writer.writerow(r)

print(f"\n{'='*80}")
print(f"Ergebnisse gespeichert: {csv_path}")
print("="*80)
