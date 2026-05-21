"""
Bulk-add UNVERIFIED_DERIVED_REPORT banner to all unverified reports.
Reads target list from _banner_targets.txt.
"""
import os

REPORTS_DIR = r"E:\clone\ssz-ligo-tests\reports"
TARGETS_FILE = os.path.join(REPORTS_DIR, 'progress', '_banner_targets.txt')

BANNER = """⚠️ STATUS: UNVERIFIED_DERIVED_REPORT (2026-05-20 Bingsi/Hermes) ⚠️
⚠️ HDF5→Command→Log→CSV→Report provenance chain NOT VERIFIED. ⚠️
⚠️ Do NOT cite numbers from this report without re-verification. ⚠️
⚠️ See reports/progress/REPORT_STATUS_INDEX.md for current classification. ⚠️

"""

with open(TARGETS_FILE, 'r') as f:
    targets = [line.strip() for line in f if line.strip()]

print(f"Processing {len(targets)} files...")
count = 0
errors = 0

for fname in targets:
    fp = os.path.join(REPORTS_DIR, fname)
    if not os.path.exists(fp):
        print(f"  SKIP (not found): {fname}")
        continue

    try:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            original = f.read()

        # Check if it already has a banner
        if 'UNVERIFIED_DERIVED_REPORT' in original[:500]:
            print(f"  SKIP (already has): {fname}")
            continue

        # Check if it starts with a markdown heading or frontmatter
        # Insert banner after any YAML frontmatter or right at the top
        if original.startswith('---'):
            # Has YAML frontmatter — insert after closing ---
            end_fm = original.find('---\n', 3)
            if end_fm != -1:
                new_content = original[:end_fm+4] + '\n' + BANNER + original[end_fm+4:]
            else:
                new_content = BANNER + original
        elif original.startswith('# ') or original.startswith('## '):
            # Has markdown heading — insert after first heading line
            first_nl = original.find('\n')
            if first_nl != -1:
                new_content = original[:first_nl+1] + '\n' + BANNER + original[first_nl+1:]
            else:
                new_content = BANNER + original
        else:
            new_content = BANNER + original

        with open(fp, 'w', encoding='utf-8', newline='') as f:
            f.write(new_content)

        count += 1
        print(f"  BANNERED: {fname}")

    except Exception as e:
        errors += 1
        print(f"  ERROR: {fname}: {e}")

print(f"\nDone: {count} bannered, {errors} errors")
