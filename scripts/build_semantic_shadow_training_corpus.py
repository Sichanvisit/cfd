"""Build a semantic shadow preview training corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.semantic_shadow_training_corpus import (  # noqa: E402
    build_semantic_shadow_training_corpus,
    render_semantic_shadow_training_corpus_markdown,
)


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_corpus_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_corpus_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_corpus_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    frame, summary, enriched_rows = build_semantic_shadow_training_corpus()
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": enriched_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_semantic_shadow_training_corpus_markdown(summary, frame),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
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
