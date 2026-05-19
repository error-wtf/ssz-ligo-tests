"""Run All Artifact Gate Scripts — Reproducibility Entry Point.

Executes the full L1 artifact gate pipeline in order:

  1.  run_unit_normalization_audit        -- FFT/PSD unit checks
  2.  run_l1_line_notch_test             -- Line detection + notching
  3.  run_l1_stft_omicron_lite           -- STFT time-frequency analysis
  4.  run_l1_multiwindow_stationarity    -- Bandpower quantile +-1000s
  5.  run_h1l1_cross_coherence           -- H1/L1 coherence + phase
  6.  run_h1l1_time_delay_scan           -- Time-delay scan +-20ms
  7.  run_l1_notch_sweep                 -- Systematic peak removal
  8.  run_subband_gaussianity            -- 5-band kurtosis/gaussianity
  9.  run_phase_randomization_null       -- Phase randomization (N=200)
  10. run_gaussianity_artifact_gate      -- Full Gaussianity gate
  11. run_gw250207_artifact_gate         -- Cross-event comparison

Usage:
  python scripts/run_all_artifact_gates.py [--skip-slow] [--event-only]

Flags:
  --skip-slow   Skip time-delay scan and phase randomization (slow)
  --event-only  Skip unit audit, run event tests only

All outputs go to reports/ and data_manifest/.
A final index is written to reports/ARTIFACT_GATE_INDEX.md.

READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
"""
import sys
import time
import datetime
import traceback
from pathlib import Path

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORTS = Path(__file__).parent.parent / "reports"
LOGS = Path(__file__).parent.parent / "logs"
for _d in (REPORTS, LOGS):
    _d.mkdir(exist_ok=True)

# Parse flags
SKIP_SLOW = "--skip-slow" in sys.argv
EVENT_ONLY = "--event-only" in sys.argv

# ---------------------------------------------------------------------------
# PIPELINE DEFINITION
# ---------------------------------------------------------------------------
PIPELINE = [
    {
        "id": "01",
        "module": "run_unit_normalization_audit",
        "label": "Unit & Normalization Audit",
        "slow": False,
        "skip_if_event_only": True,
    },
    {
        "id": "02",
        "module": "run_l1_line_notch_test",
        "label": "L1 Line/Notch Test",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "03",
        "module": "run_l1_stft_omicron_lite",
        "label": "L1 STFT Omicron-Lite",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "04",
        "module": "run_l1_multiwindow_stationarity",
        "label": "L1 Multi-Window Stationarity",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "05",
        "module": "run_h1l1_cross_coherence",
        "label": "H1/L1 Cross-Coherence + Phase",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "06",
        "module": "run_h1l1_time_delay_scan",
        "label": "H1/L1 Time-Delay Scan +-20ms",
        "slow": True,
        "skip_if_event_only": False,
    },
    {
        "id": "07",
        "module": "run_l1_notch_sweep",
        "label": "L1 Notch Sweep (top peaks)",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "08",
        "module": "run_subband_gaussianity",
        "label": "Sub-band Gaussianity (5 bands)",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "09",
        "module": "run_phase_randomization_null",
        "label": "Phase Randomization Null Test",
        "slow": True,
        "skip_if_event_only": False,
    },
    {
        "id": "10",
        "module": "run_gaussianity_artifact_gate",
        "label": "Gaussianity Artifact Gate",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "11",
        "module": "run_gw250207_artifact_gate",
        "label": "GW250207 Cross-Event Comparison",
        "slow": False,
        "skip_if_event_only": False,
    },
    {
        "id": "12",
        "module": "run_artifact_score",
        "label": "Artifact Score + Claim Gate",
        "slow": False,
        "skip_if_event_only": False,
    },
]

# ---------------------------------------------------------------------------
# RUNNER
# ---------------------------------------------------------------------------


def run_step(step):
    mod_name = step["module"]
    try:
        # Import relative to scripts/ directory
        import importlib.util
        scripts_dir = Path(__file__).parent
        mod_path = scripts_dir / f"{mod_name}.py"
        if not mod_path.exists():
            return "MISSING", f"Script not found: {mod_path}"
        spec = importlib.util.spec_from_file_location(mod_name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "run"):
            mod.run()
        return "OK", ""
    except Exception:
        return "ERROR", traceback.format_exc()


