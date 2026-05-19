#!/usr/bin/env python3
"""
HDF5 Posterior Inspection - Phase 5
Inspect LIGO posterior samples without scientific interpretation
"""

import h5py
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
NESTED_DIR = ROOT / "01_EXTRACTED" / "nested"
RESULTS_DIR = ROOT / "05_RESULTS"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Find HDF5 files
def find_hdf5_files():
    """Find all HDF5 files in nested directory"""
    hdf5_files = []
    
    # Check posteriors
    posteriors_dir = NESTED_DIR / "posteriors"
    if posteriors_dir.exists():
        hdf5_files.extend(posteriors_dir.rglob("*.hdf5"))
        hdf5_files.extend(posteriors_dir.rglob("*.h5"))
    
    # Check other directories
    for subdir in NESTED_DIR.iterdir():
        if subdir.is_dir():
            hdf5_files.extend(subdir.rglob("*.hdf5"))
            hdf5_files.extend(subdir.rglob("*.h5"))
    
    return sorted(set(hdf5_files))

def inspect_hdf5_structure(filepath):
    """Inspect HDF5 file structure without loading all data"""
    results = {
        'file': str(filepath),
        'groups': [],
        'datasets': [],
        'attributes': {},
        'shape_info': {}
    }
    
    try:
        with h5py.File(filepath, 'r') as f:
            # List groups
            def list_items(name, obj):
                if isinstance(obj, h5py.Group):
                    results['groups'].append(name)
                    if obj.attrs:
                        results['attributes'][name] = dict(obj.attrs)
                elif isinstance(obj, h5py.Dataset):
                    results['datasets'].append(name)
                    results['shape_info'][name] = {
                        'shape': obj.shape,
                        'dtype': str(obj.dtype),
                        'size_mb': obj.nbytes / (1024**2)
                    }
            
            f.visititems(list_items)
            
            # Root attributes
            if f.attrs:
                results['attributes']['/'] = dict(f.attrs)
    
    except Exception as e:
        results['error'] = str(e)
    
    return results

def create_inspection_report():
    """Create comprehensive HDF5 inspection report"""
    
    hdf5_files = find_hdf5_files()
    
    if not hdf5_files:
        print("WARNING: No HDF5 files found. Nested archives may not be extracted yet.")
        return None
    
    print(f"Found {len(hdf5_files)} HDF5 files")
    
    report_path = RESULTS_DIR / "HDF5_INSPECTION_REPORT.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# HDF5 Posterior Inspection Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Files inspected:** {len(hdf5_files)}\n\n")
        
        # Summary table
        f.write("## File Overview\n\n")
        f.write("| File | Directory | Size (MB) | Groups | Datasets |\n")
        f.write("|------|-----------|-----------|--------|----------|\n")
        
        detailed_inspections = []
        
        for hdf5_path in hdf5_files:
            rel_path = hdf5_path.relative_to(NESTED_DIR)
            parent_dir = rel_path.parent
            filename = rel_path.name
            
            # Get file size
            size_mb = hdf5_path.stat().st_size / (1024**2)
            
            # Inspect structure
            inspection = inspect_hdf5_structure(hdf5_path)
            detailed_inspections.append((hdf5_path, inspection))
            
            num_groups = len(inspection.get('groups', []))
            num_datasets = len(inspection.get('datasets', []))
            
            f.write(f"| {filename} | {parent_dir} | {size_mb:.1f} | {num_groups} | {num_datasets} |\n")
        
        # Detailed inspection
        f.write("\n## Detailed Structure\n\n")
        
        for hdf5_path, inspection in detailed_inspections:
            rel_path = hdf5_path.relative_to(NESTED_DIR)
            f.write(f"### {rel_path}\n\n")
            
            if 'error' in inspection:
                f.write(f"**Error:** {inspection['error']}\n\n")
                continue
            
            # Root attributes
            if '/' in inspection.get('attributes', {}):
                f.write("**Root Attributes:**\n")
                for key, value in inspection['attributes']['/'].items():
                    f.write(f"- `{key}`: {value}\n")
                f.write("\n")
            
            # Groups
            if inspection.get('groups'):
                f.write(f"**Groups ({len(inspection['groups'])}):**\n")
                for group in sorted(inspection['groups'])[:20]:  # Limit output
                    f.write(f"- `{group}`\n")
                if len(inspection['groups']) > 20:
                    f.write(f"- ... and {len(inspection['groups']) - 20} more\n")
                f.write("\n")
            
            # Datasets (show shapes)
            if inspection.get('datasets'):
                f.write(f"**Datasets ({len(inspection['datasets'])}):**\n")
                f.write("| Dataset | Shape | Dtype | Size (MB) |\n")
                f.write("|---------|-------|-------|-----------|\n")
                
                for dataset in sorted(inspection['datasets']):
                    shape_info = inspection['shape_info'].get(dataset, {})
                    shape = shape_info.get('shape', '?')
                    dtype = shape_info.get('dtype', '?')
                    size_mb = shape_info.get('size_mb', 0)
                    
                    f.write(f"| `{dataset}` | {shape} | {dtype} | {size_mb:.2f} |\n")
                
                f.write("\n")
            
            f.write("---\n\n")
        
        # Key parameters to look for (document for SSZ analysis)
        f.write("## Key Parameters for SSZ Analysis\n\n")
        f.write("Based on HDF5 inspection, look for these parameters in posterior samples:\n\n")
        
        key_params = [
            ("mass_1_source", "Primary mass (source frame)"),
            ("mass_2_source", "Secondary mass (source frame)"),
            ("chirp_mass", "Chirp mass (best measured)"),
            ("chi_eff", "Effective spin"),
            ("chi_p", "Precession"),
            ("final_mass", "Final mass after merger"),
            ("final_spin", "Final spin (for QNM prediction)"),
            ("luminosity_distance", "Distance to source"),
            ("inclination", "Viewing angle"),
            ("log_likelihood", "Sampling likelihood")
        ]
        
        f.write("| Parameter | Description | SSZ Relevance |\n")
        f.write("|-----------|-------------|---------------|\n")
        for param, desc in key_params:
            if param in ['final_mass', 'final_spin']:
                relevance = "CRITICAL: QNM frequency prediction"
            elif param == 'chirp_mass':
                relevance = "Waveform phase evolution"
            elif param == 'chi_eff':
                relevance = "Spin effects on merger"
            else:
                relevance = "Intrinsic source property"
            f.write(f"| `{param}` | {desc} | {relevance} |\n")
        
        f.write("\n## Status\n\n")
        f.write("**INSPECTION COMPLETE**\n\n")
        f.write("Ready for Phase 6: Posterior data loading and comparison.\n")
    
    print(f"Report saved to: {report_path}")
    return report_path

if __name__ == "__main__":
    print("=== HDF5 Inspection Phase 5 ===")
    report = create_inspection_report()
    
    if report:
        print(f"✅ Inspection complete: {report}")
    else:
        print("⚠️  No HDF5 files found. Waiting for nested extraction...")
        print("Run extract_nested_archives.py first.")
