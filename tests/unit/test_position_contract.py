from pathlib import Path

from dataclasses import fields

from backend.trading.engine.core.context import build_engine_context
from backend.trading.engine.core.models import (
    POSITION_FALLBACK_LABELS,
    POSITION_ALIGNMENT_LABELS,
    POSITION_BIAS_LABELS,
    POSITION_CONFLICT_LABELS,
    POSITION_DOMINANCE_LABELS,
    POSITION_PRIMARY_LABELS,
    POSITION_PRIMARY_AXES,
    POSITION_SECONDARY_CONTEXT_LABELS,
    POSITION_SECONDARY_AXES,
    POSITION_ZONE_LABELS,
    PositionVector,
)
from backend.trading.engine.position import (
    build_position_energy_snapshot,
    build_position_interpretation,
    build_position_snapshot,
    build_position_zones,
)


def _build_ctx():
    return build_engine_context(
        symbol="BTCUSD",
        price=95.0,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        ma20=99.0,
        ma60=98.0,
        ma120=97.0,
        ma240=96.0,
        ma480=95.0,
        support=90.0,
        resistance=110.0,
        volatility_scale=10.0,
    )


def test_position_snapshot_returns_position_only_outputs():
    snapshot = build_position_snapshot(_build_ctx())

    assert round(snapshot.vector.x_box, 2) == -0.50
    assert snapshot.zones.box_zone == "LOWER"
    assert snapshot.zones.bb20_zone == "LOWER"
    assert snapshot.zones.ma20_zone == "LOWER"
    assert snapshot.zones.ma60_zone == "LOWER"
    assert snapshot.zones.sr_zone == "LOWER"
    assert snapshot.zones.trendline_zone == "MIDDLE"
    assert snapshot.interpretation.primary_label == "LOWER_BIAS"
    assert snapshot.interpretation.bias_label == "LOWER_BIAS"
    assert snapshot.interpretation.secondary_context_label == "LOWER_CONTEXT"
    assert "BUY" not in snapshot.interpretation.primary_label
    assert "SELL" not in snapshot.interpretation.primary_label
    assert snapshot.energy.lower_position_force > snapshot.energy.upper_position_force
    assert not hasattr(snapshot.energy, "buy_position_force")
    assert not hasattr(snapshot.energy, "sell_position_force")
    assert snapshot.vector.metadata["position_primary_axes"] == list(POSITION_PRIMARY_AXES)
    assert snapshot.vector.metadata["position_secondary_axes"] == list(POSITION_SECONDARY_AXES)
    assert snapshot.vector.metadata["position_fallback_labels"] == list(POSITION_FALLBACK_LABELS)
    assert snapshot.vector.metadata["position_scale"]["version"] == "v1_position_scale"
    assert snapshot.vector.metadata["position_scale"]["box_height"] == 20.0
    assert snapshot.vector.metadata["position_scale"]["bb20_width"] == 20.0
    assert snapshot.vector.metadata["position_scale"]["bb44_width"] == 24.0
    assert snapshot.vector.metadata["position_scale"]["box_size_state"] == "WIDE"
    assert snapshot.vector.metadata["position_scale"]["bb20_width_state"] == "EXPANDED"
    assert snapshot.vector.metadata["position_scale"]["map_size_state"] == "EXPANDED"
    assert snapshot.interpretation.metadata["zone_version"] == "v2_standardized"
    assert snapshot.interpretation.metadata["zone_specs"]["x_box"]["middle"] == 0.18
    assert snapshot.interpretation.metadata["position_scale"]["inner_outer_band_ratio"] == 20.0 / 24.0
    assert snapshot.zones.metadata["zone_labels"] == list(POSITION_ZONE_LABELS)
    assert snapshot.zones.metadata["zone_sources"]["x_box"] == "COORD"
    assert snapshot.interpretation.metadata["primary_axes"]["x_box"] == snapshot.vector.x_box
    assert snapshot.interpretation.metadata["secondary_axes"]["x_sr"] == snapshot.vector.x_sr
    assert snapshot.interpretation.metadata["secondary_zones"]["x_ma20"] == snapshot.zones.ma20_zone
    assert snapshot.interpretation.metadata["secondary_context_label"] == "LOWER_CONTEXT"
    assert snapshot.interpretation.metadata["raw_alignment_label"] == "ALIGNED_LOWER_WEAK"
    assert snapshot.interpretation.metadata["alignment_softening"]["downgraded"] is True
    assert snapshot.interpretation.metadata["label_contract"]["alignment_labels"] == list(POSITION_ALIGNMENT_LABELS)
    assert snapshot.interpretation.metadata["label_contract"]["bias_labels"] == list(POSITION_BIAS_LABELS)
    assert snapshot.interpretation.metadata["label_contract"]["conflict_labels"] == list(POSITION_CONFLICT_LABELS)
    assert snapshot.interpretation.metadata["label_contract"]["dominance_labels"] == list(POSITION_DOMINANCE_LABELS)
    assert snapshot.interpretation.metadata["label_contract"]["primary_labels"] == list(POSITION_PRIMARY_LABELS)
    assert snapshot.interpretation.metadata["label_contract"]["secondary_context_labels"] == list(POSITION_SECONDARY_CONTEXT_LABELS)
    assert round(snapshot.energy.metadata["position_scale"]["expansion_score"], 4) == 0.5278
    assert snapshot.energy.metadata["secondary_lower_force"] > snapshot.energy.metadata["secondary_upper_force"]


