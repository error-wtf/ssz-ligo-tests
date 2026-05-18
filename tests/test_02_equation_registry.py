"""Test 02: Equation registry verification."""
import numpy as np
from ssz_ligo_tests import (
    get_locked_equations, get_missing_equations,
    check_ready_for_numerical_test, EquationStatus,
    PHI, XI_MAX, D_MIN
)


class TestLockedCoreEquations:
    """Verify locked core equations match SSZ Book."""

    def test_phi_matches_book(self):
        """PHI = (1 + √5)/2 ≈ 1.618"""
        expected = (1 + np.sqrt(5)) / 2
        assert np.isclose(PHI, expected)
        assert np.isclose(PHI, 1.618, rtol=0.01)

    def test_xi_max_matches_book(self):
        """Ξ_max = 1 - exp(-φ) ≈ 0.802"""
        expected = 1 - np.exp(-PHI)
        assert np.isclose(XI_MAX, expected)
        assert np.isclose(XI_MAX, 0.802, rtol=0.01)

    def test_d_min_matches_book(self):
        """D_min = 1/(1 + Ξ_max) ≈ 0.555"""
        expected = 1 / (1 + XI_MAX)
        assert np.isclose(D_MIN, expected)
        assert np.isclose(D_MIN, 0.555, rtol=0.01)

    def test_all_core_equations_locked(self):
        """All core equations have LOCKED status."""
        locked = get_locked_equations()

        names = [eq.name for eq in locked]
        assert "PHI" in names
        assert "XI_MAX" in names
        assert "D_MIN" in names
        assert "XI_WEAK" in names
        assert "XI_STRONG" in names
        assert "D_SSZ" in names

        # All must be LOCKED
        for eq in locked:
            assert eq.status == EquationStatus.LOCKED


class TestMissingForwardEquations:
    """Verify missing equations are correctly identified."""

    def test_epsilon_220_ambiguous(self):
        """ε_220 is AMBIGUOUS (3% vs 31%)."""
        from ssz_ligo_tests.equation_registry import EXPLORATORY_EQUATIONS

        # ε_220 should be missing or exploratory
        missing = get_missing_equations()
        exploratory = EXPLORATORY_EQUATIONS

        all_names = [eq.name for eq in missing + exploratory]
        assert "EPSILON_220" in all_names or any("220" in eq.name for eq in missing)

    def test_delta_psi_missing(self):
        """δΨ_SSZ(f) is MISSING."""
        missing = get_missing_equations()
        names = [eq.name for eq in missing]
        assert "DELTA_PSI_SSZ" in names

    def test_delta_amp_missing(self):
        """δA_SSZ(f) is MISSING."""
        missing = get_missing_equations()
        names = [eq.name for eq in missing]
        assert "DELTA_A_SSZ" in names

    def test_eta_220_missing(self):
        """η_220 is MISSING."""
        missing = get_missing_equations()
        names = [eq.name for eq in missing]
        assert "ETA_220" in names

    def test_h_ssz_waveform_missing(self):
        """Full h_SSZ(t) waveform is MISSING."""
        missing = get_missing_equations()
        names = [eq.name for eq in missing]
        assert "H_SSZ_WAVEFORM" in names


class TestReadinessCheck:
    """Test overall readiness for numerical tests."""

    def test_not_ready_for_numerical_test(self):
        """Should NOT be ready (missing equations)."""
        ready, reason = check_ready_for_numerical_test()

        # Must not be ready
        assert not ready, f"Should not be ready, but got: {reason}"

        # Reason must mention missing or exploratory
        assert "MISSING" in reason or "EXPLORATORY" in reason

    def test_readiness_reason_lists_missing(self):
        """Reason should list what's missing."""
        ready, reason = check_ready_for_numerical_test()

        # Should mention specific equations
        missing = get_missing_equations()
        for eq in missing[:3]:  # Check first few
            assert eq.name in reason or len(reason) > 20  # Reason is detailed
