"""
Entry setup detector reduced to a setup namer.
"""

from __future__ import annotations

from backend.domain.decision_models import DecisionContext, SetupCandidate
from backend.services.consumer_contract import (
    resolve_consumer_handoff_payload,
    resolve_consumer_observe_confirm_input,
    resolve_setup_mapping,
)


class SetupDetector:
    @staticmethod
    def _side(value: str) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _observe_confirm_shadow(context: DecisionContext) -> dict[str, object]:
        handoff = resolve_consumer_handoff_payload(
            context,
            market_mode=getattr(context, "market_mode", ""),
            box_state=getattr(context, "box_state", ""),
            bb_state=getattr(context, "bb_state", ""),
        )
        observe_confirm = handoff.get("observe_confirm") if isinstance(handoff, dict) else None
        if isinstance(observe_confirm, dict):
            return dict(observe_confirm)
        return dict(resolve_consumer_observe_confirm_input(context) or {})

    @staticmethod
    def _matched(
        *,
        setup_id: str,
        side: str,
        entry_quality: float,
        reason: str,
        mapping: dict[str, object] | None = None,
    ) -> SetupCandidate:
        metadata = {"reason": str(reason or "")}
        if isinstance(mapping, dict):
            metadata["setup_mapping_contract"] = str(mapping.get("mapping_contract_version", "") or "")
            metadata["setup_mapping_rule_id"] = str(mapping.get("rule_id", "") or "")
            metadata["setup_mapping_specialized"] = bool(mapping.get("specialized", False))
            metadata["setup_mapping_specialization_basis"] = list(mapping.get("specialization_basis", []) or [])
        return SetupCandidate(
            setup_id=str(setup_id or ""),
            side=str(side or "").upper(),
            status="matched",
            trigger_state="READY",
            entry_quality=float(entry_quality),
            score=float(entry_quality),
            metadata=metadata,
        )

    @staticmethod
    def _rejected(*, side: str, trigger_state: str, reason: str) -> SetupCandidate:
        return SetupCandidate(
            setup_id="",
            side=str(side or "").upper(),
            status="rejected",
            trigger_state=str(trigger_state or "UNKNOWN").upper(),
            entry_quality=0.0,
            score=0.0,
            metadata={"reason": str(reason or "")},
        )

    @staticmethod
    def _entry_quality_from_confidence(shadow_confidence: float) -> float:
        return max(0.0, min(1.0, float(shadow_confidence or 0.0)))

    @classmethod
    def _resolve_naming_inputs(cls, *, context: DecisionContext, action: str) -> tuple[str, str, str, float]:
        shadow = cls._observe_confirm_shadow(context)
        if not shadow:
            return "", "", "", 0.0
        handoff_side = cls._side(shadow.get("side", ""))
        if handoff_side not in {"BUY", "SELL"}:
            handoff_action = cls._side(shadow.get("action", ""))
            handoff_side = handoff_action if handoff_action in {"BUY", "SELL"} else ""
        action_side = cls._side(action)
        side = handoff_side or action_side
        archetype_id = str(shadow.get("archetype_id", "") or "").strip().lower()
        shadow_reason = str(shadow.get("reason", "") or "").strip() or "setup_naming_unknown_reason"
        shadow_conf = float(shadow.get("confidence", 0.0) or 0.0)
        return archetype_id, side, shadow_reason, shadow_conf

    def detect_entry_setup(
        self,
        *,
        context: DecisionContext,
        action: str,
        h1_gap: float,
        m1_gap: float,
        score_gap: float,
    ) -> SetupCandidate:
        del h1_gap, m1_gap, score_gap
        action_side = self._side(action)
        if action_side not in {"BUY", "SELL"}:
            return self._rejected(side=action_side, trigger_state="UNKNOWN", reason="invalid_action")

        shadow = self._observe_confirm_shadow(context)
        if not shadow:
            return self._rejected(side=action_side, trigger_state="UNKNOWN", reason="observe_confirm_missing")

        shadow_archetype, side, shadow_reason, shadow_conf = self._resolve_naming_inputs(context=context, action=action)
        if side not in {"BUY", "SELL"}:
            return self._rejected(side=action_side, trigger_state="UNKNOWN", reason="setup_naming_missing_side")
        if side != action_side:
            return self._rejected(side=action_side, trigger_state="UNKNOWN", reason=f"setup_naming_side_mismatch_{side.lower()}")
        if not shadow_archetype:
            return self._rejected(side=side, trigger_state="UNKNOWN", reason="setup_naming_missing_archetype")

        mapping = resolve_setup_mapping(
            archetype_id=shadow_archetype,
            side=side,
            market_mode=getattr(context, "market_mode", ""),
            reason=shadow_reason,
        )
        setup_id = str(mapping.get("setup_id", "") or "")
        if not setup_id:
            return self._rejected(
                side=side,
                trigger_state="UNKNOWN",
                reason=f"setup_naming_unmapped_{shadow_archetype.lower()}",
            )

        return self._matched(
            setup_id=setup_id,
            side=side,
            entry_quality=self._entry_quality_from_confidence(shadow_confidence=shadow_conf),
            reason=f"shadow_{shadow_reason}",
            mapping=mapping,
        )
