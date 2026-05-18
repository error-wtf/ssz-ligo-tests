"""LIGO data adapter - minimal readonly access to LIGO release data.

IMPORTANT: 
- Never modify raw LIGO data
- Never use FTI/TIGER 0-byte files
- Never load huge datasets by default
- Never use posterior fields as direct observables
"""
import os
import h5py
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple


def scan_ligo_release(root: str) -> Dict:
    """Scan LIGO release directory structure.
    
    Returns:
        Dictionary with file inventory
    """
    root_path = Path(root)
    inventory = {
        'root': str(root_path),
        'hdf5_files': [],
        'posterior_files': [],
        'strain_files': [],
        'ringdown_files': [],
        'qnmrf_files': [],
        'metafiles': [],
        'zero_byte_files': [],
        'total_size_gb': 0
    }
    
    if not root_path.exists():
        return inventory
    
    for item in root_path.rglob('*'):
        if item.is_file():
            size = item.stat().st_size
            
            # Track zero-byte files (FTI/TIGER)
            if size == 0:
                inventory['zero_byte_files'].append(str(item))
                continue
            
            inventory['total_size_gb'] += size / (1024**3)
            
            # Classify by name and extension
            name_lower = item.name.lower()
            
            if item.suffix == '.hdf5' or item.suffix == '.h5':
                inventory['hdf5_files'].append(str(item))
                
                if 'strain' in name_lower:
                    inventory['strain_files'].append(str(item))
                elif 'ringdown' in name_lower:
                    inventory['ringdown_files'].append(str(item))
                elif 'qnm' in name_lower or 'qnmrf' in name_lower:
                    inventory['qnmrf_files'].append(str(item))
                elif 'posterior' in name_lower or 'posterior' in str(item.parent).lower():
                    inventory['posterior_files'].append(str(item))
            
            elif item.suffix in ['.json', '.yaml', '.yml', '.txt']:
                if 'meta' in name_lower:
                    inventory['metafiles'].append(str(item))
    
    return inventory


def classify_ligo_file(path: str) -> str:
    """Classify LIGO file type."""
    name_lower = Path(path).name.lower()
    
    if 'strain' in name_lower:
        return 'STRAIN'
    elif 'ringdown' in name_lower:
        return 'RINGDOWN'
    elif 'qnm' in name_lower or 'qnmrf' in name_lower:
        return 'QNMRF'
    elif 'posterior' in name_lower:
        return 'POSTERIOR'
    elif 'fti' in name_lower or 'tiger' in name_lower:
        return 'FTI_TIGER'
    else:
        return 'UNKNOWN'


def find_hdf5_files(root: str) -> List[str]:
    """Find all HDF5 files in release."""
    root_path = Path(root)
    return [str(f) for f in root_path.rglob('*.hdf5')] + [str(f) for f in root_path.rglob('*.h5')]


def hdf5_structure_summary(path: str, max_depth: int = 2) -> Dict:
    """Get structure summary of HDF5 file without loading data.
    
    Args:
        path: path to HDF5 file
        max_depth: maximum depth to traverse
    
    Returns:
        Dictionary with structure info
    """
    summary = {
        'path': path,
        'groups': [],
        'datasets': [],
        'shape_hints': {},
        'error': None
    }
    
    try:
        with h5py.File(path, 'r') as f:
            def visitor(name, obj, depth=0):
                if depth > max_depth:
                    return
                if isinstance(obj, h5py.Group):
                    summary['groups'].append(name)
                elif isinstance(obj, h5py.Dataset):
                    summary['datasets'].append(name)
                    summary['shape_hints'][name] = obj.shape
            
            f.visititems(lambda name, obj: visitor(name, obj))
    except Exception as e:
        summary['error'] = str(e)
    
    return summary


def identify_real_vs_symlink(path: str) -> Tuple[bool, Optional[str]]:
    """Identify if file is real or symlink.
    
    Returns:
        (is_real, target_if_symlink)
    """
    p = Path(path)
    if p.is_symlink():
        return False, str(p.readlink())
    return True, None


