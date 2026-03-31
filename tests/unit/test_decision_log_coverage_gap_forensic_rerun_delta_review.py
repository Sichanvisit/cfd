import importlib.util
import sys
from types import SimpleNamespace
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "decision_log_coverage_gap_forensic_rerun_delta_review.py"
)
spec = importlib.util.spec_from_file_location(
    "decision_log_coverage_gap_forensic_rerun_delta_review",
    SCRIPT_PATH,
)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_forensic_rerun_delta_review_report_marks_positive_delta():
    before_reports = {
        "b2": {
            "summary": {
                "sample_rows": 30,
                "matched_rows": 7,
                "fallback_matches": 7,
                "unmatched_outside_coverage": 23,
            },
            "coverage": {
                "rows_scanned": 100,
                "source_count": 2,
                "earliest_time": "2026-03-27T15:29:43",
                "latest_time": "2026-03-29T23:41:00",
            },
            "decision_sources": [{"path": "a.csv"}],
            "decision_detail_sources": [],
            "decision_archive_sources": [],
        },
        "b3": {
            "summary": {
                "row_count": 30,
                "manual_review_rows": 30,
                "coverage_gap_rows": 23,
                "fallback_rows": 7,
            }
        },
        "b4": {
            "summary": {"row_count": 30, "family_count": 4, "repeat_families": 4},
            "family_counts": {"decision_log_coverage_gap": 23},
        },
        "b5": {
            "summary": {
                "candidate_count": 4,
                "critical_candidates": 1,
                "high_candidates": 3,
            },
            "action_candidates": [{"family": "decision_log_coverage_gap", "priority": "critical"}],
        },
    }
    after_reports = {
        "b2": {
            "summary": {
                "sample_rows": 30,
                "matched_rows": 12,
                "fallback_matches": 10,
                "unmatched_outside_coverage": 18,
            },
            "coverage": {
                "rows_scanned": 160,
                "source_count": 4,
                "earliest_time": "2026-03-27T14:00:00",
                "latest_time": "2026-03-30T01:47:58",
            },
            "decision_sources": [{"path": "a.csv"}, {"path": "b.csv"}],
            "decision_detail_sources": [],
            "decision_archive_sources": [{"path": "archive.parquet"}],
        },
        "b3": {
            "summary": {
                "row_count": 30,
                "manual_review_rows": 24,
                "coverage_gap_rows": 18,
                "fallback_rows": 10,
            }
        },
        "b4": {
            "summary": {"row_count": 30, "family_count": 4, "repeat_families": 4},
            "family_counts": {"decision_log_coverage_gap": 18, "guard_leak": 4},
        },
        "b5": {
            "summary": {
                "candidate_count": 4,
                "critical_candidates": 0,
                "high_candidates": 3,
            },
            "action_candidates": [{"family": "guard_leak", "priority": "high"}],
        },
    }

    report = module.build_forensic_rerun_delta_review_report(
        before_reports=before_reports,
        after_reports=after_reports,
        now=datetime.fromisoformat("2026-03-30T03:00:00"),
    )

    assert report["assessment"]["rerun_state"] == "forensic_delta_positive"
    assert report["assessment"]["recommended_next_step"] == "C6_close_out_handoff"
    assert report["delta_summary"]["matched_rows_delta"] == 5
    assert report["delta_summary"]["coverage_gap_rows_delta"] == -5
    assert report["delta_summary"]["after_top_candidate_family"] == "guard_leak"


def test_build_forensic_rerun_delta_review_report_marks_archive_only_improvement():
    before_reports = {
        "b2": {
            "summary": {
                "sample_rows": 30,
                "matched_rows": 7,
                "fallback_matches": 7,
                "unmatched_outside_coverage": 23,
            },
            "coverage": {
                "rows_scanned": 22027,
                "source_count": 7,
                "earliest_time": "2026-03-27T15:29:43",
                "latest_time": "2026-03-29T23:41:00",
            },
            "decision_sources": [{"path": "a.csv"}, {"path": "b.csv"}, {"path": "c.csv"}],
            "decision_detail_sources": [{}, {}, {}, {}],
            "decision_archive_sources": [],
        },
        "b3": {
            "summary": {
                "row_count": 30,
                "manual_review_rows": 30,
                "coverage_gap_rows": 23,
                "fallback_rows": 7,
            }
        },
        "b4": {
            "summary": {"row_count": 30, "family_count": 4, "repeat_families": 4},
            "family_counts": {
                "decision_log_coverage_gap": 23,
                "consumer_stage_misalignment": 3,
                "guard_leak": 2,
                "probe_promoted_too_early": 2,
            },
        },
        "b5": {
            "summary": {
                "candidate_count": 4,
                "critical_candidates": 1,
                "high_candidates": 3,
            },
            "action_candidates": [{"family": "decision_log_coverage_gap", "priority": "critical"}],
        },
    }
    after_reports = {
        "b2": {
            "summary": {
                "sample_rows": 30,
                "matched_rows": 7,
                "fallback_matches": 7,
                "unmatched_outside_coverage": 23,
            },
            "coverage": {
                "rows_scanned": 26378,
                "source_count": 10,
                "earliest_time": "2026-03-27T15:29:43",
                "latest_time": "2026-03-30T01:47:58",
            },
            "decision_sources": [{"path": "a.csv"}, {"path": "b.csv"}, {"path": "c.csv"}, {"path": "d.csv"}, {"path": "e.csv"}],
            "decision_detail_sources": [{}, {}, {}, {}],
            "decision_archive_sources": [{"path": "archive.parquet"}],
        },
        "b3": {
            "summary": {
                "row_count": 30,
                "manual_review_rows": 30,
                "coverage_gap_rows": 23,
                "fallback_rows": 7,
            }
        },
        "b4": {
            "summary": {"row_count": 30, "family_count": 4, "repeat_families": 4},
            "family_counts": {
                "decision_log_coverage_gap": 23,
                "consumer_stage_misalignment": 3,
                "guard_leak": 2,
                "probe_promoted_too_early": 2,
            },
        },
        "b5": {
            "summary": {
                "candidate_count": 4,
                "critical_candidates": 1,
                "high_candidates": 3,
            },
            "action_candidates": [{"family": "decision_log_coverage_gap", "priority": "critical"}],
        },
    }

    report = module.build_forensic_rerun_delta_review_report(
        before_reports=before_reports,
        after_reports=after_reports,
        now=datetime.fromisoformat("2026-03-30T03:30:00"),
    )

    assert report["assessment"]["rerun_state"] == "archive_provenance_improved_but_gap_unchanged"
    assert report["delta_summary"]["archive_source_delta"] == 1
    assert report["delta_summary"]["matched_rows_delta"] == 0
    assert report["delta_summary"]["coverage_gap_rows_delta"] == 0
    assert (
        report["assessment"]["remaining_gap_interpretation"]
        == "internal archive provenance improved but remaining gap still appears to sit outside currently available workspace coverage"
    )


