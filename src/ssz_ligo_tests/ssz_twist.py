"""SSZ Twist / Polarisation Rotation Branch.

Theory doc: docs/SSZ_TWIST_ANHOLONOMY_BRANCH.md
Branch ID:  TWIST_POLARIZATION_PHASE_BRANCH
Status:     DERIVED_V0_CONCEPTUAL

The current V0/V1 pipeline models SSZ as scalar scale + phase:
    h_SSZ = h_GR * (1 + dA) * exp(i*dPsi)

This module adds the TWIST branch:
    [h_+^SSZ]   = S(r,f) * R(theta) * [h_+^GR]
    [h_x^SSZ]                          [h_x^GR]

where R(theta) is a 2x2 polarisation rotation matrix and theta_SSZ
is the SSZ-induced twist angle (not yet derived from first principles).

RULES:
- theta_SSZ not yet derived from Christoffel/spin-connection
- V0 placeholder: theta ~ Xi(r_source) * phi_geom (conceptual)
- No real LIGO claim from this module
- rotate_polarizations and apply_ssz_scale_and_twist are runnable
- twist_angle_v0 is clearly labelled as placeholder

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import numpy as np
from .ssz_core import get_xi


TWIST_BRANCH_STATUS = "DERIVED_V0_CONCEPTUAL"
READY_FOR_REAL_CLAIM = "NO"


def twist_angle_v0(freqs, M_kg, rs_m, branch="rsg"):
    """V0 conceptual twist angle placeholder.

    The SSZ spin-connection holonomy in the polarisation plane is not
    yet derived. This function returns a V0 dimensional-analysis estimate:

        theta_V0(r) ~ Xi(r_char) * phi_geom

    where r_char is a characteristic source radius and phi_geom is a
    geometric phase factor (set to 1 here as order-of-magnitude).

    This is CONCEPTUAL ONLY. Do not use for any LIGO claim.

    Parameters
    ----------
    freqs : array
        Frequency array [Hz]
    M_kg : float
        Total binary mass [kg]
    rs_m : float
        Schwarzschild radius of the source [m]
    branch : str
        "rsg" — use r_ISCO as characteristic radius (default)
        "photon_sphere" — use r* = 1.387 * rs

    Returns
    -------
    theta : array
        V0 twist angle [rad], shape matching freqs
        Status: CONCEPTUAL — not derived from spin connection
    r_char : float
        Characteristic radius used [m]
    xi_char : float
        Xi at characteristic radius (order of magnitude)
    status : str
        Always "DERIVED_V0_CONCEPTUAL"

    Notes
    -----
    Derivation path (not yet done):
        1. Compute Gamma^lambda_munu^SSZ from SSZ metric
        2. Compute spin connection omega_mu^{ab,SSZ}
        3. Integrate holonomy along null path: U(gamma) in SO(2)
        4. Extract rotation angle theta from U
    """
    G = 6.674e-11
    C = 2.998e8

    if branch == "rsg":
        r_isco_factor = 3.0
        r_char = r_isco_factor * rs_m
    elif branch == "photon_sphere":
        r_char = 1.387 * rs_m
    else:
        raise ValueError(f"Unknown branch '{branch}'. Use 'rsg' or 'photon_sphere'.")

    xi_char = get_xi(r_char, rs_m)
    phi_geom = 1.0

    theta_scalar = xi_char * phi_geom
    theta = np.full_like(np.asarray(freqs, dtype=float), theta_scalar)

    return theta, r_char, float(xi_char), TWIST_BRANCH_STATUS


def rotate_polarizations(h_plus, h_cross, theta):
    """Rotate GW polarisation state by angle theta.

    Applies a 2x2 rotation in (h_+, h_x) space:

        [h_+']   = | cos θ   -sin θ | * [h_+]
        [h_x']     | sin θ    cos θ |   [h_x]

    This is exact: R(theta) in SO(2), preserves total power.

    Parameters
    ----------
    h_plus : array
        Plus polarisation strain [dimensionless or complex]
    h_cross : array
        Cross polarisation strain [dimensionless or complex]
    theta : float or array
        Rotation angle [rad]

    Returns
    -------
    h_plus_rot : array
        Rotated plus polarisation
    h_cross_rot : array
        Rotated cross polarisation

    Notes
    -----
    For theta=0: identity (no twist).
    For theta=pi/4: maximal + <-> x mixing.
    For theta=pi/2: h_+ -> -h_x, h_x -> h_+.
    """
    c = np.cos(theta)
    s = np.sin(theta)
    h_plus_rot = c * h_plus - s * h_cross
    h_cross_rot = s * h_plus + c * h_cross
    return h_plus_rot, h_cross_rot


def apply_ssz_scale_and_twist(h_plus, h_cross, scale, theta):
    """Apply full SSZ scale + twist transformation.

    [h_+^SSZ]   = scale * R(theta) * [h_+^GR]
    [h_x^SSZ]                         [h_x^GR]

    where scale = (1 + dA_SSZ) * exp(i*dPsi_SSZ) is the existing
    V0/V1 scale factor and theta is the new twist angle.

    Setting theta=0 recovers the V0/V1 scale-only model exactly.

    Parameters
    ----------
    h_plus : array
        GR plus polarisation [complex frequency domain]
    h_cross : array
        GR cross polarisation [complex frequency domain]
    scale : complex float or array
        Combined SSZ scale factor (1+dA)*exp(i*dPsi)
    theta : float or array
        SSZ twist angle [rad]

    Returns
    -------
    h_plus_ssz : array
        SSZ plus polarisation
    h_cross_ssz : array
        SSZ cross polarisation
    """
    h_plus_rot, h_cross_rot = rotate_polarizations(h_plus, h_cross, theta)
    return scale * h_plus_rot, scale * h_cross_rot


def detector_strain_with_twist(h_plus_gr, h_cross_gr, scale, theta,
                                f_plus, f_cross):
    """Compute single-detector strain with SSZ scale + twist.

    h_I = F^+ * h_+^SSZ + F^x * h_x^SSZ
        = F^+ * scale * (h_+ cos θ - h_x sin θ)
        + F^x * scale * (h_+ sin θ + h_x cos θ)

    For theta=0: recovers h_I = scale * (F^+ h_+ + F^x h_x).

    Parameters
    ----------
    h_plus_gr, h_cross_gr : array
        GR polarisation components [complex]
    scale : complex float or array
        SSZ scale factor
    theta : float or array
        SSZ twist angle [rad]
    f_plus, f_cross : float
        Detector antenna pattern functions F^+, F^x [dimensionless]

    Returns
    -------
    h_det_ssz : array
        Detector strain with SSZ scale + twist
    h_det_gr : array
        Detector strain without SSZ (GR baseline)
    delta_h : array
        Difference h_SSZ - h_GR
    """
    h_plus_ssz, h_cross_ssz = apply_ssz_scale_and_twist(
        h_plus_gr, h_cross_gr, scale, theta
    )
    h_det_ssz = f_plus * h_plus_ssz + f_cross * h_cross_ssz
    h_det_gr = f_plus * h_plus_gr + f_cross * h_cross_gr
    delta_h = h_det_ssz - h_det_gr
    return h_det_ssz, h_det_gr, delta_h


def twist_sensitivity_scan(h_plus_gr, h_cross_gr, scale,
                            f_plus, f_cross, psd_f, psd_v, fs,
                            theta_values=None):
    """Scan over twist angles and compute lnL difference vs theta=0.

    For each theta, computes:
        delta_lnL(theta) = lnL[h_SSZ(theta)] - lnL[h_SSZ(theta=0)]

    Detectability criterion: |delta_lnL| >= 8 -> DETECTABLE

    Parameters
    ----------
    h_plus_gr, h_cross_gr : array
        GR polarisation components [complex, frequency domain]
    scale : complex or array
        SSZ scale factor (from V0/V1 pipeline)
    f_plus, f_cross : float
        Antenna patterns
    psd_f, psd_v : array
        PSD frequency and value arrays
    fs : float
        Sample rate [Hz]
    theta_values : array or None
        Twist angles to scan [rad]. Default: 0 to pi/4 in 20 steps.

    Returns
    -------
    results : list of dict
        Each entry: theta, delta_lnL, detectability
    """
    if theta_values is None:
        theta_values = np.linspace(0, np.pi / 4, 20)

    df = float(fs) / len(h_plus_gr)
    pi = np.interp(psd_f, psd_f, psd_v, left=psd_v[1], right=psd_v[-1])
    pi = np.where(pi > 0, pi, pi[pi > 0].min())

    def nwip(a, b):
        return 4.0 * np.real(np.sum(a * np.conj(b) / pi)) * df

    h_ref, _, _ = detector_strain_with_twist(
        h_plus_gr, h_cross_gr, scale, 0.0, f_plus, f_cross
    )

    results = []
    for theta in theta_values:
        h_ssz, _, _ = detector_strain_with_twist(
            h_plus_gr, h_cross_gr, scale, theta, f_plus, f_cross
        )
        lnL_ref = nwip(h_ref, h_ref) - 0.5 * nwip(h_ref, h_ref)
        lnL_ssz = nwip(h_ref, h_ssz) - 0.5 * nwip(h_ssz, h_ssz)
        dlnL = lnL_ssz - lnL_ref

        if abs(dlnL) >= 8.0:
            det = "DETECTABLE"
        elif abs(dlnL) >= 2.0:
            det = "MARGINAL"
        else:
            det = "UNDETECTABLE"

        results.append({
            "theta_rad": float(theta),
            "theta_deg": float(np.degrees(theta)),
            "delta_lnL": float(dlnL),
            "detectability": det,
        })
    return results
