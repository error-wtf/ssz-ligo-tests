"""Tests for the Source/Propagation SSZ Twist Branch.

Branch: SOURCE_PROPAGATION_TWIST_BRANCH
Status: DERIVED_V0_CONCEPTUAL
LOCAL_ARM_TWIST_STATUS: CLOSED_NEGLIGIBLE
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO

Tests:
  1.  theta=0 recovers scale-only (GR in limit scale=1, theta=0)
  2.  SO(2) rotation: power h+^2+hx^2 conserved before scale
  3.  SO(2) rotation: identity at theta=0
  4.  SO(2) rotation: inverse at -theta
  5.  SO(2) rotation: composition R(a+b) = R(a) R(b)
  6.  H1/L1 projections respond differently under twist
  7.  H1/L1 ratio shifts with theta (differential response)
  8.  Scale-only: both detectors scale by same factor
  9.  theta_constant returns flat array
  10. theta_xi_proxy: increases toward merger (higher f -> smaller r -> higher Xi)
  11. theta_rsg_proxy: monotonically increasing with f, tanh shape
  12. theta_rsg_proxy: f_char has correct Kepler value
  13. detector_projection: linearity in (F+, Fx)
  14. detector_projection: zero at zero antenna pattern
  15. apply_source_scale_twist: scale=1, theta=0 is identity
  16. apply_source_scale_twist: scale factor applies uniformly
  17. compare_scale_only_vs_scale_twist: returns one row per theta
  18. compare_scale_only_vs_scale_twist: theta=0 row matches scale-only
  19. compare_scale_only_vs_scale_twist: h1_l1_ratio_shift grows with |theta|
  20. compare_scale_only_vs_scale_twist: resid_vs_scale grows with |theta|
  21. Synthetic PSD: positive everywhere
  22. Synthetic lnL: zero for perfect model match
  23. No posterior parameters in any function signature
  24. LOCAL_ARM_TWIST not applied
  25. Claim gate: status labels correct
"""
import sys
import numpy as np
import numpy.testing as npt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ssz_ligo_tests.source_propagation_twist import (
    theta_constant,
    theta_xi_proxy,
    theta_rsg_proxy,
    rotate_polarizations,
    apply_source_scale_twist,
    detector_projection,
    compare_scale_only_vs_scale_twist,
    synthetic_asd_ligo,
    SOURCE_PROPAGATION_TWIST_STATUS,
    LOCAL_ARM_TWIST_STATUS,
    G_NEWTON,
    C_LIGHT,
    M_SUN,
)

FS = 4096.0
T_SEC = 0.5
N = int(FS * T_SEC)
FREQS = np.fft.rfftfreq(N, 1.0 / FS)
FREQS_POS = FREQS[FREQS > 0]

M_TOT = 20.0 * M_SUN
RS = 2 * G_NEWTON * M_TOT / C_LIGHT**2

F_PLUS_H1 = 0.592
F_CROSS_H1 = 0.344
F_PLUS_L1 = 0.437
F_CROSS_L1 = 0.683

RNG = np.random.default_rng(42)
HP_GR = RNG.standard_normal(len(FREQS_POS)) + 1j * RNG.standard_normal(len(FREQS_POS))
HX_GR = RNG.standard_normal(len(FREQS_POS)) + 1j * RNG.standard_normal(len(FREQS_POS))
HP_GR *= 1e-23
HX_GR *= 1e-23

THETA_SCAN = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1]
SCALE = 0.95


