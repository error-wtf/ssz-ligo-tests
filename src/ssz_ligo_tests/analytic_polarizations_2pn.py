"""Analytic 2PN-separated h_plus / h_cross approximation.

Purpose: Break the 0PN polarization degeneracy for twist-branch testing.
Status:  ANALYTIC_2PN_CONTROL_APPROXIMATION

Reference formulas: Arun et al. 2004 PRD 71 084008 (amplitude corrections);
  Blanchet et al. TaylorF2 phase series.

Rules:
  - No LALSuite required.
  - No posterior parameters.
  - Non-spinning, quasi-circular inspiral only.
  - Valid in inspiral regime f << f_ISCO.
  - Mark all outputs as ANALYTIC_2PN_CONTROL, not final GR PE waveform.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
POLARIZATION_CONTROL: ANALYTIC_2PN_APPROXIMATION
"""
import numpy as np

C_LIGHT = 2.998e8
G_NEWTON = 6.674e-11
M_SUN = 1.989e30

POLARIZATION_CONTROL_STATUS = "ANALYTIC_2PN_APPROXIMATION"


def _pn_x(freqs, M_total_kg):
    """PN expansion parameter x = (pi M f G/c^3)^{2/3}."""
    u = (np.pi * G_NEWTON * M_total_kg / C_LIGHT**3 * freqs)**(1.0 / 3.0)
    return u**2


def _pn_u(freqs, M_total_kg):
    """PN velocity u = (pi M f G/c^3)^{1/3}."""
    return (np.pi * G_NEWTON * M_total_kg / C_LIGHT**3 * freqs)**(1.0 / 3.0)


def phase_2pn_taylorf2(freqs, M_chirp_kg, M_total_kg, eta,
                       t_c=0.0, phi_c=0.0):
    """TaylorF2 phase at 2PN order (non-spinning, circular).

    Psi(f) = 2 pi f t_c - phi_c - pi/4
             + (3/(128 eta)) * u^{-5} * [
                 1                                          (0PN)
                 + (20/9)(743/336 + 11/4 eta) * u^2        (1PN)
                 - 16 pi * u^3                              (1.5PN)
                 + 10*(3058673/1016064 + 5429/1008*eta
                       + 617/144*eta^2) * u^4              (2PN)
               ]

    Source: Blanchet et al. (2004) review; Arun et al. (2004) PRD 71 084008.
    Conventions: u = (pi M_total G f / c^3)^{1/3}

    Parameters
    ----------
    freqs : ndarray
        Frequency array [Hz], must be > 0
    M_chirp_kg : float
        Chirp mass [kg]
    M_total_kg : float
        Total mass [kg]
    eta : float
        Symmetric mass ratio = m1*m2 / M_total^2
    t_c, phi_c : float
        Coalescence time and phase (default 0)

    Returns
    -------
    psi : ndarray, same shape as freqs
    """
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, 1e-10)
    u = _pn_u(safe_f, M_total_kg)

    c0PN = 1.0
    c1PN = (20.0 / 9.0) * (743.0 / 336.0 + 11.0 / 4.0 * eta) * u**2
    c15PN = -16.0 * np.pi * u**3
    c2PN = (10.0 * (3058673.0 / 1016064.0
                    + 5429.0 / 1008.0 * eta
                    + 617.0 / 144.0 * eta**2) * u**4)

    psi_stationary = (3.0 / (128.0 * eta)) * u**(-5) * (
        c0PN + c1PN + c15PN + c2PN
    )

    psi = 2.0 * np.pi * safe_f * t_c - phi_c - np.pi / 4.0 + psi_stationary
    return psi


def amplitude_0pn(freqs, M_chirp_kg, d_lum_m):
    """Leading-order (0PN) Fourier amplitude.

    A_0(f) = C * (pi Mc)^{5/6} * f^{-7/6}

    C = sqrt(5*pi/24) * G^{5/6} / (c^{3/2} * pi^{7/6})

    Source: Cutler & Flanagan (1994); Finn & Chernoff (1993).
    """
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, 1e-10)
    G = G_NEWTON
    c = C_LIGHT
    prefac = (np.sqrt(5.0 * np.pi / 24.0)
              * G**(5.0 / 6.0) / (c**(3.0 / 2.0) * np.pi**(7.0 / 6.0)))
    A = prefac * (G * M_chirp_kg / c**3)**(5.0 / 6.0) * safe_f**(-7.0 / 6.0)
    return A / d_lum_m


