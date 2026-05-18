"""SSZ-LIGO Equation Registry.

Tracks all SSZ equations and their status for LIGO forward model.
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class EquationStatus(Enum):
    LOCKED = "LOCKED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    EXPLORATORY_ONLY = "EXPLORATORY_ONLY"
    INVALID_FOR_LIGO = "INVALID_FOR_LIGO"


@dataclass
class Equation:
    name: str
    formula: str
    variables: List[str]
    units: str
    source_path: str
    source_excerpt: str
    status: EquationStatus
    usable_in_test: bool
    anti_circularity_risk: str


# LOCKED CORE EQUATIONS - From SSZ_BOOK_DE_CLEAN.md
LOCKED_CORE_EQUATIONS = [
    Equation(
        name="PHI",
        formula="(1 + sqrt(5)) / 2",
        variables=[],
        units="dimensionless",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.1",
        source_excerpt="φ = (1+√5)/2 = 1.618... (Goldener Schnitt)",
        status=EquationStatus.LOCKED,
        usable_in_test=True,
        anti_circularity_risk="none - fundamental constant"
    ),
    Equation(
        name="XI_MAX",
        formula="1 - exp(-PHI)",
        variables=["PHI"],
        units="dimensionless",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.1",
        source_excerpt="Ξ_max = 1 - exp(-φ) ≈ 0.802",
        status=EquationStatus.LOCKED,
        usable_in_test=True,
        anti_circularity_risk="none - derived from φ"
    ),
    Equation(
        name="D_MIN",
        formula="1 / (1 + XI_MAX)",
        variables=["XI_MAX"],
        units="dimensionless",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.1",
        source_excerpt="D_min = 0.555",
        status=EquationStatus.LOCKED,
        usable_in_test=True,
        anti_circularity_risk="none - derived from Ξ_max"
    ),
    Equation(
        name="XI_WEAK",
        formula="r_s / (2 * r)",
        variables=["r_s", "r"],
        units="dimensionless",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.1",
        source_excerpt="Ξ_weak(r) = r_s/(2r)",
        status=EquationStatus.LOCKED,
        usable_in_test=True,
        anti_circularity_risk="low - weak field regime"
    ),
    Equation(
        name="XI_STRONG",
        formula="min(1 - exp(-PHI * r / r_s), XI_MAX)",
        variables=["PHI", "r", "r_s", "XI_MAX"],
        units="dimensionless",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.1",
        source_excerpt="Ξ_strong(r) = min(1 - exp(-φr/r_s), Ξ_max)",
        status=EquationStatus.LOCKED,
        usable_in_test=True,
        anti_circularity_risk="low - strong field regime"
    ),
    Equation(
        name="D_SSZ",
        formula="1 / (1 + XI)",
        variables=["XI"],
        units="dimensionless",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.1",
        source_excerpt="D(r) = 1/(1 + Ξ(r))",
        status=EquationStatus.LOCKED,
        usable_in_test=True,
        anti_circularity_risk="none - core definition"
    ),
    Equation(
        name="SCHWARZSCHILD_RADIUS",
        formula="2 * G * M / c^2",
        variables=["G", "M", "c"],
        units="meters",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.1",
        source_excerpt="r_s = 2GM/c²",
        status=EquationStatus.LOCKED,
        usable_in_test=True,
        anti_circularity_risk="none - standard physics"
    ),
]

# MISSING FORWARD MODEL EQUATIONS
MISSING_FORWARD_EQUATIONS = [
    Equation(
        name="DELTA_PSI_SSZ",
        formula="NOT_IN_CORPUS",
        variables=["f", "M", "r_s"],
        units="radians",
        source_path="NOT_FOUND",
        source_excerpt="Phase correction formula not found in SSZ corpus",
        status=EquationStatus.MISSING,
        usable_in_test=False,
        anti_circularity_risk="high - cannot construct h_SSZ(f) without this"
    ),
    Equation(
        name="DELTA_A_SSZ",
        formula="NOT_IN_CORPUS",
        variables=["f", "M", "r_s"],
        units="dimensionless",
        source_path="NOT_FOUND",
        source_excerpt="Amplitude correction formula not found in SSZ corpus",
        status=EquationStatus.MISSING,
        usable_in_test=False,
        anti_circularity_risk="high - cannot construct h_SSZ(f) without this"
    ),
    Equation(
        name="EPSILON_220",
        formula="AMBIGUOUS",
        variables=["D_min"],
        units="dimensionless",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.30",
        source_excerpt="Book says 'ca. 3%' but also D_min² ≈ 31%",
        status=EquationStatus.EXPLORATORY_ONLY,
        usable_in_test=False,
        anti_circularity_risk="high - internal inconsistency in corpus"
    ),
    Equation(
        name="ETA_220",
        formula="NOT_IN_CORPUS",
        variables=["D_min"],
        units="dimensionless",
        source_path="NOT_FOUND",
        source_excerpt="Damping shift formula not found",
        status=EquationStatus.MISSING,
        usable_in_test=False,
        anti_circularity_risk="high - cannot predict tau_SSZ without this"
    ),
    Equation(
        name="H_SSZ_WAVEFORM",
        formula="NOT_IN_CORPUS",
        variables=["t", "M", "r_s", "parameters"],
        units="strain",
        source_path="ssz-complete-documentation/08_FALSIFICATION/known_limitations.md",
        source_excerpt="'complete GW waveform calculation in SSZ is not yet available'",
        status=EquationStatus.MISSING,
        usable_in_test=False,
        anti_circularity_risk="high - core requirement for LIGO test"
    ),
    Equation(
        name="GW_PROPAGATION_SSZ",
        formula="NOT_IN_CORPUS",
        variables=["h_mu_nu", "g_SSZ"],
        units="various",
        source_path="NOT_FOUND",
        source_excerpt="SSZ wave equation in SSZ background not found",
        status=EquationStatus.MISSING,
        usable_in_test=False,
        anti_circularity_risk="high - needed for propagation effects"
    ),
]

# EXPLORATORY / HEURISTIC
EXPLORATORY_EQUATIONS = [
    Equation(
        name="RINGDOWN_SHIFT_HEURISTIC",
        formula="f_SSZ = f_GR * (1 + epsilon)",
        variables=["f_GR", "epsilon"],
        units="Hz",
        source_path="SSZ_BOOK_DE_CLEAN.md Ch.30",
        source_excerpt="QNM frequency shift mentioned but not derived",
        status=EquationStatus.EXPLORATORY_ONLY,
        usable_in_test=False,
        anti_circularity_risk="medium - heuristic only"
    ),
]


def get_all_equations() -> List[Equation]:
    """Get all registered equations."""
    return LOCKED_CORE_EQUATIONS + MISSING_FORWARD_EQUATIONS + EXPLORATORY_EQUATIONS


def get_locked_equations() -> List[Equation]:
    """Get only locked equations."""
    return [eq for eq in get_all_equations() 
            if eq.status == EquationStatus.LOCKED]


def get_missing_equations() -> List[Equation]:
    """Get only missing equations."""
    return [eq for eq in get_all_equations() 
            if eq.status == EquationStatus.MISSING]


def check_ready_for_numerical_test() -> tuple:
    """Check if ready for numerical LIGO test."""
    missing = get_missing_equations()
    exploratory = [eq for eq in get_all_equations() 
                   if eq.status == EquationStatus.EXPLORATORY_ONLY]
    
    if missing:
        return False, f"MISSING_EQUATIONS: {[eq.name for eq in missing]}"
    
    if exploratory:
        return False, f"EXPLORATORY_ONLY: {[eq.name for eq in exploratory]}"
    
    return True, "ALL_EQUATIONS_LOCKED"


def generate_registry_report() -> str:
    """Generate markdown report of equation registry."""
    lines = ["# SSZ Equation Registry\n\n"]
    
    lines.append("## LOCKED CORE EQUATIONS\n\n")
    for eq in LOCKED_CORE_EQUATIONS:
        lines.append(f"### {eq.name}\n")
        lines.append(f"- **Formula:** `{eq.formula}`\n")
        lines.append(f"- **Source:** {eq.source_path}\n")
        lines.append(f"- **Status:** {eq.status.value}\n")
        lines.append(f"- **Usable:** {eq.usable_in_test}\n\n")
    
    lines.append("## MISSING FORWARD MODEL EQUATIONS\n\n")
    for eq in MISSING_FORWARD_EQUATIONS:
        lines.append(f"### {eq.name}\n")
        lines.append(f"- **Formula:** {eq.formula}\n")
        lines.append(f"- **Source:** {eq.source_path}\n")
        lines.append(f"- **Excerpt:** {eq.source_excerpt}\n")
        lines.append(f"- **Status:** {eq.status.value}\n")
        lines.append(f"- **Risk:** {eq.anti_circularity_risk}\n\n")
    
    lines.append("## EXPLORATORY EQUATIONS\n\n")
    for eq in EXPLORATORY_EQUATIONS:
        lines.append(f"### {eq.name}\n")
        lines.append(f"- **Formula:** {eq.formula}\n")
        lines.append(f"- **Status:** {eq.status.value}\n\n")
    
    # Readiness check
    ready, reason = check_ready_for_numerical_test()
    lines.append("\n## READINESS CHECK\n\n")
    lines.append(f"**Ready for numerical test:** {ready}\n")
    lines.append(f"**Reason:** {reason}\n")
    
    return "".join(lines)


if __name__ == "__main__":
    report = generate_registry_report()
    print(report)
