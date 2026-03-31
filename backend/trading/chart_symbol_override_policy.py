from __future__ import annotations

from copy import deepcopy


SYMBOL_OVERRIDE_POLICY_V1 = {
    "contract_version": "symbol_override_policy_v1",
    "override_policy": {
        "meaning_override_forbidden": True,
        "strength_override_forbidden": True,
        "family_disable_forbidden": True,
        "allowed_axes": [
            "confirm_multiplier",
            "probe_multiplier",
            "support_tolerance",
            "structural_relief",
            "scene_context_relaxation",
            "visual_relief_visibility",
        ],
    },
    "symbols": {
        "XAUUSD": {
            "router": {
                "probe": {
                    "upper_reject": {
                        "enabled": True,
                        "structural_reject_min": 0.12,
                        "floor_mult": 0.60,
                        "advantage_mult": 0.10,
                        "support_tolerance": 0.04,
                    },
                    "lower_second_support": {
                        "enabled": True,
                        "structural_support_min": 0.14,
                        "reclaim_min": 0.18,
                        "secondary_min": 0.10,
                        "persistence_min": 0.10,
                        "belief_min": 0.46,
                    },
                },
                "context": {
                    "upper_reject_watch": {
                        "enabled": True,
                        "bb20_min": -0.08,
                        "upper_reject_min": 0.06,
                        "sr_resistance_min": 0.10,
                        "trend_resistance_m15_min": 0.08,
                        "bb20_mid_lose_min": 0.06,
                        "box_mid_reject_min": 0.06,
                        "sell_support_floor": 0.14,
                        "sell_support_buy_margin": -0.02,
                    },
                    "mixed_upper_reject": {
                        "enabled": True,
                        "bb20_min": -0.16,
                        "bb44_min": -0.10,
                        "structural_reject_min": 0.12,
                        "confirm_response_min": 0.12,
                        "mixed_support_floor": 0.18,
                        "confirm_buy_support_margin": 0.02,
                        "confirm_sell_support_floor": 0.10,
                        "confirm_sell_support_buy_margin": -0.04,
                    },
                    "upper_reject_context": {
                        "enabled": True,
                        "bb20_min": -0.08,
                        "structural_reject_min": 0.12,
                        "sr_resistance_min": 0.10,
                        "trend_resistance_m15_min": 0.08,
                        "bb20_mid_lose_min": 0.06,
                        "box_mid_reject_min": 0.06,
                        "sell_support_floor": 0.12,
                        "sell_support_buy_margin": -0.02,
                    },
                },
                "relief": {
                    "second_support_probe": {
                        "enabled": True,
                    },
                    "upper_structural_probe": {
                        "enabled": True,
                    },
                },
            },
            "painter": {
                "scene_allow": {
                    "xau_second_support_buy_probe": {
                        "enabled": True,
                        "base_allowed_bb_states": ["LOWER_EDGE", "BREAKDOWN"],
                        "mid_relief_bb_states": ["MID", "MIDDLE"],
                    },
                    "xau_upper_sell_probe": {
                        "enabled": True,
                        "allowed_box_states": [
                            "UPPER",
                            "UPPER_EDGE",
                            "ABOVE",
                            "LOWER",
                            "LOWER_EDGE",
                            "BELOW",
                            "MIDDLE",
                        ],
                        "extended_bb_states": [
                            "MID",
                            "MIDDLE",
                            "UPPER",
                            "UPPER_EDGE",
                            "ABOVE",
                            "BREAKOUT",
                        ],
                        "allow_unknown_bb_state": True,
                    },
                },
                "relief_visibility": {
                    "xau_second_support_probe_relief": {
                        "enabled": True,
                        "mid_bb_states": ["MID", "MIDDLE"],
                    },
                },
            },
        },
        "BTCUSD": {
            "router": {
                "probe": {
                    "lower_rebound": {
                        "enabled": True,
                        "floor_mult": 0.86,
                        "advantage_mult": 0.42,
                        "support_tolerance": 0.010,
                    },
                    "upper_reject": {
                        "enabled": True,
                        "floor_mult": 0.68,
                        "advantage_mult": 0.18,
                        "support_tolerance": 0.020,
                    },
                },
                "context": {
                    "lower_buy_context": {
                        "enabled": True,
                        "middle_x_box_max": 0.12,
                    },
                    "midline_rebound_transition": {
                        "enabled": True,
                    },
                },
                "relief": {
                    "lower_structural_probe": {
                        "enabled": True,
                        "support_min": 0.22,
                        "reclaim_min": 0.16,
                        "secondary_min": 0.08,
                        "context_support_min": 0.46,
                        "context_pair_gap_min": 0.18,
                        "context_bb44_max": 0.18,
                        "context_sr_min": -0.18,
                    },
                },
            },
            "painter": {
                "scene_allow": {
                    "btc_lower_buy_conservative_probe": {
                        "enabled": True,
                        "extra_bb_states": ["MID", "MIDDLE", "LOWER_EDGE", "BREAKDOWN"],
                    },
                },
            },
        },
        "NAS100": {
            "router": {
                "probe": {
                    "clean_confirm": {
                        "enabled": True,
                        "floor_mult": 0.74,
                        "advantage_mult": 0.26,
                        "support_tolerance": 0.015,
                    },
                },
                "relief": {
                    "clean_confirm_middle_anchor": {
                        "enabled": True,
                        "support_min": 0.34,
                        "pair_gap_min": 0.10,
                        "confirm_fake_gap_min": -0.08,
                        "wait_confirm_gap_min": -0.05,
                    },
                },
            },
            "painter": {
                "scene_allow": {
                    "nas_clean_confirm_probe": {
                        "enabled": True,
                        "extra_bb_states": ["MID", "MIDDLE", "LOWER_EDGE", "BREAKDOWN"],
                    },
                },
            },
        },
    },
}


def build_symbol_override_policy_v1() -> dict:
    return deepcopy(SYMBOL_OVERRIDE_POLICY_V1)
