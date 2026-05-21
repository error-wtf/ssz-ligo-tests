"""
HDF5 Provenance Audit — STEP 02
Reads all 6 GW240925 strain HDF5 files, computes SHA256, extracts keys,
attributes, strain statistics. Writes JSON + CSV manifest.
"""
import os, hashlib, json, time, re
import numpy as np
import h5py

TRIGGER = 1411261107.984

FILES = [
    r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5",
    r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_16KHZ_R1\STRAIN_HDF\H1\1410334720\H-H1_GWOSC_O4b4DiscC00_16KHZ_R1-1411260416-4096.hdf5",
    r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\L1\1410334720\L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5",
    r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_16KHZ_R1\STRAIN_HDF\L1\1410334720\L-L1_GWOSC_O4b4DiscC00_16KHZ_R1-1411260416-4096.hdf5",
    r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\V1\1410334720\V-V1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5",
    r"E:\clone\ligo-gw240925-gw250207-release\18600070\GW240925-C00-Strain\GW240925-C00-Strain\O4b4DiscC00_16KHZ_R1\STRAIN_HDF\V1\1410334720\V-V1_GWOSC_O4b4DiscC00_16KHZ_R1-1411260416-4096.hdf5",
]

DETECTOR_MAP = {'H': 'H1 (Hanford)', 'L': 'L1 (Livingston)', 'V': 'V1 (Virgo)'}
RESULTS = []
CSV_LINES = ["filename,detector,file_size_bytes,sha256,gps_start,gps_end,duration_s,sample_rate_hz,n_samples,strain_dataset,strain_min,strain_max,strain_mean,strain_std,trigger_inside,trigger_offset_s"]

t0 = time.time()

for fp in FILES:
    fname = os.path.basename(fp)
    fsize = os.path.getsize(fp)
    detector_code = fname.split('-')[0]
    detector = DETECTOR_MAP[detector_code]

    # SHA256
    print(f"Computing SHA256: {fname} ({fsize/1e6:.1f} MB)...")
    sha = hashlib.sha256()
    with open(fp, 'rb') as f:
        while True:
            chunk = f.read(8*1024*1024)
            if not chunk:
                break
            sha.update(chunk)
    sha256 = sha.hexdigest()
    print(f"  SHA256: {sha256}")

    # HDF5
    print(f"  Opening HDF5...")
    strain_path = None
    strain_shape = None
    strain_dtype = None
    gps_start = None
    duration = None
    sample_rate = None
    root_keys = []
    attrs = {}
    strain_min = strain_max = strain_mean = strain_std = None
    first10 = last10 = None
    n_samples = None

    with h5py.File(fp, 'r') as f:
        root_keys = list(f.keys())
        for k, v in f.attrs.items():
            try:
                if isinstance(v, np.ndarray):
                    attrs[k] = v.tolist() if v.size < 100 else f"<array shape={v.shape}>"
                else:
                    attrs[k] = str(v) if not isinstance(v, (int, float, str, bool)) else v
            except:
                attrs[k] = f"<unreadable: {type(v).__name__}>"

        # Find strain dataset
        for candidate in ['strain/Strain', 'Strain', 'strain']:
            if candidate in f:
                ds = f[candidate]
                strain_path = candidate
                strain_shape = tuple(ds.shape)
                strain_dtype = str(ds.dtype)
                strain = ds[:]
                strain_min = float(np.min(strain))
                strain_max = float(np.max(strain))
                strain_mean = float(np.mean(strain))
                strain_std = float(np.std(strain))
                first10 = [float(x) for x in strain[:10]]
                last10 = [float(x) for x in strain[-10:]]
                n_samples = len(strain)
                break

        # GPS from attributes
        if 'GPSstart' in f.attrs:
            gps_start = float(f.attrs['GPSstart'])
        if 'Duration' in f.attrs:
            duration = float(f.attrs['Duration'])

    # Fallback: from filename
    if gps_start is None:
        m = re.search(r'-(\d{10})-(\d+)\.hdf5', fname)
        if m:
            gps_start = float(m.group(1))
            duration = float(m.group(2))

    gps_end = gps_start + duration if gps_start and duration else None
    trigger_inside = (gps_start <= TRIGGER <= gps_end) if gps_start and gps_end else None
    trigger_offset = TRIGGER - gps_start if gps_start else None

    # Sample rate from filename
    if '4KHZ' in fname:
        sample_rate = 4096
    elif '16KHZ' in fname:
        sample_rate = 16384

    result = {
        'filename': fname, 'path': fp, 'detector': detector,
        'file_size_bytes': fsize, 'sha256': sha256,
        'root_keys': root_keys, 'hdf5_attrs': attrs,
        'strain_dataset_path': strain_path,
        'strain_shape': strain_shape, 'strain_dtype': strain_dtype,
        'n_samples': n_samples,
        'gps_start': gps_start, 'duration_s': duration, 'gps_end': gps_end,
        'sample_rate_hz': sample_rate,
        'trigger_gps': TRIGGER,
        'trigger_inside_window': trigger_inside,
        'trigger_offset_s': trigger_offset,
    }
    if strain_path:
        result.update({
            'strain_min': strain_min, 'strain_max': strain_max,
            'strain_mean': strain_mean, 'strain_std': strain_std,
            'first_10_samples': first10, 'last_10_samples': last10,
        })

    RESULTS.append(result)

    status = "INSIDE" if trigger_inside else ("OUTSIDE" if trigger_inside is False else "UNKNOWN")
    print(f"  {detector}: {strain_path} shape={strain_shape} GPS=[{gps_start}, {gps_end}] "
          f"trigger_offset={trigger_offset:.3f}s -> {status}")
    if strain_path:
        print(f"  Strain: min={strain_min:.4e} max={strain_max:.4e} mean={strain_mean:.4e} std={strain_std:.4e}")

    # CSV line
    CSV_LINES.append(f"{fname},{detector},{fsize},{sha256},{gps_start},{gps_end},{duration},{sample_rate},{n_samples},{strain_path},{strain_min},{strain_max},{strain_mean},{strain_std},{trigger_inside},{trigger_offset}")

elapsed = time.time() - t0

# Write JSON
JSON_PATH = r"E:\clone\ssz-ligo-tests\reports\progress\raw_ligo_hdf5_provenance.json"
with open(JSON_PATH, 'w') as f:
    json.dump(RESULTS, f, indent=2, default=str)

# Write CSV
CSV_PATH = r"E:\clone\ssz-ligo-tests\data_manifest\raw_ligo_hdf5_manifest.csv"
os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
with open(CSV_PATH, 'w') as f:
    f.write('\n'.join(CSV_LINES) + '\n')

print(f"\n{'='*60}")
print(f"Processed {len(RESULTS)} files in {elapsed:.1f}s")
print(f"JSON: {JSON_PATH}")
print(f"CSV:  {CSV_PATH}")
print(f"\nTRIGGER INSIDE WINDOW for ALL 6 files: {all(r['trigger_inside_window'] for r in RESULTS)}")
for r in RESULTS:
    s = "[OK]" if r['trigger_inside_window'] else "[FAIL]"
    print(f"  {s} {r['filename'][:50]}... offset={r['trigger_offset_s']:.3f}s")
print("DONE")
