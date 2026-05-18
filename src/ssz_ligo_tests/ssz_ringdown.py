"""SSZ ringdown - QNM predictions with CONFLICTING SOURCES marked.

WARNING: SSZ corpus contains THREE conflicting statements about QNM shift:
1. Source A: ~3% (Book Ch.30 text)
2. Source B: ~D_min² ≈ 31% (Book Ch.30 "proportional to D_min²")
3. Source C: ~39% at photon sphere (qnm_spectrum.md)

These are NOT consistent. Ringdown test is BLOCKED until resolved.
"""
import numpy as np
from typing import Optional, Literal
from .constants import D_MIN


# RINGDOWN STATUS
RINGDOWN_MODEL_STATUS = "CONFLICTING_SSZ_SOURCES"

# V51 PDF indicates ~3% for fundamental mode, below current single-event precision
# Source corpus: epsilon_220 ~ 0.03 (3%) mentioned in Ch.30
# But: exact derivation/locking missing, so marked EXPLORATORY

CONFLICTING_SOURCES = {
    "source_a_3_percent": {
        "value": 0.03,
        "origin": "SSZ_BOOK_DE_CLEAN.md Ch.30 / V51 PDF",
        "formula": "approximately 3%",
        "context": "Fundamental mode QNM shift, below single-event precision",
        "status": "EXPLORATORY_ONLY"
    },
    "source_b_31_percent": {
        "value": D_MIN ** 2,
        "origin": "Older interpretation 'proportional to D_min^2'",
        "formula": "eps ~ D_min^2 ~ 0.31",
        "context": "Possibly outdated or different physical regime",
        "status": "SUPERSEDED_OR_DIFFERENT_REGIME"
    },
    "source_c_39_percent": {
        "value": 0.39,
        "origin": "qnm_spectrum.md at photon sphere (DISCARDED)",
        "formula": "f_SSZ/f_GR ~ 1.39",
        "context": "NOT FOR LIGO - different physical scenario",
        "status": "DISCARDED_FOR_LIGO"
    }
}


def get_ringdown_conflict_report() -> str:
    """Generate report of ringdown source status.
    
    V51 PDF indicates ~3% for fundamental mode, below current precision.
    This is EXPLORATORY - needs exact derivation before numerical claims.
    """
    lines = ["# SSZ Ringdown Source Status Report\n\n"]
    lines.append(f"**Status:** {RINGDOWN_MODEL_STATUS}\n\n")
    
    lines.append("## Authoritative Source\n\n")
    v51 = CONFLICTING_SOURCES["source_a_3_percent"]
    lines.append(f"**V51 PDF / Book Ch.30:**\n")
    lines.append(f"- Value: ~{v51['value']*100:.0f}%\n")
    lines.append(f"- Context: {v51['context']}\n")
    lines.append(f"- Status: {v51['status']}\n\n")
    
    lines.append("## Important Note\n\n")
    lines.append("The ~3% shift is BELOW current single-event detector precision.\n")
    lines.append("Testable via stacking or next-gen detectors (ET/CE).\n\n")
    
    lines.append("## Discarded/Outdated Sources\n\n")
    lines.append("- 39% photon-sphere value: NOT FOR LIGO\n")
    lines.append("- 31% D_min^2 interpretation: Possibly different regime\n\n")
    lines.append("## Resolution Required\n\n")
    lines.append("Which source is authoritative? "
                 "This must be resolved before any numerical claims.\n")
    return "".join(lines)


def check_ringdown_usable() -> tuple:
    """Check if ringdown can be used for numerical test.
    
    Returns:
        (usable: bool, reason: str)
    """
    return False, (
        f"{RINGDOWN_MODEL_STATUS}: CONFLICTING sources for epsilon_220. "
        "BLOCKED until resolved. "
        "Values: ~3% (V51), ~31% (D_min^2), ~39% (photon sphere). "
        "Resolution required before numerical claims."
    )


def ringdown_damped_sinusoid(t: np.ndarray, 
                             A: float, 
                             f: float, 
                             tau: float, 
                             phi0: float = 0) -> np.ndarray:
    """Standard damped sinusoid for ringdown (model-agnostic)."""
    return A * np.exp(-t / tau) * np.cos(2 * np.pi * f * t + phi0)


def ssz_ringdown_frequency_shift(f_gr: float,
                                 epsilon_220: Optional[float] = None,
                                 source: Optional[Literal["A", "B", "C"]] = None
                                 ) -> float:
    """SSZ QNM frequency shift - PARTIAL/EXPLORATORY.

    Args:
        f_gr: GR ringdown frequency
        epsilon_220: relative shift (if explicitly provided and resolved)
        source: which source to use (A=3%, B=31%, C=39%)

    Raises:
        ValueError: if epsilon_220 not locked (None)
    """
    if epsilon_220 is not None:
        return f_gr * (1 + epsilon_220)

    conflict_msg = get_ringdown_conflict_report()
    raise ValueError(
        f"RINGDOWN BLOCKED: epsilon_220 not locked - {RINGDOWN_MODEL_STATUS}\n\n"
        f"{conflict_msg}\n\n"
        f"To use this function, you must:\n"
        f"1. Resolve which source is authoritative\n"
        f"2. Explicitly provide epsilon_220 with documented source\n"
        f"3. Or use 'source' parameter with resolved choice"
    )


def ssz_ringdown_tau_shift(tau_gr: float,
                           eta_220: Optional[float] = None) -> float:
    """SSZ QNM damping time shift.

    No formula for η_220 exists in SSZ corpus; raises unless eta_220 provided.
    """
    if eta_220 is not None:
        return tau_gr * (1 + eta_220)
    raise ValueError(
        "RINGDOWN BLOCKED: eta_220 not locked - formula not found in SSZ corpus. "
        "See SSZ_FORWARD_MODEL_EQUATION_GAPS.md: MISSING_FORWARD_EQUATION."
    )


def epsilon_220_from_corpus(source_choice: Optional[str] = None) -> float:
    """Attempt to retrieve ε_220 from SSZ corpus.
    
    This will ALWAYS fail with conflict report until sources are resolved.
    """
    raise NotImplementedError(
        f"Cannot retrieve epsilon_220: CONFLICTING_SSZ_SOURCES\n\n"
        f"Conflicting values:\n"
        f"  - Source A (Book text): ~3%\n"
        f"  - Source B (D_min²): ~31%\n"
        f"  - Source C (Photon sphere): ~39%\n\n"
        f"Resolution required from SSZ authors."
    )
