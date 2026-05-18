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


def gr_strain_from_phase_transport(h_plus_t, arm_length_m, wavelength_m):
    """Recover GR strain from arm phase transport formula (unit test / verification).

    From the TT-gauge null geodesic:
        Φ_x = (4π L / λ) · (1 + h_+(t)/2)
        Φ_y = (4π L / λ) · (1 - h_+(t)/2)
        ΔΦ  = (4π L / λ) · h_+(t)
        h   = ΔΦ · λ / (4π L) = h_+(t)  ✓

    This function verifies the round-trip holds: should return h_plus_t unchanged.

    NOTE on float64 precision: phi0 = 4πL/λ ~ 4.7e10. At h ~ 1e-21,
    phi0 * h/2 ~ 2.4e-11, which is at the float64 round-off floor
    (eps ~ 2.2e-16 * phi0 ~ 1e-5). Use h >= 1e-10 for numerical verification.
    The analytical formula is exact; the numerical test requires h >> eps*phi0/phi0.
    Real LIGO signals at h~1e-21 are measured via homodyne lock-in, not by
    direct phase subtraction — this limitation is only in the test, not in LIGO.

    Parameters
    ----------
    h_plus_t : float or array
        GW strain (+ polarisation) [dimensionless]
    arm_length_m : float
        Interferometer arm length [m]
    wavelength_m : float
        Laser wavelength [m]

    Returns
    -------
    h_recovered : float or array
        Recovered strain — should equal h_plus_t to numerical precision
    phi_x : float or array
        Phase along arm x [rad]
    phi_y : float or array
        Phase along arm y [rad]
    """
    phi0 = 4.0 * np.pi * arm_length_m / wavelength_m
    phi_x = phi0 * (1.0 + h_plus_t / 2.0)
    phi_y = phi0 * (1.0 - h_plus_t / 2.0)
    delta_phi = phi_x - phi_y
    h_recovered = strain_from_phase_difference(delta_phi, wavelength_m,
                                               arm_length_m)
    return h_recovered, phi_x, phi_y


def ssz_arm_strain_correction(r_det_m, r_s_det_m, h_plus_t,
                               arm_length_m, wavelength_m):
    """SSZ correction to LIGO strain from near-detector arm modification.

    In SSZ, the null geodesic along arm x picks up a factor s(r)/D(r):
        Φ_x^SSZ = (4π L / λ) · [s/D]_arm · (1 + h_+(t)/2)
        ΔΦ^SSZ  = (4π L / λ) · [s/D]_arm · h_+(t)
        h_SSZ   = [s/D]_arm · h_+(t)

    The correction [s/D - 1] at Earth surface is ~1.4e-9, negligible.
    This function makes the smallness explicit.

    Parameters
    ----------
    r_det_m : float
        Detector radial coordinate from Earth centre [m]
    r_s_det_m : float
        Schwarzschild radius of Earth [m] (= 8.87e-3 m)
    h_plus_t : float or array
        GR strain (+ polarisation) [dimensionless]
    arm_length_m : float
        Interferometer arm length [m]
    wavelength_m : float
        Laser wavelength [m]

    Returns
    -------
    h_ssz : float or array
        SSZ-corrected strain [dimensionless]
    s_over_d : float
        [s/D]_arm correction factor
    delta_h : float or array
        Absolute SSZ arm correction h_SSZ - h_GR
    """
    xi = r_s_det_m / (2.0 * r_det_m)
    s = 1.0 + xi
    d = 1.0 / (1.0 + xi)
    s_over_d = s / d
    h_ssz = s_over_d * h_plus_t
    delta_h = h_ssz - h_plus_t
    return h_ssz, s_over_d, delta_h