class TestThetaParametrisations:

    def test_theta_constant_flat(self):
        theta, status = theta_constant(FREQS_POS, 0.1)
        npt.assert_allclose(theta, 0.1, atol=1e-15)
        assert len(theta) == len(FREQS_POS)

    def test_theta_constant_zero(self):
        theta, _ = theta_constant(FREQS_POS, 0.0)
        npt.assert_allclose(theta, 0.0, atol=1e-15)

    def test_theta_constant_status(self):
        _, status = theta_constant(FREQS_POS, 0.05)
        assert status == "THETA_CONSTANT_PROXY"

    def test_theta_xi_proxy_shape(self):
        theta, r_arr, xi_arr, status = theta_xi_proxy(
            FREQS_POS, M_TOT, RS, alpha=1.0
        )
        assert len(theta) == len(FREQS_POS)
        assert len(r_arr) == len(FREQS_POS)
        assert len(xi_arr) == len(FREQS_POS)

    def test_theta_xi_proxy_status(self):
        _, _, _, status = theta_xi_proxy(FREQS_POS, M_TOT, RS)
        assert status == "THETA_XI_PROXY"

    def test_theta_xi_proxy_increases_with_freq(self):
        # Higher f -> smaller r -> larger Xi -> larger theta
        f_test = np.array([20.0, 50.0, 100.0, 150.0])
        theta, r_arr, _, _ = theta_xi_proxy(f_test, M_TOT, RS, alpha=1.0)
        assert r_arr[0] > r_arr[-1], "Larger f -> smaller r"
        assert theta[0] < theta[-1], "Larger f -> larger theta"

    def test_theta_xi_proxy_alpha_scales(self):
        t1, _, _, _ = theta_xi_proxy(FREQS_POS, M_TOT, RS, alpha=1.0)
        t2, _, _, _ = theta_xi_proxy(FREQS_POS, M_TOT, RS, alpha=2.0)
        npt.assert_allclose(t2, 2.0 * t1, rtol=1e-12)

    def test_theta_rsg_proxy_shape(self):
        theta, xi_char, f_char, status = theta_rsg_proxy(
            FREQS_POS, M_TOT, RS, alpha=1.0
        )
        assert len(theta) == len(FREQS_POS)
        assert xi_char > 0
        assert f_char > 0

    def test_theta_rsg_proxy_status(self):
        _, _, _, status = theta_rsg_proxy(FREQS_POS, M_TOT, RS)
        assert status == "THETA_RSG_PROXY"

    def test_theta_rsg_proxy_monotone(self):
        f_test = np.linspace(20.0, 200.0, 50)
        theta, _, _, _ = theta_rsg_proxy(f_test, M_TOT, RS, alpha=1.0)
        assert np.all(np.diff(theta) >= 0), "RSG proxy must be monotone increasing"

    def test_theta_rsg_proxy_f_char_kepler(self):
        r_char = 3.0 * RS
        expected_f_char = (1.0 / np.pi) * np.sqrt(G_NEWTON * M_TOT / r_char**3)
        _, _, f_char, _ = theta_rsg_proxy(FREQS_POS, M_TOT, RS)
        assert abs(f_char - expected_f_char) / expected_f_char < 1e-10

    def test_theta_rsg_proxy_alpha_scales(self):
        t1, _, _, _ = theta_rsg_proxy(FREQS_POS, M_TOT, RS, alpha=1.0)
        t2, _, _, _ = theta_rsg_proxy(FREQS_POS, M_TOT, RS, alpha=0.5)
        npt.assert_allclose(t2, 0.5 * t1, rtol=1e-12)


class TestRotatePolarizations:

    def test_identity_at_zero(self):
        hp_r, hx_r = rotate_polarizations(HP_GR, HX_GR, 0.0)
        npt.assert_allclose(hp_r, HP_GR, atol=1e-40)
        npt.assert_allclose(hx_r, HX_GR, atol=1e-40)

    def test_power_conserved(self):
        for theta in [0.01, 0.1, 0.5, np.pi / 4]:
            hp_r, hx_r = rotate_polarizations(HP_GR, HX_GR, theta)
            power_in = float(np.sum(np.abs(HP_GR)**2 + np.abs(HX_GR)**2))
            power_out = float(np.sum(np.abs(hp_r)**2 + np.abs(hx_r)**2))
            assert abs(power_out / power_in - 1.0) < 1e-12, (
                f"Power not conserved at theta={theta}: ratio={power_out/power_in}"
            )

    def test_inverse_at_neg_theta(self):
        theta = 0.3
        hp_r, hx_r = rotate_polarizations(HP_GR, HX_GR, theta)
        hp_back, hx_back = rotate_polarizations(hp_r, hx_r, -theta)
        npt.assert_allclose(hp_back, HP_GR, atol=1e-12)
        npt.assert_allclose(hx_back, HX_GR, atol=1e-12)

    def test_composition(self):
        a, b = 0.3, 0.2
        hp_ab1, hx_ab1 = rotate_polarizations(HP_GR, HX_GR, a + b)
        hp_a, hx_a = rotate_polarizations(HP_GR, HX_GR, a)
        hp_ab2, hx_ab2 = rotate_polarizations(hp_a, hx_a, b)
        npt.assert_allclose(hp_ab1, hp_ab2, atol=1e-12)
        npt.assert_allclose(hx_ab1, hx_ab2, atol=1e-12)

    def test_pure_plus_input_mixes_cross(self):
        hp = np.ones(10, dtype=complex)
        hx = np.zeros(10, dtype=complex)
        _, hx_r = rotate_polarizations(hp, hx, 0.1)
        assert float(np.max(np.abs(hx_r))) > 0, "Twist should mix h+ into hx"

    def test_90deg_rotation(self):
        hp = np.array([1.0 + 0j])
        hx = np.array([0.0 + 0j])
        hp_r, hx_r = rotate_polarizations(hp, hx, np.pi / 2)
        npt.assert_allclose(hp_r, [0.0], atol=1e-14)
        npt.assert_allclose(hx_r, [1.0], atol=1e-14)


