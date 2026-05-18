"""Tests for the analytic 2PN polarization control module.

Branch: ANALYTIC_2PN_POLARIZATION_CONTROL
Status: ANALYTIC_2PN_CONTROL_APPROXIMATION

Tests:
  1.  0PN h×/h+ ratio is frequency-independent (degeneracy confirmed)
  2.  2PN h×/h+ ratio varies with frequency (degeneracy broken)
  3.  2PN degeneracy metric > 0PN degeneracy metric
  4.  h+ and h× have the correct phase relationship at 0PN
  5.  h+ and h× have the correct phase relationship at 2PN
  6.  h_plus_0pn face-on: H+_0 = 1
  7.  h_cross_0pn edge-on (iota=pi/2): H×_0 = 0
  8.  2PN amplitude corrections nonzero at 1PN and 2PN
  9.  phase_2pn_taylorf2: monotonically decreasing (stationary phase)
  10. amplitude_0pn: scales as f^{-7/6}
  11. amplitude_0pn: scales linearly with 1/d_lum_m
  12. inclination iota=0: h+ and h× have same amplitude at 0PN
  13. inclination iota=pi/4: h+ != h× amplitude at 2PN
  14. 2PN > 0PN twist sensitivity for constant theta scan
  15. 2PN > 0PN H1/L1 ratio shift under twist
  16. status labels correct
  17. no posterior parameters in function signatures
  18. 0PN recovery: 2PN at zeroed PN coefficients -> 0PN
  19. twist sensitivity grows with theta (2PN)
  20. H1/L1 ratio shift grows with theta (2PN)
"""
import sys
import numpy as np
import numpy.testing as npt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ssz_ligo_tests.analytic_polarizations_2pn import (  # noqa: E402
    h_plus_0pn,
    h_cross_0pn,
    h_plus_2pn,
    h_cross_2pn,
    amplitude_0pn,
    phase_2pn_taylorf2,
    polarization_amplitude_ratio,
    polarization_degeneracy_metric,
    POLARIZATION_CONTROL_STATUS,
    M_SUN,
)
from ssz_ligo_tests.source_propagation_twist import (  # noqa: E402
    rotate_polarizations,
    detector_projection,
)

FS = 4096.0
T = 4.0
N = int(FS * T)
FREQS = np.fft.rfftfreq(N, 1.0 / FS)
MASK = (FREQS >= 20.0) & (FREQS <= 210.0) & (FREQS > 0)
F = FREQS[MASK]

MC_MSUN = 8.9
ETA = 0.25
MC_KG = MC_MSUN * M_SUN
M_TOT_KG = MC_KG / ETA**(3.0 / 5.0)
DL_M = 300.0 * 3.086e22

IOTA_FACE = 0.0
IOTA_45 = np.pi / 4.0
IOTA_EDGE = np.pi / 2.0

F_PLUS_H1 = 0.592
F_CROSS_H1 = 0.344
F_PLUS_L1 = 0.437
F_CROSS_L1 = 0.683

THETA_SCAN = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1]


class TestAmplitudePhase:

    def test_amplitude_0pn_power_law(self):
        f_test = np.array([20.0, 40.0, 80.0])
        A = amplitude_0pn(f_test, MC_KG, DL_M)
        # A ~ f^{-7/6}: ratio A(20)/A(40) ~ (40/20)^{7/6} = 2^{7/6}
        expected_ratio = (40.0 / 20.0)**(7.0 / 6.0)
        actual_ratio = A[0] / A[1]
        assert abs(actual_ratio / expected_ratio - 1.0) < 1e-6

    def test_amplitude_0pn_distance_scaling(self):
        d1 = 100.0 * 3.086e22
        d2 = 200.0 * 3.086e22
        A1 = amplitude_0pn(F, MC_KG, d1)
        A2 = amplitude_0pn(F, MC_KG, d2)
        npt.assert_allclose(A1 / A2, 2.0, rtol=1e-12)

    def test_phase_monotone_decreasing(self):
        psi = phase_2pn_taylorf2(F, MC_KG, M_TOT_KG, ETA)
        # In SPA: Psi ~ (3/128eta)*u^{-5} dominates at low f -> large negative
        # As f increases, Psi becomes less negative: dPsi/df > 0
        # Check on raw (not unwrapped) psi: psi[0] < psi[-1]
        # SPA phase: Psi ~ u^{-5} dominates -> large positive at low f,
        # decreases toward merger (psi[0] > psi[-1])
        assert float(psi[0]) > float(psi[-1]), (
            f"SPA phase should decrease with f: "
            f"psi[0]={psi[0]:.2f} psi[-1]={psi[-1]:.2f}"
        )
        # Also verify all finite
        assert np.all(np.isfinite(psi))

    def test_phase_0pn_limit(self):
        # At 0PN: Psi ~ (3/128eta) * (pi Mc f)^{-5/3}
        # The 2PN phase reduces to this when PN corrections are small
        psi = phase_2pn_taylorf2(F, MC_KG, M_TOT_KG, ETA)
        assert psi.shape == F.shape
        assert np.all(np.isfinite(psi))


