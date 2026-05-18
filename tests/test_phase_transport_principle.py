"""Tests for the SSZ-LIGO Phase Transport Principle.

Branch: PHASE_TRANSPORT_BRANCH
Status: DERIVED_V0_CONCEPTUAL
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO

Tests:
  1. Co-scaling argument: local Xi unobservable when optics co-scale
  2. Relative phase: ΔΦ = Φ_x - Φ_y is the only observable
  3. U(1) transport: exp(iΦ), relative holonomy exp(iΔΦ)
  4. SO(2) rotation: R(θ), relative rotation R_rel = R_y^{-1} R_x
  5. Full transport U(1)×SO(2): separates phase and frame twist
  6. GR recovery: theta=0, scale=1 → standard Michelson
  7. SSZ source-frame: scale/twist modifies h+/hx before projection
  8. Phase-to-strain formula
  9. Path dependence: retarded integral vs instantaneous
 10. Claim gate: DERIVED_V0_CONCEPTUAL labels enforced
"""
import sys
import numpy as np
import numpy.testing as npt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ssz_ligo_tests.phase_transport import photon_phase_arm  # noqa: E402, F401
from ssz_ligo_tests.phase_transport import (  # noqa: E402
    relative_phase,
    phase_to_strain,
    transport_operator_u1,
    relative_transport_u1,
    rotation_operator_so2,
    relative_rotation,
    coscaling_argument,
    full_transport,
    gr_michelson_response,
    ssz_source_frame_response,
    C_LIGHT,
    L_LIGO,
    LAMBDA_LIGO,
)

FS = 4096.0
T_SEC = 0.25
N = int(FS * T_SEC)
T = np.arange(N) / FS
H0 = 1e-21
F_GW = 100.0
F_PLUS = 0.5
F_CROSS = 0.5 * np.sqrt(3)


class TestCoScalingArgument:
    """Principle 1: local co-scaling is not directly observable."""

    def test_unit_fringe_ratio_under_coscaling(self):
        result = coscaling_argument(xi_local=1e-4)
        assert result["coscaled_fringe_ratio"] == 1.0, (
            "Co-scaled fringe count must be unchanged"
        )

    def test_is_coscaled_unobservable_flag(self):
        result = coscaling_argument(xi_local=0.1667)
        assert result["is_coscaled_unobservable"] is True

    def test_earth_xi_negligible(self):
        # r_s ~ 90m, r_det ~ 1 AU
        r_s = 90.0
        r_det = 1.5e11
        xi_earth = r_s / (2 * r_det)
        result = coscaling_argument(xi_local=xi_earth)
        assert result["observable_local_correction"] < 1e-8, (
            f"Xi at Earth should be < 1e-8, got {xi_earth:.2e}"
        )

    def test_coscaling_fringe_ratio_independent_of_xi(self):
        for xi in [1e-10, 1e-4, 0.1, 0.5]:
            result = coscaling_argument(xi)
            assert result["coscaled_fringe_ratio"] == 1.0

    def test_s_d_values_consistent(self):
        xi = 0.1667
        result = coscaling_argument(xi)
        assert abs(result["s"] - (1 + xi)) < 1e-14
        assert abs(result["D"] - 1 / (1 + xi)) < 1e-14
        assert abs(result["s_over_D"] - (1 + xi)**2) < 1e-12


