"""Ops/router endpoints extracted from monolithic FastAPI app module."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse


def create_ops_router(
    *,
    app: FastAPI,
    kst,
    app_version: str,
    runbook_doc: Path,
    alert_policy_doc: Path,
    changelog_md: Path,
    step11_doc: Path,
    step12_doc: Path,
    runtime_status_json: Path,
    project_root: Path,
    classify_release_gate: Callable[[int, int, int], dict[str, Any]],
) -> APIRouter:
    router = APIRouter(tags=["ops"])

    @router.get("/health")
    def health():
        return {"status": "ok"}

    @router.get("/ops/readiness")
    def ops_readiness():
        now_iso = datetime.now(kst).isoformat(timespec="seconds")
        docs_state = {
            "runbook_exists": runbook_doc.exists(),
            "alert_policy_exists": alert_policy_doc.exists(),
            "changelog_exists": changelog_md.exists(),
            "step11_exists": step11_doc.exists(),
            "step12_exists": step12_doc.exists(),
        }

        runtime_status = {}
        if runtime_status_json.exists():
            try:
                runtime_status = dict(json.loads(runtime_status_json.read_text(encoding="utf-8")) or {})
            except Exception:
                runtime_status = {}
        status_payload = runtime_status.get("status") if isinstance(runtime_status.get("status"), dict) else runtime_status
        active_alerts = 0
        rollback_count = 0
        warning_total = 0
        if isinstance(status_payload, dict):
            alerts = status_payload.get("alerts", {})
            if isinstance(alerts, dict):
                active_alerts = int(alerts.get("active_count", 0) or 0)
            policy_snapshot = status_payload.get("policy_snapshot", {})
            if isinstance(policy_snapshot, dict):
                policy_runtime = policy_snapshot.get("policy_runtime", {})
                if isinstance(policy_runtime, dict):
                    rollback_count = int(policy_runtime.get("rollback_count", 0) or 0)
            runtime_warning_counters = status_payload.get("runtime_warning_counters", {})
            if isinstance(runtime_warning_counters, dict):
                for row in runtime_warning_counters.values():
                    if isinstance(row, dict):
                        warning_total += int(row.get("count", 0) or 0)
        gate = classify_release_gate(active_alerts, rollback_count, warning_total)

        obs = getattr(app.state, "observability", None)
        obs_summary = {"exists": False, "events_count": 0, "counter_keys": []}
        if obs is not None:
            snap = obs.snapshot(last_n=10)
            counters = snap.get("counters", {}) if isinstance(snap, dict) else {}
            obs_summary = {
                "exists": True,
                "events_count": int(snap.get("events_count", 0) or 0),
                "counter_keys": sorted([str(k) for k in dict(counters).keys() if str(k) != "updated_at"]),
            }

        return {
            "as_of": now_iso,
            "version": app_version,
            "release_gate": gate,
            "docs": docs_state,
            "runtime": {
                "active_alerts": int(active_alerts),
                "policy_rollback_count": int(rollback_count),
                "warning_total": int(warning_total),
            },
            "observability": obs_summary,
        }

    @router.post("/layout/generate")
    def layout_generate(payload: dict[str, Any]):
        prompt = str(payload.get("prompt", "") or "").strip()
        symbol = str(payload.get("symbol", "") or "").strip()
        width = int(payload.get("width", 1280) or 1280)
        height = int(payload.get("height", 720) or 720)
        spec = app.state.layout_service.generate_layout(prompt=prompt, symbol=symbol, width=width, height=height)
        return {"ok": True, "layout": spec}

    @router.post("/layout/render")
    def layout_render(payload: dict[str, Any]):
        spec = payload.get("layout")
        if not isinstance(spec, dict):
            raise HTTPException(status_code=400, detail="payload.layout object is required")
        layout_id = str(payload.get("layout_id", "") or "").strip() or None
        try:
            result = app.state.layout_service.render_layout(spec, layout_id=layout_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        result["image_url"] = f"/layout/image/{result['layout_id']}"
        return {"ok": True, **result}

    @router.post("/layout/generate-and-render")
    def layout_generate_and_render(payload: dict[str, Any]):
        prompt = str(payload.get("prompt", "") or "").strip()
        symbol = str(payload.get("symbol", "") or "").strip()
        width = int(payload.get("width", 1280) or 1280)
        height = int(payload.get("height", 720) or 720)
        spec = app.state.layout_service.generate_layout(prompt=prompt, symbol=symbol, width=width, height=height)
        result = app.state.layout_service.render_layout(spec)
        result["image_url"] = f"/layout/image/{result['layout_id']}"
        return {"ok": True, "layout": spec, **result}

    @router.get("/layout/image/{layout_id}")
    def layout_image(layout_id: str):
        path = project_root / "data" / "layouts" / f"{layout_id}.png"
        if not path.exists():
            raise HTTPException(status_code=404, detail="layout image not found")
        return FileResponse(path, media_type="image/png")

    return router
