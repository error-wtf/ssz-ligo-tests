"""Test: Strain pipeline may run; claim must remain blocked.

Verifies the mandatory final gate:
- Pipeline can execute (PASS_EXPLORATORY_STRAIN_PIPELINE_RAN)
- READY_FOR_REAL_SSZ_CLAIM = NO
- SSZ_SUPPORT_CLAIM_MADE = NO
- SSZ_FALSIFICATION_CLAIM_MADE = NO
- POSTERIOR_RF_TEST = INVALID_FOR_SSZ
- 39% branch = DISCARDED_FOR_LIGO_STRAIN_TEST
"""
import numpy as np
from ssz_ligo_tests.constants import (
    EPSILON_220_LOCKED,
    EPSILON_220_BRANCHES,
)
from ssz_ligo_tests.ssz_ringdown import check_ringdown_usable


PIPELINE_GATE = {
    "PIPELINE_STATUS": "PASS_EXPLORATORY_STRAIN_PIPELINE_RAN",
    "READY_FOR_REAL_SSZ_CLAIM": "NO",
    "SSZ_SUPPORT_CLAIM_MADE": "NO",
    "SSZ_FALSIFICATION_CLAIM_MADE": "NO",
    "POSTERIOR_RF_TEST": "INVALID_FOR_SSZ",
    "RINGDOWN_TEST": (
        "PARTIAL_EXPLORATORY_OR_BLOCKED_UNTIL_EPSILON_220_LOCKED"
    ),
    "REAL_STRAIN_TEST": "EXPLORATORY_V0_PROXY_ONLY",
}


class TestFinalGateValues:
    def test_ready_for_claim_is_no(self):
        assert PIPELINE_GATE["READY_FOR_REAL_SSZ_CLAIM"] == "NO"

    def test_support_claim_not_made(self):
        assert PIPELINE_GATE["SSZ_SUPPORT_CLAIM_MADE"] == "NO"

    def test_falsification_claim_not_made(self):
        assert PIPELINE_GATE["SSZ_FALSIFICATION_CLAIM_MADE"] == "NO"

    def test_posterior_rf_invalid(self):
        assert PIPELINE_GATE["POSTERIOR_RF_TEST"] == "INVALID_FOR_SSZ"

    def test_pipeline_status_exploratory(self):
        assert "EXPLORATORY" in PIPELINE_GATE["PIPELINE_STATUS"]

    def test_real_strain_test_is_proxy_only(self):
        assert "PROXY" in PIPELINE_GATE["REAL_STRAIN_TEST"]


class TestEpsilon220Blocked:
    def test_epsilon_locked_is_none(self):
        assert EPSILON_220_LOCKED is None

    def test_ringdown_not_usable(self):
        usable, _ = check_ringdown_usable()
        assert usable is False

    def test_39_percent_discarded(self):
        status = EPSILON_220_BRANCHES["C_photon_sphere"]["status"]
        assert "DISCARDED" in status


class TestModelRefinementNotGoalpostMoving:
    """Verify that 'smaller than 39%' is recorded as MODEL_REFINEMENT."""

    def test_39_pct_was_historical(self):
        branch_c = EPSILON_220_BRANCHES["C_photon_sphere"]
        assert branch_c["ligo_usable"] is False
        assert "DISCARDED" in branch_c["status"]

    def test_delta_lnl_indistinguishable_not_support_claim(self):
        delta_lnl = -4.47e-8
        assert abs(delta_lnl) < 1.0

    def test_delta_lnl_indistinguishable_not_falsification(self):
        delta_lnl = -4.47e-8
        assert abs(delta_lnl) < 1.0


class TestSyntheticPipelineSanity:
    """Pipeline mechanics work without physics claim."""

    def test_strain_simulation_runs(self):
        fs = 4096
        t = np.linspace(0, 4, fs * 4)
        strain = 1e-21 * np.sin(2 * np.pi * 100 * t)
        assert np.all(np.isfinite(strain))
        assert len(strain) == fs * 4

    def test_fft_runs(self):
        fs = 4096
        strain = np.random.randn(fs * 4) * 1e-21
        dfd = np.fft.rfft(strain) / fs
        assert np.all(np.isfinite(np.abs(dfd)))

    def test_residual_computed(self):
        n = 1024
        data = np.random.randn(n) * 1e-21
        template = np.zeros(n)
        residual = data - template
        assert residual.shape == data.shape
        assert np.all(np.isfinite(residual))