def test_position_zones_use_raw_labels_only_as_near_zero_fallback():
    position = PositionVector(
        x_box=0.02,
        x_bb20=-0.01,
        x_bb44=0.03,
        metadata={"box_state": "UPPER", "bb_state": "LOWER_EDGE"},
    )

    zones = build_position_zones(position)

    assert zones.box_zone == "UPPER"
    assert zones.bb20_zone == "LOWER_EDGE"
    assert zones.bb44_zone == "MIDDLE"
    assert zones.metadata["zone_sources"]["x_box"] == "RAW_FALLBACK"
    assert zones.metadata["zone_sources"]["x_bb20"] == "RAW_FALLBACK"
    assert zones.metadata["zone_sources"]["x_bb44"] == "COORD"
    assert zones.metadata["raw_fallback_eligible"] is True
    assert zones.metadata["raw_fallback_ambiguity"] == {"x_box": True, "x_bb20": True, "x_bb44": True}

    interpretation = build_position_interpretation(position, zones=zones)
    assert interpretation.primary_label == "CONFLICT_BOX_UPPER_BB20_LOWER"
    assert interpretation.alignment_label == ""
    assert interpretation.conflict_kind == "CONFLICT_BOX_UPPER_BB20_LOWER"
    assert interpretation.used_raw_fallback is True
    assert interpretation.metadata["raw_fallback_eligible"] is True