class TestRelativePhase:
    """Principle 2: ΔΦ is the only observable."""

    def test_difference_of_arms(self):
        phi_x = np.array([1.0, 2.0, 3.0])
        phi_y = np.array([0.5, 1.5, 2.5])
        dphi = relative_phase(phi_x, phi_y)
        npt.assert_allclose(dphi, [0.5, 0.5, 0.5])

    def test_equal_arms_gives_zero(self):
        phi = np.sin(2 * np.pi * F_GW * T) * 1e-5
        dphi = relative_phase(phi, phi)
        npt.assert_allclose(dphi, 0.0, atol=1e-30)

    def test_sign_convention(self):
        # x-arm sees +h, y-arm sees -h → ΔΦ = 2 * Φ_x_contribution
        phi_x = np.array([1.0])
        phi_y = np.array([-1.0])
        dphi = relative_phase(phi_x, phi_y)
        npt.assert_allclose(dphi, [2.0])

    def test_global_offset_cancels(self):
        offset = 1e5   # large DC offset in both arms
        phi_x = np.array([1.0 + offset, 2.0 + offset])
        phi_y = np.array([0.5 + offset, 1.5 + offset])
        dphi = relative_phase(phi_x, phi_y)
        npt.assert_allclose(dphi, [0.5, 0.5], atol=1e-10)


class TestPhaseToStrain:

    def test_formula(self):
        dphi = 1.0
        h = phase_to_strain(dphi, LAMBDA_LIGO, L_LIGO)
        expected = LAMBDA_LIGO / (2.0 * np.pi * L_LIGO)
        assert abs(h - expected) < 1e-30

    def test_zero_phase_zero_strain(self):
        h = phase_to_strain(np.zeros(5), LAMBDA_LIGO, L_LIGO)
        npt.assert_allclose(h, 0.0, atol=1e-40)

    def test_linearity(self):
        dphi = np.array([1.0, 2.0, 3.0])
        h = phase_to_strain(dphi, LAMBDA_LIGO, L_LIGO)
        npt.assert_allclose(h[1], 2 * h[0], rtol=1e-12)
        npt.assert_allclose(h[2], 3 * h[0], rtol=1e-12)


class TestU1Transport:
    """U(1) phase transport operator."""

    def test_zero_phase_gives_unity(self):
        u = transport_operator_u1(0.0)
        assert abs(u - 1.0) < 1e-15

    def test_pi_phase_gives_minus_one(self):
        u = transport_operator_u1(np.pi)
        assert abs(u - (-1.0)) < 1e-14

    def test_unit_modulus(self):
        for phi in [0.1, 0.5, np.pi, 2.0]:
            u = transport_operator_u1(phi)
            assert abs(abs(u) - 1.0) < 1e-14

    def test_relative_transport_extracts_delta_phi(self):
        phi_x = 1.3
        phi_y = 0.8
        u_x = transport_operator_u1(phi_x)
        u_y = transport_operator_u1(phi_y)
        u_rel, dphi = relative_transport_u1(u_x, u_y)
        assert abs(dphi - (phi_x - phi_y)) < 1e-13

    def test_relative_transport_equal_arms_zero(self):
        phi = 2.5
        u = transport_operator_u1(phi)
        u_rel, dphi = relative_transport_u1(u, u)
        assert abs(dphi) < 1e-14

    def test_relative_transport_array(self):
        phi_x = np.array([0.1, 0.5, 1.0])
        phi_y = np.array([0.05, 0.3, 0.7])
        u_x = transport_operator_u1(phi_x)
        u_y = transport_operator_u1(phi_y)
        _, dphi = relative_transport_u1(u_x, u_y)
        npt.assert_allclose(dphi, phi_x - phi_y, atol=1e-12)


