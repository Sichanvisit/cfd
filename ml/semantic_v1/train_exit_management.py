from __future__ import annotations

import argparse
import json

from ml.semantic_v1.evaluate import build_train_config, train_semantic_model


def main() -> int:
    parser = argparse.ArgumentParser(description="Train semantic exit management model v1.")
    parser.add_argument("--dataset", default="", help="Path to exit_management_dataset.parquet")
    parser.add_argument("--output-dir", default="", help="Directory to write semantic_v1 model artifacts")
    args = parser.parse_args()

    config = build_train_config("exit_management", dataset_path=args.dataset or None, output_dir=args.output_dir or None)
    summary = train_semantic_model(config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

