import pandas as pd

from ml.semantic_v1.dataset_splits import assess_split_health, attach_split_columns, build_holdout_bucket, build_split_health_payload


def test_assess_split_health_reports_fail_for_unhealthy_validation_split():
    frame = pd.DataFrame(
        [
            {"time_split_bucket": "train", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": 1}
            for _ in range(80)
        ]
        + [
            {"time_split_bucket": "train", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": 0}
            for _ in range(80)
        ]
        + [
            {"time_split_bucket": "validation", "symbol": "XAUUSD", "preflight_regime": "TREND", "setup_id": "s2", "target": 1}
            for _ in range(40)
        ]
        + [
            {"time_split_bucket": "validation", "symbol": "XAUUSD", "preflight_regime": "TREND", "setup_id": "s2", "target": 0}
            for _ in range(4)
        ]
        + [
            {"time_split_bucket": "test", "symbol": "NAS100", "preflight_regime": "RANGE", "setup_id": "s3", "target": 1}
            for _ in range(80)
        ]
        + [
            {"time_split_bucket": "test", "symbol": "NAS100", "preflight_regime": "RANGE", "setup_id": "s3", "target": 0}
            for _ in range(80)
        ]
    )

    summary = assess_split_health(frame, target_col="target")

    assert summary.overall_status == "fail"
    assert any(str(issue).startswith("validation:minority_class_below_minimum") for issue in summary.blocking_issues)


def test_assess_split_health_reports_warning_for_unbalanced_test_slices():
    rows = []
    for idx in range(128):
        rows.append({"time_split_bucket": "train", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": idx % 2})
    for idx in range(80):
        rows.append({"time_split_bucket": "validation", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": idx % 2})
    rows.extend(
        {"time_split_bucket": "test", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": 1}
        for _ in range(56)
    )
    rows.extend(
        {"time_split_bucket": "test", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": 0}
        for _ in range(4)
    )
    rows.extend(
        {"time_split_bucket": "test", "symbol": "XAUUSD", "preflight_regime": "TREND", "setup_id": "s2", "target": 1 if idx % 2 == 0 else 0}
        for idx in range(140)
    )

    summary = assess_split_health(pd.DataFrame(rows), target_col="target")

    assert summary.overall_status == "warning"
    assert any(item.group_col == "symbol" and item.status == "warning" for item in summary.slice_health)


def test_assess_split_health_surfaces_single_class_sparse_slices_as_unsupported():
    rows = []
    for idx in range(128):
        rows.append({"time_split_bucket": "train", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": idx % 2})
    for idx in range(80):
        rows.append({"time_split_bucket": "validation", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": idx % 2})
    rows.extend(
        {"time_split_bucket": "test", "symbol": "BTCUSD", "preflight_regime": "RANGE", "setup_id": "s1", "target": 1}
        for _ in range(60)
    )
    rows.extend(
        {"time_split_bucket": "test", "symbol": "XAUUSD", "preflight_regime": "TREND", "setup_id": "s2", "target": 1 if idx % 2 == 0 else 0}
        for idx in range(140)
    )

    summary = assess_split_health(pd.DataFrame(rows), target_col="target")

    assert summary.overall_status == "healthy"
    assert any(item.group_col == "symbol" and item.status == "unsupported" for item in summary.slice_health)
    assert any(str(issue).startswith("symbol:unsupported_slices=") for issue in summary.unsupported_issues)


def test_attach_split_columns_can_adapt_time_boundary_to_satisfy_minority_thresholds():
    rows = []
    for idx in range(550):
        rows.append(
            {
                "time": f"2026-03-20T09:{idx % 60:02d}:00+09:00",
                "signal_bar_ts": 1773936000 + idx,
                "symbol": "BTCUSD",
                "preflight_regime": "RANGE",
                "target": 0 if idx < 250 else 1,
            }
        )
    for idx in range(150):
        rows.append(
            {
                "time": f"2026-03-21T09:{idx % 60:02d}:00+09:00",
                "signal_bar_ts": 1774022400 + idx,
                "symbol": "BTCUSD",
                "preflight_regime": "RANGE",
                "target": 0 if idx < 90 else 1,
            }
        )
    for idx in range(150):
        rows.append(
            {
                "time": f"2026-03-22T09:{idx % 60:02d}:00+09:00",
                "signal_bar_ts": 1774108800 + idx,
                "symbol": "BTCUSD",
                "preflight_regime": "RANGE",
                "target": 0 if idx < 5 else 1,
            }
        )
    for idx in range(150):
        rows.append(
            {
                "time": f"2026-03-23T09:{idx % 60:02d}:00+09:00",
                "signal_bar_ts": 1774195200 + idx,
                "symbol": "BTCUSD",
                "preflight_regime": "RANGE",
                "target": 0 if idx < 70 else 1,
            }
        )
    frame = pd.DataFrame(rows)

    out, summary = attach_split_columns(
        frame,
        time_col="time",
        signal_bar_ts_col="signal_bar_ts",
        symbol_col="symbol",
        regime_col="preflight_regime",
        target_col="target",
    )

    fixed_validation = frame.sort_values("signal_bar_ts", kind="mergesort").iloc[700:850]["target"].value_counts().to_dict()
    validation_counts = out[out["time_split_bucket"] == "validation"]["target"].value_counts().to_dict()
    test_counts = out[out["time_split_bucket"] == "test"]["target"].value_counts().to_dict()

    assert min(fixed_validation.values()) < 32
    assert summary.time_split_strategy == "adaptive_target_balance"
    assert min(validation_counts.values()) >= 32
    assert min(test_counts.values()) >= 64


def test_build_split_health_payload_surfaces_bucket_coverage_and_holdout_health():
    rows = []
    for idx in range(90):
        bucket = "train" if idx < 50 else "validation" if idx < 70 else "test"
        rows.append(
            {
                "event_ts": 1773936000 + idx,
                "time_split_bucket": bucket,
                "symbol": "BTCUSD" if idx % 2 == 0 else "XAUUSD",
                "preflight_regime": "RANGE" if idx % 3 else "TREND",
                "setup_id": "s1" if idx % 2 == 0 else "s2",
                "symbol_holdout_bucket": "holdout" if idx % 11 == 0 else "train",
                "regime_holdout_bucket": "holdout" if idx % 13 == 0 else "train",
                "target": 1 if idx % 4 else 0,
            }
        )

    payload = build_split_health_payload(pd.DataFrame(rows), target_col="target")

    assert payload["version"] == "semantic_dataset_split_health_v1"
    assert len(payload["bucket_coverage"]) == 3
    assert payload["bucket_coverage"][0]["bucket"] == "train"
    assert "symbol_counts" in payload["bucket_coverage"][0]
    assert "regime_counts" in payload["bucket_coverage"][0]
    assert "class_imbalance_ratio" in payload["bucket_coverage"][0]
    assert "unsupported_issues" in payload
    assert len(payload["holdout_health"]) == 2
    assert {item["label"] for item in payload["holdout_health"]} == {"symbol", "regime"}
    assert all("class_balance" in item for item in payload["holdout_health"])


def test_build_holdout_bucket_assigns_at_least_one_group_when_multiple_tokens_exist():
    series = pd.Series(["BTCUSD", "BTCUSD", "NAS100", "XAUUSD", "XAUUSD"], dtype="object")

    out = build_holdout_bucket(series, salt="symbol_holdout", holdout_fraction=0.2)

    counts = out.value_counts(dropna=False).to_dict()
    assert counts.get("holdout", 0) >= 1
    assert counts.get("train", 0) >= 1


def test_build_holdout_bucket_prefers_dual_class_groups_when_target_available():
    series = pd.Series(["RANGE", "RANGE", "TREND", "TREND", "SHOCK", "SHOCK"], dtype="object")
    target = pd.Series([0, 1, 0, 1, 1, 1], dtype="int64")

    out = build_holdout_bucket(series, salt="regime_holdout", holdout_fraction=0.2, target_series=target)

    holdout_groups = set(series[out == "holdout"].astype(str).unique())
    assert holdout_groups
    assert "SHOCK" not in holdout_groups


def test_attach_split_columns_produces_non_empty_holdout_buckets_for_multi_symbol_and_regime_data():
    rows = []
    symbols = ["BTCUSD", "NAS100", "XAUUSD"]
    regimes = ["RANGE", "TREND", "UNKNOWN"]
    for idx in range(180):
        rows.append(
            {
                "time": f"2026-03-20T09:{idx % 60:02d}:00+09:00",
                "signal_bar_ts": 1773936000 + idx,
                "symbol": symbols[idx % len(symbols)],
                "preflight_regime": regimes[idx % len(regimes)],
                "target": 1 if idx % 3 else 0,
            }
        )

    out, summary = attach_split_columns(
        pd.DataFrame(rows),
        time_col="time",
        signal_bar_ts_col="signal_bar_ts",
        symbol_col="symbol",
        regime_col="preflight_regime",
        target_col="target",
    )

    assert set(out["symbol_holdout_bucket"].unique()) == {"train", "holdout"}
    assert set(out["regime_holdout_bucket"].unique()) == {"train", "holdout"}
    assert summary.symbol_holdout_counts.get("holdout", 0) > 0
    assert summary.regime_holdout_counts.get("holdout", 0) > 0
