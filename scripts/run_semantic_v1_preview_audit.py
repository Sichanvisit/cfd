from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis" / "semantic_v1"
SHADOW_COMPARE_GLOB = "semantic_shadow_compare_report_*.json"

TARGET_METRICS_KEYS = {
    "timing": "timing_metrics",
    "entry_quality": "entry_quality_metrics",
    "exit_management": "exit_management_metrics",
}

FORBIDDEN_FEATURE_COLUMNS = {
    "outcome",
    "blocked_by",
    "label_unknown_count",
    "label_positive_count",
    "label_negative_count",
    "label_is_ambiguous",
    "label_source_descriptor",
    "is_censored",
    "transition_label_status",
    "management_label_status",
    "transition_positive_count",
    "transition_negative_count",
    "transition_unknown_count",
    "management_positive_count",
    "management_negative_count",
    "management_unknown_count",
    "transition_direction",
    "transition_same_side_positive_count",
    "transition_adverse_positive_count",
    "transition_quality_score",
    "management_exit_favor_positive_count",
    "management_hold_favor_positive_count",
    "semantic_target_source",
    "target_timing_now_vs_wait",
    "target_timing_margin",
    "target_entry_quality",
    "target_entry_quality_margin",
    "target_exit_management",
    "target_exit_management_margin",
}


def _resolve_path(value: str | Path | None, default: Path | None = None) -> Path:
    if value is None:
        if default is None:
            raise ValueError("path is required")
        path = default
    else:
        path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"expected object JSON: {path}")
    return dict(payload)


