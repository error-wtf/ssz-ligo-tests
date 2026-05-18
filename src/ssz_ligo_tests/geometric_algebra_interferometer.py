"""SSZ Geometric Algebra Interferometer Model.

Theory doc: docs/SSZ_GEOMETRIC_ALGEBRA_INTERFEROMETER_MODEL.md
Branch:     GA_INTERFEROMETER_BRANCH
Status:     DERIVED_V0_CONCEPTUAL

LIGO measures the phase difference:
    ΔΦ(t) = Φ_x(t) - Φ_y(t)

where each arm phase is a retarded line integral:
    Φ_i(t) = ∫_0^L F_i(ℓ, t - ℓ/c) dℓ

SSZ modifies the arm integrand via:
    Scale: s(r) = 1 + Ξ(r)
    Twist: R(θ) in the (e_x, e_y) arm plane

This module implements:
1. GA rotor: rotate_arm_basis(e_x, e_y, theta)
2. scale_and_twist_basis(scale, theta)
3. phase_integral_arm(field, L, c, t_grid): retarded integral
4. interferometer_phase_difference(phi_x, phi_y)
5. strain_from_phase_difference(delta_phi, wavelength, arm_length)
6. synthetic_gr_wave_plus(t, h0, f): h_xx = +h, h_yy = -h
7. synthetic_ssz_scale(t, Xi): constant scale field
8. synthetic_ssz_twist(t, theta): constant twist field
9. michelson_response: full end-to-end forward model

GA rotor in the (e_x, e_y) plane:
    R(θ) = exp(-θ/2 · e_x∧e_y)
    e_x → R e_x R† = e_x cosθ - e_y sinθ
    e_y → R e_y R† = e_x sinθ + e_y cosθ

In 2D vector representation: this is the standard SO(2) rotation.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import numpy as np


C_LIGHT = 2.998e8


# ---------------------------------------------------------------------------
# 1. Geometric Algebra rotor (2D, arm plane)
# ---------------------------------------------------------------------------

def rotate_arm_basis(e_x, e_y, theta):
    """Rotate arm basis vectors by angle theta in the (e_x, e_y) plane.

    GA rotor: R(θ) = exp(-θ/2 · B) with B = e_x∧e_y
    Action:   e_i → R e_i R†

    Result in component form:
        e_x' = e_x cosθ - e_y sinθ
        e_y' = e_x sinθ + e_y cosθ

    Parameters
    ----------
    e_x, e_y : ndarray, shape (2,)
        Unit basis vectors for arms x and y
    theta : float
        Rotation angle [rad]

    Returns
    -------
    e_x_rot, e_y_rot : ndarray, shape (2,)
        Rotated basis vectors
    """
    c, s = np.cos(theta), np.sin(theta)
    # Standard SO(2) counter-clockwise rotation:
    #   e_x' =  cos(θ) e_x + sin(θ) e_y
    #   e_y' = -sin(θ) e_x + cos(θ) e_y
    # (passive rotation: basis rotates, components transform inversely)
    # At θ=π/2: e_x → e_y, e_y → -e_x
    e_x_rot = c * e_x + s * e_y
    e_y_rot = -s * e_x + c * e_y
    return e_x_rot, e_y_rot


def scale_and_twist_basis(e_x, e_y, scale, theta):
    """Apply SSZ scale + twist to arm basis vectors.

    Combined transformation:
        e_i^SSZ = scale · R(θ) e_i R(θ)†

    Parameters
    ----------
    e_x, e_y : ndarray, shape (2,)
        Unit arm basis vectors
    scale : float
        SSZ scale factor s(r)/D(r) or (1+Ξ)²
    theta : float
        SSZ twist angle [rad]

    Returns
    -------
    e_x_ssz, e_y_ssz : ndarray, shape (2,)
        Scaled and twisted basis vectors
    """
    e_x_rot, e_y_rot = rotate_arm_basis(e_x, e_y, theta)
    return scale * e_x_rot, scale * e_y_rot


# ---------------------------------------------------------------------------
# 2. Synthetic GW fields
# ---------------------------------------------------------------------------

def synthetic_gr_wave_plus(t_grid, h0, f_gw):
    """Monochromatic + polarised GW: h_xx = +h(t), h_yy = -h(t).

    Parameters
    ----------
    t_grid : ndarray
        Time array [s]
    h0 : float
        Strain amplitude [dimensionless]
    f_gw : float
        GW frequency [Hz]

    Returns
    -------
    h_xx, h_yy : ndarray
        Metric perturbation components along arm x and y
    """
    h = h0 * np.sin(2.0 * np.pi * f_gw * t_grid)
    return h, -h


def synthetic_gr_wave_cross(t_grid, h0, f_gw):
    """Monochromatic × polarised GW: h_xy = h_yx = h(t), h_xx = h_yy = 0.

    Parameters
    ----------
    t_grid : ndarray
        Time array [s]
    h0 : float
        Strain amplitude [dimensionless]
    f_gw : float
        GW frequency [Hz]

    Returns
    -------
    h_xx, h_yy : ndarray
        Projected components for Michelson response
        (for × pol: h_xx = 0, h_yy = 0 in standard L-frame)
    h_xy : ndarray
        Off-diagonal component
    """
    h = h0 * np.sin(2.0 * np.pi * f_gw * t_grid)
    return np.zeros_like(h), np.zeros_like(h), h


def synthetic_ssz_scale(t_grid, xi_val):
    """Constant SSZ scale field s(t) = 1 + Xi.

    In the far-field / static approximation the SSZ scale along the arm
    is constant (Ξ evaluated at the detector location). This function
    returns a constant array for use in arm integrals.

    Parameters
    ----------
    t_grid : ndarray
        Time array [s] (shape only — output is constant)
    xi_val : float
        Ξ value at the arm location

    Returns
    -------
    scale : ndarray
        s/D = (1+Ξ)² values, shape matching t_grid
    s_val : float
        s = 1 + Ξ
    d_val : float
        D = 1/(1+Ξ)
    """
    s_val = 1.0 + xi_val
    d_val = 1.0 / s_val
    s_over_d = s_val / d_val
    return np.full_like(t_grid, s_over_d), s_val, d_val


def synthetic_ssz_twist(t_grid, theta_val):
    """Constant SSZ twist field theta(t) = theta_val.

    Placeholder — real theta(t) would come from the spin connection
    holonomy (not yet derived).

    Parameters
    ----------
    t_grid : ndarray
        Time array [s] (shape only)
    theta_val : float
        Constant twist angle [rad]

    Returns
    -------
    theta : ndarray
        Constant array theta_val, shape matching t_grid
    """
    return np.full_like(t_grid, float(theta_val))


# ---------------------------------------------------------------------------
# 3. Phase integral (retarded)
# ---------------------------------------------------------------------------

def phase_integral_arm(field_t, L, c, t_grid, n_steps=None):
    """Retarded path integral of a field along one arm.

    Φ(t) = ∫_0^L F(ℓ, t - ℓ/c) dℓ

    The field is sampled at t_ret = t - ℓ/c for each position ℓ along
    the arm. This captures the fact that photons at position ℓ at time t
    entered the arm at time t - ℓ/c.

    For LIGO (L=4 km, f~100 Hz):
        ωL/c = 2π*100*4000/3e8 ≈ 8.4e-3 rad << 1
    So retarded ≈ instantaneous to 0.01% — but we implement it correctly.

    Parameters
    ----------
    field_t : ndarray, shape (N,)
        Field values at times t_grid [units depend on context]
    L : float
        Arm length [m]
    c : float
        Speed of light [m/s]
    t_grid : ndarray, shape (N,)
        Time array [s], must be uniformly spaced
    n_steps : int or None
        Number of integration steps along the arm.
        Default: max(100, int(L/c * fs)) where fs = 1/dt

    Returns
    -------
    phi : ndarray, shape (N,)
        Phase integral Φ(t) [same units as field_t × m]
    phi_instantaneous : ndarray, shape (N,)
        Instantaneous approximation Φ_inst = L * F(t) for comparison
    retarded_correction : ndarray, shape (N,)
        Relative correction (phi - phi_inst) / phi_inst
    """
    dt = float(t_grid[1] - t_grid[0])
    fs = 1.0 / dt

    if n_steps is None:
        transit = L / c
        n_steps = max(50, int(transit * fs))

    ell = np.linspace(0.0, L, n_steps)
    d_ell = L / (n_steps - 1)
    tau = ell / c       # retardation per position

    phi = np.zeros(len(t_grid))
    for k, t_k in enumerate(t_grid):
        t_ret = t_k - tau
        # Interpolate field at retarded times
        f_ret = np.interp(t_ret, t_grid, field_t,
                          left=field_t[0], right=field_t[-1])
        phi[k] = np.trapezoid(f_ret, dx=d_ell)

    phi_inst = L * field_t
    # Absolute retarded correction (avoid division by tiny phi_inst).
    # Relative correction would blow up when phi_inst ~ h0 ~ 1e-21.
    # Use dimensionless ratio only when phi_inst is not negligible.
    phi_max = float(np.max(np.abs(phi_inst)))
    if phi_max > 0:
        ret_corr = (phi - phi_inst) / phi_max
    else:
        ret_corr = np.zeros_like(phi)

    return phi, phi_inst, ret_corr


def interferometer_phase_difference(phi_x, phi_y):
    """Interferometer output: ΔΦ = Φ_x - Φ_y.

    Parameters
    ----------
    phi_x, phi_y : ndarray
        Arm phase integrals [same units]

    Returns
    -------
    delta_phi : ndarray
        Phase difference Φ_x - Φ_y
    """
    return phi_x - phi_y


def strain_from_phase_difference(delta_phi, wavelength, arm_length):
    """Map phase difference to effective strain.

    h(t) = ΔΦ · λ / (4π L)

    Parameters
    ----------
    delta_phi : ndarray
        Phase difference [rad]
    wavelength : float
        Laser wavelength [m] (LIGO: 1064e-9 m)
    arm_length : float
        Arm length [m] (LIGO: 4000 m)

    Returns
    -------
    h : ndarray
        Strain [dimensionless]
    """
    return delta_phi * wavelength / (4.0 * np.pi * arm_length)


# ---------------------------------------------------------------------------
# 4. Full Michelson response: end-to-end forward model
# ---------------------------------------------------------------------------

def michelson_response(t_grid, h_xx, h_yy,
                        scale=1.0, theta=0.0,
                        L=4000.0, c=C_LIGHT,
                        wavelength=1064e-9,
                        n_steps=None):
    """Full Michelson interferometer forward model with SSZ scale + twist.

    Pipeline:
    1. Apply SSZ scale + twist to arm basis directions
    2. Project h_xx, h_yy onto twisted arm directions
    3. Compute retarded phase integral for each arm
    4. Compute phase difference
    5. Map to strain

    For theta=0 and scale=1 with h_+(t) input, should recover h(t) (Test A).

    Parameters
    ----------
    t_grid : ndarray
        Time array [s], uniformly spaced
    h_xx, h_yy : ndarray
        Metric perturbation components along nominal x and y arms
    scale : float
        SSZ scale factor s/D (default: 1.0 = pure GR)
    theta : float
        SSZ twist angle [rad] (default: 0.0 = no twist)
    L : float
        Arm length [m]
    c : float
        Speed of light [m/s]
    wavelength : float
        Laser wavelength [m]
    n_steps : int or None
        Integration steps along arm

    Returns
    -------
    h_strain : ndarray
        Effective strain h(t) [dimensionless]
    phi_x, phi_y : ndarray
        Arm phase integrals
    delta_phi : ndarray
        Phase difference
    meta : dict
        Diagnostics: scale, theta, [s/D-1], retarded_correction_rms
    """
    e_x = np.array([1.0, 0.0])
    e_y = np.array([0.0, 1.0])

    e_x_ssz, e_y_ssz = scale_and_twist_basis(e_x, e_y, scale, theta)

    # Nominal photon wavevector magnitude: ω_L / c
    # We absorb this into the field definition: F_x(t) = h_xx(t) / 2
    # so that Φ_x = (ω_L/c) ∫ (1 + h_xx/2) dℓ → phase modulation part
    # We track only the GW modulation (subtract the DC free-propagation phase)

    # Projected GW field onto arm directions after twist
    # e_x^SSZ component along nominal x is cos(theta)*scale
    # For the GW metric element: h_xx projected onto twisted e_x
    proj_x = float(e_x_ssz[0]**2)   # e_x^SSZ · ê_x projected
    proj_y = float(e_y_ssz[1]**2)   # e_y^SSZ · ê_y projected

    # Field along arm x: (ω_L/c) * (1 + h_eff_x/2) → modulation part
    # h_eff_x = proj_x * h_xx + (twist cross-term) * h_yy
    proj_x_onto_y = float(e_x_ssz[1]**2)  # leakage of x arm into y direction
    proj_y_onto_x = float(e_y_ssz[0]**2)  # leakage of y arm into x direction

    field_x = 0.5 * (proj_x * h_xx + proj_x_onto_y * h_yy) * scale
    field_y = 0.5 * (proj_y * h_yy + proj_y_onto_x * h_xx) * scale

    phi_x, phi_x_inst, ret_x = phase_integral_arm(
        field_x, L, c, t_grid, n_steps=n_steps
    )
    phi_y, phi_y_inst, ret_y = phase_integral_arm(
        field_y, L, c, t_grid, n_steps=n_steps
    )

    delta_phi = interferometer_phase_difference(phi_x, phi_y)
    h_strain = strain_from_phase_difference(delta_phi, wavelength, L)

    meta = {
        "scale": scale,
        "theta_rad": theta,
        "s_over_D_minus_1": scale - 1.0,
        "proj_x": proj_x,
        "proj_y": proj_y,
        "proj_cross_x": proj_x_onto_y,
        "proj_cross_y": proj_y_onto_x,
        "retarded_correction_rms_x": float(np.sqrt(np.mean(ret_x**2))),
        "retarded_correction_rms_y": float(np.sqrt(np.mean(ret_y**2))),
    }

    return h_strain, phi_x, phi_y, delta_phi, meta
