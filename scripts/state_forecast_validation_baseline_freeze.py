from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from backend.trading.engine.core.forecast_engine import FORECAST_HARVEST_TARGETS_V1
from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EvidenceVector,
    ForecastFeaturesV1,
    StateRawSnapshot,
    StateVectorV2,
)


OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
REPORT_VERSION = "state_forecast_validation_sf0_baseline_v1"

SOURCE_REFS = {
    "models": "backend/trading/engine/core/models.py",
    "state_builder": "backend/trading/engine/state/builder.py",
    "advanced_inputs": "backend/trading/engine/state/advanced_inputs.py",
    "forecast_engine": "backend/trading/engine/core/forecast_engine.py",
    "context_classifier": "backend/services/context_classifier.py",
    "entry_service": "backend/services/entry_service.py",
    "consumer_contract": "backend/services/consumer_contract.py",
}

STATE_RAW_METADATA_BRIDGE_FIELDS_V1 = [
    "state_advanced_inputs_v1",
    "advanced_input_activation_state",
    "advanced_input_activation_reasons",
    "tick_flow_bias",
    "tick_flow_burst",
    "tick_flow_state",
    "tick_sample_size",
    "order_book_imbalance",
    "order_book_thinness",
    "order_book_state",
    "order_book_levels",
    "event_risk_score",
    "event_risk_state",
    "event_risk_match_count",
]

STATE_EXECUTION_BRIDGE_FIELDS_V1 = [
    "wait_patience_gain",
    "confirm_aggression_gain",
    "hold_patience_gain",
    "fast_exit_risk_penalty",
    "patience_state_label",
    "topdown_state_label",
    "quality_state_label",
    "execution_friction_state",
    "session_exhaustion_state",
    "event_risk_state",
]

ENTRY_PAYLOAD_SURFACE_FIELDS_V1 = [
    "position_snapshot_v2",
    "state_vector_v2",
    "evidence_vector_v1",
    "belief_state_v1",
    "barrier_state_v1",
    "forecast_features_v1",
    "transition_forecast_v1",
    "trade_management_forecast_v1",
    "forecast_gap_metrics_v1",
    "energy_helper_v2",
]

ADVANCED_INPUT_ACTIVATION_REASONS_V1 = [
    "force_on",
    "shock_regime",
    "spread_stress",
    "low_participation",
    "wait_conflict",
    "wait_noise",
]

ADVANCED_INPUT_COLLECTORS_V1 = [
    {
        "collector_key": "tick_history",
        "collector_function": "_collect_tick_history",
        "collector_source": "advanced_inputs.py",
        "collector_state_field": "collector_state",
        "payload_fields": [
            "collector_enabled",
            "collector_available",
            "collector_active",
            "collector_state",
            "collector_source",
            "tick_flow_bias",
            "tick_flow_burst",
            "tick_sample_size",
        ],
    },
    {
        "collector_key": "order_book",
        "collector_function": "_collect_order_book",
        "collector_source": "advanced_inputs.py",
        "collector_state_field": "collector_state",
        "payload_fields": [
            "collector_enabled",
            "collector_available",
            "collector_active",
            "collector_state",
            "collector_source",
            "order_book_imbalance",
            "order_book_thinness",
            "order_book_levels",
        ],
    },
    {
        "collector_key": "event_risk",
        "collector_function": "_collect_event_risk",
        "collector_source": "advanced_inputs.py",
        "collector_state_field": "collector_state",
        "payload_fields": [
            "collector_enabled",
            "collector_available",
            "collector_active",
            "collector_state",
            "collector_source",
            "event_risk_score",
            "event_match_count",
        ],
    },
]

RELEVANT_TEST_FILES_V1 = [
    "tests/unit/test_state_contract.py",
    "tests/unit/test_entry_wait_state_bias_policy.py",
    "tests/unit/test_forecast_contract.py",
    "tests/unit/test_forecast_bucket_validation.py",
    "tests/unit/test_forecast_shadow_compare_readiness.py",
]


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _type_name(value: Any) -> str:
    name = getattr(value, "__name__", None)
    if name:
        return str(name)
    return str(value)


