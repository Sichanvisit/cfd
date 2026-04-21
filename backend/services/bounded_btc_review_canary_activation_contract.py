"""Build bounded activation contract for BTC review canary after signoff prep."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


BOUNDED_BTC_REVIEW_CANARY_ACTIVATION_CONTRACT_VERSION = "bounded_btc_review_canary_activation_contract_v1"

BOUNDED_BTC_REVIEW_CANARY_ACTIVATION_CONTRACT_COLUMNS = [
    "contract_id",
    "market_family",
    "surface_name",
    "contract_status",
    "activation_mode",
    "manual_signoff_required",
    "allow_live_activation",
    "symbol_allowlist",
    "surface_allowlist",
    "size_multiplier_cap",
    "performance_guard",
    "rollback_guard",
    "activation_checklist",
    "blocking_reason",
    "recommended_next_step",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_bounded_btc_review_canary_activation_contract(
    *,
    btc_initial_entry_canary_signoff_packet_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    packet_frame = _to_frame(btc_initial_entry_canary_signoff_packet_payload)
    if packet_frame.empty:
        empty = pd.DataFrame(columns=BOUNDED_BTC_REVIEW_CANARY_ACTIVATION_CONTRACT_COLUMNS)
        return empty, {
            "bounded_btc_review_canary_activation_contract_version": BOUNDED_BTC_REVIEW_CANARY_ACTIVATION_CONTRACT_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "pending_manual_signoff_count": 0,
            "recommended_next_action": "await_btc_signoff_packet",
        }

    rows: list[dict[str, Any]] = []
    for packet in packet_frame.to_dict(orient="records"):
        if str(packet.get("market_family", "")).upper() != "BTCUSD":
            continue
        signoff_state = str(packet.get("signoff_state", ""))
        packet_status = str(packet.get("packet_status", ""))
        allow_live_activation = signoff_state == "MANUAL_SIGNOFF_APPROVED" and packet_status == "REVIEW_PACKET_READY"
        blocking_reason = "" if allow_live_activation else "manual_signoff_pending"
        rows.append(
            {
                "contract_id": "bounded_activation_contract::BTCUSD::initial_entry_surface",
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "contract_status": "PENDING_MANUAL_SIGNOFF" if not allow_live_activation else "CAN_ACTIVATE",
                "activation_mode": "review_canary_bounded",
                "manual_signoff_required": True,
                "allow_live_activation": allow_live_activation,
                "symbol_allowlist": _stable_json(["BTCUSD"]),
                "surface_allowlist": _stable_json(["initial_entry_surface"]),
                "size_multiplier_cap": 0.25,
                "performance_guard": _stable_json(
                    {
                        "max_elapsed_ms": 200.0,
                        "require_baseline_locked": True,
                        "require_regression_watch_healthy": True,
                    }
                ),
                "rollback_guard": _stable_json(
                    {
                        "rollback_on_regression_over_200ms": True,
                        "rollback_on_false_positive_cluster": True,
                        "rollback_mode": "disable_canary_and_return_to_review_only",
                    }
                ),
                "activation_checklist": _stable_json(
                    [
                        "manual signoff approved",
                        "live override remains disabled outside canary scope",
                        "btc only allowlist remains active",
                        "size cap remains at 0.25x",
                        "entry performance watch remains healthy",
                    ]
                ),
                "blocking_reason": blocking_reason,
                "recommended_next_step": (
                    "activate_btc_review_canary_bounded"
                    if allow_live_activation
                    else "manual_signoff_btcusd_initial_entry_review_canary"
                ),
            }
        )

    frame = pd.DataFrame(rows, columns=BOUNDED_BTC_REVIEW_CANARY_ACTIVATION_CONTRACT_COLUMNS)
    summary = {
        "bounded_btc_review_canary_activation_contract_version": BOUNDED_BTC_REVIEW_CANARY_ACTIVATION_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "pending_manual_signoff_count": int((frame["contract_status"] == "PENDING_MANUAL_SIGNOFF").sum()) if not frame.empty else 0,
        "recommended_next_action": (
            "manual_signoff_before_btc_canary_activation"
            if not frame.empty and (frame["allow_live_activation"] == False).any()
            else "await_btc_signoff_packet"
        ),
    }
    return frame, summary


def render_bounded_btc_review_canary_activation_contract_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Bounded BTC Review Canary Activation Contract",
        "",
        f"- version: `{summary.get('bounded_btc_review_canary_activation_contract_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- pending_manual_signoff_count: `{summary.get('pending_manual_signoff_count', 0)}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
