"""
Build the shadow-auto candidate bridge from calibration outputs.

Usage:
  python scripts/build_shadow_auto_candidates.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_candidate_bridge import (  # noqa: E402
    build_shadow_auto_candidate_bridge,
    load_shadow_auto_bridge_frame,
    render_shadow_auto_candidate_bridge_markdown,
)


def _default_ranking_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_latest.csv"


def _default_patch_draft_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_patch_draft_latest.csv"


def _default_correction_candidates_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_correction_candidates_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_candidates_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_candidates_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_candidates_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking-path", default=str(_default_ranking_path()))
    parser.add_argument("--patch-draft-path", default=str(_default_patch_draft_path()))
    parser.add_argument("--correction-candidates-path", default=str(_default_correction_candidates_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    ranking_path = Path(args.ranking_path)
    patch_draft_path = Path(args.patch_draft_path)
    correction_candidates_path = Path(args.correction_candidates_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    ranking = load_shadow_auto_bridge_frame(ranking_path)
    patch_draft = load_shadow_auto_bridge_frame(patch_draft_path)
    correction_candidates = load_shadow_auto_bridge_frame(correction_candidates_path)
    bridge, summary = build_shadow_auto_candidate_bridge(
        ranking,
        patch_draft=patch_draft,
        correction_candidates=correction_candidates,
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    bridge.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": bridge.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_shadow_auto_candidate_bridge_markdown(summary, bridge),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ranking_path": str(ranking_path),
                "patch_draft_path": str(patch_draft_path),
                "correction_candidates_path": str(correction_candidates_path),
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
