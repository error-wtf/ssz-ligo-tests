"""Test 01: Source of truth inventory verification."""
import pytest
from pathlib import Path


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


@pytest.mark.corpus
@pytest.mark.parametrize("root_name,root_path", SOURCE_ROOTS)
def test_source_root_exists(root_name, root_path):
    """Each source root must exist."""
    assert Path(root_path).exists(), f"Source root not found: {root_path}"


@pytest.mark.corpus
@pytest.mark.parametrize("root_name,root_path", SOURCE_ROOTS)
def test_source_root_has_content(root_name, root_path):
    """Each source root must have files."""
    root = Path(root_path)
    if not root.exists():
        pytest.skip(f"Root not found: {root_path}")

    files = list(root.rglob('*'))
    assert len(files) > 0, f"No files found in {root_path}"


@pytest.mark.corpus
def test_critical_ssz_book_exists():
    """SSZ_BOOK_DE_CLEAN.md must exist."""
    book_path = r"E:\clone\book-full\07_BUILD\SSZ_BOOK_DE_CLEAN.md"
    assert Path(book_path).exists(), "SSZ_BOOK_DE_CLEAN.md not found"


@pytest.mark.corpus
def test_critical_pdf_exists():
    """SSZ PDF version must exist."""
    pdf_path = r"E:\clone\book-full\05_OUTPUT\V7_BUILD\06_final_v7\SSZ_BOOK_DE_FINAL_V51_PERFECT.pdf"
    assert Path(pdf_path).exists(), "SSZ PDF not found"


@pytest.mark.corpus
def test_ssz_metric_pure_is_canonical():
    """ssz-metric-pure is canonical per memory."""
    # From memory: ssz-metric-pure is canonical
    # ssz-full-metric was just the development path
    path = r"E:\clone\ssz-metric-pure"
    assert Path(path).exists(), "ssz-metric-pure (canonical) not found"
