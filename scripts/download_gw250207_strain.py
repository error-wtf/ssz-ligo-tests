"""Download GW250207 strain HDF5 files from GWOSC.

GW250207 GPS time: ~1422964625.26 (S250207bg)

Uses GWOSC API v2 to discover the correct strain file URLs:
  https://gwosc.org/api/v2/events/GW250207_115645/strain-files/

Then downloads 4096s 4kHz HDF5 files for H1 and L1.

Run this script once before running run_gw250207_comparison.py.
"""
import json
import urllib.request
from pathlib import Path

TRIGGER_GPS = 1422964625.26
EVENT_NAME = "GW250207_115645"

OUT_DIR = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW250207-Strain\O4b4DiscC00_4KHZ_R1\STRAIN_HDF"
)

HEADERS = {"User-Agent": "Mozilla/5.0 ssz-ligo-tests/1.0"}


def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def download_file(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        sz = dest.stat().st_size // 1024
        print(f"  Already exists: {dest.name} ({sz} KB)")
        return True
    print(f"  Downloading: {url}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"  Saved: {dest.name} ({len(data)//1024} KB)")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def discover_urls():
    """Use GWOSC API v2 to find strain file URLs for the event."""
    # API v2 event strain files endpoint
    api_url = f"https://gwosc.org/api/v2/events/{EVENT_NAME}/strain-files/"
    print(f"Querying GWOSC API v2: {api_url}")
    try:
        data = api_get(api_url)
        results = data.get("results", [])
        print(f"  Found {len(results)} strain file entries")
        urls = {"H1": [], "L1": []}
        for r in results:
            url = r.get("hdf5_url") or r.get("url", "")
            det = r.get("detector", "")
            fmt = r.get("format", "")
            rate = r.get("sampling_rate", 0)
            dur = r.get("duration", 0)
            if fmt == "hdf5" and rate == 4096 and dur == 4096:
                if det in ("H1", "L1"):
                    urls[det].append((url, r.get("gps_start", 0)))
                    print(f"    {det}: {url}")
        return urls
    except Exception as e:
        print(f"  API v2 failed: {e}")
        return {"H1": [], "L1": []}


def run():
    print("GW250207 Strain Download")
    print(f"Trigger GPS: {TRIGGER_GPS}")
    print(f"Output dir : {OUT_DIR}")
    print()

    urls = discover_urls()

    # If API found files, download them
    downloaded = {"H1": False, "L1": False}
    for det in ("H1", "L1"):
        for url, gps_start in urls[det]:
            fname = url.split("/")[-1]
            dest = OUT_DIR / det / str(gps_start) / fname
            if download_file(url, dest):
                downloaded[det] = True
                break

    print()
    if all(downloaded.values()):
        print("Download complete. Run:")
        print("  python scripts/run_gw250207_comparison.py")
    else:
        missing = [d for d, ok in downloaded.items() if not ok]
        print(f"Still missing: {missing}")
        print()
        print("Manual download instructions:")
        url_ev = f"https://gwosc.org/eventapi/html/GWTC-3/{EVENT_NAME}/"
        print(f"  1. Go to: {url_ev}")
        print("  2. Download: 4kHz HDF5, 4096s blocks for H1 and L1")
        print(f"  3. Place H1 file in: {OUT_DIR / 'H1'}")
        print(f"  4. Place L1 file in: {OUT_DIR / 'L1'}")
        print()
        print("Alternative — fetch via GWOSC data API:")
        print("  https://gwosc.org/api/v2/datasets/events/O4/?format=json")


if __name__ == "__main__":
    run()
