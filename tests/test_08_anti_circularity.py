"""Test 08: Anti-circularity protections."""
import pytest
from ssz_ligo_tests import (
    CircularityStatus,
    classify_observable_source,
    check_independence,
    flag_posterior_self_consistency_risk,
    FORBIDDEN_POSTERIOR_FIELDS,
    ALLOWED_OBSERVABLES
)


class TestPosteriorFieldsForbidden:
    """Posterior fields are NOT direct observables."""

    @pytest.mark.parametrize("field", FORBIDDEN_POSTERIOR_FIELDS[:5])
    def test_posterior_fields_flagged_invalid(self, field):
        """Posterior fields are INVALID as observables."""
        status = classify_observable_source(field)
        assert status == CircularityStatus.INVALID

    def test_f_from_posterior_invalid(self):
        """H1_only/f is posterior → INVALID."""
        status = classify_observable_source("H1_only/f")
        assert status == CircularityStatus.INVALID

    def test_m_from_posterior_invalid(self):
        """H1_only/m is posterior → INVALID."""
        status = classify_observable_source("H1_only/m")
        assert status == CircularityStatus.INVALID

    def test_chi_from_posterior_invalid(self):
        """H1_only/chi is posterior → INVALID."""
        status = classify_observable_source("H1_only/chi")
        assert status == CircularityStatus.INVALID


class TestStrainAllowed:
    """Strain data IS valid observable."""

    @pytest.mark.parametrize("field", ALLOWED_OBSERVABLES[:3])
    def test_strain_fields_valid(self, field):
        """Strain fields are VALID_INDEPENDENT."""
        status = classify_observable_source(field)
        assert status == CircularityStatus.VALID_INDEPENDENT


class TestKerrNotSSZReference:
    """Kerr formula cannot be SSZ reference."""

    def test_same_source_circular(self):
        """Same source for prediction and measurement = circular."""
        status = check_independence(
            prediction_source="Kerr_formula",
            measured_source="Kerr_formula",
            reference_source="Kerr"
        )
        assert status == CircularityStatus.CIRCULARITY_RISK

    def test_strain_independent(self):
        """Strain is independent of model."""
        status = check_independence(
            prediction_source="SSZ_model",
            measured_source="strain_data",
            reference_source="GR"
        )
        assert status == CircularityStatus.VALID_INDEPENDENT


class TestSelfConsistencyRisk:
    """R_f = f_measured / f_Kerr is circular."""

    def test_r_f_circular(self):
        """R_f test is circular if f_measured from Kerr fit."""
        risk = flag_posterior_self_consistency_risk("H1_only/f")
        assert risk is not None
        assert "circular" in risk.lower() or "posterior" in risk.lower()
