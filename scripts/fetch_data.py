#!/usr/bin/env python3
"""
Fetch Data Script for SSZ-LIGO Test Suite
Downloads the GW240925 strain data from Zenodo (Record 18600070)
and extracts the HDF5 files to the expected location.
"""
import sys
import urllib.request
import tarfile
from pathlib import Path

ZENODO_RECORD = "18600070"
TAR_URL = f"https://zenodo.org/api/records/{ZENODO_RECORD}/files/GW240925-C00-Strain.tar/content"

# Target paths resolved dynamically relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = REPO_ROOT.parent / "ligo-gw240925-gw250207-release"
RECORD_DIR = BASE_DIR / ZENODO_RECORD
TAR_PATH = RECORD_DIR / "GW240925-C00-Strain.tar"
EXTRACT_DIR = RECORD_DIR / "GW240925-C00-Strain"

# Expected HDF5 files for verification
EXPECTED_FILES = [
    EXTRACT_DIR / "GW240925-C00-Strain" / "O4b4DiscC00_4KHZ_R1" / "STRAIN_HDF" / "H1" / "1410334720" / "H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5",
    EXTRACT_DIR / "GW240925-C00-Strain" / "O4b4DiscC00_16KHZ_R1" / "STRAIN_HDF" / "H1" / "1410334720" / "H-H1_GWOSC_O4b4DiscC00_16KHZ_R1-1411260416-4096.hdf5",
    EXTRACT_DIR / "GW240925-C00-Strain" / "O4b4DiscC00_4KHZ_R1" / "STRAIN_HDF" / "L1" / "1410334720" / "L-L1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5",
    EXTRACT_DIR / "GW240925-C00-Strain" / "O4b4DiscC00_16KHZ_R1" / "STRAIN_HDF" / "L1" / "1410334720" / "L-L1_GWOSC_O4b4DiscC00_16KHZ_R1-1411260416-4096.hdf5",
    EXTRACT_DIR / "GW240925-C00-Strain" / "O4b4DiscC00_4KHZ_R1" / "STRAIN_HDF" / "V1" / "1410334720" / "V-V1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5",
    EXTRACT_DIR / "GW240925-C00-Strain" / "O4b4DiscC00_16KHZ_R1" / "STRAIN_HDF" / "V1" / "1410334720" / "V-V1_GWOSC_O4b4DiscC00_16KHZ_R1-1411260416-4096.hdf5",
]


def check_files_exist():
    return all(p.exists() for p in EXPECTED_FILES)


def download_tar():
    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    if TAR_PATH.exists():
        # Check if the file size is reasonable (expecting ~2.4 GB)
        size = TAR_PATH.stat().st_size
        if size > 2000 * 1024 * 1024:
            print(f"Tar file already exists and is complete: {TAR_PATH} ({size / 1024 / 1024:.1f} MB)")
            return True
        else:
            print(f"Tar file exists but seems incomplete ({size / 1024 / 1024:.1f} MB). Re-downloading...")

    print("Downloading GW240925 C00 Strain Tar from Zenodo...")
    print(f"URL: {TAR_URL}")
    print(f"Dest: {TAR_PATH}")

    headers = {"User-Agent": "Mozilla/5.0 ssz-ligo-tests/1.0"}
    req = urllib.request.Request(TAR_URL, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 1024 * 1024  # 1 MB blocks
            downloaded = 0

            with open(TAR_PATH, 'wb') as out_file:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        # Print progress every 100 MB or at completion
                        if downloaded % (100 * block_size) == 0 or downloaded == total_size:
                            print(f"  Downloaded: {downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB ({percent:.1f}%)", flush=True)
                    else:
                        if downloaded % (100 * block_size) == 0:
                            print(f"  Downloaded: {downloaded / 1024 / 1024:.1f} MB", flush=True)

            print("Download completed successfully.")
            return True
    except Exception as e:
        print(f"Error during download: {e}", file=sys.stderr)
        if TAR_PATH.exists():
            TAR_PATH.unlink()  # Remove incomplete file
        return False


def extract_tar():
    print(f"Extracting tar file to {EXTRACT_DIR}...")
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(TAR_PATH, 'r') as tar:
            # We can print some progress during extraction
            members = tar.getmembers()
            total = len(members)
            print(f"  Extracting {total} items...")
            for i, member in enumerate(members, 1):
                tar.extract(member, path=EXTRACT_DIR)
                if i % 10 == 0 or i == total:
                    print(f"  Extracted {i}/{total} items", flush=True)
        print("Extraction completed successfully.")
        return True
    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        return False


def main():
    print(f"\n{'='*60}")
    print("SSZ-LIGO DATA FETCH PIPELINE")
    print(f"{'='*60}")

    if check_files_exist():
        print("[OK] All 6 GW240925 HDF5 strain files are already present.")
        print("Skipping download and extraction.")
        return True

    print("Some or all GW240925 HDF5 files are missing. Starting fetch...")

    if not download_tar():
        print("[FAIL] FAILED to download data tar.", file=sys.stderr)
        return False

    if not extract_tar():
        print("[FAIL] FAILED to extract data tar.", file=sys.stderr)
        return False

    if check_files_exist():
        print("[OK] Successfully fetched and verified all 6 HDF5 files.")
        return True
    else:
        print("[FAIL] Extraction completed, but some expected files are still missing!", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
