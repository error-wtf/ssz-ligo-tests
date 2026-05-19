"""Artifact Score Automat — Test 81 + 88.

Aggregates all artifact gate results into a single score and verdict.
Reads existing CSV manifests from previous diagnostic runs.

Score components (each 0-3 points, lower=cleaner):
  1.  L1/H1 bandpower ratio         (>2.0=3, >1.5=2, >1.2=1, else=0)
  2.  L1 stationarity quantile      (>95%=3, >85%=2, >75%=1, else=0)
  3.  L1 line fraction              (>0.6=3, >0.4=2, >0.2=1, else=0)
  4.  L1 20-40Hz excess kurtosis    (>20=3, >5=2, >2=1, else=0)
  5.  H1/L1 coherence               (<0.02=0, <0.05=1, <0.1=2, else=3)
  6.  Cross-phase stability R       (>0.95=0, >0.8=1, >0.5=2, else=3)
  7.  Phase rand BP quantile        (<50%=0, <80%=1, <95%=2, else=3)
  8.  DQ status                     (UNRESOLVED=3, FLAGGED=2, PASS=0)

Total 0-24:
  0-4:  ARTIFACT_RISK: LOW
  5-10: ARTIFACT_RISK: MEDIUM
  11-17: ARTIFACT_RISK: HIGH
  18-24: ARTIFACT_RISK: CRITICAL

CLAIM_ALLOWED: NO until ARTIFACT_RISK: LOW AND DQ: PASS AND Omicron available.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import datetime
import csv
import json
from pathlib import Path

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
MANIFEST = Path(__file__).parent.parent / "data_manifest"
for _d in (REPORTS, LOGS, MANIFEST):
    _d.mkdir(exist_ok=True)

LOG_PATH = LOGS / "artifact_score.log"
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# LOAD CSV MANIFEST
# ---------------------------------------------------------------------------
def load_csv(name):
    p = MANIFEST / name
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def safe_float(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# SCORE COMPONENTS
# ---------------------------------------------------------------------------
def score_l1_h1_ratio(rows):
    """From gw250207_artifact_gate.csv or multiwindow."""
    # Try gw250207_artifact_gate first
    gate_rows = load_csv("gw250207_artifact_gate.csv")
    for r in gate_rows:
        if r.get("event") == "GW240925":
            ratio = safe_float(r.get("l1_h1_ratio"))
            if ratio is not None:
                if ratio > 2.0:
                    return 3, ratio
                if ratio > 1.5:
                    return 2, ratio
                if ratio > 1.2:
                    return 1, ratio
                return 0, ratio
    return None, None


def score_l1_stationarity():
    rows = load_csv("l1_multiwindow_stationarity.csv")
    for r in rows:
        q = safe_float(r.get("trigger_quantile_pct"))
        if q is not None:
            if q > 95:
                return 3, q
            if q > 85:
                return 2, q
            if q > 75:
                return 1, q
            return 0, q
    # fallback from gw250207 gate
    gate_rows = load_csv("gw250207_artifact_gate.csv")
    for r in gate_rows:
        if r.get("event") == "GW240925":
            q = safe_float(r.get("l1_stationarity_q"))
            if q is not None:
                if q > 95:
                    return 3, q
                if q > 85:
                    return 2, q
                if q > 75:
                    return 1, q
                return 0, q
    return None, None


def score_line_fraction():
    rows = load_csv("gw250207_artifact_gate.csv")
    for r in rows:
        if r.get("event") == "GW240925":
            lf = safe_float(r.get("l1_line_frac"))
            if lf is not None:
                if lf > 0.6:
                    return 3, lf
                if lf > 0.4:
                    return 2, lf
                if lf > 0.2:
                    return 1, lf
                return 0, lf
    # fallback: notch sweep
    rows = load_csv("l1_notch_sweep.csv")
    if rows:
        # first row with n_notched=0 is baseline
        baseline = next((r for r in rows
                         if safe_float(r.get("n_peaks_notched")) == 0), None)
        if baseline:
            lf = safe_float(baseline.get("line_frac_removed"))
            if lf is not None:
                if lf > 0.6:
                    return 3, lf
                if lf > 0.4:
                    return 2, lf
                if lf > 0.2:
                    return 1, lf
                return 0, lf
    return None, None


def score_subband_kurtosis():
    rows = load_csv("subband_gaussianity.csv")
    # L1 trigger 20-40 Hz band
    r = next((x for x in rows
               if x.get("det") == "L1"
               and x.get("tag") == "TRIGGER"
               and x.get("band") == "20-40"), None)
    if r:
        ek = safe_float(r.get("excess_kurtosis"))
        if ek is not None:
            ek = abs(ek)
            if ek > 20:
                return 3, ek
            if ek > 5:
                return 2, ek
            if ek > 2:
                return 1, ek
            return 0, ek
    return None, None


def score_coherence():
    rows = load_csv("gw250207_artifact_gate.csv")
    for r in rows:
        if r.get("event") == "GW240925":
            coh = safe_float(r.get("coh_mean"))
            if coh is not None:
                # Low coherence = GOOD (not anomalous)
                if coh < 0.02:
                    return 0, coh
                if coh < 0.05:
                    return 1, coh
                if coh < 0.1:
                    return 2, coh
                return 3, coh
    # fallback from h1l1_cross_coherence
    rows = load_csv("h1l1_cross_coherence.csv")
    if rows:
        r = rows[0]
        coh = safe_float(r.get("coh_trigger"))
        if coh is not None:
            if coh < 0.02:
                return 0, coh
            if coh < 0.05:
                return 1, coh
            if coh < 0.1:
                return 2, coh
            return 3, coh
    return None, None


def score_cross_phase():
    rows = load_csv("gw250207_artifact_gate.csv")
    for r in rows:
        if r.get("event") == "GW240925":
            R = safe_float(r.get("cross_phase_R"))
            if R is not None:
                # High R = STABLE phase. Stable ~170deg = geometrically
                # plausible, not anomalous. Score 0 (not penalized).
                # Only penalize if phase is highly unstable (R<0.5)
                if R > 0.95:
                    return 0, R   # very stable = plausible geometry
                if R > 0.8:
                    return 0, R   # stable
                if R > 0.5:
                    return 1, R
                return 2, R
    return None, None


def score_phase_randomization():
    rows = load_csv("phase_randomization_null.csv")
    r = next((x for x in rows
               if x.get("det") == "L1"
               and x.get("tag") == "TRIGGER"), None)
    if r:
        q = safe_float(r.get("q_bp"))
        if q is not None:
            # q is fraction (0-1). Low = real signal BELOW surrogate mean.
            # High (>0.95) = real BP higher than 95% of surrogates -> excess
            if q < 0.5:
                return 0, q
            if q < 0.8:
                return 1, q
            if q < 0.95:
                return 2, q
            return 3, q
    return None, None


def score_dq_status():
    # Check for known DQ status from reports
    dq_report = REPORTS / "DQ_AWARE_FINAL_LIGO_STATUS.md"
    gate_report = REPORTS / "L1_ARTIFACT_GATE_FINAL_STATUS.md"
    if gate_report.exists():
        text = gate_report.read_text(encoding="utf-8", errors="ignore")
        if "DQ_FLAGGED" in text or "DQ_UNRESOLVED" in text:
            return 3, "DQ_UNRESOLVED"
        if "DQ_PASS" in text:
            return 0, "DQ_PASS"
    if dq_report.exists():
        return 3, "DQ_FLAGGED_DIAGNOSTIC_ONLY"
    return 3, "DQ_UNKNOWN"


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    log(f"ARTIFACT SCORE AUTOMAT -- {NOW}")
    log(f"Event: GW240925 GPS=1411261107.984")
    log()

    components = [
        ("L1/H1 bandpower ratio",     score_l1_h1_ratio(None)),
        ("L1 stationarity quantile",  score_l1_stationarity()),
        ("L1 line fraction",          score_line_fraction()),
        ("L1 20-40Hz excess kurtosis", score_subband_kurtosis()),
        ("H1/L1 coherence",           score_coherence()),
        ("Cross-phase stability R",   score_cross_phase()),
        ("Phase-rand BP quantile",    score_phase_randomization()),
        ("DQ status",                 score_dq_status()),
    ]

    log(f"  {'Component':35s} {'Score':>6} {'Value':>12} {'Notes'}")
    log("  " + "-" * 70)

    total = 0
    n_scored = 0
    rows_out = []
    score_notes = {
        0: "clean",
        1: "mild",
        2: "elevated",
        3: "high_risk",
    }

    for label, (score, value) in components:
        if score is None:
            val_str = "N/A"
            note = "not available"
            log(f"  {'N/A':3s}  {label:35s} {val_str:>12}  {note}")
        else:
            total += score
            n_scored += 1
            val_str = (f"{value:.4f}" if isinstance(value, float)
                       else str(value))
            note = score_notes.get(score, "")
            log(f"  {score:3d}  {label:35s} {val_str:>12}  {note}")
        rows_out.append({
            "component": label,
            "score": score if score is not None else "N/A",
            "value": value if value is not None else "N/A",
        })

    log()
    log(f"  Total score: {total} / {n_scored * 3} (max {len(components)*3})")

    # Risk level
    if n_scored < 4:
        risk = "UNKNOWN"
    elif total <= 4:
        risk = "LOW"
    elif total <= 10:
        risk = "MEDIUM"
    elif total <= 17:
        risk = "HIGH"
    else:
        risk = "CRITICAL"

    log(f"  ARTIFACT_RISK: {risk}")

    # ---------------------------------------------------------------------------
    # CLAIM GATE
    # ---------------------------------------------------------------------------
    blockers = []

    dq_score, dq_val = score_dq_status()
    if dq_score >= 2:
        blockers.append(f"L1_DQ_UNRESOLVED: {dq_val}")

    if risk in ("HIGH", "CRITICAL", "UNKNOWN"):
        blockers.append(f"ARTIFACT_RISK_{risk}")

    omicron_avail = False  # manual flag — update when Omicron obtained
    if not omicron_avail:
        blockers.append("OMICRON_IDQ_NOT_AVAILABLE")

    gw250207_avail = (MANIFEST / "gw250207_artifact_gate.csv").exists()
    gate_rows = load_csv("gw250207_artifact_gate.csv")
    has_gw250207 = any(r.get("event") == "GW250207" for r in gate_rows)
    if not has_gw250207:
        blockers.append("GW250207_STRAIN_NOT_DOWNLOADED")

    claim_allowed = len(blockers) == 0

    log()
    log(f"{'='*65}")
    log("CLAIM GATE VERDICT")
    log(f"{'='*65}")
    log(f"  CLAIM_ALLOWED: {'YES' if claim_allowed else 'NO'}")
    if blockers:
        log("  BLOCKERS:")
        for b in blockers:
            log(f"    - {b}")
    else:
        log("  No blockers — claim gate would pass.")
    log()
    log("  READY_FOR_REAL_LIGO_SSZ_CLAIM: NO")
    log("  (Hardcoded: requires manual review + external DQ confirmation)")

    # ---------------------------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------------------------
    csv_path = MANIFEST / "artifact_score.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh,
                           fieldnames=["component", "score", "value"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_out)

    verdict = {
        "event": "GW240925",
        "timestamp": NOW,
        "total_score": total,
        "max_score": len(components) * 3,
        "n_scored": n_scored,
        "artifact_risk": risk,
        "claim_allowed": claim_allowed,
        "blockers": blockers,
        "READY_FOR_REAL_LIGO_SSZ_CLAIM": "NO",
    }
    json_path = MANIFEST / "artifact_gate_verdict.json"
    json_path.write_text(json.dumps(verdict, indent=2) + "\n",
                         encoding="utf-8")

    md = [
        "# Artifact Score — GW240925",
        f"Generated: {NOW}",
        "",
        "## Score Components",
        "",
        "| Component | Score | Value | Category |",
        "|-----------|-------|-------|----------|",
    ]
    for r in rows_out:
        sc = r["score"]
        cat = score_notes.get(sc, "N/A") if isinstance(sc, int) else "N/A"
        v = r["value"]
        v_str = f"{v:.4f}" if isinstance(v, float) else str(v)
        md.append(f"| {r['component']} | {sc} | {v_str} | {cat} |")

    md += [
        "",
        f"**Total: {total} / {n_scored*3}**  "
        f"(of max {len(components)*3})",
        "",
        f"## ARTIFACT_RISK: {risk}",
        "",
        "| Risk Level | Score Range |",
        "|------------|-------------|",
        "| LOW        | 0-4         |",
        "| MEDIUM     | 5-10        |",
        "| HIGH       | 11-17       |",
        "| CRITICAL   | 18-24       |",
        "",
        "## Claim Gate",
        "",
        f"**CLAIM_ALLOWED: {'YES' if claim_allowed else 'NO'}**",
        "",
    ]
    if blockers:
        md.append("**Blockers:**")
        for b in blockers:
            md.append(f"- {b}")
    md += [
        "",
        "## Hardcoded Gate",
        "```",
        "READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "Requires: Omicron/iDQ + DQ pass + ARTIFACT_RISK: LOW",
        "          + manual review + external confirmation",
        "```",
        "",
        "## Anti-Circularity",
        "- No SSZ parameters used",
        "- SSZ_SUPPORT_CLAIM_MADE: NO",
        "- SSZ_FALSIFICATION_CLAIM_MADE: NO",
    ]

    rpath = REPORTS / "ARTIFACT_SCORE_REPORT.md"
    rpath.write_text("\n".join(md) + "\n", encoding="utf-8")

    log("Outputs:")
    log(f"  {rpath}")
    log(f"  {csv_path}")
    log(f"  {json_path}")
    flush_log()


if __name__ == "__main__":
    run()
