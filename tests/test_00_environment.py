"""Test 00: Environment and basic imports."""


def test_import_ssz_ligo():
    """Can import the ssz_ligo_tests package."""
    import ssz_ligo_tests as slt
    assert slt.__version__ == "0.2.0"


def test_constants_available():
    """Core constants are available."""
    from ssz_ligo_tests import PHI, XI_MAX, D_MIN, N0
    assert PHI > 1.6 and PHI < 1.7
    assert XI_MAX > 0.8 and XI_MAX < 0.81
    assert D_MIN > 0.55 and D_MIN < 0.56
    assert N0 == 4


def test_core_functions_available():
    """Core functions are importable."""
    from ssz_ligo_tests import (
        xi_weak, xi_strong, d_ssz
    )
    assert callable(xi_weak)
    assert callable(xi_strong)
    assert callable(d_ssz)


def test_equation_registry_available():
    """Equation registry is accessible."""
    from ssz_ligo_tests import (
        get_locked_equations, get_missing_equations,
        check_ready_for_numerical_test
    )

    locked = get_locked_equations()
    _ = get_missing_equations()

    # Should have locked core equations
    assert len(locked) > 0

    # Check if ready for numerical test
    ready, reason = check_ready_for_numerical_test()
    # Should NOT be ready (missing forward equations)
    assert not ready
    assert "MISSING" in reason or "EXPLORATORY" in reason
