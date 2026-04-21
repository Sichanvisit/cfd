from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.core.config import Config
from backend.services.apply_executor import ApplyExecutor
from backend.services.approval_loop import ApprovalLoop
from backend.services.checkpoint_improvement_pa8_apply_handlers import (
    register_default_pa8_apply_handlers,
)
from backend.services.checkpoint_improvement_pa9_apply_handlers import (
    register_default_pa9_apply_handlers,
)
from backend.services.event_bus import EventBus
from backend.services.state25_weight_patch_apply_handlers import (
    register_default_state25_weight_patch_apply_handlers,
)
from backend.services.state25_threshold_patch_apply_handlers import (
    register_default_state25_threshold_patch_apply_handlers,
)
from backend.services.telegram_approval_bridge import TelegramApprovalBridge
from backend.services.telegram_notification_hub import TelegramNotificationHub
from backend.services.telegram_state_store import TelegramStateStore
from backend.services.telegram_update_poller import TelegramUpdatePoller


CHECKPOINT_IMPROVEMENT_TELEGRAM_RUNTIME_CONTRACT_VERSION = (
    "checkpoint_improvement_telegram_runtime_v0"
)


@dataclass(slots=True)
class CheckpointImprovementTelegramRuntime:
    telegram_state_store: TelegramStateStore
    event_bus: EventBus
    approval_loop: ApprovalLoop
    apply_executor: ApplyExecutor
    notification_hub: TelegramNotificationHub
    telegram_approval_bridge: TelegramApprovalBridge
    telegram_update_poller: TelegramUpdatePoller


def build_checkpoint_improvement_telegram_runtime(
    *,
    db_path: str | Path | None = None,
    auto_subscribe: bool = True,
) -> CheckpointImprovementTelegramRuntime:
    store = TelegramStateStore(db_path=db_path)
    event_bus = EventBus()
    approval_loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=event_bus,
        allowed_user_ids=getattr(Config, "TG_ALLOWED_USER_IDS", ()),
    )
    apply_executor = ApplyExecutor(telegram_state_store=store)
    register_default_pa8_apply_handlers(apply_executor)
    register_default_pa9_apply_handlers(apply_executor)
    register_default_state25_weight_patch_apply_handlers(apply_executor)
    register_default_state25_threshold_patch_apply_handlers(apply_executor)
    notification_hub = TelegramNotificationHub(telegram_state_store=store)
    bridge = TelegramApprovalBridge(
        telegram_state_store=store,
        event_bus=event_bus,
        approval_loop=approval_loop,
        apply_executor=apply_executor,
        dispatch_handler=notification_hub.handle_dispatch_record,
        auto_subscribe=auto_subscribe,
    )
    update_poller = TelegramUpdatePoller(
        telegram_state_store=store,
        telegram_approval_bridge=bridge,
        telegram_notification_hub=notification_hub,
    )
    return CheckpointImprovementTelegramRuntime(
        telegram_state_store=store,
        event_bus=event_bus,
        approval_loop=approval_loop,
        apply_executor=apply_executor,
        notification_hub=notification_hub,
        telegram_approval_bridge=bridge,
        telegram_update_poller=update_poller,
    )
