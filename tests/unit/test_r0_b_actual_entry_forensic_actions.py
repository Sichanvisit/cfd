import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "r0_b_actual_entry_forensic_actions.py"
spec = importlib.util.spec_from_file_location("r0_b_actual_entry_forensic_actions", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_family_report(path: Path, family_groups: list[dict]) -> None:
    payload = {
        "report_version": "r0_b4_family_clustering_v1",
        "generated_at": "2026-03-29T15:00:00",
        "summary": {"row_count": sum(int(g.get("count", 0)) for g in family_groups)},
        "family_groups": family_groups,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_action_report_maps_family_to_priority_owner_and_next_action(tmp_path):
    family_report = tmp_path / "b4.json"
    _write_family_report(
        family_report,
        [
            {
                "family": "runtime_linkage_integrity_gap",
                "count": 15,
                "representative_sample_rank": 1,
                "representative_ticket": 101,
                "representative_symbol": "XAUUSD",
                "representative_setup_id": "range_upper_reversal_sell",
                "representative_reason": "runtime key suspicious",
                "top_blocked_by": {"barrier_guard": 11},
                "top_stages": {"PROBE": 11},
                "top_observe_reasons": {"upper_reject_confirm": 11},
                "context_counts": {"runtime_linkage_integrity_gap|stage=PROBE|blocked=barrier_guard|observe=upper_reject_confirm|setup=range_upper_reversal_sell": 11},
                "sample_ranks": [1, 2, 3],
            },
            {
                "family": "probe_promoted_too_early",
                "count": 2,
                "representative_sample_rank": 12,
                "representative_ticket": 212,
                "representative_symbol": "XAUUSD",
                "representative_setup_id": "",
                "representative_reason": "probe too early",
                "top_blocked_by": {"forecast_guard": 2},
                "top_stages": {"PROBE": 2},
                "top_observe_reasons": {"upper_reject_probe_observe": 2},
                "context_counts": {"probe_promoted_too_early|stage=PROBE|blocked=forecast_guard|observe=upper_reject_probe_observe|setup=-": 2},
                "sample_ranks": [12, 19],
            },
        ],
    )

    report = module.build_actual_entry_forensic_action_report(
        family_report_path=family_report,
        now=datetime.fromisoformat("2026-03-29T15:30:00"),
    )

    assert report["summary"]["candidate_count"] == 2
    assert report["summary"]["critical_candidates"] == 1
    assert report["summary"]["high_candidates"] == 1

    first = report["action_candidates"][0]
    second = report["action_candidates"][1]

    assert first["family"] == "runtime_linkage_integrity_gap"
    assert first["priority"] == "critical"
    assert module.STORAGE_COMPACTION in first["suspected_owners"]
    assert module.ENTRY_ENGINES in first["suspected_owners"]
    assert "runtime_snapshot_key" in first["suspected_issue"]
    assert "generic anchor_value=0.0" in first["next_action"]

    assert second["family"] == "probe_promoted_too_early"
    assert second["priority"] == "high"
    assert module.ENTRY_SERVICE in second["suspected_owners"]
    assert module.ENTRY_TRY_OPEN in second["suspected_owners"]
    assert "probe_plan_ready" in second["next_action"]


def test_build_action_report_orders_by_priority_then_evidence_count(tmp_path):
    family_report = tmp_path / "b4.json"
    _write_family_report(
        family_report,
        [
            {
                "family": "guard_leak",
                "count": 8,
                "representative_sample_rank": 30,
                "representative_ticket": 330,
                "representative_symbol": "XAUUSD",
                "representative_setup_id": "",
                "representative_reason": "guard leak",
                "top_blocked_by": {"forecast_guard": 8},
                "top_stages": {"OBSERVE": 8},
                "top_observe_reasons": {"upper_reject_confirm": 8},
                "context_counts": {},
                "sample_ranks": [30],
            },
            {
                "family": "decision_log_coverage_gap",
                "count": 3,
                "representative_sample_rank": 20,
                "representative_ticket": 320,
                "representative_symbol": "XAUUSD",
                "representative_setup_id": "",
                "representative_reason": "coverage",
                "top_blocked_by": {"": 3},
                "top_stages": {"": 3},
                "top_observe_reasons": {"": 3},
                "context_counts": {},
                "sample_ranks": [20],
            },
        ],
    )

    report = module.build_actual_entry_forensic_action_report(
        family_report_path=family_report,
        now=datetime.fromisoformat("2026-03-29T15:30:00"),
    )

    assert report["action_candidates"][0]["family"] == "decision_log_coverage_gap"
    assert report["action_candidates"][1]["family"] == "guard_leak"
    assert report["action_candidates"][0]["rank"] == 1
    assert report["action_candidates"][1]["rank"] == 2


def test_write_action_report_writes_json_csv_and_markdown(tmp_path):
    family_report = tmp_path / "b4.json"
    output_dir = tmp_path / "analysis"
    _write_family_report(
        family_report,
        [
            {
                "family": "consumer_stage_misalignment",
                "count": 3,
                "representative_sample_rank": 7,
                "representative_ticket": 307,
                "representative_symbol": "NAS100",
                "representative_setup_id": "",
                "representative_reason": "consumer mismatch",
                "top_blocked_by": {"energy_soft_block": 2},
                "top_stages": {"BLOCKED": 2},
                "top_observe_reasons": {"lower_rebound_confirm": 2},
                "context_counts": {},
                "sample_ranks": [7, 8, 9],
            }
        ],
    )

    result = module.write_actual_entry_forensic_action_report(
        family_report_path=family_report,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-29T15:30:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
    payload = json.loads(Path(result["latest_json_path"]).read_text(encoding="utf-8"))
    assert payload["report_version"] == module.REPORT_VERSION
    assert payload["summary"]["candidate_count"] == 1
    assert payload["action_candidates"][0]["family"] == "consumer_stage_misalignment"