def _amp_corrections_hplus(x, eta, iota):
    """PN amplitude corrections for h_plus: H+_0 + H+_1PN + H+_2PN.

    Returns total amplitude factor (dimensionless).

    Source: Arun et al. 2004 PRD 71 084008, Eq. (3.6)-(3.10).
    Notation: x = (pi M f G/c^3)^{2/3}, eta = m1 m2 / M^2.

    Note: 1.5PN amplitude correction is zero for non-spinning circular
    inspiral in the restricted waveform approximation.
    """
    ci = np.cos(iota)
    si = np.sin(iota)
    ci2 = ci**2
    si2 = si**2

    # 0PN: standard
    H0 = (1.0 + ci2) / 2.0

    # 1PN: Eq. (3.7) of Arun et al.
    # H+^{1/2} (half-integer PN) is zero for circular orbits
    # H+^{1} (1PN):
    H1 = (x * ((19.0 / 6.0 + 3.0 / 2.0 * eta - 1.0 / 3.0 * eta**2)
               + (-19.0 / 6.0 + 11.0 / 6.0 * eta) * ci2))

    # 2PN: Eq. (3.9) of Arun et al.
    H2 = (x**2 * (
        (5.0 / 24.0) * (22.0 - 92.0 * eta + 96.0 * eta**2)
        + (-9.0 / 8.0) * (2.0 - 4.0 * eta + 3.0 * eta**2) * ci2
        + (5.0 / 24.0) * (2.0 - 8.0 * eta) * si2   # si^2 term (face-on suppressed)
    ))

    return H0 + H1 + H2


def _amp_corrections_hcross(x, eta, iota):
    """PN amplitude corrections for h_cross: H×_0 + H×_1PN + H×_2PN.

    Source: Arun et al. 2004 PRD 71 084008, Eq. (3.6)-(3.10).

    Note: h× has a ci = cos(iota) factor; at iota=0 (face-on),
    H×_0 = cos(0) = 1. At iota=pi/2 (edge-on), H×_0 = 0.
    The 1PN and 2PN corrections break the simple -i*h+ relation.
    """
    ci = np.cos(iota)
    si = np.sin(iota)
    ci2 = ci**2
    si2 = si**2

    # 0PN
    H0 = ci

    # 1PN: the cos(iota) prefactor AND a distinct coefficient from h+
    # Arun et al. Eq. (3.7) cross terms
    H1 = x * ci * (17.0 / 6.0 - 5.0 / 6.0 * eta)

    # 2PN: cross-polarisation 2PN amplitude
    # Arun et al. Eq (3.9): distinct from h+
    H2 = x**2 * ci * (
        (5.0 / 8.0) * (2.0 + 10.0 * eta - 22.0 * eta**2)
        + (-1.0 / 4.0) * (2.0 - 6.0 * eta) * si2
    )

    return H0 + H1 + H2


def h_plus_2pn(freqs, M_chirp_kg, M_total_kg, eta,
               iota, d_lum_m, t_c=0.0, phi_c=0.0):
    """2PN h_plus in frequency domain (TaylorF2, non-spinning, circular).

    h+(f) = A_0(f) * H+(x, eta, iota) * exp(i Psi_2PN(f))

    Parameters
    ----------
    freqs : ndarray
        Frequency array [Hz], positive values only
    M_chirp_kg : float
        Chirp mass [kg]
    M_total_kg : float
        Total mass [kg]
    eta : float
        Symmetric mass ratio
    iota : float
        Inclination angle [rad] (0=face-on, pi/2=edge-on)
    d_lum_m : float
        Luminosity distance [m]
    t_c, phi_c : float
        Coalescence time [s] and phase [rad]

    Returns
    -------
    hp : ndarray, complex
        h_plus frequency domain waveform
    status : str
    """
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, 1e-10)
    A0 = amplitude_0pn(safe_f, M_chirp_kg, d_lum_m)
    x = _pn_x(safe_f, M_total_kg)
    H_plus = _amp_corrections_hplus(x, eta, iota)
    psi = phase_2pn_taylorf2(safe_f, M_chirp_kg, M_total_kg, eta, t_c, phi_c)
    hp = A0 * H_plus * np.exp(1j * psi)
    return hp, POLARIZATION_CONTROL_STATUS