def _resolve_latest_matching_path(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = sorted(
        (item for item in directory.glob(pattern) if item.is_file()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _feature_joinable_rows(paths: Iterable[Path]) -> int:
    total = 0
    for path in paths:
        parquet = pq.read_table(path, columns=[column for column in ("replay_row_key", "decision_row_key") if column in pq.ParquetFile(path).schema_arrow.names])
        frame = parquet.to_pandas()
        replay_key = frame["replay_row_key"] if "replay_row_key" in frame.columns else ""
        decision_key = frame["decision_row_key"] if "decision_row_key" in frame.columns else ""
        join_key = replay_key.fillna("").astype(str).str.strip() if hasattr(replay_key, "fillna") else decision_key.fillna("").astype(str).str.strip()
        if hasattr(decision_key, "fillna"):
            join_key = replay_key.fillna("").astype(str).str.strip()
            empty_mask = join_key.eq("")
            join_key = join_key.where(~empty_mask, decision_key.fillna("").astype(str).str.strip())
        total += int(join_key.ne("").sum())
    return total


def _replay_joinable_rows(paths: Iterable[Path]) -> int:
    total = 0
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = str(raw_line or "").strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, Mapping):
                    continue
                replay_key = str(payload.get("replay_row_key", "") or payload.get("row_key", "") or "").strip()
                decision_key = str(payload.get("decision_row_key", "") or "").strip()
                if replay_key or decision_key:
                    total += 1
    return total


def _join_coverage_summary(build_manifest: Mapping[str, Any]) -> dict[str, Any]:
    feature_files = [_resolve_path(path) for path in build_manifest.get("feature_files", [])]
    replay_files = [_resolve_path(path) for path in build_manifest.get("replay_files", [])]
    joined_rows = int(build_manifest.get("joined_rows", 0) or 0)
    feature_joinable_rows = _feature_joinable_rows(feature_files) if feature_files else 0
    replay_joinable_rows = _replay_joinable_rows(replay_files) if replay_files else 0
    max_matchable_rows = min(feature_joinable_rows, replay_joinable_rows) if feature_joinable_rows and replay_joinable_rows else 0
    coverage_ratio = round(joined_rows / max_matchable_rows, 6) if max_matchable_rows > 0 else None
    issues: list[str] = []
    if max_matchable_rows <= 0:
        issues.append("max_matchable_rows_unavailable")
    elif coverage_ratio is not None and coverage_ratio < 0.98:
        issues.append(f"join_coverage_below_threshold:{coverage_ratio}<0.98")
    return {
        "joined_rows": joined_rows,
        "feature_joinable_rows": feature_joinable_rows,
        "replay_joinable_rows": replay_joinable_rows,
        "max_matchable_rows": max_matchable_rows,
        "coverage_ratio": coverage_ratio,
        "status": "healthy" if not issues else "fail",
        "issues": issues,
    }


def _leakage_summary(metrics: Mapping[str, Any]) -> dict[str, Any]:
    feature_columns = [str(column) for column in metrics.get("feature_columns", [])]
    forbidden_hits = sorted(column for column in feature_columns if column in FORBIDDEN_FEATURE_COLUMNS)
    return {
        "feature_count": len(feature_columns),
        "forbidden_feature_hits": forbidden_hits,
        "status": "healthy" if not forbidden_hits else "fail",
    }


def _feature_tier_summary(metrics: Mapping[str, Any]) -> dict[str, Any]:
    observed_only_dropped = [
        str(column)
        for column in list(metrics.get("dataset_observed_only_dropped_feature_columns", []) or [])
        if str(column).strip()
    ]
    return {
        "source_generation": str(metrics.get("dataset_source_generation", "") or ""),
        "tier_policy": dict(metrics.get("dataset_feature_tier_policy", {}) or {}),
        "tier_summary": dict(metrics.get("dataset_feature_tier_summary", {}) or {}),
        "observed_only_dropped_feature_count": int(len(observed_only_dropped)),
        "observed_only_dropped_feature_columns": observed_only_dropped[:12],
    }


def _shadow_compare_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "report_path": "",
            "status": "missing",
            "issues": ["shadow_compare_report_missing"],
            "summary": {},
            "compare_label_counts": {},
            "trace_quality_counts": {},
            "top_candidate": {},
        }

    payload = _load_json(path)
    summary = dict(payload.get("summary", {}) or {})
    compare_label_counts = dict(payload.get("compare_label_counts", {}) or {})
    trace_quality_counts = dict(payload.get("trace_quality_counts", {}) or {})
    candidates = list(payload.get("candidate_threshold_table", []) or [])

    issues: list[str] = []
    if int(summary.get("rows_total", 0) or 0) <= 0:
        issues.append("shadow_compare_rows_unavailable")
    if int(summary.get("shadow_available_rows", 0) or 0) <= 0:
        issues.append("shadow_compare_shadow_rows_unavailable")
    if int(summary.get("scorable_shadow_rows", 0) or 0) < 32:
        issues.append("shadow_compare_scorable_rows_below_gate")
    if not candidates:
        issues.append("shadow_compare_candidate_thresholds_missing")

    return {
        "report_path": str(path),
        "status": "healthy" if not issues else "warning",
        "issues": issues,
        "summary": summary,
        "compare_label_counts": compare_label_counts,
        "trace_quality_counts": trace_quality_counts,
        "top_candidate": dict(candidates[0]) if candidates else {},
    }


def _promotion_gate_summary(
    *,
    join_summary: Mapping[str, Any],
    per_target: Mapping[str, Mapping[str, Any]],
    shadow_compare: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    if str(join_summary.get("status", "")) != "healthy":
        blockers.extend(str(issue) for issue in join_summary.get("issues", []))

    for dataset_key, details in per_target.items():
        split_status = str(details.get("split_health_status", "") or "")
        auc = details.get("auc")
        leakage_hits = list(details.get("leakage", {}).get("forbidden_feature_hits", []))
        if leakage_hits:
            blockers.append(f"{dataset_key}:forbidden_feature_hits")
        if split_status == "fail":
            blockers.append(f"{dataset_key}:split_health_fail")
        elif split_status == "warning":
            warnings.append(f"{dataset_key}:split_health_warning")

        if dataset_key in {"timing", "entry_quality"} and isinstance(auc, (int, float)) and auc <= 0.5:
            blockers.append(f"{dataset_key}:auc_not_better_than_random:{auc:.6f}")
        if dataset_key == "exit_management":
            validation_balance = details.get("validation_class_balance", {})
            minority = min((int(v) for v in validation_balance.values()), default=0) if validation_balance else 0
            if minority < 32:
                blockers.append(f"{dataset_key}:validation_minority_below_gate:{minority}<32")

    shadow_compare_status = str(shadow_compare.get("status", "") or "")
    shadow_compare_issues = [str(issue) for issue in list(shadow_compare.get("issues", []) or [])]
    if shadow_compare_status == "missing":
        blockers.append("shadow_compare_report_missing")
    elif shadow_compare_status == "warning":
        warnings.extend(f"shadow_compare:{issue}" for issue in shadow_compare_issues)

    shadow_compare_ready = len(blockers) == 0
    return {
        "shadow_compare_ready": shadow_compare_ready,
        "status": "pass" if shadow_compare_ready else "blocked",
        "blocking_issues": blockers,
        "warning_issues": warnings,
        "shadow_compare_status": shadow_compare_status,
        "shadow_compare_report_path": str(shadow_compare.get("report_path", "") or ""),
    }


def _render_markdown(report: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Semantic Preview Audit")
    lines.append("")
    lines.append(f"- Created At: `{report['created_at']}`")
    lines.append(f"- Build Manifest: `{report['build_manifest_path']}`")
    lines.append(f"- Model Metrics: `{report['metrics_path']}`")
    lines.append("")
    join_summary = report["join_coverage"]
    lines.append("## Join Coverage")
    lines.append(f"- Status: `{join_summary['status']}`")
    lines.append(f"- Joined Rows: `{join_summary['joined_rows']}`")
    lines.append(f"- Max Matchable Rows: `{join_summary['max_matchable_rows']}`")
    lines.append(f"- Coverage Ratio: `{join_summary['coverage_ratio']}`")
    if join_summary["issues"]:
        lines.append(f"- Issues: `{', '.join(join_summary['issues'])}`")
    lines.append("")

    lines.append("## Target Summary")
    for dataset_key in ("timing", "entry_quality", "exit_management"):
        metrics = report["targets"][dataset_key]
        lines.append(f"### {dataset_key}")
        lines.append(f"- AUC: `{metrics.get('auc')}`")
        lines.append(f"- Accuracy: `{metrics.get('accuracy')}`")
        lines.append(f"- Split Health: `{metrics.get('split_health_status')}`")
        lines.append(f"- Promotion Blocked: `{metrics.get('split_health_promotion_blocked')}`")
        lines.append(f"- Validation Balance: `{metrics.get('validation_class_balance')}`")
        lines.append(f"- Test Balance: `{metrics.get('test_class_balance')}`")
        leakage = metrics["leakage"]
        lines.append(f"- Leakage Status: `{leakage['status']}`")
        lines.append(f"- Forbidden Feature Hits: `{leakage['forbidden_feature_hits']}`")
        feature_tier = metrics.get("feature_tier", {})
        lines.append(f"- Source Generation: `{feature_tier.get('source_generation', '')}`")
        lines.append(f"- Tier Policy: `{feature_tier.get('tier_policy', {})}`")
        lines.append(f"- Tier Summary: `{feature_tier.get('tier_summary', {})}`")
        lines.append(
            f"- Observed-Only Dropped Count: `{feature_tier.get('observed_only_dropped_feature_count', 0)}`"
        )
        lines.append(
            f"- Observed-Only Dropped Sample: `{feature_tier.get('observed_only_dropped_feature_columns', [])}`"
        )
        lines.append(f"- Dataset Dropped Features: `{metrics.get('dataset_dropped_feature_columns', [])}`")
        lines.append(f"- Training Dropped Features: `{metrics.get('training_dropped_feature_columns', [])}`")
        lines.append("")

    shadow_compare = report.get("shadow_compare", {})
    lines.append("## Shadow Compare")
    lines.append(f"- Status: `{shadow_compare.get('status', '')}`")
    lines.append(f"- Report Path: `{shadow_compare.get('report_path', '')}`")
    lines.append(f"- Issues: `{shadow_compare.get('issues', [])}`")
    lines.append(f"- Summary: `{shadow_compare.get('summary', {})}`")
    lines.append(f"- Compare Labels: `{shadow_compare.get('compare_label_counts', {})}`")
    lines.append(f"- Trace Quality: `{shadow_compare.get('trace_quality_counts', {})}`")
    lines.append(f"- Top Candidate: `{shadow_compare.get('top_candidate', {})}`")
    lines.append("")

    promotion = report["promotion_gate"]
    lines.append("## Promotion Gate")
    lines.append(f"- Status: `{promotion['status']}`")
    lines.append(f"- Shadow Compare Ready: `{promotion['shadow_compare_ready']}`")
    lines.append(f"- Shadow Compare Status: `{promotion.get('shadow_compare_status', '')}`")
    lines.append(f"- Shadow Compare Report Path: `{promotion.get('shadow_compare_report_path', '')}`")
    lines.append(f"- Blocking Issues: `{promotion['blocking_issues']}`")
    lines.append(f"- Warning Issues: `{promotion['warning_issues']}`")
    return "\n".join(lines) + "\n"


def build_preview_audit(
    *,
    metrics_path: Path,
    build_manifest_path: Path,
    shadow_compare_path: Path | None = None,
) -> dict[str, Any]:
    metrics_payload = _load_json(metrics_path)
    build_manifest = _load_json(build_manifest_path)
    join_summary = _join_coverage_summary(build_manifest)

    targets: dict[str, dict[str, Any]] = {}
    for dataset_key, metrics_key in TARGET_METRICS_KEYS.items():
        metrics = dict(metrics_payload.get(metrics_key, {}) or {})
        metrics["leakage"] = _leakage_summary(metrics)
        metrics["feature_tier"] = _feature_tier_summary(metrics)
        targets[dataset_key] = metrics

    shadow_compare = _shadow_compare_summary(shadow_compare_path)
    promotion_gate = _promotion_gate_summary(
        join_summary=join_summary,
        per_target=targets,
        shadow_compare=shadow_compare,
    )
    return {
        "created_at": datetime.now().astimezone().isoformat(),
        "report_version": "semantic_preview_audit_v2",
        "metrics_path": str(metrics_path),
        "build_manifest_path": str(build_manifest_path),
        "join_coverage": join_summary,
        "targets": targets,
        "shadow_compare": shadow_compare,
        "promotion_gate": promotion_gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build semantic preview audit report from metrics and dataset build manifest.")
    parser.add_argument("--metrics-path", required=True, help="Path to semantic preview metrics.json")
    parser.add_argument("--build-manifest", required=True, help="Path to semantic_v1 dataset build manifest json")
    parser.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR), help="Directory to write JSON/MD reports")
    parser.add_argument(
        "--shadow-compare-path",
        default="",
        help="Optional semantic shadow compare report path; when omitted the latest report in analysis-dir is used if present.",
    )
    args = parser.parse_args()

    metrics_path = _resolve_path(args.metrics_path)
    build_manifest_path = _resolve_path(args.build_manifest)
    analysis_dir = _resolve_path(args.analysis_dir, DEFAULT_ANALYSIS_DIR)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    shadow_compare_path = (
        _resolve_path(args.shadow_compare_path)
        if str(args.shadow_compare_path or "").strip()
        else _resolve_latest_matching_path(analysis_dir, SHADOW_COMPARE_GLOB)
    )

    report = build_preview_audit(
        metrics_path=metrics_path,
        build_manifest_path=build_manifest_path,
        shadow_compare_path=shadow_compare_path,
    )
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

    json_path = analysis_dir / f"semantic_preview_audit_{timestamp}.json"
    md_path = analysis_dir / f"semantic_preview_audit_{timestamp}.md"
    latest_json_path = analysis_dir / "semantic_preview_audit_latest.json"
    latest_md_path = analysis_dir / "semantic_preview_audit_latest.md"

    json_text = json.dumps(report, ensure_ascii=False, indent=2)
    md_text = _render_markdown(report)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    latest_json_path.write_text(json_text, encoding="utf-8")
    latest_md_path.write_text(md_text, encoding="utf-8")

    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "latest_json_path": str(latest_json_path),
                "latest_md_path": str(latest_md_path),
                "promotion_gate": report["promotion_gate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
