"""Test: Posterior R_f is INVALID_FOR_SSZ.

Verifies that using H1_only/f,m,chi as an SSZ verdict raises or returns
INVALID_FOR_SSZ — never a support/falsification claim.

Source: docs/EPSILON_220_BRANCH_LOCK.md §Posterior R_f
        anti_circularity.py
"""
import pytest
from ssz_ligo_tests.anti_circularity import (
    classify_observable_source,
    CircularityStatus,
)


POSTERIOR_RF_LABELS = [
    "H1_only/f",
    "H1_only/m",
    "H1_only/chi",
    "online_posterior_samples",
    "pseobnr/samples",
    "posterior_f_220",
    "posterior_m_final",
    "posterior_chi_final",
]

VALID_STRAIN_LABELS = [
    "H1/strain",
    "L1/strain",
]


class TestPosteriorRfInvalid:
    @pytest.mark.parametrize("label", POSTERIOR_RF_LABELS)
    def test_posterior_label_is_invalid(self, label):
        status = classify_observable_source(label)
        assert status == CircularityStatus.INVALID, (
            f"Label '{label}' should be INVALID but got {status}"
        )

    def test_posterior_cannot_be_ssz_verdict(self):
        for label in POSTERIOR_RF_LABELS:
            status = classify_observable_source(label)
            assert status != CircularityStatus.VALID_INDEPENDENT, (
                f"Posterior label '{label}' must never be VALID_INDEPENDENT"
            )


class TestValidStrainLabels:
    @pytest.mark.parametrize("label", VALID_STRAIN_LABELS)
    def test_strain_label_is_valid(self, label):
        status = classify_observable_source(label)
        assert status == CircularityStatus.VALID_INDEPENDENT, (
            f"Strain label '{label}' should be VALID_INDEPENDENT, got {status}"
        )


class TestRingdownKerr:
    """Kerr-internal consistency check is not an SSZ test."""

    def test_ringdown_posterior_is_invalid(self):
        for label in ["ringdown/f_220", "ringdown/tau_220", "qnmrf/H1"]:
            status = classify_observable_source(label)
            assert status in (
                CircularityStatus.INVALID,
                CircularityStatus.CIRCULARITY_RISK,
            ), (
                f"Ringdown posterior '{label}' should be INVALID or "
                f"CIRCULARITY_RISK, got {status}"
            )
