# 한글 설명: runtime_status 응답의 UI 카드 필드 매핑 정의를 분리한 모듈입니다.
"""UI card field map for runtime status response."""

from __future__ import annotations


def build_ui_card_field_map():
    return {
        "runtime_status_payload_path": "status",
        "cards": {
            "api_status": {
                "description": "API status card reads runtimeStatus root object",
                "source": "response.status",
                "frontend_read": "data.runtimeStatus",
            },
            "exit_metrics_summary": {
                "description": "Exit metrics summary counters",
                "source": "response.status.exit_metrics",
                "frontend_read": "data.runtimeStatus.exit_metrics",
            },
            "exit_metric_thresholds": {
                "description": "Exit metric good/warn/bad thresholds",
                "source": "response.status.exit_metric_thresholds",
                "frontend_read": "data.runtimeStatus.exit_metric_thresholds",
            },
            "exit_execution_profile": {
                "description": "Execution profile configured/effective/regime",
                "source": "response.status.exit_execution_profile",
                "frontend_read": "data.runtimeStatus.exit_execution_profile",
            },
            "stage_selection_distribution": {
                "description": "Stage selection distribution short/mid/long",
                "source": "response.status.stage_selection_distribution",
                "frontend_read": "data.runtimeStatus.stage_selection_distribution",
            },
            "stage_winloss_snapshot": {
                "description": "Stage-level winloss snapshot",
                "source": "response.status.stage_winloss_snapshot",
                "frontend_read": "data.runtimeStatus.stage_winloss_snapshot",
            },
            "invalid_learning_sample_count": {
                "description": "Invalid learning sample count",
                "source": "response.status.invalid_learning_sample_count",
                "frontend_read": "data.runtimeStatus.invalid_learning_sample_count",
            },
            "label_clip_applied_count": {
                "description": "Label clip applied count",
                "source": "response.status.label_clip_applied_count",
                "frontend_read": "data.runtimeStatus.label_clip_applied_count",
            },
            "net_vs_gross_gap_avg": {
                "description": "Average net-vs-gross gap",
                "source": "response.status.net_vs_gross_gap_avg",
                "frontend_read": "data.runtimeStatus.net_vs_gross_gap_avg",
            },
            "expectancy_by_symbol": {
                "description": "Expectancy decomposition by symbol",
                "source": "response.status.expectancy_by_symbol",
                "frontend_read": "data.runtimeStatus.expectancy_by_symbol",
            },
            "expectancy_by_regime": {
                "description": "Expectancy decomposition by regime",
                "source": "response.status.expectancy_by_regime",
                "frontend_read": "data.runtimeStatus.expectancy_by_regime",
            },
            "expectancy_by_hour_bucket": {
                "description": "Expectancy decomposition by hour bucket",
                "source": "response.status.expectancy_by_hour_bucket",
                "frontend_read": "data.runtimeStatus.expectancy_by_hour_bucket",
            },
            "runtime_warning_counters": {
                "description": "Runtime warning counters",
                "source": "response.status.runtime_warning_counters",
                "frontend_read": "data.runtimeStatus.runtime_warning_counters",
            },
            "api_latency_snapshot": {
                "description": "API latency snapshot",
                "source": "response.status.api_latency_snapshot",
                "frontend_read": "data.runtimeStatus.api_latency_snapshot",
            },
            "learning_fallback_summary": {
                "description": "Learning fallback summary",
                "source": "response.status.learning_fallback_summary",
                "frontend_read": "data.runtimeStatus.learning_fallback_summary",
            },
            "d_execution_state": {
                "description": "Phase D execution state",
                "source": "response.status.d_execution_state",
                "frontend_read": "data.runtimeStatus.d_execution_state",
            },
            "d_acceptance_snapshot": {
                "description": "Phase D acceptance snapshot",
                "source": "response.status.d_acceptance_snapshot",
                "frontend_read": "data.runtimeStatus.d_acceptance_snapshot",
            },
            "policy_snapshot": {
                "description": "Policy snapshot and fallback flow",
                "source": "response.status.policy_snapshot",
                "frontend_read": "data.runtimeStatus.policy_snapshot",
            },
            "sqlite_mirror_status": {
                "description": "CSV to SQLite mirror health",
                "source": "response.status.sqlite_mirror_status",
                "frontend_read": "data.runtimeStatus.sqlite_mirror_status",
            },
            "exit_blend_runtime": {
                "description": "Rule-model blend runtime status",
                "source": "response.status.exit_blend_runtime",
                "frontend_read": "data.runtimeStatus.exit_blend_runtime",
            },
            "alerts": {
                "description": "Runtime alerts pass/warn/fail",
                "source": "response.status.alerts",
                "frontend_read": "data.runtimeStatus.alerts",
            },
            "symbol_policy_snapshot": {
                "description": "Per-symbol policy snapshot",
                "source": "response.status.symbol_policy_snapshot",
                "frontend_read": "data.runtimeStatus.symbol_policy_snapshot",
            },
            "symbol_default_snapshot": {
                "description": "Per-symbol default snapshot",
                "source": "response.status.symbol_default_snapshot",
                "frontend_read": "data.runtimeStatus.symbol_default_snapshot",
            },
            "symbol_applied_vs_default": {
                "description": "Per-symbol applied-vs-default comparison",
                "source": "response.status.symbol_applied_vs_default",
                "frontend_read": "data.runtimeStatus.symbol_applied_vs_default",
            },
            "symbol_blend_runtime": {
                "description": "Per-symbol blend runtime",
                "source": "response.status.symbol_blend_runtime",
                "frontend_read": "data.runtimeStatus.symbol_blend_runtime",
            },
            "symbol_learning_split": {
                "description": "C2 per-symbol learning split status",
                "source": "response.status.symbol_learning_split",
                "frontend_read": "data.runtimeStatus.symbol_learning_split",
            },
            "learning_apply_loop": {
                "description": "C1 learning/apply loop status",
                "source": "response.status.learning_apply_loop",
                "frontend_read": "data.runtimeStatus.learning_apply_loop",
            },
            "kpi_evaluation": {
                "description": "Runtime KPI evaluation pass/warn/fail",
                "source": "response.status.kpi_evaluation",
                "frontend_read": "data.runtimeStatus.kpi_evaluation",
            },
            "current_market_view": {
                "description": "Per-symbol current market interpretation cards and logs",
                "source": "response.status.current_market_view",
                "frontend_read": "data.runtimeStatus.current_market_view",
            },
        },
    }
