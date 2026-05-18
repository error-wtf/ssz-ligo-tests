"""Test ringdown conflict detection - BLOCKED status."""
import pytest
import numpy as np
from ssz_ligo_tests import (
    RINGDOWN_MODEL_STATUS,
    CONFLICTING_SOURCES,
    get_ringdown_conflict_report,
    check_ringdown_usable,
    ssz_ringdown_frequency_shift,
    epsilon_220_from_corpus,
    D_MIN
)


class TestRingdownStatus:
    """Verify ringdown is marked BLOCKED."""

    def test_status_is_conflicting(self):
        """RINGDOWN_MODEL_STATUS is CONFLICTING_SSZ_SOURCES."""
        assert RINGDOWN_MODEL_STATUS == "CONFLICTING_SSZ_SOURCES"

    def test_conflicting_sources_defined(self):
        """Three conflicting sources are documented."""
        assert "source_a_3_percent" in CONFLICTING_SOURCES
        assert "source_b_31_percent" in CONFLICTING_SOURCES
        assert "source_c_39_percent" in CONFLICTING_SOURCES

    def test_source_a_is_3_percent(self):
        """Source A: ~3%."""
        source = CONFLICTING_SOURCES["source_a_3_percent"]
        assert source["value"] == 0.03

    def test_source_b_is_31_percent(self):
        """Source B: ~D_min² ≈ 31%."""
        source = CONFLICTING_SOURCES["source_b_31_percent"]
        expected = D_MIN ** 2  # ≈ 0.308
        assert np.isclose(source["value"], expected, rtol=0.01)

    def test_source_c_is_39_percent(self):
        """Source C: ~39% at photon sphere."""
        source = CONFLICTING_SOURCES["source_c_39_percent"]
        assert source["value"] == 0.39

    def test_factor_10_difference(self):
        """Source A vs B differ by factor ~10."""
        val_a = CONFLICTING_SOURCES["source_a_3_percent"]["value"]
        val_b = CONFLICTING_SOURCES["source_b_31_percent"]["value"]
        ratio = val_b / val_a
        assert ratio > 5  # Significant discrepancy


class TestCheckRingdownUsable:
    """Verify ringdown usability check fails."""

    def test_returns_not_usable(self):
        """check_ringdown_usable() returns False."""
        usable, reason = check_ringdown_usable()
        assert not usable

    def test_reason_mentions_conflict(self):
        """Reason mentions conflicting sources."""
        usable, reason = check_ringdown_usable()
        assert "CONFLICTING" in reason or "BLOCKED" in reason


class TestRingdownFunctionRaises:
    """Verify ringdown functions raise errors."""

    def test_ssz_ringdown_frequency_shift_raises(self):
        """ssz_ringdown_frequency_shift always raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ssz_ringdown_frequency_shift(250.0)

        assert "CONFLICTING" in str(exc_info.value) or "BLOCKED" in str(exc_info.value)

    def test_error_includes_conflict_report(self):
        """Error message includes conflict details."""
        with pytest.raises(ValueError) as exc_info:
            ssz_ringdown_frequency_shift(250.0)

        error_msg = str(exc_info.value)
        # Should mention the conflicting sources
        assert "3%" in error_msg or "31%" in error_msg or "39%" in error_msg

    def test_epsilon_220_from_corpus_raises(self):
        """epsilon_220_from_corpus raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            epsilon_220_from_corpus()

        assert "CONFLICTING" in str(exc_info.value)


class TestConflictReport:
    """Test conflict report generation."""

    def test_report_includes_all_sources(self):
        """Report documents all three conflicting sources."""
        report = get_ringdown_conflict_report()

        assert "3%" in report
        assert "31%" in report or "0.31" in report or "D_min" in report
        assert "39%" in report or "1.39" in report

    def test_report_asks_resolution_questions(self):
        """Report asks resolution questions."""
        report = get_ringdown_conflict_report()

        assert "Which source" in report
        assert "interferometer" in report.lower() or "QNM" in report
