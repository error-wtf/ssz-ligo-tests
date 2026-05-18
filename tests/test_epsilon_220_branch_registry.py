"""Test: epsilon_220 branch registry.

Verifies:
- three branches exist
- none is default for claim
- real claim remains blocked
- exploratory values match expected ranges
"""
from ssz_ligo_tests.epsilon_220_registry import (
    epsilon_220_for_real_ligo_claim,
    status,
    epsilon_220_exploratory_options,
    BRANCH_CONFLICT_SUMMARY,
    FORMULA_STATUS,
    READY_FOR_REAL_CLAIM,
)
from ssz_ligo_tests.constants import D_MIN


class TestRegistryConstants:
    def test_formula_status_blocked(self):
        assert FORMULA_STATUS == "BLOCKED_BRANCH_CONFLICT"

    def test_ready_for_claim_no(self):
        assert READY_FOR_REAL_CLAIM == "NO"

    def test_status_blocked(self):
        assert "BLOCKED" in status


class TestRealClaimBlocked:
    def test_epsilon_for_claim_is_none(self):
        assert epsilon_220_for_real_ligo_claim is None

    def test_ligo_claim_not_allowed(self):
        assert BRANCH_CONFLICT_SUMMARY["ligo_claim_allowed"] is False


class TestThreeBranchesExist:
    def test_v51_branch_exists(self):
        assert "v51_ch30_3_percent" in epsilon_220_exploratory_options

    def test_dmin_branch_exists(self):
        assert "dmin_squared_scale" in epsilon_220_exploratory_options

    def test_photon_sphere_branch_exists(self):
        assert "photon_sphere_39_percent" in epsilon_220_exploratory_options


class TestBranchValues:
    def test_v51_is_3_percent(self):
        v = epsilon_220_exploratory_options["v51_ch30_3_percent"]["value"]
        assert abs(v - 0.03) < 0.005

    def test_dmin_squared_matches_constant(self):
        v = epsilon_220_exploratory_options["dmin_squared_scale"]["value"]
        assert abs(v - D_MIN ** 2) < 1e-6

    def test_photon_sphere_is_39_percent(self):
        v = epsilon_220_exploratory_options["photon_sphere_39_percent"]["value"]
        assert abs(v - 0.39) < 0.01

    def test_branches_not_equal(self):
        a = epsilon_220_exploratory_options["v51_ch30_3_percent"]["value"]
        b = epsilon_220_exploratory_options["dmin_squared_scale"]["value"]
        c = epsilon_220_exploratory_options["photon_sphere_39_percent"]["value"]
        assert a != b
        assert b != c
        assert a != c


class TestNoBranchIsDefault:
    def test_no_branch_ligo_compatible(self):
        for name, branch in epsilon_220_exploratory_options.items():
            assert branch["ligo_strain_compatible"] is False, (
                f"Branch {name} incorrectly marked ligo_strain_compatible"
            )