def h_cross_2pn(freqs, M_chirp_kg, M_total_kg, eta,
                iota, d_lum_m, t_c=0.0, phi_c=0.0):
    """2PN h_cross in frequency domain (TaylorF2, non-spinning, circular).

    h×(f) = A_0(f) * H×(x, eta, iota) * exp(i (Psi_2PN(f) - pi/2))

    The additional -pi/2 phase in h× relative to h+ is exact at all PN
    orders for non-spinning circular orbits in the stationary phase
    approximation.

    Parameters
    ----------
    (same as h_plus_2pn)

    Returns
    -------
    hx : ndarray, complex
    status : str
    """
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, 1e-10)
    A0 = amplitude_0pn(safe_f, M_chirp_kg, d_lum_m)
    x = _pn_x(safe_f, M_total_kg)
    H_cross = _amp_corrections_hcross(x, eta, iota)
    psi = phase_2pn_taylorf2(safe_f, M_chirp_kg, M_total_kg, eta, t_c, phi_c)
    hx = A0 * H_cross * np.exp(1j * (psi - np.pi / 2.0))
    return hx, POLARIZATION_CONTROL_STATUS


def h_plus_0pn(freqs, M_chirp_kg, M_total_kg, eta,
               iota, d_lum_m, t_c=0.0, phi_c=0.0):
    """0PN h_plus baseline (for degeneracy comparison)."""
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, 1e-10)
    A0 = amplitude_0pn(safe_f, M_chirp_kg, d_lum_m)
    ci = np.cos(iota)
    H0 = (1.0 + ci**2) / 2.0
    psi = phase_2pn_taylorf2(safe_f, M_chirp_kg, M_total_kg, eta, t_c, phi_c)
    return A0 * H0 * np.exp(1j * psi), "0PN_BASELINE"


def h_cross_0pn(freqs, M_chirp_kg, M_total_kg, eta,
                iota, d_lum_m, t_c=0.0, phi_c=0.0):
    """0PN h_cross baseline (for degeneracy comparison)."""
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, 1e-10)
    A0 = amplitude_0pn(safe_f, M_chirp_kg, d_lum_m)
    ci = np.cos(iota)
    H0 = ci
    psi = phase_2pn_taylorf2(safe_f, M_chirp_kg, M_total_kg, eta, t_c, phi_c)
    return A0 * H0 * np.exp(1j * (psi - np.pi / 2.0)), "0PN_BASELINE"


def polarization_amplitude_ratio(hp, hx):
    """Frequency-dependent amplitude ratio |h×(f)| / |h+(f)|.

    At 0PN this is constant (= 2 cos(i) / (1+cos²i)).
    At 2PN this varies with f — the key degeneracy diagnostic.

    Parameters
    ----------
    hp, hx : ndarray, complex

    Returns
    -------
    ratio : ndarray, real
        |hx(f)| / |hp(f)| for hp != 0
    """
    hp = np.asarray(hp)
    hx = np.asarray(hx)
    safe_hp = np.where(np.abs(hp) > 0, np.abs(hp), np.nan)
    return np.abs(hx) / safe_hp


def polarization_degeneracy_metric(hp, hx):
    """Quantify how degenerate h+ and h× are.

    Returns the std of |hx(f)/hp(f)| normalized by mean.
    At 0PN: std/mean -> 0 (perfectly degenerate).
    At 2PN: std/mean > 0 (frequency-dependent ratio).

    A higher value means less degeneracy = better twist sensitivity.
    """
    ratio = polarization_amplitude_ratio(hp, hx)
    valid = ratio[np.isfinite(ratio)]
    if len(valid) == 0 or np.mean(valid) == 0:
        return 0.0
    return float(np.std(valid) / np.mean(valid))