def _dataclass_field_inventory(model: type[Any], *, section_name: str, source_ref: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in fields(model):
        rows.append(
            {
                "section": section_name,
                "name": str(item.name),
                "type": _type_name(item.type),
                "source_ref": source_ref,
            }
        )
    return rows


def _bridge_inventory(items: list[str], *, section_name: str, source_ref: str) -> list[dict[str, Any]]:
    return [
        {
            "section": section_name,
            "name": str(item),
            "type": "bridge_field",
            "source_ref": source_ref,
        }
        for item in items
    ]


def _harvest_inventory() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for section_name, names in FORECAST_HARVEST_TARGETS_V1.items():
        grouped[str(section_name)] = [
            {
                "section": str(section_name),
                "name": str(field_name),
                "type": "harvest_field",
                "source_ref": SOURCE_REFS["forecast_engine"],
            }
            for field_name in list(names or [])
        ]
    return grouped


def _test_inventory() -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for relative_path in RELEVANT_TEST_FILES_V1:
        absolute_path = ROOT / relative_path
        inventory.append(
            {
                "path": relative_path,
                "exists": bool(absolute_path.exists()),
                "source_ref": relative_path,
            }
        )
    return inventory


def _flatten_inventory_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    inventories = dict(report.get("inventories", {}) or {})
    rows: list[dict[str, Any]] = []

    flat_sections = (
        "state_raw_snapshot_fields",
        "state_vector_v2_fields",
        "evidence_vector_fields",
        "belief_state_fields",
        "barrier_state_fields",
        "forecast_features_fields",
        "state_raw_metadata_bridge_fields",
        "state_execution_bridge_fields",
        "entry_payload_surface_fields",
        "advanced_input_activation_reasons",
        "consumer_guardrail_inventory",
    )
    for section_name in flat_sections:
        for item in list(inventories.get(section_name, []) or []):
            rows.append(
                {
                    "inventory_group": section_name,
                    "item_name": _coerce_text(item.get("name")),
                    "item_type": _coerce_text(item.get("type")),
                    "source_ref": _coerce_text(item.get("source_ref")),
                    "detail": _coerce_text(item.get("detail") or item.get("type")),
                }
            )

    harvest_targets = dict(inventories.get("forecast_harvest_targets", {}) or {})
    for section_name, items in harvest_targets.items():
        for item in list(items or []):
            rows.append(
                {
                    "inventory_group": f"forecast_harvest_targets.{section_name}",
                    "item_name": _coerce_text(item.get("name")),
                    "item_type": _coerce_text(item.get("type")),
                    "source_ref": _coerce_text(item.get("source_ref")),
                    "detail": _coerce_text(item.get("detail") or section_name),
                }
            )

    for collector in list(inventories.get("advanced_input_collectors", []) or []):
        rows.append(
            {
                "inventory_group": "advanced_input_collectors",
                "item_name": _coerce_text(collector.get("collector_key")),
                "item_type": "collector",
                "source_ref": SOURCE_REFS["advanced_inputs"],
                "detail": _coerce_text(collector.get("collector_function")),
            }
        )

    for test_row in list(inventories.get("relevant_test_files", []) or []):
        rows.append(
            {
                "inventory_group": "relevant_test_files",
                "item_name": _coerce_text(test_row.get("path")),
                "item_type": "test_file",
                "source_ref": _coerce_text(test_row.get("source_ref")),
                "detail": "exists" if bool(test_row.get("exists")) else "missing",
            }
        )
    return rows


def build_state_forecast_validation_baseline_report(*, now: datetime | None = None) -> dict[str, Any]:
    current_now = _resolve_now(now)
    state_raw_snapshot_fields = _dataclass_field_inventory(
        StateRawSnapshot,
        section_name="state_raw_snapshot_fields",
        source_ref=SOURCE_REFS["models"],
    )
    state_vector_v2_fields = _dataclass_field_inventory(
        StateVectorV2,
        section_name="state_vector_v2_fields",
        source_ref=SOURCE_REFS["models"],
    )
    evidence_vector_fields = _dataclass_field_inventory(
        EvidenceVector,
        section_name="evidence_vector_fields",
        source_ref=SOURCE_REFS["models"],
    )
    belief_state_fields = _dataclass_field_inventory(
        BeliefState,
        section_name="belief_state_fields",
        source_ref=SOURCE_REFS["models"],
    )
    barrier_state_fields = _dataclass_field_inventory(
        BarrierState,
        section_name="barrier_state_fields",
        source_ref=SOURCE_REFS["models"],
    )
    forecast_features_fields = _dataclass_field_inventory(
        ForecastFeaturesV1,
        section_name="forecast_features_fields",
        source_ref=SOURCE_REFS["models"],
    )
    harvest_targets = _harvest_inventory()
    relevant_tests = _test_inventory()
    state_raw_metadata_bridge_fields = _bridge_inventory(
        STATE_RAW_METADATA_BRIDGE_FIELDS_V1,
        section_name="state_raw_metadata_bridge_fields",
        source_ref=SOURCE_REFS["state_builder"],
    )
    state_execution_bridge_fields = _bridge_inventory(
        STATE_EXECUTION_BRIDGE_FIELDS_V1,
        section_name="state_execution_bridge_fields",
        source_ref=SOURCE_REFS["context_classifier"],
    )
    entry_payload_surface_fields = _bridge_inventory(
        ENTRY_PAYLOAD_SURFACE_FIELDS_V1,
        section_name="entry_payload_surface_fields",
        source_ref=SOURCE_REFS["entry_service"],
    )
    advanced_input_activation_reasons = _bridge_inventory(
        ADVANCED_INPUT_ACTIVATION_REASONS_V1,
        section_name="advanced_input_activation_reasons",
        source_ref=SOURCE_REFS["advanced_inputs"],
    )
    consumer_guardrail_inventory = [
        {
            "section": "consumer_guardrail_inventory",
            "name": "energy_helper_v2.helper_only",
            "type": "guardrail",
            "detail": "consumer may read helper hints only and never promote it to identity owner",
            "source_ref": SOURCE_REFS["consumer_contract"],
        },
        {
            "section": "consumer_guardrail_inventory",
            "name": "forecast_payload.direct_reinterpretation_forbidden",
            "type": "guardrail",
            "detail": "consumer may not directly reinterpret forecast payloads",
            "source_ref": SOURCE_REFS["consumer_contract"],
        },
        {
            "section": "consumer_guardrail_inventory",
            "name": "semantic_vectors.direct_reinterpretation_forbidden",
            "type": "guardrail",
            "detail": "consumer may not directly reinterpret response/state/evidence/belief/barrier vectors",
            "source_ref": SOURCE_REFS["consumer_contract"],
        },
    ]

    harvest_field_count = sum(len(list(items or [])) for items in harvest_targets.values())
    summary = {
        "state_raw_snapshot_field_count": int(len(state_raw_snapshot_fields)),
        "state_vector_v2_field_count": int(len(state_vector_v2_fields)),
        "evidence_vector_field_count": int(len(evidence_vector_fields)),
        "belief_state_field_count": int(len(belief_state_fields)),
        "barrier_state_field_count": int(len(barrier_state_fields)),
        "forecast_features_field_count": int(len(forecast_features_fields)),
        "state_raw_metadata_bridge_field_count": int(len(state_raw_metadata_bridge_fields)),
        "state_execution_bridge_field_count": int(len(state_execution_bridge_fields)),
        "entry_payload_surface_field_count": int(len(entry_payload_surface_fields)),
        "forecast_harvest_section_count": int(len(harvest_targets)),
        "forecast_harvest_field_count": int(harvest_field_count),
        "advanced_input_collector_count": int(len(ADVANCED_INPUT_COLLECTORS_V1)),
        "advanced_input_activation_reason_count": int(len(advanced_input_activation_reasons)),
        "relevant_test_file_count": int(len(relevant_tests)),
        "existing_relevant_test_file_count": int(sum(1 for row in relevant_tests if bool(row.get("exists")))),
    }
    assessment = {
        "baseline_locked": True,
        "validation_focus": "coverage_then_activation_then_value",
        "consumer_rule": "scene_owner_with_state_and_forecast_as_modifier_only",
        "recommended_next_step": "SF1_state_coverage_audit",
        "next_questions": [
            "Which state fields are historically sparse or default-heavy?",
            "Which advanced collectors are usually inactive or unavailable?",
            "Which harvest targets are present but weakly used or low-value?",
        ],
    }
    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "baseline_kind": "state_forecast_validation_sf0_inventory_freeze",
        "source_refs": SOURCE_REFS,
        "inventories": {
            "state_raw_snapshot_fields": state_raw_snapshot_fields,
            "state_vector_v2_fields": state_vector_v2_fields,
            "evidence_vector_fields": evidence_vector_fields,
            "belief_state_fields": belief_state_fields,
            "barrier_state_fields": barrier_state_fields,
            "forecast_features_fields": forecast_features_fields,
            "state_raw_metadata_bridge_fields": state_raw_metadata_bridge_fields,
            "state_execution_bridge_fields": state_execution_bridge_fields,
            "entry_payload_surface_fields": entry_payload_surface_fields,
            "forecast_harvest_targets": harvest_targets,
            "advanced_input_activation_reasons": advanced_input_activation_reasons,
            "advanced_input_collectors": ADVANCED_INPUT_COLLECTORS_V1,
            "relevant_test_files": relevant_tests,
            "consumer_guardrail_inventory": consumer_guardrail_inventory,
        },
        "baseline_summary": summary,
        "baseline_assessment": assessment,
    }


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = _flatten_inventory_rows(report)
    fieldnames = ["inventory_group", "item_name", "item_type", "source_ref", "detail"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("baseline_summary", {}) or {})
    assessment = dict(report.get("baseline_assessment", {}) or {})
    inventories = dict(report.get("inventories", {}) or {})
    harvest_targets = dict(inventories.get("forecast_harvest_targets", {}) or {})
    advanced_collectors = list(inventories.get("advanced_input_collectors", []) or [])
    test_rows = list(inventories.get("relevant_test_files", []) or [])
    lines = [
        "# State / Forecast Validation SF0 Baseline",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- baseline_locked: `{assessment.get('baseline_locked', False)}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- state_raw_snapshot_field_count: `{summary.get('state_raw_snapshot_field_count', 0)}`",
        f"- state_vector_v2_field_count: `{summary.get('state_vector_v2_field_count', 0)}`",
        f"- evidence/belief/barrier field count: `{summary.get('evidence_vector_field_count', 0)}` / `{summary.get('belief_state_field_count', 0)}` / `{summary.get('barrier_state_field_count', 0)}`",
        f"- forecast_features_field_count: `{summary.get('forecast_features_field_count', 0)}`",
        f"- forecast_harvest_section_count: `{summary.get('forecast_harvest_section_count', 0)}`",
        f"- forecast_harvest_field_count: `{summary.get('forecast_harvest_field_count', 0)}`",
        f"- advanced_input_collector_count: `{summary.get('advanced_input_collector_count', 0)}`",
        f"- relevant_test_file_count: `{summary.get('relevant_test_file_count', 0)}`",
        "",
        "## Harvest Targets",
        "",
        "| section | field_count |",
        "|---|---|",
    ]
    for section_name, items in harvest_targets.items():
        lines.append(f"| {section_name} | {len(list(items or []))} |")

    lines.extend(
        [
            "",
            "## Advanced Collectors",
            "",
            "| collector | function | payload_fields |",
            "|---|---|---|",
        ]
    )
    for item in advanced_collectors:
        payload_fields = ", ".join(list(item.get("payload_fields", []) or []))
        lines.append(
            f"| {_coerce_text(item.get('collector_key'))} | {_coerce_text(item.get('collector_function'))} | {payload_fields} |"
        )

    lines.extend(
        [
            "",
            "## Relevant Tests",
            "",
            "| path | exists |",
            "|---|---|",
        ]
    )
    for row in test_rows:
        lines.append(f"| {_coerce_text(row.get('path'))} | {bool(row.get('exists'))} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_state_forecast_validation_baseline_report(
    *,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_baseline_report(now=now)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_sf0_baseline_latest.json"
    latest_csv = output_dir / "state_forecast_validation_sf0_baseline_latest.csv"
    latest_md = output_dir / "state_forecast_validation_sf0_baseline_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report, latest_csv)
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze SF0 baseline inventory for state / forecast validation.")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_baseline_report(output_dir=args.output_dir)
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