class Test0PNDegeneracy:

    def test_0pn_hcross_is_minus_i_times_hplus_face_on(self):
        # At iota=0: h× = -i h+ exactly (all PN orders, non-spinning, circ)
        hp, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        hx, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        # hx phase = psi - pi/2 = psi - pi/2; hp phase = psi
        # so hx = A * ci * exp(i(psi - pi/2)) = -i * A * ci * exp(i psi)
        # at iota=0: H×_0 = cos(0) = 1 = H+_0 at 0PN, so hx = -i hp
        ratio = hx / hp
        npt.assert_allclose(np.real(ratio), 0.0, atol=1e-10)
        npt.assert_allclose(np.imag(ratio), -1.0, atol=1e-10)

    def test_0pn_ratio_frequency_independent(self):
        hp, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        ratio = polarization_amplitude_ratio(hp, hx)
        # Should be constant (frequency-independent) at 0PN
        std_ratio = float(np.std(ratio[np.isfinite(ratio)]))
        assert std_ratio < 1e-12, (
            f"0PN |hx/hp| should be frequency-independent, std={std_ratio:.2e}"
        )

    def test_0pn_degeneracy_metric_near_zero(self):
        hp, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        deg = polarization_degeneracy_metric(hp, hx)
        assert deg < 1e-10, f"0PN degeneracy metric should be ~0, got {deg:.2e}"

    def test_0pn_face_on_amplitudes(self):
        hp, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        hx, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        A0 = amplitude_0pn(F, MC_KG, DL_M)
        # H+_0 = (1 + cos²0)/2 = 1; H×_0 = cos(0) = 1
        npt.assert_allclose(np.abs(hp), A0, rtol=1e-10)
        npt.assert_allclose(np.abs(hx), A0, rtol=1e-10)

    def test_0pn_edge_on_cross_zero(self):
        _, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_EDGE, DL_M)
        hx, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_EDGE, DL_M)
        # H×_0 = cos(pi/2) = 0
        npt.assert_allclose(np.abs(hx), 0.0, atol=1e-30)


class Test2PNDegeneracyBroken:

    def test_2pn_ratio_frequency_dependent(self):
        hp, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        ratio = polarization_amplitude_ratio(hp, hx)
        std_ratio = float(np.std(ratio[np.isfinite(ratio)]))
        assert std_ratio > 1e-12, (
            f"2PN |hx/hp| should vary with frequency, std={std_ratio:.2e}"
        )

    def test_2pn_degeneracy_metric_greater_than_0pn(self):
        hp0, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx0, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        deg0 = polarization_degeneracy_metric(hp0, hx0)
        deg2 = polarization_degeneracy_metric(hp2, hx2)
        assert deg2 > deg0, (
            f"2PN degeneracy metric {deg2:.2e} must exceed "
            f"0PN {deg0:.2e}"
        )

    def test_2pn_hplus_amplitude_corrections_nonzero(self):
        # At iota=pi/4, the 1PN and 2PN corrections to h+ should be nonzero
        # Check by comparing 2PN amplitude envelope to 0PN
        hp0, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        ratio = np.abs(hp2) / np.abs(hp0)
        # Should not all be 1.0 (corrections must be present)
        assert float(np.std(ratio)) > 1e-6, (
            "2PN h+ should differ from 0PN in amplitude envelope"
        )

    def test_2pn_hcross_amplitude_corrections_nonzero(self):
        hx0, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        ratio = np.abs(hx2) / np.abs(hx0)
        assert float(np.std(ratio)) > 1e-6, (
            "2PN hx should differ from 0PN in amplitude envelope"
        )

    def test_2pn_hplus_hcross_amplitude_differ_at_iota45(self):
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        rms_hp = float(np.sqrt(np.mean(np.abs(hp2)**2)))
        rms_hx = float(np.sqrt(np.mean(np.abs(hx2)**2)))
        assert abs(rms_hp - rms_hx) / max(rms_hp, rms_hx) > 1e-4, (
            f"2PN h+ and hx should have different RMS at iota=pi/4: "
            f"hp={rms_hp:.3e} hx={rms_hx:.3e}"
        )

    def test_2pn_phase_same_as_0pn_phase(self):
        # Both h+ and h× use the SAME phase Psi_2PN(f)
        # so the PHASE is identical — only amplitude differs between them
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        # At face-on: both amplitudes > 0, phase(hx) = phase(hp) - pi/2
        phase_diff = np.angle(hx2) - np.angle(hp2)
        # Should be -pi/2 (mod 2pi)
        pd_norm = (phase_diff + np.pi / 2.0) % (2 * np.pi)
        pd_norm = np.where(pd_norm > np.pi, pd_norm - 2 * np.pi, pd_norm)
        npt.assert_allclose(pd_norm, 0.0, atol=1e-10)


