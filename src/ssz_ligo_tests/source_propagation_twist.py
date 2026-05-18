"""Source/Propagation SSZ Twist Branch.

Theory doc: docs/SOURCE_PROPAGATION_TWIST_BRANCH.md
Branch:     SOURCE_PROPAGATION_TWIST_BRANCH
Status:     DERIVED_V0_CONCEPTUAL

Forward model:
  [h+^SSZ]   =  S(f) * R(theta(f)) * [h+^GR]
  [hx^SSZ]                             [hx^GR]

  R(theta) = [[cos theta, -sin theta],
              [sin theta,  cos theta]]

  h_det = F+ * h+^SSZ + Fx * hx^SSZ

LOCAL_ARM_TWIST_STATUS: CLOSED_NEGLIGIBLE
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import numpy as np
from ssz_ligo_tests.ssz_core import get_xi

C_LIGHT = 2.998e8
G_NEWTON = 6.674e-11
M_SUN = 1.989e30

SOURCE_PROPAGATION_TWIST_STATUS = "DERIVED_V0_CONCEPTUAL"
LOCAL_ARM_TWIST_STATUS = "CLOSED_NEGLIGIBLE"


# ---------------------------------------------------------------------------
# 1. Theta parametrisations
# ---------------------------------------------------------------------------

def theta_constant(freqs, theta0):
    """Constant (frequency-independent) polarisation twist proxy.

    Simplest sensitivity model: theta = const for all f.
    No physics claim — for exploratory scan only.

    Parameters
    ----------
    freqs : array_like
        Frequency array [Hz]
    theta0 : float
        Constant twist angle [rad]

    Returns
    -------
    theta : ndarray, same shape as freqs
    status : str
    """
    freqs = np.asarray(freqs, dtype=float)
    theta = np.full_like(freqs, float(theta0))
    return theta, "THETA_CONSTANT_PROXY"


def theta_xi_proxy(freqs, M_kg, rs_m, alpha=1.0):
    """Xi-proxy theta(f): twist proportional to Xi at emission radius.

    Uses Kepler relation to map frequency to emission radius:
      r(f) = (G M_tot / (pi^2 f^2))^{1/3}   [Kepler 3rd law]
      theta(f) = alpha * Xi(r(f), rs_m)

    Xi uses weak-field formula Xi = rs/(2r) when r >> rs,
    strong-field formula Xi = 1 - exp(-phi*r/rs) when r < 3rs.

    No physics claim — proxy for sensitivity testing.

    Parameters
    ----------
    freqs : array_like
        Frequency array [Hz]
    M_kg : float
        Total binary mass [kg]
    rs_m : float
        Schwarzschild radius [m] = 2GM/c^2
    alpha : float
        Dimensionless coupling constant (default 1.0)

    Returns
    -------
    theta : ndarray
        Twist angle [rad] at each frequency
    r_arr : ndarray
        Emission radius [m] at each frequency
    xi_arr : ndarray
        Xi value at each radius
    status : str
    """
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, 1.0)
    r_arr = (G_NEWTON * M_kg / (np.pi**2 * safe_f**2))**(1.0 / 3.0)
    xi_arr = np.array([get_xi(float(r), rs_m) for r in r_arr])
    theta = alpha * xi_arr
    return theta, r_arr, xi_arr, "THETA_XI_PROXY"


def theta_rsg_proxy(freqs, M_kg, rs_m, alpha=1.0):
    """RSG-proxy theta(f): twist at ISCO-like characteristic radius.

    Uses a fixed characteristic radius r_char = 3 rs (ISCO for
    Schwarzschild) as reference, scaled by frequency via a
    smooth tapering function that approaches Xi(r_char) at merger
    and falls off at low frequency (large r).

    theta(f) = alpha * Xi(r_char) * tanh(f / f_char)
    f_char   = (1/pi) * sqrt(G M / r_char^3)   [Kepler at r_char]

    No physics claim — proxy for sensitivity testing.

    Parameters
    ----------
    freqs : array_like
        Frequency array [Hz]
    M_kg : float
        Total binary mass [kg]
    rs_m : float
        Schwarzschild radius [m]
    alpha : float
        Dimensionless coupling constant (default 1.0)

    Returns
    -------
    theta : ndarray
    xi_char : float
    f_char : float
    status : str
    """
    freqs = np.asarray(freqs, dtype=float)
    r_char = 3.0 * rs_m
    xi_char = float(get_xi(r_char, rs_m))
    f_char = (1.0 / np.pi) * np.sqrt(G_NEWTON * M_kg / r_char**3)
    theta = alpha * xi_char * np.tanh(freqs / f_char)
    return theta, xi_char, f_char, "THETA_RSG_PROXY"


# ---------------------------------------------------------------------------
# 2. Polarisation rotation (SO(2))
# ---------------------------------------------------------------------------

def rotate_polarizations(hp, hx, theta):
    """Apply SO(2) rotation R(theta) to (h+, hx) polarisation pair.

    [h+^rot]   =  [[cos theta, -sin theta]] [h+]
    [hx^rot]      [[sin theta,  cos theta]] [hx]

    Properties:
    - Identity at theta=0
    - Power conserving: h+^2 + hx^2 unchanged
    - Invertible: R(-theta) = R^{-1}(theta)

    Parameters
    ----------
    hp, hx : ndarray
        Plus and cross polarisation amplitudes (may be complex)
    theta : float or ndarray
        Rotation angle(s) [rad]. If array, must broadcast with hp/hx.

    Returns
    -------
    hp_rot, hx_rot : ndarray
        Rotated polarisations
    """
    hp = np.asarray(hp)
    hx = np.asarray(hx)
    theta = np.asarray(theta, dtype=float)
    c = np.cos(theta)
    s = np.sin(theta)
    hp_rot = c * hp - s * hx
    hx_rot = s * hp + c * hx
    return hp_rot, hx_rot


# ---------------------------------------------------------------------------
# 3. Full source-frame SSZ forward model
# ---------------------------------------------------------------------------

def apply_source_scale_twist(hp, hx, scale, theta):
    """Apply SSZ source-frame scale + polarisation twist.

    [h+^SSZ]   =  scale * R(theta) * [h+^GR]
    [hx^SSZ]                          [hx^GR]

    LOCAL_ARM_TWIST: NOT applied (CLOSED_NEGLIGIBLE).
    This function operates on source-frame polarisations only.

    Parameters
    ----------
    hp, hx : ndarray
        GR polarisation amplitudes (time or frequency domain)
    scale : float or ndarray
        SSZ amplitude scale factor S(f). Real positive.
    theta : float or ndarray
        SSZ polarisation twist angle [rad].

    Returns
    -------
    hp_ssz, hx_ssz : ndarray
        SSZ-modified polarisations
    """
    hp_rot, hx_rot = rotate_polarizations(hp, hx, theta)
    hp_ssz = scale * hp_rot
    hx_ssz = scale * hx_rot
    return hp_ssz, hx_ssz


# ---------------------------------------------------------------------------
# 4. Detector projection
# ---------------------------------------------------------------------------

def detector_projection(hp, hx, F_plus, F_cross):
    """Project (h+, hx) onto detector via antenna patterns.

    h_det = F+ * h+ + Fx * hx

    Parameters
    ----------
    hp, hx : ndarray
        Polarisation amplitudes (GR or SSZ-modified)
    F_plus, F_cross : float
        Detector antenna pattern functions

    Returns
    -------
    h_det : ndarray
        Detector strain
    """
    return float(F_plus) * np.asarray(hp) + float(F_cross) * np.asarray(hx)


# ---------------------------------------------------------------------------
# 5. Synthetic comparison: GR vs scale-only vs scale+twist
# ---------------------------------------------------------------------------

def compare_scale_only_vs_scale_twist(
    hp_gr, hx_gr, scale, theta_arr,
    F_plus_h1, F_cross_h1, F_plus_l1, F_cross_l1,
    psd_h1=None, psd_l1=None, freqs=None
):
    """Synthetic scan comparing GR, scale-only, and scale+twist models.

    For each theta in theta_arr, computes:
    - Detector strains for H1 and L1
    - Power residuals relative to GR
    - H1/L1 response ratio
    - Optional noise-weighted inner product (if PSDs provided)

    Parameters
    ----------
    hp_gr, hx_gr : ndarray
        GR polarisation amplitudes (frequency domain, complex)
    scale : float or ndarray
        SSZ amplitude scale S(f)
    theta_arr : array_like
        Twist angles to scan [rad]
    F_plus_h1, F_cross_h1 : float
        H1 antenna patterns
    F_plus_l1, F_cross_l1 : float
        L1 antenna patterns
    psd_h1, psd_l1 : ndarray or None
        One-sided PSD arrays (same length as hp_gr) for lnL
    freqs : ndarray or None
        Frequency array [Hz] for noise-weighted inner product

    Returns
    -------
    results : list of dict
        One dict per theta value with all comparison metrics
    """
    hp_gr = np.asarray(hp_gr, dtype=complex)
    hx_gr = np.asarray(hx_gr, dtype=complex)
    theta_arr = np.asarray(theta_arr, dtype=float)

    # GR reference projections
    h_gr_h1 = detector_projection(hp_gr, hx_gr, F_plus_h1, F_cross_h1)
    h_gr_l1 = detector_projection(hp_gr, hx_gr, F_plus_l1, F_cross_l1)

    rms_gr_h1 = float(np.sqrt(np.mean(np.abs(h_gr_h1)**2)))
    rms_gr_l1 = float(np.sqrt(np.mean(np.abs(h_gr_l1)**2)))

    # Scale-only reference (theta=0)
    hp_sc, hx_sc = apply_source_scale_twist(hp_gr, hx_gr, scale, 0.0)
    h_sc_h1 = detector_projection(hp_sc, hx_sc, F_plus_h1, F_cross_h1)
    h_sc_l1 = detector_projection(hp_sc, hx_sc, F_plus_l1, F_cross_l1)
    rms_sc_h1 = float(np.sqrt(np.mean(np.abs(h_sc_h1)**2)))
    rms_sc_l1 = float(np.sqrt(np.mean(np.abs(h_sc_l1)**2)))

    results = []
    for theta in theta_arr:
        hp_tw, hx_tw = apply_source_scale_twist(hp_gr, hx_gr, scale, theta)
        h_tw_h1 = detector_projection(hp_tw, hx_tw, F_plus_h1, F_cross_h1)
        h_tw_l1 = detector_projection(hp_tw, hx_tw, F_plus_l1, F_cross_l1)

        rms_tw_h1 = float(np.sqrt(np.mean(np.abs(h_tw_h1)**2)))
        rms_tw_l1 = float(np.sqrt(np.mean(np.abs(h_tw_l1)**2)))

        # Power residuals vs scale-only
        resid_h1 = float(np.sqrt(np.mean(np.abs(h_tw_h1 - h_sc_h1)**2)))
        resid_l1 = float(np.sqrt(np.mean(np.abs(h_tw_l1 - h_sc_l1)**2)))

        # H1/L1 amplitude ratio under twist vs GR
        ratio_tw = rms_tw_h1 / rms_tw_l1 if rms_tw_l1 > 0 else float("nan")
        ratio_gr = rms_gr_h1 / rms_gr_l1 if rms_gr_l1 > 0 else float("nan")
        ratio_sc = rms_sc_h1 / rms_sc_l1 if rms_sc_l1 > 0 else float("nan")

        # Noise-weighted lnL (synthetic, if PSDs provided)
        lnl_gr_h1 = lnl_gr_l1 = None
        lnl_tw_h1 = lnl_tw_l1 = None
        dlnl_h1 = dlnl_l1 = None

        if psd_h1 is not None and freqs is not None:
            df = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 1.0
            lnl_gr_h1 = _lnl_synthetic(h_gr_h1, h_gr_h1, psd_h1, df)
            lnl_tw_h1 = _lnl_synthetic(h_tw_h1, h_gr_h1, psd_h1, df)
            dlnl_h1 = lnl_tw_h1 - lnl_gr_h1

        if psd_l1 is not None and freqs is not None:
            df = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 1.0
            lnl_gr_l1 = _lnl_synthetic(h_gr_l1, h_gr_l1, psd_l1, df)
            lnl_tw_l1 = _lnl_synthetic(h_tw_l1, h_gr_l1, psd_l1, df)
            dlnl_l1 = lnl_tw_l1 - lnl_gr_l1

        results.append({
            "theta_rad": float(theta),
            "rms_gr_h1": rms_gr_h1,
            "rms_gr_l1": rms_gr_l1,
            "rms_sc_h1": rms_sc_h1,
            "rms_sc_l1": rms_sc_l1,
            "rms_tw_h1": rms_tw_h1,
            "rms_tw_l1": rms_tw_l1,
            "resid_vs_scale_h1": resid_h1,
            "resid_vs_scale_l1": resid_l1,
            "h1_l1_ratio_gr": ratio_gr,
            "h1_l1_ratio_sc": ratio_sc,
            "h1_l1_ratio_tw": ratio_tw,
            "h1_l1_ratio_shift": ratio_tw - ratio_gr if not (
                np.isnan(ratio_tw) or np.isnan(ratio_gr)) else float("nan"),
            "lnl_gr_h1": lnl_gr_h1,
            "lnl_tw_h1": lnl_tw_h1,
            "delta_lnl_h1": dlnl_h1,
            "lnl_gr_l1": lnl_gr_l1,
            "lnl_tw_l1": lnl_tw_l1,
            "delta_lnl_l1": dlnl_l1,
            "status": SOURCE_PROPAGATION_TWIST_STATUS,
        })
    return results


def _lnl_synthetic(h_model, h_true, psd, df):
    """Synthetic noise-weighted log-likelihood (signal injection model).

    lnL = -0.5 * <h_model - h_true | h_model - h_true>
    where <a|b> = 4 Re sum(a* b / psd) df

    Used for synthetic signal-in-signal tests only.
    Not applied to real LIGO noise.
    """
    diff = h_model - h_true
    safe_psd = np.where(psd > 0, psd, np.min(psd[psd > 0]))
    return -0.5 * 4.0 * float(np.real(np.sum(diff * np.conj(diff) / safe_psd))) * df


# ---------------------------------------------------------------------------
# 6. Synthetic PSD helper
# ---------------------------------------------------------------------------

def synthetic_asd_ligo(freqs, f_knee=30.0, asd_floor=3e-24):
    """Simple synthetic LIGO-like ASD for tests.

    ASD(f) = asd_floor * (f_knee/f)^2 + asd_floor   for f > 0

    Not a real LIGO sensitivity curve. For synthetic tests only.
    """
    freqs = np.asarray(freqs, dtype=float)
    safe_f = np.where(freqs > 0, freqs, f_knee)
    asd = asd_floor * (1.0 + (f_knee / safe_f)**2)
    return asd**2   # return PSD = ASD^2