def test_write_forensic_rerun_delta_review_report_uses_frozen_baseline_snapshot(tmp_path, monkeypatch):
    def _write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(__import__("json").dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_b2 = tmp_path / "b2.json"
    latest_b3 = tmp_path / "b3.json"
    latest_b4 = tmp_path / "b4.json"
    latest_b5 = tmp_path / "b5.json"
    baseline_snapshot = tmp_path / "baseline.json"
    output_dir = tmp_path / "out"

    _write_json(latest_b2, {"summary": {"sample_rows": 30, "matched_rows": 99}, "coverage": {}})
    _write_json(latest_b3, {"summary": {"coverage_gap_rows": 99}})
    _write_json(latest_b4, {"summary": {"family_count": 1}, "family_counts": {"guard_leak": 1}})
    _write_json(latest_b5, {"summary": {"candidate_count": 1}, "action_candidates": [{"family": "guard_leak"}]})
    _write_json(
        baseline_snapshot,
        {
            "b2": {
                "summary": {
                    "sample_rows": 30,
                    "matched_rows": 7,
                    "fallback_matches": 7,
                    "unmatched_outside_coverage": 23,
                },
                "coverage": {
                    "rows_scanned": 22027,
                    "source_count": 7,
                    "earliest_time": "2026-03-27T15:29:43",
                    "latest_time": "2026-03-29T23:41:00",
                },
                "decision_sources": [{}, {}, {}],
                "decision_detail_sources": [{}, {}, {}, {}],
                "decision_archive_sources": [],
            },
            "b3": {"summary": {"coverage_gap_rows": 23, "manual_review_rows": 30}},
            "b4": {
                "summary": {"family_count": 4, "repeat_families": 4, "row_count": 30},
                "family_counts": {"decision_log_coverage_gap": 23},
            },
            "b5": {
                "summary": {"candidate_count": 4, "critical_candidates": 1, "high_candidates": 3},
                "action_candidates": [{"family": "decision_log_coverage_gap", "priority": "critical"}],
            },
        },
    )

    after_b2 = {
        "summary": {
            "sample_rows": 30,
            "matched_rows": 7,
            "fallback_matches": 7,
            "unmatched_outside_coverage": 23,
        },
        "coverage": {
            "rows_scanned": 26443,
            "source_count": 10,
            "earliest_time": "2026-03-27T15:29:43",
            "latest_time": "2026-03-30T01:51:29",
        },
        "decision_sources": [{}, {}, {}, {}, {}],
        "decision_detail_sources": [{}, {}, {}, {}],
        "decision_archive_sources": [{}],
    }
    after_b3 = {"summary": {"coverage_gap_rows": 23, "manual_review_rows": 30}}
    after_b4 = {
        "summary": {"family_count": 4, "repeat_families": 4, "row_count": 30},
        "family_counts": {"decision_log_coverage_gap": 23},
    }
    after_b5 = {
        "summary": {"candidate_count": 4, "critical_candidates": 1, "high_candidates": 3},
        "action_candidates": [{"family": "decision_log_coverage_gap", "priority": "critical"}],
    }

    def _module_for(report: dict, suffix: str):
        return SimpleNamespace(
            **{
                f"write_actual_entry_forensic_{suffix}_report": lambda output_dir: {
                    "latest_json_path": str(output_dir / f"{suffix}.json"),
                    "report": report,
                }
            }
        )

    modules = iter(
        [
            _module_for(after_b2, "match"),
            _module_for(after_b3, "table"),
            _module_for(after_b4, "family"),
            _module_for(after_b5, "action"),
        ]
    )

    monkeypatch.setattr(module, "_load_script_module", lambda *_args, **_kwargs: next(modules))

    result = module.write_forensic_rerun_delta_review_report(
        b2_report_path=latest_b2,
        b3_report_path=latest_b3,
        b4_report_path=latest_b4,
        b5_report_path=latest_b5,
        baseline_snapshot_path=baseline_snapshot,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-30T04:00:00"),
    )

    report = result["report"]
    assert report["baseline_snapshot"]["source"] == "frozen_snapshot"
    assert report["delta_summary"]["archive_source_delta"] == 1
    assert report["delta_summary"]["matched_rows_delta"] == 0
    assert report["assessment"]["rerun_state"] == "archive_provenance_improved_but_gap_unchanged"
