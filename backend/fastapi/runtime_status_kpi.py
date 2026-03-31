"""KPI evaluation for runtime status."""

from __future__ import annotations

import os


def evaluate_runtime_kpi(*, expectancy_by_symbol: dict, d_acceptance_snapshot: dict, stage_winloss_snapshot: dict):
    try:
        exp_good = float(os.getenv("KPI_EXPECTANCY_GOOD", "0.15") or 0.15)
        exp_warn_low = float(os.getenv("KPI_EXPECTANCY_WARN_LOW", "-0.05") or -0.05)
        p2m_good = float(os.getenv("KPI_PLUS_TO_MINUS_GOOD", "0.18") or 0.18)
        p2m_warn = float(os.getenv("KPI_PLUS_TO_MINUS_WARN", "0.28") or 0.28)
        p2m_baseline_jump = float(os.getenv("KPI_PLUS_TO_MINUS_BASELINE_JUMP", "0.08") or 0.08)
        adv_good = float(os.getenv("KPI_ADVERSE_STOP_GOOD", "0.22") or 0.22)
        adv_warn = float(os.getenv("KPI_ADVERSE_STOP_WARN", "0.32") or 0.32)
        adv_baseline_jump = float(os.getenv("KPI_ADVERSE_STOP_BASELINE_JUMP", "0.10") or 0.10)
        hard_exp_drop = float(os.getenv("KPI_HARD_EXPECTANCY_DROP", "-0.25") or -0.25)
        hard_p2m = float(os.getenv("KPI_HARD_PLUS_TO_MINUS", "0.40") or 0.40)
        hard_adv = float(os.getenv("KPI_HARD_ADVERSE_STOP", "0.45") or 0.45)

        def _grade_expectancy(v: float) -> str:
            if float(v) >= exp_good:
                return "pass"
            if float(v) < exp_warn_low:
                return "fail"
            return "warn"

        def _grade_ratio(cur: float, good: float, warn: float, baseline: float | None = None, baseline_jump: float = 0.0) -> str:
            if baseline is not None and (float(cur) - float(baseline)) > float(baseline_jump):
                return "fail"
            if float(cur) <= float(good):
                return "pass"
            if float(cur) <= float(warn):
                return "warn"
            return "fail"

        overall_expectancy = 0.0
        sym_values = []
        if isinstance(expectancy_by_symbol, dict) and expectancy_by_symbol:
            for _, v in expectancy_by_symbol.items():
                if isinstance(v, dict):
                    try:
                        sym_values.append(float(v.get("expectancy", 0.0) or 0.0))
                    except Exception:
                        pass
            if sym_values:
                overall_expectancy = float(sum(sym_values) / max(1, len(sym_values)))
        expectancy_grade = _grade_expectancy(overall_expectancy)

        p2m_cur = float((d_acceptance_snapshot or {}).get("plus_to_minus_ratio_current", 0.0) or 0.0)
        p2m_base = float((d_acceptance_snapshot or {}).get("plus_to_minus_ratio_baseline", p2m_cur) or p2m_cur)
        p2m_grade = _grade_ratio(p2m_cur, p2m_good, p2m_warn, baseline=p2m_base, baseline_jump=p2m_baseline_jump)

        adv_cur = float((d_acceptance_snapshot or {}).get("adverse_stop_ratio_current", 0.0) or 0.0)
        adv_base = float((d_acceptance_snapshot or {}).get("adverse_stop_ratio_baseline", adv_cur) or adv_cur)
        adv_grade = _grade_ratio(adv_cur, adv_good, adv_warn, baseline=adv_base, baseline_jump=adv_baseline_jump)

        stage_profit_vals = []
        stage_snapshot = stage_winloss_snapshot if isinstance(stage_winloss_snapshot, dict) else {}
        for key in ("short", "mid", "long", "protect", "lock", "hold"):
            row = stage_snapshot.get(key)
            if isinstance(row, dict):
                try:
                    stage_profit_vals.append(float(row.get("avg_net_pnl", row.get("expectancy", row.get("avg_profit", 0.0))) or 0.0))
                except Exception:
                    pass
        positive_stage = int(sum(1 for x in stage_profit_vals if float(x) > 0))
        stage_grade = "pass" if positive_stage >= 2 else ("warn" if positive_stage == 1 else "fail")

        symbol_non_negative = int(sum(1 for x in sym_values if float(x) >= 0.0))
        symbol_grade = "pass" if symbol_non_negative >= 2 else ("warn" if symbol_non_negative == 1 else "fail")

        hard_triggered = bool(
            (float(overall_expectancy) <= float(hard_exp_drop))
            or (float(p2m_cur) >= float(hard_p2m))
            or (float(adv_cur) >= float(hard_adv))
        )
        grade_to_score = {"pass": 0, "warn": 1, "fail": 2}
        worst_grade = max(
            [expectancy_grade, p2m_grade, adv_grade, stage_grade, symbol_grade],
            key=lambda g: grade_to_score.get(str(g), 1),
        )
        overall_grade = "fail" if hard_triggered else worst_grade
        return {
            "overall": overall_grade,
            "hard_triggered": bool(hard_triggered),
            "metrics": {
                "expectancy_overall": {"value": round(float(overall_expectancy), 6), "grade": expectancy_grade},
                "plus_to_minus_ratio": {"current": round(float(p2m_cur), 4), "baseline": round(float(p2m_base), 4), "grade": p2m_grade},
                "adverse_stop_ratio": {"current": round(float(adv_cur), 4), "baseline": round(float(adv_base), 4), "grade": adv_grade},
                "stage_profit_health": {"positive_stage_count": int(positive_stage), "grade": stage_grade},
                "symbol_expectancy_health": {"non_negative_symbol_count": int(symbol_non_negative), "grade": symbol_grade},
            },
        }
    except Exception:
        return {}
