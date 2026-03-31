from adapters.file_observability_adapter import FileObservabilityAdapter


def test_file_observability_adapter_writes_counters_and_events(tmp_path):
    adapter = FileObservabilityAdapter(base_dir=tmp_path / "obs")

    adapter.incr("orders_success_total", 2)
    adapter.incr("orders_success_total", 1)
    adapter.event("order_success", payload={"symbol": "BTCUSD"})

    snap = adapter.snapshot(last_n=10)

    assert snap["counters"]["orders_success_total"] == 3
    assert snap["events_count"] >= 1
    assert any(e.get("name") == "order_success" for e in snap["events"])


def test_file_observability_adapter_rolls_events_and_keeps_snapshot_visible(tmp_path):
    adapter = FileObservabilityAdapter(
        base_dir=tmp_path / "obs",
        events_max_bytes=1,
        events_backup_count=1,
        events_retention_days=0,
    )

    adapter.event("first_event", payload={"seq": 1})
    adapter.event("second_event", payload={"seq": 2})
    adapter.event("third_event", payload={"seq": 3})

    archives = sorted((tmp_path / "obs").glob("events.*.jsonl"))
    assert len(archives) <= 1
    assert (tmp_path / "obs" / "events.jsonl").exists()

    snap = adapter.snapshot(last_n=10)

    names = [e.get("name") for e in snap["events"]]
    assert "second_event" in names or "first_event" in names
    assert "third_event" in names
