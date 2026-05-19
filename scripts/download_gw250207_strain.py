"""Download GW250207 strain HDF5 files from GWOSC.

GW250207 GPS time: ~1422964625 (S250207bg)
File segment needed: 4096s block containing trigger.

GWOSC open data URL pattern:
  https://gwosc.org/eventapi/json/GWTC-3/...
  or direct:
  https://gwosc.org/archive/links/S250207bg/H1/1422964096/4096/

Run this script once to fetch the strain files.
Requires: requests (already in .venv via standard library urllib)
"""
import urllib.request
import os
from pathlib import Path

# GW250207 trigger GPS: 1422964625.26 (from GWOSC catalog)
# 4096s block: 1422964096 to 1422968192
TRIGGER_GPS = 1422964625.26

OUT_DIR = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW250207-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)

# GWOSC direct HDF5 URLs — 4096s 4kHz files
FILES = [
    (
        "H1",
        "H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1422964096-4096.hdf5",
        ("https://gwosc.org/archive/data/O4/"
         "H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1422964096-4096.hdf5"),
    ),
    (
        "L1",
        "L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1422964096-4096.hdf5",
        ("https://gwosc.org/archive/data/O4/"
         "L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1422964096-4096.hdf5"),
    ),
]


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  Already exists: {dest.name}")
        return True
    print(f"  Downloading: {dest.name}")
    print(f"  URL: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"  Saved: {dest} ({len(data)//1024} KB)")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def run():
    print(f"GW250207 Strain Download")
    print(f"Trigger GPS: {TRIGGER_GPS}")
    print(f"Output dir: {OUT_DIR}")
    print()

    # Try GWOSC event API first to get correct URLs
    import json
    api_url = ("https://gwosc.org/eventapi/json/GWTC-3/GW250207_115645/"
               "?format=json")
    print(f"Checking GWOSC event API: {api_url}")
    try:
        req = urllib.request.Request(api_url,
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            meta = json.loads(resp.read())
        print(f"  Event found: {meta.get('commonName', 'unknown')}")
        # Try to find strain data links
        datasets = meta.get("datasets", [])
        for ds in datasets:
            print(f"    Dataset: {ds}")
    except Exception as e:
        print(f"  API call failed: {e}")

    print()
    print("Attempting direct downloads...")
    for det, fname, url in FILES:
        dest = OUT_DIR / det / "1422964096" / fname
        download(url, dest)

    print()
    print("NOTE: If download fails, manually fetch from:")
    print("  https://gwosc.org/events/GW250207_115645/")
    print("  Download: 4kHz HDF5, 4096s block containing GPS 1422964625")
    print(f"  Place in: {OUT_DIR}/H1/... and {OUT_DIR}/L1/...")


if __name__ == "__main__":
    run()
