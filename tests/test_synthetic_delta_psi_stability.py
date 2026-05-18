"""Test: Synthetic deltaPsi proxy — finite values, V0_PROXY label.

Applies SSZ V0 proxy phase deformation to a synthetic frequency grid.
No real LIGO data. No physics claim.
"""
import numpy as np
from ssz_ligo_tests.ssz_core import xi_weak, d_ssz
from ssz_ligo_tests.constants import G, C, M_SUN

PROXY_LABEL = "SSZ_FORWARD_V0_PROXY"

MC_MSUN = 8.9
ETA = 0.25
M_KG = (MC_MSUN * M_SUN / ETA ** (3.0 / 5.0))
RS_M = 2.0 * G * M_KG / C ** 2
F_LOW = 20.0
F_HIGH = 800.0
KAPPA = 1.0


def compute_dpsi_v0(freqs, M_kg, rs):
    dpsi = np.zeros(len(freqs))
    mask = (freqs >= F_LOW) & (freqs <= F_HIGH) & (freqs > 0)
    for i in np.where(mask)[0]:
        r = (G * M_kg / (np.pi * freqs[i]) ** 2) ** (1.0 / 3.0)
        xi = xi_weak(r, rs)
        dpsi[i] = KAPPA * (1.0 - d_ssz(xi))
    return dpsi


class TestDeltaPsiSynthetic:
    def test_label_is_v0_proxy(self):
        assert PROXY_LABEL == "SSZ_FORWARD_V0_PROXY"

    def test_dpsi_finite_on_grid(self):
        freqs = np.linspace(F_LOW, F_HIGH, 200)
        dpsi = compute_dpsi_v0(freqs, M_KG, RS_M)
        assert np.all(np.isfinite(dpsi))

    def test_dpsi_nonnegative_in_band(self):
        freqs = np.linspace(F_LOW, F_HIGH, 200)
        dpsi = compute_dpsi_v0(freqs, M_KG, RS_M)
        assert np.all(dpsi >= 0)

    def test_dpsi_max_below_pi(self):
        freqs = np.linspace(F_LOW, F_HIGH, 200)
        dpsi = compute_dpsi_v0(freqs, M_KG, RS_M)
        assert dpsi.max() < np.pi

    def test_dpsi_increases_with_frequency(self):
        freqs = np.linspace(F_LOW, F_HIGH, 50)
        dpsi = compute_dpsi_v0(freqs, M_KG, RS_M)
        assert dpsi[-1] > dpsi[0], (
            "deltaPsi V0 proxy increases with f: smaller r at high f "
            "means larger Xi_weak, larger 1-D"
        )

    def test_h_ssz_from_gr_is_finite(self):
        freqs = np.linspace(F_LOW, F_HIGH, 200)
        h_gr = np.ones(len(freqs), dtype=complex) * 1e-23
        dpsi = compute_dpsi_v0(freqs, M_KG, RS_M)
        h_ssz = h_gr * np.exp(1j * dpsi)
        assert np.all(np.isfinite(np.abs(h_ssz)))

    def test_no_ssz_claim(self):
        """Canary: proxy output does not constitute a physics verdict."""
        freqs = np.linspace(F_LOW, F_HIGH, 10)
        dpsi = compute_dpsi_v0(freqs, M_KG, RS_M)
        assert dpsi.max() < 1.0