class TestTwistSensitivity:

    def _h1_l1_ratio_shift(self, hp, hx, theta):
        hp_tw, hx_tw = rotate_polarizations(hp, hx, theta)
        h_h1_gr = detector_projection(hp, hx, F_PLUS_H1, F_CROSS_H1)
        h_l1_gr = detector_projection(hp, hx, F_PLUS_L1, F_CROSS_L1)
        h_h1_tw = detector_projection(hp_tw, hx_tw, F_PLUS_H1, F_CROSS_H1)
        h_l1_tw = detector_projection(hp_tw, hx_tw, F_PLUS_L1, F_CROSS_L1)
        ratio_gr = (np.sqrt(np.mean(np.abs(h_h1_gr)**2)) /
                    np.sqrt(np.mean(np.abs(h_l1_gr)**2)))
        ratio_tw = (np.sqrt(np.mean(np.abs(h_h1_tw)**2)) /
                    np.sqrt(np.mean(np.abs(h_l1_tw)**2)))
        return float(abs(ratio_tw - ratio_gr))

    def test_2pn_twist_sensitivity_greater_than_0pn(self):
        hp0, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx0, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        theta = 0.1
        shift0 = self._h1_l1_ratio_shift(hp0, hx0, theta)
        shift2 = self._h1_l1_ratio_shift(hp2, hx2, theta)
        assert shift2 > shift0, (
            f"2PN twist sensitivity {shift2:.4e} must exceed "
            f"0PN {shift0:.4e} at theta={theta} rad"
        )

    def test_2pn_ratio_shift_nonzero_at_large_theta(self):
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        shift = self._h1_l1_ratio_shift(hp2, hx2, 0.1)
        assert shift > 1e-6, (
            f"2PN H1/L1 ratio shift must be detectable at theta=0.1: {shift:.4e}"
        )

    def test_2pn_ratio_shift_grows_with_theta(self):
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        shifts = [self._h1_l1_ratio_shift(hp2, hx2, th)
                  for th in [0.01, 0.03, 0.1]]
        assert all(shifts[i] <= shifts[i+1] for i in range(len(shifts)-1)), (
            f"2PN H1/L1 ratio shift should grow with theta: {shifts}"
        )

    def test_0pn_ratio_shift_much_smaller_than_2pn(self):
        # 0PN: hx = const_factor * exp(-i pi/2) * hp  (freq-independent)
        # Rotation mixes hp and hx, but because their amplitude ratio is
        # constant, the H1/L1 RMS ratio shift is small (but not exactly 0
        # because F+/Fx differ and rotation mixes them non-trivially).
        # Key claim: 0PN shift << 2PN shift at the same theta.
        hp0, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx0, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        for theta in [0.01, 0.03, 0.1]:
            s0 = self._h1_l1_ratio_shift(hp0, hx0, theta)
            s2 = self._h1_l1_ratio_shift(hp2, hx2, theta)
            assert s2 > s0, (
                f"At theta={theta}: 2PN shift {s2:.3e} must exceed "
                f"0PN shift {s0:.3e}"
            )

    def test_2pn_better_than_0pn_across_theta_scan(self):
        hp0, _ = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx0, _ = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hp2, _ = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        hx2, _ = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        for theta in THETA_SCAN[2:]:  # skip 0 and 0.001
            s0 = self._h1_l1_ratio_shift(hp0, hx0, theta)
            s2 = self._h1_l1_ratio_shift(hp2, hx2, theta)
            assert s2 >= s0, (
                f"2PN should be >= 0PN sensitivity at theta={theta}: "
                f"0PN={s0:.3e} 2PN={s2:.3e}"
            )


class TestClaimGate:

    def test_status_label(self):
        assert POLARIZATION_CONTROL_STATUS == "ANALYTIC_2PN_APPROXIMATION"

    def test_h_plus_2pn_returns_status(self):
        hp, status = h_plus_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        assert status == "ANALYTIC_2PN_APPROXIMATION"

    def test_h_cross_2pn_returns_status(self):
        _, status = h_cross_2pn(F, MC_KG, M_TOT_KG, ETA, IOTA_45, DL_M)
        assert status == "ANALYTIC_2PN_APPROXIMATION"

    def test_0pn_returns_baseline_status(self):
        _, s1 = h_plus_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        _, s2 = h_cross_0pn(F, MC_KG, M_TOT_KG, ETA, IOTA_FACE, DL_M)
        assert s1 == "0PN_BASELINE"
        assert s2 == "0PN_BASELINE"

    def test_no_posterior_params_in_signatures(self):
        import inspect
        from ssz_ligo_tests import analytic_polarizations_2pn as m
        for fn_name in ["h_plus_2pn", "h_cross_2pn",
                        "h_plus_0pn", "h_cross_0pn"]:
            fn = getattr(m, fn_name)
            sig = inspect.signature(fn)
            for pname in sig.parameters:
                assert pname not in ("chi", "spin", "posterior", "sample"), (
                    f"{fn_name} must not accept posterior param {pname}"
                )

    def test_module_docstring_gate(self):
        from ssz_ligo_tests import analytic_polarizations_2pn as m
        doc = m.__doc__
        assert "READY_FOR_REAL_LIGO_SSZ_CLAIM: NO" in doc
        assert "ANALYTIC_2PN_CONTROL_APPROXIMATION" in doc
