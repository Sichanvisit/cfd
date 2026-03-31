from __future__ import annotations

from backend.trading.engine.core.models import (
    EngineContext,
    POSITION_FALLBACK_LABELS,
    POSITION_PRIMARY_AXES,
    POSITION_SECONDARY_AXES,
    PositionSnapshot,
    PositionVector,
)
from backend.trading.engine.position.bb_position import compute_bb20_position, compute_bb44_position
from backend.trading.engine.position.box_position import compute_box_position
from backend.trading.engine.position.interpretation import summarize_position
from backend.trading.engine.position.ma_position import compute_ma_positions
from backend.trading.engine.position.size_profile import compute_position_scale_metadata
from backend.trading.engine.position.sr_position import compute_sr_position
from backend.trading.engine.position.trendline_position import compute_trendline_position


def build_position_vector(ctx: EngineContext) -> PositionVector:
    ma_positions = compute_ma_positions(ctx)
    position_scale = compute_position_scale_metadata(ctx)
    trendline_map = dict((ctx.metadata or {}).get("mtf_trendline_map_v1", {}) or {})
    trendline_flat_keys = (
        "x_tl_m1",
        "x_tl_m15",
        "x_tl_h1",
        "x_tl_h4",
        "tl_proximity_m1",
        "tl_proximity_m15",
        "tl_proximity_h1",
        "tl_proximity_h4",
        "tl_side_m1",
        "tl_side_m15",
        "tl_side_h1",
        "tl_side_h4",
        "tl_kind_m1",
        "tl_kind_m15",
        "tl_kind_h1",
        "tl_kind_h4",
    )
    return PositionVector(
        x_box=compute_box_position(ctx),
        x_bb20=compute_bb20_position(ctx),
        x_bb44=compute_bb44_position(ctx),
        x_ma20=float(ma_positions["x_ma20"]),
        x_ma60=float(ma_positions["x_ma60"]),
        x_sr=compute_sr_position(ctx),
        x_trendline=compute_trendline_position(ctx),
        metadata={
            "symbol": ctx.symbol,
            "market_mode": ctx.market_mode,
            "direction_policy": ctx.direction_policy,
            "box_state": ctx.box_state,
            "bb_state": ctx.bb_state,
            "raw_box_state": ctx.box_state,
            "raw_bb_state": ctx.bb_state,
            "position_primary_axes": list(POSITION_PRIMARY_AXES),
            "position_secondary_axes": list(POSITION_SECONDARY_AXES),
            "position_fallback_labels": list(POSITION_FALLBACK_LABELS),
            "position_scale": position_scale,
            "mtf_ma_big_map_v1": dict((ctx.metadata or {}).get("mtf_ma_big_map_v1", {}) or {}),
            "mtf_trendline_map_v1": trendline_map,
            **{key: trendline_map.get(key) for key in trendline_flat_keys if key in trendline_map},
        },
    )


def build_position_snapshot(ctx: EngineContext) -> PositionSnapshot:
    return summarize_position(build_position_vector(ctx))
