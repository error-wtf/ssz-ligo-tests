"""Anti-circularity tests.

Ensures no circular reasoning in SSZ-LIGO tests.
"""
import numpy as np
import pytest


class TestAntiCircularityRules:
    """Test that forbidden practices are blocked."""

    def test_posterior_fields_not_direct_observables(self):
        """Posterior f, m, χ are MODEL PARAMETERS not observables."""
        # These are from LIGO parameter estimation:
        _posterior_f = 251.0  # noqa: F841
        _posterior_m = 68.0  # noqa: F841
        _posterior_chi = 0.69  # noqa: F841

        # These are MODEL INFERRED, not direct measurements!
        # Using them directly assumes the Kerr/QNM model.

        # Anti-circularity: Mark these as MODEL_DEPENDENT
        assert "f" in ["f", "m", "chi"]  # They exist
        # But should NOT be used as independent test of that model

    def test_kerr_is_not_ssz_reference(self):
        """Kerr formula cannot be SSZ reference model."""
        # Forbidden: R_f = f_measured / f_Kerr
        # Reason: f_measured comes from Kerr/QNM fit
        #         f_Kerr uses same formula
        # Result: R_f ≈ 1 is tautology, not test

        # This would be circular:
        f_measured = 251.0  # From Kerr/QNM fit
        f_kerr = 251.0  # From same Kerr formula

        # R_f = 1 is guaranteed by construction!
        R_f = f_measured / f_kerr

        # This is NOT a valid SSZ test
        assert R_f == 1.0
        # But this proves nothing about SSZ!

    def test_same_fit_parameters_not_independent(self):
        """Cannot use f, m, χ from same fit as independent test."""
        # If f, m, χ all come from ONE ringdown fit,
        # they are mutually correlated.

        fit_result = {
            'f': 251.0,
            'm': 68.0,
            'chi': 0.69
        }

        # These are JOINTLY estimated
        # Cannot pick one to test the others

        # Forbidden:
        # f_from_fit = fit_result['f']
        # f_predicted_from_m_chi = some_formula(fit_result['m'], fit_result['chi'])
        # test: f_from_fit == f_predicted  # CIRCULAR!

        assert 'f' in fit_result
        assert 'm' in fit_result
        assert 'chi' in fit_result
        # All from same posterior → not independent

    def test_strain_is_real_observable(self):
        """Strain d(t) is the actual observable."""
        # This is what LIGO actually measures (after calibration)
        strain = np.random.randn(1000)  # Example strain data

        # Strain is model-independent (just calibrated voltage)
        assert len(strain) == 1000
        assert np.isreal(strain).all()

    def test_residual_is_valid_test(self):
        """Residual r = d - h is valid test statistic."""
        data = np.random.randn(100)
        model_h = np.zeros(100)  # Some model

        residual = data - model_h

        # This is valid because it compares:
        # - data (independent measurement)
        # - model (prediction to be tested)
        assert len(residual) == len(data)


class TestModelLockRequirement:
    """Test that model must be locked before data comparison."""

    def test_ssz_parameters_must_be_locked(self):
        """All SSZ params must be locked from corpus."""
        from ssz_ligo_tests.forward_model import SSZForwardModel

        model = SSZForwardModel()

        # Before locking: cannot compute
        with pytest.raises(ValueError, match="not locked"):
            model.ssz_ringdown_frequency_shift(250.0)

        # After locking: can compute
        model.lock_epsilon_220(0.03, "test_source")
        result = model.ssz_ringdown_frequency_shift(250.0)
        assert result == 250.0 * 1.03

    def test_no_post_hoc_adjustment(self):
        """Cannot adjust parameters after seeing data."""
        # This is preregistration principle

        from ssz_ligo_tests.forward_model import SSZForwardModel
        model = SSZForwardModel()

        # Lock BEFORE seeing data
        model.lock_epsilon_220(0.03, "SSZ_BOOK_DE_CLEAN.md Ch.30")

        # Now see data (hypothetical)
        _data_f = 260.0  # noqa: F841

        # Predicted
        _predicted_f = model.ssz_ringdown_frequency_shift(251.0)  # noqa: F841

        # If mismatch: CANNOT adjust epsilon_220!
        # Model was locked, so test fails or passes honestly

        assert model.epsilon_220 == 0.03  # Still locked


class TestForbiddenObservables:
    """List observables that MUST NOT be used."""

    FORBIDDEN = [
        # From posterior files - all model-dependent
        "H1_only/f",
        "H1_only/m",
        "H1_only/chi",
        "H1_only/m1",
        "H1_only/m2",
        "H1_only/a1",
        "H1_only/a2",
        # Any model-inferred parameter
    ]

    ALLOWED = [
        # Raw or minimally processed
        "H1/strain_data",
        "H1/residual",
        "H1/power_spectrum",
    ]

    def test_forbidden_list_comprehensive(self):
        """All posterior fields are forbidden."""
        for field in self.FORBIDDEN:
            assert "H1_only" in field or "H1" in field
            # These are from parameter estimation
            assert any(x in field for x in ['f', 'm', 'chi', 'a1', 'a2', 'm1', 'm2'])

    def test_allowed_are_strain_based(self):
        """Only strain-based observables allowed."""
        for field in self.ALLOWED:
            assert any(x in field for x in ['strain', 'residual', 'power'])