class TestSO2FrameRotation:
    """SO(2) frame twist operator."""

    def test_identity_at_zero(self):
        R = rotation_operator_so2(0.0)
        npt.assert_allclose(R, np.eye(2), atol=1e-15)

    def test_determinant_one(self):
        for theta in [0.1, 0.5, np.pi / 4, np.pi]:
            R = rotation_operator_so2(theta)
            assert abs(np.linalg.det(R) - 1.0) < 1e-14

    def test_orthogonal(self):
        for theta in [0.3, 1.0, 2.0]:
            R = rotation_operator_so2(theta)
            npt.assert_allclose(R @ R.T, np.eye(2), atol=1e-14)

    def test_relative_rotation_zero_when_equal(self):
        R_rel, delta_theta = relative_rotation(0.3, 0.3)
        assert abs(delta_theta) < 1e-14
        npt.assert_allclose(R_rel, np.eye(2), atol=1e-14)

    def test_relative_rotation_is_difference(self):
        theta_x, theta_y = 0.4, 0.1
        R_rel, delta_theta = relative_rotation(theta_x, theta_y)
        assert abs(delta_theta - (theta_x - theta_y)) < 1e-14
        R_expected = rotation_operator_so2(theta_x - theta_y)
        npt.assert_allclose(R_rel, R_expected, atol=1e-14)

    def test_so2_is_abelian(self):
        # R_y^{-1} R_x = R(theta_x - theta_y) for abelian SO(2)
        t1, t2 = 0.7, 0.2
        R1 = rotation_operator_so2(t1)
        R2 = rotation_operator_so2(t2)
        R_rel_direct, _ = relative_rotation(t1, t2)
        R_rel_matrix = np.linalg.inv(R2) @ R1
        npt.assert_allclose(R_rel_direct, R_rel_matrix, atol=1e-14)


class TestFullTransport:
    """Combined U(1) × SO(2) transport."""

    def test_zero_twist_matches_phase_only(self):
        phi_x = np.array([0.5, 1.0, 1.5])
        phi_y = np.array([0.2, 0.8, 1.2])
        dphi, R_rel, dtheta, u_rel = full_transport(phi_x, phi_y, 0.0, 0.0)
        npt.assert_allclose(dphi, phi_x - phi_y, atol=1e-14)
        assert abs(dtheta) < 1e-14
        npt.assert_allclose(R_rel, np.eye(2), atol=1e-14)

    def test_equal_arms_zero_observable(self):
        phi = np.array([1.0, 2.0])
        dphi, R_rel, dtheta, u_rel = full_transport(phi, phi, 0.2, 0.2)
        npt.assert_allclose(dphi, 0.0, atol=1e-14)
        assert abs(dtheta) < 1e-14

    def test_separability_phase_and_rotation(self):
        phi_x, phi_y = 1.0, 0.7
        theta_x, theta_y = 0.3, 0.1
        dphi, R_rel, dtheta, _ = full_transport(
            phi_x, phi_y, theta_x, theta_y
        )
        assert abs(dphi - (phi_x - phi_y)) < 1e-14
        assert abs(dtheta - (theta_x - theta_y)) < 1e-14


