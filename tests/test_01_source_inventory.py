"""Test 01: Source of truth inventory verification."""
import pytest
import sys
from pathlib import Path

# Detect local Linux paths vs old hardcoded Windows paths
IS_WINDOWS = sys.platform.startswith('win')

if not IS_WINDOWS:
    # Safe Linux-compatible paths
    REPO_MAPPING = {
        "SSZ-METRIC_COMPLETE": "/home/error/physics/SSZ-METRIC_COMPLETE",
        "Segmented-Spacetime-Mass-Projection-Unified-Results": "/home/error/physics/Segmented-Spacetime-Mass-Projection-Unified-Results",
        "Segmented-Spacetime-Starmaps": "/home/error/physics/Segmented-Spacetime-Starmaps",
        "frequency-curvature-validation": "/home/error/physics/frequency-curvature-validation",
        "g79-cygnus-tests": "/home/error/physics/g79-cygnus-tests",
        "galactic-year": "/home/error/physics/galactic-year",
        "segmented-calculation-suite": "/home/error/physics/segmented-calculation-suite",
        "segmented-energy": "/home/error/physics/segmented-energy",
        "ssz-all-tests": "/home/error/physics/ssz-all-tests",
        "ssz-complete-documentation": "/home/error/physics/ssz-complete-documentation",
        "ssz-full-metric": "/home/error/physics/ssz-full-metric",
        "ssz-lagrange": "/home/error/physics/ssz-lagrange",
        "ssz-lensing": "/home/error/physics/ssz-lensing",
        "ssz-ligo-tests": "/home/error/physics/ssz-ligo-tests",
        "ssz-metric-final": "/home/error/physics/ssz-metric-final",
        "ssz-metric-pure": "/home/error/physics/ssz-metric-pure",
        "ssz-paper-plots": "/home/error/physics/ssz-paper-plots",
        "ssz-qubits": "/home/error/physics/ssz-qubits",
        "ssz-schumann": "/home/error/physics/ssz-schumann",
        "ssz-trajectories": "/home/error/physics/ssz-trajectories",
    }
else:
    # Windows fallback
    REPO_MAPPING = {
        "book-full-06-papers": r"E:\clone\book-full\06_PAPERS",
        "book-full-v7": r"E:\clone\book-full\05_OUTPUT\V7_BUILD\06_final_v7",
        "ssz-qubit-papers": r"E:\clone\SSZ_QUBIT_PAPERS",
        "ssz-complete-doc": r"E:\clone\ssz-complete-documentation",
        "ssz-all-tests": r"E:\clone\ssz-all-tests",
        "segmented-mass-projection": r"E:\clone\Segmented-Spacetime-Mass-Projection-Unified-Results",
        "ssz-metric-pure": r"E:\clone\ssz-metric-pure",
        "segmented-calc-suite": r"E:\clone\segmented-calculation-suite",
    }

SOURCE_ROOTS = list(REPO_MAPPING.items())


@pytest.mark.corpus
@pytest.mark.parametrize("root_name,root_path", SOURCE_ROOTS)
def test_source_root_exists(root_name, root_path):
    """Each source root must exist."""
    # Skip book-full checks on Linux if raw Windows directories are not present,
    # as we have them converted in /home/error/hilfsdateien/chatgpt/
    if not IS_WINDOWS and "book-full" in root_name:
        pytest.skip("Skipping raw Windows book directory check on Linux")
        
    assert Path(root_path).exists(), f"Source root not found: {root_path}"


@pytest.mark.corpus
@pytest.mark.parametrize("root_name,root_path", SOURCE_ROOTS)
def test_source_root_has_content(root_name, root_path):
    """Each source root must have files."""
    if not IS_WINDOWS and "book-full" in root_name:
        pytest.skip("Skipping raw Windows book directory check on Linux")
        
    root = Path(root_path)
    if not root.exists():
        pytest.skip(f"Root not found: {root_path}")

    files = list(root.rglob('*'))
    assert len(files) > 0, f"No files found in {root_path}"


@pytest.mark.corpus
def test_critical_ssz_book_exists():
    """SSZ_BOOK_DE_CLEAN.md must exist."""
    if not IS_WINDOWS:
        book_path = "/home/error/hilfsdateien/chatgpt/SSZ_BOOK_DE_FINAL_BEST_VERSION.md"
    else:
        book_path = r"E:\clone\book-full\07_BUILD\SSZ_BOOK_DE_CLEAN.md"
        
    assert Path(book_path).exists(), f"SSZ_BOOK_DE_CLEAN.md not found at {book_path}"


@pytest.mark.corpus
def test_critical_pdf_exists():
    """SSZ PDF version must exist."""
    if not IS_WINDOWS:
        pdf_path = "/home/error/hilfsdateien/chatgpt/SSZ_BOOK_DE_FINAL_BEST_VERSION.pdf"
    else:
        pdf_path = r"E:\clone\book-full\05_OUTPUT\V7_BUILD\06_final_v7\SSZ_BOOK_DE_FINAL_V51_PERFECT.pdf"
        
    assert Path(pdf_path).exists(), f"SSZ PDF not found at {pdf_path}"


@pytest.mark.corpus
def test_ssz_metric_pure_is_canonical():
    """ssz-metric-pure is canonical per memory."""
    if not IS_WINDOWS:
        path = "/home/error/physics/ssz-metric-pure"
    else:
        path = r"E:\clone\ssz-metric-pure"
        
    assert Path(path).exists(), f"ssz-metric-pure (canonical) not found at {path}"
