from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_checkpoint_pa8_symbol_action_canary_bundle import main


def test_build_checkpoint_pa8_symbol_action_canary_bundle_writes_btcusd_outputs(tmp_path: Path) -> None:
    resolved_path = tmp_path / "resolved.csv"
    pa8_packet_path = tmp_path / "pa8_packet.json"
    symbol_review_path = tmp_path / "btc_review.json"

    with resolved_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "checkpoint_id",
                "surface_name",
                "checkpoint_type",
                "checkpoint_rule_family_hint",
                "runtime_proxy_management_action_label",
                "hindsight_best_management_action_label",
                "unrealized_pnl_state",
                "source",
                "position_side",
                "current_profit",
                "runtime_hold_quality_score",
                "runtime_partial_exit_ev",
                "runtime_full_exit_risk",
                "runtime_continuation_odds",
                "runtime_reversal_odds",
                "giveback_ratio",
                "generated_at",
            ],
        )
        writer.writeheader()
        for index in range(55):
            writer.writerow(
                {
                    "symbol": "BTCUSD",
                    "checkpoint_id": f"CP{index}",
                    "surface_name": "protective_exit_surface",
                    "checkpoint_type": "RECLAIM_CHECK",
                    "checkpoint_rule_family_hint": "active_open_loss",
                    "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                    "hindsight_best_management_action_label": "WAIT",
                    "unrealized_pnl_state": "OPEN_LOSS",
                    "source": "exit_manage_hold",
                    "position_side": "SELL",
                    "current_profit": "-0.30",
                    "runtime_hold_quality_score": "0.39",
                    "runtime_partial_exit_ev": "0.37",
                    "runtime_full_exit_risk": "0.61",
                    "runtime_continuation_odds": "0.87",
                    "runtime_reversal_odds": "0.69",
                    "giveback_ratio": "0.99",
                    "generated_at": "",
                }
            )

    pa8_packet_path.write_text(
        json.dumps(
            {
                "summary": {"action_baseline_review_ready": True},
                "symbol_rows": [{"symbol": "BTCUSD", "review_state": "PRIMARY_REVIEW"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    symbol_review_path.write_text(
        json.dumps({"summary": {"review_result": "narrow_wait_boundary_candidate_identified"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--symbol",
            "BTCUSD",
            "--resolved-dataset-path",
            str(resolved_path),
            "--pa8-action-review-packet-path",
            str(pa8_packet_path),
            "--symbol-review-path",
            str(symbol_review_path),
            "--approval-decision",
            "APPROVE",
        ]
    )

    assert exit_code == 0
    activation_apply = Path(
        r"C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_btcusd_action_only_canary_activation_apply_latest.json"
    )
    payload = json.loads(activation_apply.read_text(encoding="utf-8"))
    assert payload["summary"]["active"] is True