def find_strain_files(root: str) -> List[str]:
    """Find strain data files."""
    inventory = scan_ligo_release(root)
    return inventory['strain_files']


def find_ringdown_files(root: str) -> List[str]:
    """Find ringdown analysis files."""
    inventory = scan_ligo_release(root)
    return inventory['ringdown_files']


def find_qnmrf_files(root: str) -> List[str]:
    """Find QNMRF files."""
    inventory = scan_ligo_release(root)
    return inventory['qnmrf_files']


def load_small_hdf5_dataset(path: str, internal_path: str, 
                            max_size_mb: float = 10.0) -> Optional[np.ndarray]:
    """Load small HDF5 dataset with size limit.
    
    Args:
        path: HDF5 file path
        internal_path: internal dataset path
        max_size_mb: maximum size in MB to load
    
    Returns:
        Data array or None if too large
    """
    try:
        with h5py.File(path, 'r') as f:
            ds = f[internal_path]
            size_mb = ds.nbytes / (1024**2)
            
            if size_mb > max_size_mb:
                print(f"Refusing to load {size_mb:.1f} MB dataset (limit: {max_size_mb} MB)")
                return None
            
            return ds[()]
    except Exception as e:
        print(f"Error loading {path}/{internal_path}: {e}")
        return None


def check_fti_tiger_usable(path: str) -> bool:
    """Check if FTI/TIGER file is usable (not 0-byte).
    
    Returns:
        True if file exists and has content
    """
    if not os.path.exists(path):
        return False
    
    size = os.path.getsize(path)
    if size == 0:
        print(f"WARNING: {path} is 0-byte (FTI/TIGER broken product)")
        return False
    
    return True


def generate_data_availability_report(ligo_root: str) -> str:
    """Generate markdown report of LIGO data availability."""
    inventory = scan_ligo_release(ligo_root)
    
    lines = ["# LIGO Data Availability Report\n\n"]
    lines.append(f"**Root:** {inventory['root']}\n\n")
    lines.append(f"**Total Size:** {inventory['total_size_gb']:.2f} GB\n\n")
    
    lines.append("## File Counts\n\n")
    lines.append(f"- HDF5 files: {len(inventory['hdf5_files'])}\n")
    lines.append(f"- Strain files: {len(inventory['strain_files'])}\n")
    lines.append(f"- Ringdown files: {len(inventory['ringdown_files'])}\n")
    lines.append(f"- QNMRF files: {len(inventory['qnmrf_files'])}\n")
    lines.append(f"- Posterior files: {len(inventory['posterior_files'])}\n")
    lines.append(f"- Metafiles: {len(inventory['metafiles'])}\n\n")
    
    lines.append("## Zero-Byte Files (FTI/TIGER)\n\n")
    lines.append(f"Count: {len(inventory['zero_byte_files'])}\n\n")
    if inventory['zero_byte_files']:
        lines.append("**WARNING:** These files are broken/0-byte and must not be used:\n\n")
        for zf in inventory['zero_byte_files'][:10]:  # Show first 10
            lines.append(f"- {Path(zf).name}\n")
        if len(inventory['zero_byte_files']) > 10:
            lines.append(f"- ... and {len(inventory['zero_byte_files']) - 10} more\n")
    
    lines.append("\n## Usability Summary\n\n")
    lines.append("| Data Type | Status | Notes |\n")
    lines.append("|-----------|--------|-------|\n")
    lines.append(f"| Strain | {'✅' if inventory['strain_files'] else '❌'} | Direct observable |\n")
    lines.append(f"| Ringdown | {'⚠️' if inventory['ringdown_files'] else '❌'} | Model-dependent |\n")
    lines.append(f"| Posterior | {'⚠️' if inventory['posterior_files'] else '❌'} | NOT direct observable |\n")
    lines.append(f"| FTI/TIGER | {'❌' if inventory['zero_byte_files'] else '✅'} | Broken if 0-byte |\n")
    
    return "".join(lines)


if __name__ == "__main__":
    # Test with actual LIGO data root
    LIGO_ROOT = r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    report = generate_data_availability_report(LIGO_ROOT)
    print(report)