class TestGRRecovery:
    """GR Michelson response in the no-SSZ limit."""

    def test_instantaneous_response_correlated(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        h_det, _, _, _ = gr_michelson_response(
            h_plus, h_cross, 1.0, 0.0, t_grid=None
        )
        corr = float(np.corrcoef(h_det, h_plus)[0, 1])
        assert corr > 0.99, f"GR recovery correlation too low: {corr:.4f}"

    def test_retarded_response_correlated(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        h_det, phi_x, phi_y, dphi = gr_michelson_response(
            h_plus, h_cross, 1.0, 0.0,
            L=L_LIGO, c=C_LIGHT, t_grid=T, n_steps=100
        )
        # ΔΦ should be correlated with h_plus
        corr = float(np.corrcoef(dphi, h_plus)[0, 1])
        assert corr > 0.99, (
            f"Retarded GR response should correlate with h+: {corr:.4f}"
        )

    def test_phi_x_minus_phi_y_gives_delta_phi(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        _, phi_x, phi_y, dphi = gr_michelson_response(
            h_plus, h_cross, 1.0, 0.0, t_grid=T, n_steps=80
        )
        npt.assert_allclose(dphi, phi_x - phi_y, atol=1e-40)

    def test_cross_polarization_antenna_pattern(self):
        h_plus = np.zeros(N)
        h_cross = H0 * np.sin(2 * np.pi * F_GW * T)
        h_det, _, _, _ = gr_michelson_response(
            h_plus, h_cross, F_PLUS, F_CROSS, t_grid=None
        )
        # h_cross contribution from F×
        npt.assert_allclose(h_det, F_CROSS * h_cross, atol=1e-40)


class TestSSZSourceFrameResponse:
    """SSZ source-frame modification."""

    def test_gr_limit_theta_zero_scale_one(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        h_ssz, h_gr, _, _, meta = ssz_source_frame_response(
            h_plus, h_cross, F_PLUS, F_CROSS,
            scale=1.0, theta=0.0
        )
        npt.assert_allclose(h_ssz, h_gr, atol=1e-40)
        assert meta["delta_h_rms"] == 0.0

    def test_scale_only_amplifies(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        h_ssz, h_gr, _, _, meta = ssz_source_frame_response(
            h_plus, h_cross, F_PLUS, F_CROSS,
            scale=1.3, theta=0.0
        )
        ratio = meta["h_det_ssz_rms"] / meta["h_det_gr_rms"]
        assert abs(ratio - 1.3) < 1e-12, (
            f"Scale=1.3 should amplify by 1.3, got ratio={ratio:.6f}"
        )

    def test_twist_mixes_polarizations(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        _, _, h_plus_ssz, h_cross_ssz, _ = ssz_source_frame_response(
            h_plus, h_cross, F_PLUS, F_CROSS,
            scale=1.0, theta=0.1
        )
        # Twist should generate non-zero h_cross even from pure h_plus input
        assert float(np.max(np.abs(h_cross_ssz))) > 0, (
            "Twist should mix h+ into h×"
        )

    def test_twist_preserves_total_power(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = H0 * 0.5 * np.cos(2 * np.pi * F_GW * T)
        for theta in [0.1, 0.3, np.pi / 4]:
            _, _, h_p_ssz, h_c_ssz, _ = ssz_source_frame_response(
                h_plus, h_cross, F_PLUS, F_CROSS,
                scale=1.0, theta=theta
            )
            power_in = float(np.mean(h_plus**2 + h_cross**2))
            power_out = float(np.mean(h_p_ssz**2 + h_c_ssz**2))
            assert abs(power_out / power_in - 1.0) < 1e-12, (
                f"Twist alone (scale=1) must preserve total power at "
                f"theta={theta:.2f}: ratio={power_out/power_in:.8f}"
            )

    def test_delta_h_grows_with_theta(self):
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        diffs = []
        for theta in [0.01, 0.05, 0.1, 0.2]:
            _, _, _, _, meta = ssz_source_frame_response(
                h_plus, h_cross, F_PLUS, F_CROSS,
                scale=1.0, theta=theta
            )
            diffs.append(meta["delta_h_rms"])
        assert all(diffs[i] < diffs[i + 1] for i in range(len(diffs) - 1)), (
            f"delta_h should grow with theta: {diffs}"
        )

    def test_detector_null_without_plus_cross(self):
        # h+ = 0, h× = 0 → h_det = 0 regardless of SSZ
        h_zero = np.zeros(N)
        h_ssz, h_gr, _, _, _ = ssz_source_frame_response(
            h_zero, h_zero, F_PLUS, F_CROSS,
            scale=2.0, theta=0.5
        )
        npt.assert_allclose(h_ssz, 0.0, atol=1e-40)
        npt.assert_allclose(h_gr, 0.0, atol=1e-40)


class TestClaimGate:

    def test_module_labels(self):
        from ssz_ligo_tests import phase_transport as pt
        src = pt.__doc__
        assert "DERIVED_V0_CONCEPTUAL" in src
        assert "READY_FOR_REAL_LIGO_SSZ_CLAIM: NO" in src
        assert "SSZ_SUPPORT_CLAIM_MADE: NO" in src

    def test_no_posterior_parameters(self):
        # All functions accept only synthetic/physical inputs
        h_plus = H0 * np.sin(2 * np.pi * F_GW * T)
        h_cross = np.zeros_like(h_plus)
        result = ssz_source_frame_response(
            h_plus, h_cross, F_PLUS, F_CROSS,
            scale=1.0, theta=0.0
        )
        assert result is not None
        assert len(result) == 5