def test_position_raw_labels_are_ignored_when_any_primary_axis_is_clear():
    position = PositionVector(
        x_box=0.19,
        x_bb20=-0.01,
        x_bb44=0.03,
        metadata={"box_state": "LOWER", "bb_state": "UPPER_EDGE"},
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert zones.box_zone == "UPPER"
    assert zones.bb20_zone == "MIDDLE"
    assert zones.bb44_zone == "MIDDLE"
    assert zones.metadata["zone_sources"]["x_box"] == "COORD"
    assert zones.metadata["zone_sources"]["x_bb20"] == "COORD"
    assert zones.metadata["raw_fallback_eligible"] is False
    assert zones.metadata["raw_fallback_ambiguity"] == {"x_box": False, "x_bb20": True, "x_bb44": True}
    assert interpretation.used_raw_fallback is False
    assert interpretation.primary_label == "UNRESOLVED_POSITION"
    assert interpretation.metadata["raw_fallback_eligible"] is False


def test_position_interpretation_promotes_middle_upper_transition_to_bias():
    position = PositionVector(
        x_box=-0.06,
        x_bb20=0.36,
        x_bb44=0.19,
        x_ma20=0.41,
        x_ma60=0.21,
        x_sr=-0.07,
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert zones.box_zone == "MIDDLE"
    assert zones.bb20_zone == "UPPER"
    assert zones.bb44_zone == "UPPER"
    assert interpretation.bias_label == "MIDDLE_UPPER_BIAS"
    assert interpretation.primary_label == "MIDDLE_UPPER_BIAS"
    assert interpretation.secondary_context_label == "UPPER_CONTEXT"
    assert interpretation.metadata["primary_side_votes"] == {"UPPER": 2, "LOWER": 0, "MIDDLE": 1}


def test_position_interpretation_promotes_middle_lower_transition_to_bias():
    position = PositionVector(
        x_box=0.06,
        x_bb20=-0.36,
        x_bb44=-0.19,
        x_ma20=-0.41,
        x_ma60=-0.21,
        x_sr=0.07,
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert zones.box_zone == "MIDDLE"
    assert zones.bb20_zone == "LOWER"
    assert zones.bb44_zone == "LOWER"
    assert interpretation.bias_label == "MIDDLE_LOWER_BIAS"
    assert interpretation.primary_label == "MIDDLE_LOWER_BIAS"
    assert interpretation.secondary_context_label == "LOWER_CONTEXT"
    assert interpretation.metadata["primary_side_votes"] == {"UPPER": 0, "LOWER": 2, "MIDDLE": 1}


def test_position_interpretation_keeps_one_sided_single_axis_cases_unresolved():
    position = PositionVector(
        x_box=0.24,
        x_bb20=0.05,
        x_bb44=0.02,
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert zones.box_zone == "UPPER"
    assert zones.bb20_zone == "MIDDLE"
    assert zones.bb44_zone == "MIDDLE"
    assert interpretation.bias_label == ""
    assert interpretation.primary_label == "UNRESOLVED_POSITION"
    assert interpretation.metadata["primary_side_votes"] == {"UPPER": 1, "LOWER": 0, "MIDDLE": 2}


def test_position_interpretation_promotes_non_conflicting_two_of_three_to_side_bias():
    upper_position = PositionVector(
        x_box=0.24,
        x_bb20=0.05,
        x_bb44=0.19,
    )
    upper_interpretation = build_position_interpretation(upper_position, zones=build_position_zones(upper_position))
    assert upper_interpretation.bias_label == "UPPER_BIAS"
    assert upper_interpretation.primary_label == "UPPER_BIAS"

    lower_position = PositionVector(
        x_box=-0.24,
        x_bb20=-0.05,
        x_bb44=-0.19,
    )
    lower_interpretation = build_position_interpretation(lower_position, zones=build_position_zones(lower_position))
    assert lower_interpretation.bias_label == "LOWER_BIAS"
    assert lower_interpretation.primary_label == "LOWER_BIAS"


def test_position_interpretation_softens_weak_alignment_when_composite_is_not_edge_like():
    position = PositionVector(
        x_box=-0.42,
        x_bb20=-0.38,
        x_bb44=-0.16,
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert zones.box_zone == "LOWER"
    assert zones.bb20_zone == "LOWER"
    assert zones.bb44_zone == "MIDDLE"
    assert interpretation.metadata["raw_alignment_label"] == "ALIGNED_LOWER_WEAK"
    assert interpretation.metadata["alignment_softening"]["downgraded"] is True
    assert interpretation.primary_label == "LOWER_BIAS"
    assert interpretation.bias_label == "LOWER_BIAS"


def test_position_interpretation_softens_weak_alignment_without_bb44_side_support():
    position = PositionVector(
        x_box=-0.91,
        x_bb20=-0.66,
        x_bb44=-0.10,
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert zones.box_zone == "LOWER_EDGE"
    assert zones.bb20_zone == "LOWER"
    assert zones.bb44_zone == "MIDDLE"
    assert interpretation.metadata["raw_alignment_label"] == "ALIGNED_LOWER_WEAK"
    assert interpretation.metadata["alignment_softening"]["downgraded"] is True
    assert interpretation.metadata["alignment_softening"]["reason"] == "weak_alignment_requires_bb44_side_support"
    assert interpretation.primary_label == "LOWER_BIAS"
    assert interpretation.bias_label == "LOWER_BIAS"


def test_position_zone_boundaries_are_standardized_for_primary_axes():
    cases = [
        (-1.00, "BELOW"),
        (-0.75, "LOWER_EDGE"),
        (-0.74, "LOWER"),
        (-0.18, "MIDDLE"),
        (0.00, "MIDDLE"),
        (0.18, "MIDDLE"),
        (0.19, "UPPER"),
        (0.75, "UPPER_EDGE"),
        (0.99, "UPPER_EDGE"),
        (1.00, "ABOVE"),
    ]

    for axis_name in POSITION_PRIMARY_AXES:
        for value, expected_zone in cases:
            kwargs = {"x_box": 0.0, "x_bb20": 0.0, "x_bb44": 0.0}
            kwargs[axis_name] = value
            zones = build_position_zones(PositionVector(**kwargs))
            zone_value = {
                "x_box": zones.box_zone,
                "x_bb20": zones.bb20_zone,
                "x_bb44": zones.bb44_zone,
            }[axis_name]
            assert zone_value == expected_zone


def test_position_interpretation_respects_middle_boundary_consistently():
    position = PositionVector(
        x_box=0.18,
        x_bb20=0.18,
        x_bb44=0.18,
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert zones.box_zone == "MIDDLE"
    assert zones.bb20_zone == "MIDDLE"
    assert zones.bb44_zone == "MIDDLE"
    assert interpretation.primary_label == "ALIGNED_MIDDLE"


def test_position_interpretation_exposes_native_conflict_labels_only():
    position = PositionVector(
        x_box=0.55,
        x_bb20=-0.35,
        x_bb44=0.04,
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)

    assert interpretation.conflict_kind == "CONFLICT_BOX_UPPER_BB20_LOWER"
    assert interpretation.dominance_label == "UPPER_DOMINANT_CONFLICT"
    assert interpretation.metadata["conflict_axes"] == ["x_box", "x_bb20"]
    assert interpretation.metadata["zone_signature"] == "UPPER|LOWER|MIDDLE"
    assert "legacy_conflict_kind" not in interpretation.metadata
    assert "legacy_dominance" not in interpretation.metadata


def test_position_energy_snapshot_stays_side_agnostic():
    position = PositionVector(
        x_box=0.55,
        x_bb20=-0.45,
        x_bb44=0.02,
    )

    energy = build_position_energy_snapshot(position)

    assert round(energy.upper_position_force, 4) == 0.2515
    assert round(energy.lower_position_force, 4) == 0.1575
    assert energy.position_conflict_score > 0.0
    assert energy.middle_neutrality == 0.0
    assert energy.metadata["energy_version"] == "v2_position_energy"
    assert round(energy.metadata["position_force_balance"], 4) == 0.094
    assert energy.metadata["position_dominance"] == "UPPER"
    assert energy.metadata["primary_upper_components"]["x_box"] == 0.24750000000000003
    assert energy.metadata["primary_lower_components"]["x_bb20"] == 0.1575
    assert energy.metadata["primary_only_outputs"] is True


def test_position_energy_snapshot_exposes_neutral_middle_state():
    energy = build_position_energy_snapshot(PositionVector())

    assert energy.upper_position_force == 0.0
    assert energy.lower_position_force == 0.0
    assert energy.middle_neutrality == 1.0
    assert energy.position_conflict_score == 0.0
    assert energy.metadata["position_dominance"] == "NEUTRAL"
    assert energy.metadata["position_force_balance"] == 0.0
    assert energy.metadata["secondary_upper_force"] == 0.0
    assert energy.metadata["secondary_lower_force"] == 0.0


def test_mtf_weighted_map_bias_is_exposed_as_metadata_only():
    position = PositionVector(
        metadata={
            "mtf_ma_big_map_v1": {
                "entries": {
                    "1D": {"side": "BELOW", "proximity": 0.95},
                    "4H": {"side": "BELOW", "proximity": 0.90},
                    "1H": {"side": "BELOW", "proximity": 0.82},
                    "30M": {"side": "ABOVE", "proximity": 0.20},
                    "15M": {"side": "ABOVE", "proximity": 0.15},
                },
                "stack_state": "BEAR_STACK",
            },
            "mtf_trendline_map_v1": {
                "entries": {
                    "4H": {
                        "support_side": "BELOW",
                        "support_proximity": 0.20,
                        "resistance_side": "BELOW",
                        "resistance_proximity": 0.88,
                    },
                    "1H": {
                        "support_side": "ABOVE",
                        "support_proximity": 0.18,
                        "resistance_side": "BELOW",
                        "resistance_proximity": 0.86,
                    },
                    "15M": {
                        "support_side": "ABOVE",
                        "support_proximity": 0.12,
                        "resistance_side": "BELOW",
                        "resistance_proximity": 0.70,
                    },
                    "1M": {
                        "support_side": "ABOVE",
                        "support_proximity": 0.08,
                        "resistance_side": "BELOW",
                        "resistance_proximity": 0.55,
                    },
                }
            },
        }
    )

    zones = build_position_zones(position)
    interpretation = build_position_interpretation(position, zones=zones)
    energy = build_position_energy_snapshot(position)

    assert interpretation.secondary_context_label == "NEUTRAL_CONTEXT"
    assert interpretation.metadata["mtf_ma_weight_profile_v1"]["upper_resistance_force"] > interpretation.metadata["mtf_ma_weight_profile_v1"]["lower_support_force"]
    assert interpretation.metadata["mtf_trendline_weight_profile_v1"]["upper_resistance_force"] > interpretation.metadata["mtf_trendline_weight_profile_v1"]["lower_support_force"]
    assert interpretation.metadata["mtf_context_weight_profile_v1"]["bias"] < 0.0
    assert interpretation.metadata["mtf_context_weight_profile_v1"]["owner"] == "STATE_CANDIDATE"
    assert energy.upper_position_force == 0.0
    assert energy.lower_position_force == 0.0
    assert energy.metadata["mtf_upper_force"] > energy.metadata["mtf_lower_force"]
    assert energy.metadata["mtf_force_owner"] == "STATE_CANDIDATE"


def test_position_vector_contract_is_limited_to_p1_axes():
    vector_field_names = tuple(field.name for field in fields(PositionVector) if field.name != "metadata")

    assert vector_field_names == POSITION_PRIMARY_AXES + POSITION_SECONDARY_AXES


def test_position_package_does_not_pull_in_response_state_or_side_decisions():
    root = Path(__file__).resolve().parents[2]
    position_dir = root / "backend" / "trading" / "engine" / "position"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in position_dir.glob("*.py"))

    forbidden_tokens = [
        "ResponseVector",
        "StateVector",
        "build_response_vector(",
        "build_state_vector(",
        "route_observe_confirm(",
        "\"BUY\"",
        "\"SELL\"",
    ]

    for token in forbidden_tokens:
        assert token not in sources


def test_position_coordinates_are_built_only_inside_builder():
    root = Path(__file__).resolve().parents[2]
    backend_dir = root / "backend"
    matches = []

    for path in backend_dir.rglob("*.py"):
        src = path.read_text(encoding="utf-8", errors="ignore")
        for token in (
            "compute_box_position(",
            "compute_bb20_position(",
            "compute_bb44_position(",
            "compute_ma_positions(",
            "compute_sr_position(",
            "compute_trendline_position(",
        ):
            if token in src:
                matches.append((path.name, token))

    assert sorted(matches) == [
        ("bb_position.py", "compute_bb20_position("),
        ("bb_position.py", "compute_bb44_position("),
        ("box_position.py", "compute_box_position("),
        ("builder.py", "compute_bb20_position("),
        ("builder.py", "compute_bb44_position("),
        ("builder.py", "compute_box_position("),
        ("builder.py", "compute_ma_positions("),
        ("builder.py", "compute_sr_position("),
        ("builder.py", "compute_trendline_position("),
        ("ma_position.py", "compute_ma_positions("),
        ("sr_position.py", "compute_sr_position("),
        ("trendline_position.py", "compute_trendline_position("),
    ]
