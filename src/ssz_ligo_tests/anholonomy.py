"""SSZ Interferometer Anholonomy — symbolic placeholder.

Theory doc: docs/SSZ_INTERFEROMETER_ANHOLONOMY_FORMULATION.md

LIGO measures the anholonomy of the optical phase along two arms:

    ΔΦ = Φ_x - Φ_y = (4π L / λ) · h(t)

In SSZ, the phase transport along each arm is modified by D(r), s(r).
In the far-field / weak-field limit (at the detector), Ξ_Earth ~ 1e-9,
so the near-detector correction is negligible.

The dominant SSZ effect enters through the source-frame inspiral dynamics
(δΨ_SSZ, δA_SSZ) — already implemented in derived_phase.py and
derived_amplitude.py.

This module provides:
1. Symbolic transport operator placeholders (not yet numerically derived)
2. The arm-phase integral formula
3. The holonomy → strain mapping

STATUS: SYMBOLIC_PLACEHOLDER — not numerically runnable for real claims
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
"""
import numpy as np
from .ssz_core import d_ssz, get_xi


def ssz_null_wavevector_radial(r, omega_laser, r_s=2.95e3):
    """Radial component of photon 4-wavevector in SSZ metric.

    From null condition g^{μν} k_μ k_ν = 0 in SSZ Schwarzschild:
        g^{tt} (omega/c)² + g^{rr} k_r² = 0
        -1/D² · (omega/c)² + 1/s² · k_r² = 0
        k_r = (omega/c) · s(r) / D(r)

    In GR: k_r^GR = omega/c (flat approximation)
    SSZ correction: k_r^SSZ / k_r^GR = s(r) / D(r)

    Parameters
    ----------
    r : float or array
        Radial coordinate [m]
    omega_laser : float
        Laser angular frequency [rad/s]

    Returns
    -------
    k_r : float or array
        Radial wavevector component [rad/m]
    k_r_ratio : float or array
        k_r^SSZ / k_r^GR = s/D
    """
    xi = get_xi(r, r_s)
    d = d_ssz(xi)
    s = 1.0 + xi
    k_r_gr = omega_laser / 3.0e8
    k_r_ssz = k_r_gr * s / d
    return k_r_ssz, s / d


def phase_integral_along_arm(r_start, r_end, omega_laser,
                             r_s=2.95e3, n_steps=1000):
    """Compute optical phase accumulated along one interferometer arm.

    Φ_arm = ∫_{r_start}^{r_end} k_r^SSZ(r) dr

    In GR: Φ_arm^GR = omega/c · (r_end - r_start)
    SSZ correction: δΦ = ∫ k_r^GR · (s/D - 1) dr

    Parameters
    ----------
    r_start, r_end : float
        Arm endpoints [m]
    omega_laser : float
        Laser angular frequency [rad/s]
    n_steps : int
        Integration steps

    Returns
    -------
    phi_gr : float
        GR phase [rad]
    phi_ssz : float
        SSZ phase [rad]
    delta_phi : float
        SSZ correction δΦ = φ_SSZ - φ_GR [rad]
    """
    r = np.linspace(r_start, r_end, n_steps)
    dr = (r_end - r_start) / (n_steps - 1)

    k_r_ssz, ratio = ssz_null_wavevector_radial(r, omega_laser, r_s=r_s)
    k_r_gr = omega_laser / 3.0e8

    phi_gr = k_r_gr * (r_end - r_start)
    phi_ssz = float(np.trapezoid(k_r_ssz, dx=dr))
    delta_phi = phi_ssz - phi_gr

    return phi_gr, phi_ssz, delta_phi


def interferometer_phase_difference(phi_x, phi_y):
    """Interferometer output: differential phase between two arms.

    ΔΦ = Φ_x - Φ_y

    In the presence of a GW, Φ_x and Φ_y change differently,
    producing the strain signal. In SSZ, both arms have the same
    near-detector SSZ correction (same r_Earth), so the static
    background correction cancels — only the GW-induced SSZ
    modification remains.

    Parameters
    ----------
    phi_x, phi_y : float
        Optical phase along each arm [rad]

    Returns
    -------
    delta_phi : float
        Differential phase [rad]
    """
    return phi_x - phi_y


def strain_from_phase_difference(delta_phi, wavelength, arm_length):
    """Map optical phase difference to effective GW strain.

    h = ΔΦ · λ / (4π L)

    Derivation:
    ΔL_eff = (λ / 2π) · ΔΦ / 2   (round-trip: factor 2)
    h = ΔL_eff / L = λ · ΔΦ / (4π L)

    Parameters
    ----------
    delta_phi : float
        Differential optical phase [rad]
    wavelength : float
        Laser wavelength [m], typically 1064e-9 m for LIGO
    arm_length : float
        Interferometer arm length [m], typically 4000 m for LIGO

    Returns
    -------
    h : float
        Effective strain [dimensionless]
    """
    return delta_phi * wavelength / (4.0 * np.pi * arm_length)


def transport_operator_placeholder(connection_values, path_dr):
    """Path-ordered exponential — symbolic placeholder.

    U(γ) = P exp(- ∫_γ Γ_μ dx^μ)

    NOT IMPLEMENTED — requires SSZ Christoffel symbols Γ^λ_μν^SSZ.
    See docs/SSZ_INTERFEROMETER_ANHOLONOMY_FORMULATION.md section 4.2.

    Parameters
    ----------
    connection_values : array
        Christoffel symbol values along path [NOT YET DERIVED]
    path_dr : float
        Path step size [m]

    Returns
    -------
    NotImplementedError

    Notes
    -----
    The SSZ connection is:
        Γ^r_rr^SSZ = D'/D - s'/s
    where prime = d/dr.
    Derivation from SSZ metric is pending.
    """
    raise NotImplementedError(
        "SSZ Christoffel symbols not yet derived. "
        "See docs/SSZ_INTERFEROMETER_ANHOLONOMY_FORMULATION.md"
    )


def near_detector_ssz_correction_estimate(r_detector_m=6.371e6,
                                          r_s_earth_m=8.87e-3):
    """Estimate near-detector SSZ correction at Earth surface.

    Ξ_Earth = r_s / (2 r_Earth) = 8.87e-3 / (2 * 6.371e6) ~ 7e-10

    This is the SSZ correction to photon transport at the detector location.
    It is negligible for LIGO sensitivity.

    The dominant SSZ effect for LIGO is encoded in the SOURCE-FRAME
    GW emission (δΨ_SSZ, δA_SSZ), not in the detector-arm transport.

    Returns
    -------
    xi_earth : float
        Ξ at Earth surface (weak field)
    correction_ratio : float
        s/D - 1 at Earth surface (fractional phase correction per metre)
    """
    xi_e = r_s_earth_m / (2.0 * r_detector_m)
    d = 1.0 / (1.0 + xi_e)
    s = 1.0 + xi_e
    ratio = s / d - 1.0
    return xi_e, ratio