class TestApplySourceScaleTwist:

    def test_identity(self):
        hp_s, hx_s = apply_source_scale_twist(HP_GR, HX_GR, 1.0, 0.0)
        npt.assert_allclose(hp_s, HP_GR, atol=1e-40)
        npt.assert_allclose(hx_s, HX_GR, atol=1e-40)

    def test_scale_only(self):
        hp_s, hx_s = apply_source_scale_twist(HP_GR, HX_GR, 0.9, 0.0)
        npt.assert_allclose(hp_s, 0.9 * HP_GR, atol=1e-40)
        npt.assert_allclose(hx_s, 0.9 * HX_GR, atol=1e-40)

    def test_scale_applied_after_rotation(self):
        theta = 0.2
        hp_r, hx_r = rotate_polarizations(HP_GR, HX_GR, theta)
        hp_s1, hx_s1 = apply_source_scale_twist(HP_GR, HX_GR, SCALE, theta)
        npt.assert_allclose(hp_s1, SCALE * hp_r, atol=1e-40)
        npt.assert_allclose(hx_s1, SCALE * hx_r, atol=1e-40)

    def test_twist_zero_recovers_scale_only(self):
        hp_sc, hx_sc = apply_source_scale_twist(HP_GR, HX_GR, SCALE, 0.0)
        npt.assert_allclose(hp_sc, SCALE * HP_GR, atol=1e-40)
        npt.assert_allclose(hx_sc, SCALE * HX_GR, atol=1e-40)


class TestDetectorProjection:

    def test_linearity_in_F(self):
        h1 = detector_projection(HP_GR, HX_GR, 1.0, 0.0)
        h2 = detector_projection(HP_GR, HX_GR, 0.0, 1.0)
        h12 = detector_projection(HP_GR, HX_GR, 1.0, 1.0)
        npt.assert_allclose(h12, h1 + h2, atol=1e-40)

    def test_zero_antenna_gives_zero(self):
        h = detector_projection(HP_GR, HX_GR, 0.0, 0.0)
        npt.assert_allclose(h, 0.0, atol=1e-40)

    def test_F_plus_only(self):
        h = detector_projection(HP_GR, HX_GR, 1.0, 0.0)
        npt.assert_allclose(h, HP_GR, atol=1e-40)

    def test_h1_l1_different_from_each_other(self):
        h_h1 = detector_projection(HP_GR, HX_GR, F_PLUS_H1, F_CROSS_H1)
        h_l1 = detector_projection(HP_GR, HX_GR, F_PLUS_L1, F_CROSS_L1)
        rms_h1 = float(np.sqrt(np.mean(np.abs(h_h1)**2)))
        rms_l1 = float(np.sqrt(np.mean(np.abs(h_l1)**2)))
        # Ratio must differ from 1.0 because (F+^H1, Fx^H1) != (F+^L1, Fx^L1)
        ratio = rms_h1 / rms_l1
        assert abs(ratio - 1.0) > 1e-3, (
            f"H1/L1 rms ratio should differ from 1 for different patterns: {ratio:.4f}"
        )