def main():
    print(f"{'='*65}")
    print(f"ARTIFACT GATE PIPELINE — {NOW}")
    print(f"{'='*65}")
    if SKIP_SLOW:
        print("  --skip-slow: skipping time-delay scan + phase randomization")
    if EVENT_ONLY:
        print("  --event-only: skipping unit audit")
    print()

    summary = []

    for step in PIPELINE:
        if SKIP_SLOW and step["slow"]:
            print(f"  [{step['id']}] SKIPPED (slow)  {step['label']}")
            summary.append({**step, "status": "SKIPPED_SLOW",
                            "elapsed_s": 0.0, "error": ""})
            continue

        if EVENT_ONLY and step["skip_if_event_only"]:
            print(f"  [{step['id']}] SKIPPED (event-only)  {step['label']}")
            summary.append({**step, "status": "SKIPPED_EVENT_ONLY",
                            "elapsed_s": 0.0, "error": ""})
            continue

        print(f"  [{step['id']}] RUNNING  {step['label']} ...")
        t0 = time.time()
        status, err = run_step(step)
        elapsed = time.time() - t0

        if status == "OK":
            print(f"  [{step['id']}] OK       {step['label']} "
                  f"({elapsed:.1f}s)")
        else:
            print(f"  [{step['id']}] {status}    {step['label']} "
                  f"({elapsed:.1f}s)")
            if err:
                # Print first 3 lines of traceback only
                for line in err.strip().split("\n")[-3:]:
                    print(f"          {line}")

        summary.append({**step, "status": status,
                        "elapsed_s": round(elapsed, 1), "error": err})

    # ---------------------------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------------------------
    print()
    print(f"{'='*65}")
    print("PIPELINE COMPLETE")
    print(f"{'='*65}")
    n_ok = sum(1 for s in summary if s["status"] == "OK")
    n_err = sum(1 for s in summary if s["status"] == "ERROR")
    n_skip = sum(1 for s in summary
                 if s["status"].startswith("SKIPPED"))
    total_t = sum(s["elapsed_s"] for s in summary)
    print(f"  OK={n_ok}  ERROR={n_err}  SKIPPED={n_skip}  "
          f"Total={total_t:.1f}s")
    print()

    for s in summary:
        icon = {"OK": "OK  ", "ERROR": "ERR ",
                "MISSING": "MISS", "SKIPPED_SLOW": "SKIP",
                "SKIPPED_EVENT_ONLY": "SKIP"}.get(s["status"], "????")
        print(f"  {icon}  [{s['id']}] {s['label']}")

    # ---------------------------------------------------------------------------
    # WRITE INDEX
    # ---------------------------------------------------------------------------
    md = [
        "# Artifact Gate Pipeline Index",
        f"Generated: {NOW}",
        "",
        "## Run Summary",
        "",
        "| # | Script | Status | Time (s) |",
        "|---|--------|--------|----------|",
    ]
    for s in summary:
        md.append(
            f"| {s['id']} | {s['module']} | {s['status']} "
            f"| {s['elapsed_s']:.1f} |"
        )

    md += [
        "",
        "## Report Files",
        "",
    ]

    report_files = sorted(REPORTS.glob("*.md"))
    for rf in report_files:
        md.append(f"- [{rf.name}](../{rf.relative_to(rf.parent.parent)})")

    md += [
        "",
        "## Pipeline Status",
        f"- Scripts OK: {n_ok}",
        f"- Errors: {n_err}",
        f"- Skipped: {n_skip}",
        "",
        "## Gate Verdict",
        "- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO",
        "- BLOCKER: L1_DQ_UNRESOLVED (Omicron/iDQ not available)",
        "",
        "## Reproduce",
        "```bash",
        "python scripts/run_all_artifact_gates.py",
        "python scripts/run_all_artifact_gates.py --skip-slow",
        "python scripts/run_all_artifact_gates.py --event-only",
        "```",
    ]

    index_path = REPORTS / "ARTIFACT_GATE_INDEX.md"
    index_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\n  Index: {index_path}")


if __name__ == "__main__":
    main()
