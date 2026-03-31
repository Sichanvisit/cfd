"""
Entry phase cycle runner (Phase 2~4).

1) Build 24h preflight report
2) Judge pass/fail against gate criteria
3) Emit tuning recommendations (R1/R2/R3 + SHOCK policy)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.preflight_24h_report import build_report


DEFAULT_DECISIONS = PROJECT_ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_CLOSED = PROJECT_ROOT / "data" / "trades" / "trade_closed_history.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "reports"


def _to_map(rows: list[dict], key: str) -> dict:
    out = {}
    for r in rows or []:
        out[str(r.get(key, ""))] = dict(r)
    return out


def evaluate(report: dict) -> dict:
    blocked = _to_map(report.get("blocked_by_distribution", []), "blocked_key")
    symbols = _to_map(report.get("symbol_entered_count", []), "symbol_key")
    pnl = _to_map(report.get("symbol_pnl_summary", []), "symbol_key")
    mode_rows = report.get("decision_mode_stats", []) or []
    fallback_ratio = float(report.get("fallback_ratio", 0.0) or 0.0)
    p_dist = report.get("p_distribution", {}) or {}

    required_symbols = ["NAS100", "XAUUSD", "BTCUSD"]
    entered_all = True
    entered_missing = []
    for s in required_symbols:
        n = int((symbols.get(s, {}) or {}).get("entered_n", 0) or 0)
        if n <= 0:
            entered_all = False
            entered_missing.append(s)

    dyn_rate = float((blocked.get("dynamic_threshold_not_met", {}) or {}).get("rate", 0.0) or 0.0)
    dyn_ok = dyn_rate <= 0.01

    pre_rows = report.get("preflight_block_enter_stats", []) or []
    pre_known = [r for r in pre_rows if str(r.get("value", "")).upper() != "UNKNOWN"]
    pre_overblocked = False
    if pre_known:
        # If almost everything blocked in known preflight slices, treat as over-block.
        pre_overblocked = any(float(r.get("blocked_rate", 0.0) or 0.0) >= 0.98 for r in pre_known)

    utility_block_rate = float((blocked.get("utility_below_u_min", {}) or {}).get("rate", 0.0) or 0.0)
    entered_rate = float((blocked.get("entered_or_not_blocked", {}) or {}).get("rate", 0.0) or 0.0)
    over_entry = bool(entered_rate >= 0.08 and utility_block_rate <= 0.20)
    over_block = bool(entered_rate <= 0.005 or utility_block_rate >= 0.70)

    btc = pnl.get("BTCUSD", {}) or {}
    btc_loss_persist = bool(
        int(btc.get("n", 0) or 0) >= 30 and float(btc.get("total_profit", 0.0) or 0.0) < 0.0
    )

    # SHOCK concentration check from preflight regime summary (if available)
    pre_pnl_rows = report.get("preflight_entry_pnl_summary", []) or []
    shock_rows = [r for r in pre_pnl_rows if str(r.get("field", "")) == "preflight_regime" and str(r.get("value", "")).upper() == "SHOCK"]
    shock_hard_block_recommended = False
    if shock_rows:
        sr = shock_rows[0]
        shock_hard_block_recommended = bool(
            int(sr.get("closed_matched_n", 0) or 0) >= 20 and float(sr.get("total_profit", 0.0) or 0.0) < 0.0
        )

    p_raw = (p_dist.get("raw", {}) or {})
    p_cal = (p_dist.get("calibrated", {}) or {})
    p_fixed_risk = False
    if p_cal:
        cal_span = float(p_cal.get("p95", 0.5) or 0.5) - float(p_cal.get("p5", 0.5) or 0.5)
        p_fixed_risk = bool(int(p_cal.get("n", 0) or 0) >= 100 and cal_span <= 0.08)

    pass_all = bool(entered_all and dyn_ok and (not pre_overblocked))

    recommendations: list[str] = []
    if fallback_ratio > 0.35:
        recommendations.append(
            "R1: fallback_ratio>35% -> relax ENTRY_UTILITY_MIN_WINS/LOSSES or adjust ENTRY_UTILITY_FALLBACK_*"
        )
    if over_entry:
        recommendations.append(
            "R2(over-entry): increase ENTRY_UTILITY_MIN_BY_SYMBOL by +0.02~0.04 and raise preflight penalties"
        )
    if over_block:
        recommendations.append(
            "R2(over-block): decrease ENTRY_UTILITY_MIN_BY_SYMBOL by -0.02 and lower preflight penalties"
        )
    if p_fixed_risk:
        recommendations.append(
            "R3(p fixed): lower ENTRY_UTILITY_P_CALIBRATION_BLEND_MIN and slightly raise ENTRY_UTILITY_P_WEIGHT"
        )
    if btc_loss_persist:
        recommendations.append(
            "BTC persistent loss: tighten BTC mode (raise BTC U_min or keep stricter BTC fallback/loss assumptions)"
        )
    if shock_hard_block_recommended:
        recommendations.append(
            "Phase4: set ENTRY_PREFLIGHT_HARD_BLOCK=True and keep ENTRY_PREFLIGHT_HARD_BLOCK_SHOCK_ONLY=True"
        )
    else:
        recommendations.append("Phase4: keep soft-first (no global hard block), maintain SHOCK-only option standby")

    return {
        "pass": pass_all,
        "fail_reasons": {
            "entered_missing_symbols": entered_missing,
            "dynamic_threshold_not_met_rate": dyn_rate,
            "preflight_overblocked": pre_overblocked,
        },
        "signals": {
            "fallback_ratio": fallback_ratio,
            "utility_below_u_min_rate": utility_block_rate,
            "entered_rate": entered_rate,
            "over_entry_risk": over_entry,
            "over_block_risk": over_block,
            "btc_loss_persist": btc_loss_persist,
            "p_fixed_risk": p_fixed_risk,
            "shock_hard_block_recommended": shock_hard_block_recommended,
            "decision_mode_stats": mode_rows,
        },
        "recommendations": recommendations,
    }


def run_cycle(
    decisions_csv: Path,
    closed_csv: Path,
    out_dir: Path,
    hours: int,
    match_tolerance_sec: int,
) -> tuple[Path, Path]:
    report_json, report_md = build_report(
        decisions_csv=decisions_csv,
        closed_csv=closed_csv,
        out_dir=out_dir,
        hours=hours,
        match_tolerance_sec=match_tolerance_sec,
    )
    base = json.loads(Path(report_json).read_text(encoding="utf-8"))
    verdict = evaluate(base)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_json": str(report_json),
        "report_md": str(report_md),
        "verdict": verdict,
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = out_dir / f"entry_phase_cycle_{stamp}.json"
    out_md = out_dir / f"entry_phase_cycle_{stamp}.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Entry Phase Cycle",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- report_json: {payload['report_json']}",
        f"- report_md: {payload['report_md']}",
        f"- pass: {bool(verdict.get('pass', False))}",
        "",
        "## Fail Reasons",
        f"- entered_missing_symbols: {verdict.get('fail_reasons', {}).get('entered_missing_symbols', [])}",
        f"- dynamic_threshold_not_met_rate: {float(verdict.get('fail_reasons', {}).get('dynamic_threshold_not_met_rate', 0.0)):.4f}",
        f"- preflight_overblocked: {bool(verdict.get('fail_reasons', {}).get('preflight_overblocked', False))}",
        "",
        "## Signals",
    ]
    sig = verdict.get("signals", {}) or {}
    for k in (
        "fallback_ratio",
        "utility_below_u_min_rate",
        "entered_rate",
        "over_entry_risk",
        "over_block_risk",
        "btc_loss_persist",
        "p_fixed_risk",
        "shock_hard_block_recommended",
    ):
        v = sig.get(k)
        if isinstance(v, float):
            lines.append(f"- {k}: {v:.4f}")
        else:
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Recommendations")
    for r in verdict.get("recommendations", []) or []:
        lines.append(f"- {r}")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_json, out_md


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions-csv", type=str, default=str(DEFAULT_DECISIONS))
    parser.add_argument("--closed-csv", type=str, default=str(DEFAULT_CLOSED))
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--match-tolerance-sec", type=int, default=300)
    args = parser.parse_args()

    out_json, out_md = run_cycle(
        decisions_csv=Path(args.decisions_csv),
        closed_csv=Path(args.closed_csv),
        out_dir=Path(args.out_dir),
        hours=max(1, int(args.hours)),
        match_tolerance_sec=max(10, int(args.match_tolerance_sec)),
    )
    print(f"json={out_json}")
    print(f"md={out_md}")


if __name__ == "__main__":
    main()