class TestH1L1DifferentialResponse:

    def test_scale_only_ratio_independent_of_scale(self):
        hp_s1, hx_s1 = apply_source_scale_twist(HP_GR, HX_GR, 0.9, 0.0)
        hp_s2, hx_s2 = apply_source_scale_twist(HP_GR, HX_GR, 0.7, 0.0)
        h1_h1 = detector_projection(hp_s1, hx_s1, F_PLUS_H1, F_CROSS_H1)
        h1_l1 = detector_projection(hp_s1, hx_s1, F_PLUS_L1, F_CROSS_L1)
        h2_h1 = detector_projection(hp_s2, hx_s2, F_PLUS_H1, F_CROSS_H1)
        h2_l1 = detector_projection(hp_s2, hx_s2, F_PLUS_L1, F_CROSS_L1)
        rms1 = np.sqrt(np.mean(np.abs(h1_h1)**2)) / np.sqrt(np.mean(np.abs(h1_l1)**2))
        rms2 = np.sqrt(np.mean(np.abs(h2_h1)**2)) / np.sqrt(np.mean(np.abs(h2_l1)**2))
        assert abs(rms1 - rms2) < 1e-10, (
            "H1/L1 ratio must not change under uniform scale"
        )

    def test_twist_shifts_h1_l1_ratio(self):
        hp_gr_r = np.real(HP_GR)
        hx_gr_r = np.real(HX_GR)
        h1_h1_gr = detector_projection(hp_gr_r, hx_gr_r, F_PLUS_H1, F_CROSS_H1)
        h1_l1_gr = detector_projection(hp_gr_r, hx_gr_r, F_PLUS_L1, F_CROSS_L1)
        rms_gr = (np.sqrt(np.mean(h1_h1_gr**2)) /
                  np.sqrt(np.mean(h1_l1_gr**2)))

        hp_tw, hx_tw = apply_source_scale_twist(hp_gr_r, hx_gr_r, 1.0, 0.3)
        h2_h1 = detector_projection(hp_tw, hx_tw, F_PLUS_H1, F_CROSS_H1)
        h2_l1 = detector_projection(hp_tw, hx_tw, F_PLUS_L1, F_CROSS_L1)
        rms_tw = (np.sqrt(np.mean(h2_h1**2)) /
                  np.sqrt(np.mean(h2_l1**2)))

        assert abs(rms_tw - rms_gr) > 1e-6, (
            f"Twist should shift H1/L1 ratio: GR={rms_gr:.4f} tw={rms_tw:.4f}"
        )

    def test_ratio_shift_grows_with_theta(self):
        hp_r = np.real(HP_GR)
        hx_r = np.real(HX_GR)
        h_h1_gr = detector_projection(hp_r, hx_r, F_PLUS_H1, F_CROSS_H1)
        h_l1_gr = detector_projection(hp_r, hx_r, F_PLUS_L1, F_CROSS_L1)
        ratio_gr = (np.sqrt(np.mean(h_h1_gr**2)) /
                    np.sqrt(np.mean(h_l1_gr**2)))
        shifts = []
        for theta in [0.01, 0.05, 0.1, 0.3]:
            hp_tw, hx_tw = apply_source_scale_twist(hp_r, hx_r, 1.0, theta)
            h_h1 = detector_projection(hp_tw, hx_tw, F_PLUS_H1, F_CROSS_H1)
            h_l1 = detector_projection(hp_tw, hx_tw, F_PLUS_L1, F_CROSS_L1)
            ratio_tw = (np.sqrt(np.mean(h_h1**2)) /
                        np.sqrt(np.mean(h_l1**2)))
            shifts.append(abs(ratio_tw - ratio_gr))
        assert all(shifts[i] <= shifts[i + 1] for i in range(len(shifts) - 1)), (
            f"H1/L1 ratio shift should grow with theta: {shifts}"
        )


