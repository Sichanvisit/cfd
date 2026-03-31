"""
Layout generation/render service for text + arrow PNG overlays.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


class LayoutService:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.layout_dir = self.project_root / "data" / "layouts"
        self.layout_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now_text() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _safe_text(value: str, max_len: int = 80) -> str:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        if len(text) > max_len:
            return text[: max_len - 1] + "…"
        return text

    @staticmethod
    def _default_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            try:
                return ImageFont.truetype("malgun.ttf", size)
            except Exception:
                return ImageFont.load_default()

    def generate_layout(
        self,
        prompt: str,
        symbol: str = "",
        width: int = 1280,
        height: int = 720,
    ) -> dict[str, Any]:
        """
        Deterministic template generator.
        LLM can be plugged in later by replacing this function with structured output.
        """
        width = int(max(640, min(3840, width)))
        height = int(max(360, min(2160, height)))
        symbol = str(symbol or "").upper().strip() or "MARKET"
        title = self._safe_text(prompt or f"{symbol} SIGNAL", max_len=48)
        subtitle = self._safe_text(f"{symbol} | {self._now_text()}", max_len=72)

        spec = {
            "version": "1.0",
            "canvas": {"width": width, "height": height, "background": "#0f172a"},
            "elements": [
                {
                    "id": "title",
                    "type": "text",
                    "text": title,
                    "x": int(width * 0.08),
                    "y": int(height * 0.12),
                    "font_size": max(26, int(height * 0.065)),
                    "font_color": "#f8fafc",
                },
                {
                    "id": "subtitle",
                    "type": "text",
                    "text": subtitle,
                    "x": int(width * 0.08),
                    "y": int(height * 0.22),
                    "font_size": max(16, int(height * 0.03)),
                    "font_color": "#93c5fd",
                },
                {
                    "id": "arrow",
                    "type": "arrow",
                    "x1": int(width * 0.12),
                    "y1": int(height * 0.68),
                    "x2": int(width * 0.78),
                    "y2": int(height * 0.68),
                    "color": "#22d3ee",
                    "thickness": max(4, int(height * 0.008)),
                },
                {
                    "id": "note",
                    "type": "text",
                    "text": "Auto layout preview (core-rendered PNG)",
                    "x": int(width * 0.08),
                    "y": int(height * 0.78),
                    "font_size": max(14, int(height * 0.024)),
                    "font_color": "#cbd5e1",
                },
            ],
            "meta": {"prompt": self._safe_text(prompt, 200), "symbol": symbol, "generated_at": self._now_text()},
        }
        return spec

    @staticmethod
    def validate_layout(spec: dict[str, Any]) -> tuple[bool, str]:
        if not isinstance(spec, dict):
            return False, "layout must be object"
        canvas = spec.get("canvas", {})
        elements = spec.get("elements", [])
        if not isinstance(canvas, dict):
            return False, "canvas must be object"
        if not isinstance(elements, list) or not elements:
            return False, "elements must be non-empty list"
        w = int(canvas.get("width", 0) or 0)
        h = int(canvas.get("height", 0) or 0)
        if w < 320 or h < 240:
            return False, "invalid canvas size"
        for i, e in enumerate(elements):
            if not isinstance(e, dict):
                return False, f"elements[{i}] must be object"
            t = str(e.get("type", "")).lower()
            if t not in ("text", "arrow"):
                return False, f"elements[{i}] unsupported type={t}"
            if t == "text":
                if "text" not in e:
                    return False, f"elements[{i}] text missing"
                fs = int(e.get("font_size", 0) or 0)
                if fs <= 0 or fs > 200:
                    return False, f"elements[{i}] invalid font_size"
            if t == "arrow":
                for k in ("x1", "y1", "x2", "y2"):
                    if k not in e:
                        return False, f"elements[{i}] {k} missing"
        return True, "ok"

    def render_layout(self, spec: dict[str, Any], layout_id: str | None = None) -> dict[str, Any]:
        ok, msg = self.validate_layout(spec)
        if not ok:
            raise ValueError(msg)

        canvas = spec["canvas"]
        w = int(canvas["width"])
        h = int(canvas["height"])
        bg = str(canvas.get("background", "#111827"))

        image = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(image)

        for e in spec["elements"]:
            et = str(e.get("type", "")).lower()
            if et == "text":
                text = self._safe_text(e.get("text", ""), 200)
                x = int(e.get("x", 0) or 0)
                y = int(e.get("y", 0) or 0)
                fs = int(e.get("font_size", 24) or 24)
                color = str(e.get("font_color", "#f8fafc"))
                font = self._default_font(fs)
                draw.text((x, y), text, font=font, fill=color)
            elif et == "arrow":
                x1 = int(e.get("x1", 0) or 0)
                y1 = int(e.get("y1", 0) or 0)
                x2 = int(e.get("x2", 0) or 0)
                y2 = int(e.get("y2", 0) or 0)
                color = str(e.get("color", "#22d3ee"))
                thickness = int(e.get("thickness", 5) or 5)
                draw.line((x1, y1, x2, y2), fill=color, width=thickness)
                # Arrow head
                head = max(10, thickness * 3)
                draw.polygon(
                    [(x2, y2), (x2 - head, y2 - head // 2), (x2 - head, y2 + head // 2)],
                    fill=color,
                )

        lid = str(layout_id or uuid.uuid4().hex)
        png_path = self.layout_dir / f"{lid}.png"
        json_path = self.layout_dir / f"{lid}.json"
        image.save(png_path, format="PNG")
        json_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "layout_id": lid,
            "png_path": str(png_path),
            "json_path": str(json_path),
            "created_at": self._now_text(),
        }

