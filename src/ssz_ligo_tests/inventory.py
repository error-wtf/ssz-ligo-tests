"""Source of Truth Inventory for SSZ-LIGO Test Suite.

This module inventories all 8 SSZ source roots.
"""
import os
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


SOURCE_ROOTS = [
    ("book-full-06-papers", r"E:\clone\book-full\06_PAPERS"),
    ("book-full-v7", r"E:\clone\book-full\05_OUTPUT\V7_BUILD\06_final_v7"),
    ("ssz-qubit-papers", r"E:\clone\SSZ_QUBIT_PAPERS"),
    ("ssz-complete-doc", r"E:\clone\ssz-complete-documentation"),
    ("ssz-all-tests", r"E:\clone\ssz-all-tests"),
    ("segmented-mass-projection", r"E:\clone\Segmented-Spacetime-Mass-Projection-Unified-Results"),
    ("ssz-metric-pure", r"E:\clone\ssz-metric-pure"),
    ("segmented-calc-suite", r"E:\clone\segmented-calculation-suite"),
]

RELEVANT_EXTENSIONS = {
    '.md', '.txt', '.tex', '.pdf', '.py', '.ipynb',
    '.json', '.csv', '.yaml', '.yml', '.html'
}


def classify_role(filename: str) -> str:
    """Classify file role based on name and extension."""
    fname_lower = filename.lower()
    ext = Path(filename).suffix.lower()
    
    if 'test' in fname_lower:
        return 'test'
    elif ext == '.pdf':
        if 'paper' in fname_lower or 'ssz' in fname_lower:
            return 'paper'
        return 'document'
    elif ext in ['.md', '.tex']:
        if 'formula' in fname_lower or 'equation' in fname_lower:
            return 'formula'
        elif 'theory' in fname_lower or 'foundation' in fname_lower:
            return 'theory'
        elif 'validation' in fname_lower or 'test' in fname_lower:
            return 'validation'
        return 'documentation'
    elif ext == '.py':
        if 'test' in fname_lower:
            return 'test'
        return 'code'
    elif ext in ['.json', '.yaml', '.yml']:
        return 'config'
    elif ext in ['.csv']:
        return 'data'
    elif ext == '.ipynb':
        return 'notebook'
    else:
        return 'unknown'


def inventory_root(root_name: str, root_path: str) -> List[Dict]:
    """Inventory a single source root."""
    records = []
    root = Path(root_path)
    
    if not root.exists():
        return [{
            'root': root_name,
            'full_path': root_path,
            'error': 'PATH_NOT_FOUND',
            'file_count': 0
        }]
    
    for item in root.rglob('*'):
        if item.is_file():
            ext = item.suffix.lower()
            if ext in RELEVANT_EXTENSIONS or ext == '':
                try:
                    stat = item.stat()
                    record = {
                        'root': root_name,
                        'full_path': str(item),
                        'relative_path': str(item.relative_to(root)),
                        'extension': ext,
                        'size_bytes': stat.st_size,
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'role': classify_role(item.name),
                        'error': ''
                    }
                    records.append(record)
                except (OSError, PermissionError) as e:
                    records.append({
                        'root': root_name,
                        'full_path': str(item),
                        'relative_path': str(item.relative_to(root)),
                        'extension': ext,
                        'size_bytes': -1,
                        'modified_time': '',
                        'role': 'unknown',
                        'error': str(e)
                    })
    
    return records


def run_inventory() -> Tuple[List[Dict], Dict]:
    """Run complete inventory of all 8 source roots."""
    all_records = []
    summary = {
        'timestamp': datetime.now().isoformat(),
        'roots_scanned': 0,
        'roots_found': 0,
        'total_files': 0,
        'by_root': {},
        'by_extension': {},
        'by_role': {}
    }
    
    for root_name, root_path in SOURCE_ROOTS:
        records = inventory_root(root_name, root_path)
        all_records.extend(records)
        
        summary['roots_scanned'] += 1
        if records and records[0].get('error') != 'PATH_NOT_FOUND':
            summary['roots_found'] += 1
            summary['by_root'][root_name] = len(records)
            summary['total_files'] += len(records)
        else:
            summary['by_root'][root_name] = 0
    
    # Count by extension and role
    for record in all_records:
        ext = record.get('extension', 'none')
        summary['by_extension'][ext] = summary['by_extension'].get(ext, 0) + 1
        
        role = record.get('role', 'unknown')
        summary['by_role'][role] = summary['by_role'].get(role, 0) + 1
    
    return all_records, summary


def save_inventory_csv(records: List[Dict], output_path: str):
    """Save inventory to CSV."""
    if not records:
        return
    
    fieldnames = ['root', 'full_path', 'relative_path', 'extension', 
                  'size_bytes', 'modified_time', 'role', 'error']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def save_summary_md(summary: Dict, output_path: str):
    """Save summary as Markdown."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# SSZ Source of Truth Inventory Summary\n\n")
        f.write(f"**Timestamp:** {summary['timestamp']}\n\n")
        f.write(f"**Roots Scanned:** {summary['roots_scanned']}\n")
        f.write(f"**Roots Found:** {summary['roots_found']}\n")
        f.write(f"**Total Files:** {summary['total_files']}\n\n")
        
        f.write("## Files by Root\n\n")
        for root, count in summary['by_root'].items():
            f.write(f"- **{root}:** {count} files\n")
        
        f.write("\n## Files by Extension\n\n")
        for ext, count in sorted(summary['by_extension'].items(), 
                                  key=lambda x: x[1], reverse=True)[:20]:
            f.write(f"- **{ext or '(none)'}:** {count}\n")
        
        f.write("\n## Files by Role\n\n")
        for role, count in sorted(summary['by_role'].items(), 
                                   key=lambda x: x[1], reverse=True):
            f.write(f"- **{role}:** {count}\n")


if __name__ == "__main__":
    records, summary = run_inventory()
    
    # Save outputs
    save_inventory_csv(records, 
        r"E:\clone\ssz-ligo-tests\data_manifest\source_of_truth_inventory.csv")
    save_summary_md(summary, 
        r"E:\clone\ssz-ligo-tests\docs\SOURCE_OF_TRUTH_INVENTORY.md")
    
    print(f"Inventory complete:")
    print(f"  Roots: {summary['roots_found']}/{summary['roots_scanned']}")
    print(f"  Files: {summary['total_files']}")