class TestCompareScaleOnlyVsScaleTwist:

    def test_returns_one_row_per_theta(self):
        results = compare_scale_only_vs_scale_twist(
            HP_GR, HX_GR, SCALE, THETA_SCAN,
            F_PLUS_H1, F_CROSS_H1, F_PLUS_L1, F_CROSS_L1
        )
        assert len(results) == len(THETA_SCAN)

    def test_theta_zero_row_matches_scale_only(self):
        results = compare_scale_only_vs_scale_twist(
            HP_GR, HX_GR, SCALE, [0.0, 0.1],
            F_PLUS_H1, F_CROSS_H1, F_PLUS_L1, F_CROSS_L1
        )
        r0 = results[0]
        assert abs(r0["rms_tw_h1"] - r0["rms_sc_h1"]) < 1e-12
        assert abs(r0["rms_tw_l1"] - r0["rms_sc_l1"]) < 1e-12
        assert abs(r0["resid_vs_scale_h1"]) < 1e-12
        assert abs(r0["resid_vs_scale_l1"]) < 1e-12

    def test_resid_grows_with_theta(self):
        thetas = [0.01, 0.05, 0.1]
        results = compare_scale_only_vs_scale_twist(
            HP_GR, HX_GR, SCALE, thetas,
            F_PLUS_H1, F_CROSS_H1, F_PLUS_L1, F_CROSS_L1
        )
        resids_h1 = [r["resid_vs_scale_h1"] for r in results]
        resids_l1 = [r["resid_vs_scale_l1"] for r in results]
        assert all(resids_h1[i] <= resids_h1[i+1]
                   for i in range(len(resids_h1)-1)), (
            f"H1 resid should grow with theta: {resids_h1}"
        )
        assert all(resids_l1[i] <= resids_l1[i+1]
                   for i in range(len(resids_l1)-1)), (
            f"L1 resid should grow with theta: {resids_l1}"
        )

    def test_h1_l1_ratio_shift_grows_with_theta(self):
        thetas = [0.0, 0.01, 0.05, 0.1]
        results = compare_scale_only_vs_scale_twist(
            np.real(HP_GR), np.real(HX_GR), SCALE, thetas,
            F_PLUS_H1, F_CROSS_H1, F_PLUS_L1, F_CROSS_L1
        )
        shifts = [abs(r["h1_l1_ratio_shift"]) for r in results]
        assert all(shifts[i] <= shifts[i+1] for i in range(len(shifts)-1)), (
            f"Ratio shift should grow with theta: {shifts}"
        )

    def test_scale_only_ratio_consistent(self):
        results = compare_scale_only_vs_scale_twist(
            HP_GR, HX_GR, SCALE, [0.0],
            F_PLUS_H1, F_CROSS_H1, F_PLUS_L1, F_CROSS_L1
        )
        r = results[0]
        if r["h1_l1_ratio_sc"] and not np.isnan(r["h1_l1_ratio_sc"]):
            assert r["h1_l1_ratio_sc"] > 0

    def test_with_synthetic_psd(self):
        psd = synthetic_asd_ligo(FREQS_POS)
        # Use scale=1.0 so scale-only model = GR -> delta_lnL = 0 at theta=0
        results = compare_scale_only_vs_scale_twist(
            HP_GR, HX_GR, 1.0, [0.0, 0.1],
            F_PLUS_H1, F_CROSS_H1, F_PLUS_L1, F_CROSS_L1,
            psd_h1=psd, psd_l1=psd, freqs=FREQS_POS
        )
        assert results[0]["lnl_gr_h1"] is not None
        assert results[0]["delta_lnl_h1"] is not None
        # theta=0, scale=1: twist model = GR model -> delta_lnL exactly 0
        assert abs(results[0]["delta_lnl_h1"]) < 1e-40


class TestSyntheticPSD:

    def test_psd_positive_everywhere(self):
        psd = synthetic_asd_ligo(FREQS_POS)
        assert np.all(psd > 0)

    def test_psd_shape(self):
        psd = synthetic_asd_ligo(FREQS_POS)
        assert len(psd) == len(FREQS_POS)

    def test_psd_decreasing_at_high_freq(self):
        f_test = np.array([10.0, 100.0, 1000.0])
        psd = synthetic_asd_ligo(f_test)
        assert psd[0] > psd[1] > psd[2], "PSD should decrease with frequency"


class TestClaimGate:

    def test_status_labels(self):
        assert SOURCE_PROPAGATION_TWIST_STATUS == "DERIVED_V0_CONCEPTUAL"
        assert LOCAL_ARM_TWIST_STATUS == "CLOSED_NEGLIGIBLE"

    def test_module_docstring_has_gate(self):
        from ssz_ligo_tests import source_propagation_twist as spt
        doc = spt.__doc__
        assert "READY_FOR_REAL_LIGO_SSZ_CLAIM: NO" in doc
        assert "LOCAL_ARM_TWIST_STATUS: CLOSED_NEGLIGIBLE" in doc
        assert "SSZ_SUPPORT_CLAIM_MADE: NO" in doc

    def test_no_posterior_params(self):
        import inspect
        from ssz_ligo_tests import source_propagation_twist as spt
        for name in ["theta_constant", "theta_xi_proxy", "theta_rsg_proxy",
                     "rotate_polarizations", "apply_source_scale_twist",
                     "detector_projection"]:
            fn = getattr(spt, name)
            sig = inspect.signature(fn)
            for pname in sig.parameters:
                assert pname not in ("chi", "spin", "posterior", "sample"), (
                    f"Function {name} must not accept posterior parameter {pname}"
                )

    def test_local_arm_not_applied(self):
        # apply_source_scale_twist must not call any arm-correction function
        import inspect
        from ssz_ligo_tests import source_propagation_twist as spt
        src = inspect.getsource(spt.apply_source_scale_twist)
        assert "arm_correction" not in src
        assert "Xi_arm" not in src
        assert "arm_twist" not in src
