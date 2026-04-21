from pathlib import Path
import json

import pandas as pd

from backend.services.semantic_shadow_preview_bundle import build_semantic_shadow_preview_bundle


def _make_dataset_frame(target_column: str, margin_column: str) -> pd.DataFrame:
    rows = []
    buckets = ["train"] * 4 + ["validation"] * 4 + ["test"] * 4
    for idx, bucket in enumerate(buckets):
        label = idx % 2
        rows.append(
            {
                "symbol": "BTCUSD" if idx < 6 else "NAS100",
                "signal_timeframe": "M1",
                "setup_id": f"setup_{idx % 3}",
                "setup_side": "BUY" if label else "SELL",
                "entry_stage": "probe",
                "preflight_regime": "trend" if label else "range",
                "preflight_liquidity": "normal",
                "position_x_box": float(label) + (idx * 0.01),
                "signal_age_sec": float(idx),
                "data_completeness_ratio": 0.98,
                "used_fallback_count": 0,
                "sample_weight": 1.0 + (idx * 0.1),
                "event_ts": float(idx),
                "time_split_bucket": bucket,
                target_column: label,
                margin_column: 1.0 + idx,
            }
        )
    return pd.DataFrame(rows)


def _write_dataset(path: Path, target_column: str, margin_column: str) -> None:
    frame = _make_dataset_frame(target_column, margin_column)
    frame.to_parquet(path, index=False)
    path.with_suffix(path.suffix + ".summary.json").write_text(
        json.dumps({"dataset_key": path.stem}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_build_semantic_shadow_preview_bundle_trains_all_targets(tmp_path: Path):
    dataset_dir = tmp_path / "datasets"
    output_dir = tmp_path / "models"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    _write_dataset(dataset_dir / "timing_dataset.parquet", "target_timing_now_vs_wait", "target_timing_margin")
    _write_dataset(dataset_dir / "entry_quality_dataset.parquet", "target_entry_quality", "target_entry_quality_margin")
    _write_dataset(dataset_dir / "exit_management_dataset.parquet", "target_exit_management", "target_exit_management_margin")

    frame, summary = build_semantic_shadow_preview_bundle(
        dataset_dir=dataset_dir,
        output_dir=output_dir,
    )

    assert len(frame) == 3
    assert summary["bundle_ready"] is True
    assert (output_dir / "timing_model.joblib").exists()
    assert (output_dir / "entry_quality_model.joblib").exists()
    assert (output_dir / "exit_management_model.joblib").exists()
    assert (output_dir / "metrics.json").exists()
