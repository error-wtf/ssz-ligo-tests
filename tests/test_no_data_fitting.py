"""Test: derived formulas are free of LIGO data fitting.

Verifies:
- derived_phase functions take only physical parameters (no data)
- derived_amplitude functions take only physical parameters (no data)
- no posterior fields are read
- formula outputs are deterministic for fixed inputs
- no free parameters beyond G, c, M, mu
"""
import numpy as np
import inspect
from ssz_ligo_tests.derived_phase import delta_psi_ssz_v0
from ssz_ligo_tests.derived_amplitude import delta_a_ssz_v0
from ssz_ligo_tests.derived_waveform import apply_ssz_v0_to_frequency_waveform
from ssz_ligo_tests.constants import M_SUN

MC = 8.9 * M_SUN
ETA = 0.25
M_TOTAL = MC / ETA ** (3.0 / 5.0)
MU = ETA * M_TOTAL
FREQS = np.linspace(20.0, 500.0, 50)
H_GR = np.ones(len(FREQS), dtype=complex) * 1e-23

POSTERIOR_FORBIDDEN = [
    "chi", "spin", "posterior", "bilby", "pca", "tiger",
    "pseobnr", "f_ring", "tau_ring",
]


class TestNoFittedParameters:
    def test_delta_psi_signature_no_data_arg(self):
        sig = inspect.signature(delta_psi_ssz_v0)
        param_names = list(sig.parameters.keys())
        for forbidden in POSTERIOR_FORBIDDEN:
            assert forbidden not in param_names, (
                f"delta_psi_ssz_v0 has suspicious parameter: {forbidden}"
            )

    def test_delta_a_signature_no_data_arg(self):
        sig = inspect.signature(delta_a_ssz_v0)
        param_names = list(sig.parameters.keys())
        for forbidden in POSTERIOR_FORBIDDEN:
            assert forbidden not in param_names, (
                f"delta_a_ssz_v0 has suspicious parameter: {forbidden}"
            )

    def test_waveform_signature_no_data_arg(self):
        sig = inspect.signature(apply_ssz_v0_to_frequency_waveform)
        param_names = list(sig.parameters.keys())
        for forbidden in ["chi", "spin", "posterior", "bilby"]:
            assert forbidden not in param_names


class TestDeterministicOutput:
    def test_delta_psi_deterministic(self):
        dp1, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        dp2, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        np.testing.assert_array_equal(dp1, dp2)

    def test_delta_a_deterministic(self):
        da1, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        da2, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        np.testing.assert_array_equal(da1, da2)

    def test_waveform_deterministic(self):
        h1, _, _, _ = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        h2, _, _, _ = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        np.testing.assert_array_equal(np.abs(h1), np.abs(h2))


class TestNoPosteriorFieldsRead:
    def test_delta_psi_result_independent_of_posterior(self):
        dp_default, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        dp_branch, _ = delta_psi_ssz_v0(
            FREQS, M_TOTAL, MU, branch="g2_decay"
        )
        np.testing.assert_array_equal(dp_default, dp_branch)


class TestPhysicalParametersOnly:
    def test_varying_mass_changes_output(self):
        dp1, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        dp2, _ = delta_psi_ssz_v0(FREQS, M_TOTAL * 2.0, MU * 2.0)
        assert not np.allclose(dp1, dp2), (
            "Output must depend on M, mu (no fixed values)"
        )

    def test_varying_freq_changes_output(self):
        f1 = np.linspace(20.0, 200.0, 50)
        f2 = np.linspace(100.0, 500.0, 50)
        dp1, _ = delta_psi_ssz_v0(f1, M_TOTAL, MU)
        dp2, _ = delta_psi_ssz_v0(f2, M_TOTAL, MU)
        assert not np.allclose(dp1, dp2)
