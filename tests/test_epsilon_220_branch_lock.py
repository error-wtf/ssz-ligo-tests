"""Test: epsilon_220 branch lock.

Verifies:
- Three branches (3%, 31%, 39%) are NOT interchangeable
- EPSILON_220_LOCKED is None by default
- No ringdown claim allowed without explicit lock
- Branch C (39%) is marked DISCARDED_FOR_LIGO_STRAIN_TEST
- ssz_ringdown_frequency_shift raises without explicit epsilon

Source: docs/EPSILON_220_BRANCH_LOCK.md
"""
import pytest
from ssz_ligo_tests.constants import (
    EPSILON_220_LOCKED, EPSILON_220_BRANCHES
)
from ssz_ligo_tests.ssz_ringdown import (
    ssz_ringdown_frequency_shift,
    check_ringdown_usable,
    RINGDOWN_MODEL_STATUS,
)


class TestBranchLockDefaults:
    def test_epsilon_220_locked_is_none(self):
        assert EPSILON_220_LOCKED is None

    def test_ringdown_status_is_conflicting(self):
        assert RINGDOWN_MODEL_STATUS == "CONFLICTING_SSZ_SOURCES"

    def test_three_branches_defined(self):
        keys = set(EPSILON_220_BRANCHES.keys())
        assert "A_v51_ch30" in keys
        assert "B_dmin_squared" in keys
        assert "C_photon_sphere" in keys

    def test_no_branch_is_ligo_usable(self):
        for name, branch in EPSILON_220_BRANCHES.items():
            assert branch["ligo_usable"] is False, (
                f"Branch {name} is incorrectly marked ligo_usable=True"
            )


class TestBranchValuesNotInterchangeable:
    def test_branch_a_is_3_percent(self):
        val = EPSILON_220_BRANCHES["A_v51_ch30"]["value"]
        assert abs(val - 0.03) < 0.005

    def test_branch_b_is_about_31_percent(self):
        val = EPSILON_220_BRANCHES["B_dmin_squared"]["value"]
        assert 0.28 < val < 0.35

    def test_branch_c_is_39_percent(self):
        val = EPSILON_220_BRANCHES["C_photon_sphere"]["value"]
        assert abs(val - 0.39) < 0.01

    def test_branches_not_equal(self):
        a = EPSILON_220_BRANCHES["A_v51_ch30"]["value"]
        b = EPSILON_220_BRANCHES["B_dmin_squared"]["value"]
        c = EPSILON_220_BRANCHES["C_photon_sphere"]["value"]
        assert a != b
        assert b != c
        assert a != c


class TestBranchCDiscarded:
    def test_branch_c_status_is_discarded(self):
        status = EPSILON_220_BRANCHES["C_photon_sphere"]["status"]
        assert "DISCARDED" in status, (
            f"Branch C status should contain DISCARDED, got: {status}"
        )

    def test_branch_c_not_ligo_usable(self):
        assert EPSILON_220_BRANCHES["C_photon_sphere"]["ligo_usable"] is False


class TestRingdownBlocked:
    def test_frequency_shift_raises_without_epsilon(self):
        with pytest.raises((ValueError, NotImplementedError)):
            ssz_ringdown_frequency_shift(100.0)

    def test_check_ringdown_usable_returns_false(self):
        usable, reason = check_ringdown_usable()
        assert usable is False
        assert len(reason) > 0

    def test_explicit_epsilon_allowed(self):
        f_ssz = ssz_ringdown_frequency_shift(100.0, epsilon_220=0.03)
        assert abs(f_ssz - 103.0) < 0.01

    def test_branches_a_b_c_give_different_results(self):
        f_gr = 100.0
        f_a = ssz_ringdown_frequency_shift(f_gr, epsilon_220=0.03)
        f_b = ssz_ringdown_frequency_shift(
            f_gr,
            epsilon_220=EPSILON_220_BRANCHES["B_dmin_squared"]["value"]
        )
        f_c = ssz_ringdown_frequency_shift(f_gr, epsilon_220=0.39)
        assert f_a != f_b
        assert f_b != f_c
        assert f_a != f_c
