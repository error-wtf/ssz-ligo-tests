"""SSZ-LIGO Phase Transport Module.

Theory doc: docs/SSZ_LIGO_PHASE_TRANSPORT_PRINCIPLE.md
Branch:     PHASE_TRANSPORT_BRANCH
Status:     DERIVED_V0_CONCEPTUAL

Core principle:
  Local co-scaling of the detector is NOT directly observable.
  The observable is the RELATIVE accumulated phase between two arms:

      ΔΦ(t) = Φ_x(t) - Φ_y(t)

  where each Φ_i is a retarded curve integral of the photon phase field.

  If twist is included, the full relative transport is:

      U_rel = U_y† U_x   (phase part)
      R_rel = R_y^{-1} R_x   (frame-rotation part, SO(2))

  The observable strain is:
      h(t) ~ λ/(2πL) * ΔΦ(t)

  GR is recovered when SSZ correction = 0.

Functions:
  1. photon_phase_arm(h_arm, L, c, t_grid): retarded phase integral
  2. relative_phase(phi_x, phi_y): ΔΦ = Φ_x - Φ_y
  3. phase_to_strain(delta_phi, wavelength, arm_length): h = λ/(2πL) ΔΦ
  4. transport_operator_u1(phi): U = exp(i Φ) ∈ U(1)
  5. relative_transport_u1(u_x, u_y): U_rel = U_y† U_x
  6. rotation_operator_so2(theta): R(θ) ∈ SO(2)
  7. relative_rotation(r_x, r_y): R_rel = R_y^{-1} R_x
  8. cosaling_argument(xi_local): show that co-scaling is unobservable
  9. full_transport(phi_x, phi_y, theta_x, theta_y): combined U(1)×SO(2)
 10. gr_michelson_response(h_plus, h_cross, F_plus, F_cross): GR baseline

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import numpy as np

C_LIGHT = 2.998e8
LAMBDA_LIGO = 1064e-9
L_LIGO = 4000.0


# ---------------------------------------------------------------------------
# 1. Photon phase accumulation along one arm (retarded integral)
# ---------------------------------------------------------------------------

def photon_phase_arm(h_arm, L, c, t_grid, n_steps=100):
    """Retarded photon phase accumulation along one interferometer arm.

    Φ(t) = ∫_0^L (ω_L/c) * (1 + h_arm(t - ℓ/c) / 2) dℓ

    We track only the GW modulation:
    φ(t) = (1/2) ∫_0^L h_arm(t - ℓ/c) dℓ

    The DC term (ω_L L/c) cancels in the phase difference.

    Parameters
    ----------
    h_arm : ndarray, shape (N,)
        Metric perturbation along this arm: h_xx for x-arm, h_yy for y-arm
    L : float
        Arm length [m]
    c : float
        Speed of light [m/s]
    t_grid : ndarray, shape (N,)
        Uniformly spaced time array [s]
    n_steps : int
        Number of integration points along the arm

    Returns
    -------
    phi : ndarray, shape (N,)
        Phase modulation Φ(t) = (1/2) ∫ h(t-ℓ/c) dℓ  [m]
    """
    ell = np.linspace(0.0, L, n_steps)
    d_ell = L / (n_steps - 1)
    tau = ell / c

    phi = np.zeros(len(t_grid))
    for k, t_k in enumerate(t_grid):
        h_ret = np.interp(t_k - tau, t_grid, h_arm,
                          left=h_arm[0], right=h_arm[-1])
        phi[k] = 0.5 * np.trapezoid(h_ret, dx=d_ell)

    return phi


# ---------------------------------------------------------------------------
# 2. Relative phase (the only observable)
# ---------------------------------------------------------------------------

def relative_phase(phi_x, phi_y):
    """Relative accumulated phase: ΔΦ = Φ_x - Φ_y.

    This is the **only** directly observable quantity in a Michelson
    interferometer. Absolute phases Φ_x, Φ_y are NOT observable
    because the laser source is inside the same co-scaling frame.

    Parameters
    ----------
    phi_x, phi_y : ndarray
        Phase integrals along arm x and y

    Returns
    -------
    delta_phi : ndarray
        ΔΦ = Φ_x - Φ_y
    """
    return phi_x - phi_y


def phase_to_strain(delta_phi, wavelength=LAMBDA_LIGO,
                    arm_length=L_LIGO):
    """Map phase difference to effective GW strain.

    h(t) = ΔΦ(t) * λ / (2π L)

    Note: this differs from the previous GA model by a factor of 2π
    vs 4π — here we use the standard LIGO convention:
    h = ΔΦ * λ / (2π L)

    Parameters
    ----------
    delta_phi : ndarray
        Phase difference ΔΦ [m * rad / m = rad, or just dimensionless
        if h_arm was dimensionless]
    wavelength : float
        Laser wavelength [m]
    arm_length : float
        Arm length [m]

    Returns
    -------
    h : ndarray
        Strain [dimensionless]
    """
    return delta_phi * wavelength / (2.0 * np.pi * arm_length)


# ---------------------------------------------------------------------------
# 3. U(1) phase transport operator
# ---------------------------------------------------------------------------

def transport_operator_u1(phi):
    """U(1) phase transport operator: U = exp(i Φ).

    For a scalar phase accumulation Φ along one arm, the transport
    operator is a unit complex number:

        U_i = exp(i Φ_i)

    Parameters
    ----------
    phi : ndarray or float
        Phase accumulation [rad or dimensionless]

    Returns
    -------
    U : ndarray or complex
        U(1) element exp(i Φ)
    """
    return np.exp(1j * np.asarray(phi, dtype=complex))


def relative_transport_u1(u_x, u_y):
    """Relative U(1) holonomy: U_rel = U_y† U_x = exp(i ΔΦ).

    This is the observable phase loop. It does not depend on the
    global DC phase offset because U_y† cancels it.

    Parameters
    ----------
    u_x, u_y : ndarray or complex
        U(1) transport operators for arms x and y

    Returns
    -------
    u_rel : ndarray or complex
        U_rel = conj(u_y) * u_x = exp(i ΔΦ)
    delta_phi : ndarray or float
        ΔΦ = angle(U_rel)
    """
    u_rel = np.conj(u_y) * u_x
    delta_phi = np.angle(u_rel)
    return u_rel, delta_phi


# ---------------------------------------------------------------------------
# 4. SO(2) frame rotation transport
# ---------------------------------------------------------------------------

def rotation_operator_so2(theta):
    """SO(2) rotation matrix R(θ) for frame twist in the (e_x, e_y) plane.

    R(θ) = [[cos θ, -sin θ],
             [sin θ,  cos θ]]

    In GA language: R(θ) = exp(-θ/2 · B) with B = e_x ∧ e_y.

    For the photon phase, the relevant projection is:
        <k, R e_arm R†> = cos θ · k · e_arm + sin θ · k · e_perp

    Parameters
    ----------
    theta : float
        Rotation angle [rad]

    Returns
    -------
    R : ndarray, shape (2, 2)
        SO(2) rotation matrix
    """
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def relative_rotation(theta_x, theta_y):
    """Relative SO(2) holonomy: R_rel = R_y^{-1} R_x.

    This is the observable frame-twist difference between arms.
    It represents the differential polarization rotation imprinted
    by the SSZ geometry along the two light paths.

    For the + polarised GW with SSZ twist:
        R_rel maps (h+, h×) → (cos Δθ * h+ - sin Δθ * h×,
                                sin Δθ * h+ + cos Δθ * h×)

    Parameters
    ----------
    theta_x, theta_y : float
        Frame twist angles accumulated along arms x and y

    Returns
    -------
    R_rel : ndarray, shape (2, 2)
        R_rel = R(theta_x - theta_y) [since SO(2) is abelian]
    delta_theta : float
        Differential twist Δθ = θ_x - θ_y
    """
    delta_theta = float(theta_x) - float(theta_y)
    return rotation_operator_so2(delta_theta), delta_theta


# ---------------------------------------------------------------------------
# 5. Co-scaling argument (analytical)
# ---------------------------------------------------------------------------

def coscaling_argument(xi_local):
    """Show that local co-scaling is not directly observable.

    If both the arm length L and laser wavelength λ scale by s = 1 + Xi,
    the Michelson fringe count N = L/λ is unchanged:

        N_SSZ = (s * L) / (s * λ) = L / λ = N_GR

    Only the DIFFERENTIAL accumulation ΔΦ = Φ_x - Φ_y remains observable
    when the two arms see different metric perturbations (e.g., GW).

    Parameters
    ----------
    xi_local : float
        Local Xi value at detector location

    Returns
    -------
    result : dict
        s, D, s_over_D, co_scaled_ratio, observable_delta_h_over_h
    """
    s = 1.0 + xi_local
    d = 1.0 / s
    s_over_d = s / d

    # Fringe count under co-scaling: N_SSZ / N_GR
    # Both L and lambda scale by s → ratio unchanged
    coscaled_fringe_ratio = 1.0

    # If only L scales but lambda does not (GW case):
    # ΔN = L * h / 2 / lambda (standard GW Michelson response)
    # SSZ correction to ΔN: (s - 1) * L * h / 2 / lambda ~ Xi * ΔN_GR
    delta_h_over_h = xi_local   # relative change if NOT co-scaled

    return {
        "xi_local": xi_local,
        "s": s,
        "D": d,
        "s_over_D": s_over_d,
        "coscaled_fringe_ratio": coscaled_fringe_ratio,
        "delta_h_over_h_if_not_coscaled": delta_h_over_h,
        "observable_local_correction": xi_local,
        "is_coscaled_unobservable": True,
    }


# ---------------------------------------------------------------------------
# 6. Full combined transport: U(1) × SO(2)
# ---------------------------------------------------------------------------

def full_transport(phi_x, phi_y, theta_x=0.0, theta_y=0.0):
    """Combined U(1) × SO(2) relative transport for both arms.

    The full photon transport along each arm is:
        V_i = exp(i Φ_i) · R(θ_i)   ∈ U(1) × SO(2)

    The relative transport is:
        V_rel = V_y^{-1} · V_x
              = exp(i ΔΦ) · R(Δθ)

    This is the most general form of the SSZ-LIGO observable.

    Parameters
    ----------
    phi_x, phi_y : ndarray or float
        Phase integrals along arms x and y
    theta_x, theta_y : float
        Frame twist angles along arms x and y (default 0 = GR)

    Returns
    -------
    delta_phi : ndarray or float
        Differential phase ΔΦ = Φ_x - Φ_y
    R_rel : ndarray, shape (2, 2)
        Relative SO(2) frame rotation
    delta_theta : float
        Differential twist Δθ
    u_rel : ndarray or complex
        exp(i ΔΦ), U(1) part
    """
    delta_phi = relative_phase(phi_x, phi_y)
    u_x = transport_operator_u1(phi_x)
    u_y = transport_operator_u1(phi_y)
    u_rel, _ = relative_transport_u1(u_x, u_y)
    R_rel, delta_theta = relative_rotation(theta_x, theta_y)

    return delta_phi, R_rel, delta_theta, u_rel


# ---------------------------------------------------------------------------
# 7. GR Michelson baseline
# ---------------------------------------------------------------------------

def gr_michelson_response(h_plus, h_cross, F_plus, F_cross,
                           L=L_LIGO, c=C_LIGHT, t_grid=None,
                           n_steps=100):
    """Standard GR Michelson response: h(t) = F+ h+(t) + F× h×(t).

    For a + polarised wave (h_xx = +h, h_yy = -h) in an L-shaped
    interferometer with antenna patterns F+, F×.

    This is the limiting case: SSZ correction = 0, theta = 0.

    Parameters
    ----------
    h_plus, h_cross : ndarray
        GW polarisation components
    F_plus, F_cross : float
        Detector antenna patterns
    L : float
        Arm length [m]
    c : float
        Speed of light [m/s]
    t_grid : ndarray or None
        Time array [s]. If None, uses simple instantaneous approximation.
    n_steps : int
        Integration steps for retarded integral

    Returns
    -------
    h_det : ndarray
        Detector strain F+ h+ + F× h×
    phi_x : ndarray
        Phase integral along x-arm (if t_grid provided)
    phi_y : ndarray
        Phase integral along y-arm (if t_grid provided)
    delta_phi : ndarray
        ΔΦ = Φ_x - Φ_y
    """
    if t_grid is None:
        # Instantaneous approximation (standard pipeline)
        h_xx = h_plus
        h_yy = -h_plus
        phi_x = 0.5 * L * h_xx
        phi_y = 0.5 * L * h_yy
    else:
        # Retarded integral
        h_xx = h_plus     # for + polarisation: arm x sees +h
        h_yy = -h_plus    # arm y sees -h
        phi_x = photon_phase_arm(h_xx, L, c, t_grid, n_steps)
        phi_y = photon_phase_arm(h_yy, L, c, t_grid, n_steps)

    delta_phi = relative_phase(phi_x, phi_y)

    # Detector output via antenna patterns
    h_det = F_plus * h_plus + F_cross * h_cross

    return h_det, phi_x, phi_y, delta_phi


# ---------------------------------------------------------------------------
# 8. SSZ source-frame modification (full pipeline entry point)
# ---------------------------------------------------------------------------

def ssz_source_frame_response(h_plus, h_cross, F_plus, F_cross,
                               scale=1.0, theta=0.0,
                               L=L_LIGO, c=C_LIGHT, t_grid=None,
                               n_steps=100):
    """SSZ-modified Michelson response: source-frame scale + twist.

    Applies the source-frame SSZ modification:

        [h+^SSZ]   = scale * R(theta) * [h+^GR]
        [hx^SSZ]                         [hx^GR]

    Then projects onto detector via F+, F×.

    The local arm correction is NOT applied here — it is negligible
    (see DETECTOR_SIDE_ANHOLONOMY_RESULT.md).

    Parameters
    ----------
    h_plus, h_cross : ndarray
        GR polarisation components (source frame)
    F_plus, F_cross : float
        Detector antenna patterns
    scale : float
        SSZ amplitude scale factor S(f) (default 1.0 = GR)
    theta : float
        SSZ polarisation twist angle [rad] (default 0.0 = GR)
    L, c, t_grid, n_steps : see gr_michelson_response

    Returns
    -------
    h_det_ssz : ndarray
        SSZ detector strain
    h_det_gr : ndarray
        GR detector strain (reference)
    h_plus_ssz, h_cross_ssz : ndarray
        SSZ-modified polarisation components
    meta : dict
        scale, theta, delta_h_rms (relative difference)
    """
    c_theta, s_theta = np.cos(theta), np.sin(theta)
    h_plus_ssz = scale * (c_theta * h_plus - s_theta * h_cross)
    h_cross_ssz = scale * (s_theta * h_plus + c_theta * h_cross)

    h_det_ssz = F_plus * h_plus_ssz + F_cross * h_cross_ssz
    h_det_gr = F_plus * h_plus + F_cross * h_cross

    rms_gr = float(np.sqrt(np.mean(h_det_gr**2)))
    rms_diff = float(np.sqrt(np.mean((h_det_ssz - h_det_gr)**2)))

    meta = {
        "scale": scale,
        "theta_rad": theta,
        "delta_h_rms": rms_diff,
        "delta_h_over_h_rms": rms_diff / rms_gr if rms_gr > 0 else 0.0,
        "h_det_ssz_rms": float(np.sqrt(np.mean(h_det_ssz**2))),
        "h_det_gr_rms": rms_gr,
    }

    return h_det_ssz, h_det_gr, h_plus_ssz, h_cross_ssz, meta
