"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import StatCard from "@/components/StatCard";
import MarketViewCard from "@/components/MarketViewCard";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8010";
const STABILITY_MODE = true;
const ENDPOINTS = [
  { key: "health", path: "/health" },
  { key: "latest", path: "/trades/latest" },
  { key: "analytics", path: "/trades/analytics?days=60" },
  { key: "learningOverview", path: "/ml/learning-overview?days=60" },
  { key: "runtimeStatus", path: "/runtime/status" },
  { key: "positionsEnriched", path: "/positions/enriched" },
  { key: "opsReadiness", path: "/ops/readiness" },
  { key: "runtimeObservability", path: "/runtime/observability?last_n=50" },
];
const FAST_KEYS = new Set(STABILITY_MODE ? ["health", "latest", "positionsEnriched"] : ["health", "latest", "runtimeStatus", "positionsEnriched"]);
const SLOW_KEYS = new Set(STABILITY_MODE ? ["analytics", "learningOverview", "opsReadiness", "runtimeObservability", "runtimeStatus"] : ["analytics", "learningOverview", "opsReadiness", "runtimeObservability"]);
const FAST_ENDPOINTS = ENDPOINTS.filter((e) => FAST_KEYS.has(e.key));
const SLOW_ENDPOINTS = ENDPOINTS.filter((e) => SLOW_KEYS.has(e.key));
const FAST_POLL_MS = 3000;
const ROWS_POLL_MS = 7000;
const SLOW_POLL_MS = 15000;
const SLOW_MIN_GAP_MS = 15000;
const STALE_RECOVERY_MS = 12000;
const POSITION_STICKY_MAX_SEC = 10;
const TRADE_ROW_CACHE_LIMIT = 2500;
const FAST_ENDPOINT_POLICY = {
  health: { retries: 0, delay: 120, timeoutMs: 2800 },
  latest: { retries: 0, delay: 150, timeoutMs: 3600 },
  runtimeStatus: { retries: 0, delay: 180, timeoutMs: 5200 },
  positionsEnriched: { retries: 1, delay: 300, timeoutMs: 8000 },
};

const SYMBOLS = [
  { key: "ALL", label: "전체" },
  { key: "NAS100", label: "NAS100" },
  { key: "XAUUSD", label: "XAUUSD" },
  { key: "BTCUSD", label: "BTCUSD" },
];
const HISTORY_PAGE_SIZE = 10;
const PAGE_GROUP_SIZE = 10;

const SYMBOL_ALIASES = {
  BTCUSD: ["BTC", "XBT", "BTCUSD", "BTC/USD"],
  NAS100: ["NAS100", "US100", "USTEC", "NASDAQ"],
  XAUUSD: ["XAUUSD", "XAU", "GOLD", "XAU/USD"],
};

const RULE_GROUPS = [
  { key: "session_box", label: "3단 세션박스", baseScore: 80, keywords: ["박스", "session"] },
  { key: "daily_open", label: "당일 시가", baseScore: 50, keywords: ["당일 시가", "daily open"] },
  { key: "multi_sr", label: "다중 지지/저항", baseScore: 120, keywords: ["지지", "저항", "support", "resistance"] },
  { key: "rule_of_4", label: "4번의 법칙", baseScore: 80, keywords: ["4번", "rule of 4"] },
  { key: "double_bb_20_2", label: "더블 BB(20,2)", baseScore: 80, keywords: ["bb 20/2", "bb20", "bollinger 20,2"] },
  { key: "double_bb_4_4", label: "더블 BB(4,4)", baseScore: 50, keywords: ["bb 4/4", "bb4", "bollinger 4,4"] },
  { key: "disparity", label: "이격도(DI)", baseScore: 60, keywords: ["이격도", "disparity", "di"] },
  { key: "ma_align", label: "다중 이평선 정/역배열", baseScore: 80, keywords: ["이평", "ma", "정배열", "역배열"] },
  { key: "trendline", label: "추세선", baseScore: 70, keywords: ["추세선", "trend"] },
  { key: "rsi_div", label: "이격도 다이버전스(RSI)", baseScore: 40, keywords: ["rsi", "다이버", "divergence"] },
  { key: "wick", label: "캔들꼬리(윗/아랫꼬리)", baseScore: 60, keywords: ["망치", "역망치", "꼬리", "wick", "캔들"] },
];
const RULE_LABEL_MAP = RULE_GROUPS.reduce((acc, r) => {
  acc[r.key] = r.label;
  return acc;
}, {});

const MV_ZONE_LABELS = {
  ABOVE: "상단 밖",
  UPPER: "상단",
  UPPER_EDGE: "상단 근접",
  MIDDLE: "중앙",
  LOWER_EDGE: "하단 근접",
  LOWER: "하단",
  BELOW: "하단 밖",
  UNKNOWN: "미확인",
};

const MV_MARKET_MODE_LABELS = {
  RANGE: "박스장",
  TREND: "추세장",
  EXPANSION: "확장장",
  LOW_LIQUIDITY: "저유동성",
  SHOCK: "충격장",
};

const MV_LIQUIDITY_LABELS = {
  GOOD: "양호",
  NORMAL: "보통",
  THIN: "얇음",
  LOW: "낮음",
  UNKNOWN: "미확인",
};

const MV_REASON_LABELS = {
  middle_wait: "중앙 구간이라 Position 단독 진입을 보류합니다.",
  lower_edge_observe: "하단 컨텍스트는 맞지만 반등 확정이 아직 부족해 관찰만 유지합니다.",
  upper_approach_observe: "상단 접근 중이라 거절과 돌파 방향이 더 확인돼야 합니다.",
  outer_band_reversal_support_required_observe: "반전 근거는 있지만 BB44 외곽 지지가 아직 부족해 보류합니다.",
  conflict_box_lower_bb20_upper_upper_dominant_observe: "박스는 아래인데 밴드는 위라 충돌 상태로 봅니다.",
  conflict_box_upper_bb20_lower_lower_dominant_observe: "박스는 위인데 밴드는 아래라 충돌 상태로 봅니다.",
  lower_support_fail_confirm: "하단 지지가 무너졌다고 보고 SELL 확인으로 넘깁니다.",
  upper_reject_mixed_confirm: "상단 거절이 확인돼 SELL 확인으로 넘깁니다.",
  lower_rebound_confirm: "하단 지지 반등이 확인돼 BUY 확인으로 넘깁니다.",
};

function mvSafeFloat(value) {
  const out = Number(value || 0);
  return Number.isFinite(out) ? out : 0;
}

function mvPick(mapping, raw, fallback = "") {
  const key = String(raw || "").trim().toUpperCase();
  if (!key) return fallback;
  return mapping[key] || String(raw || "").replaceAll("_", " ").trim();
}

function mvReasonText(reason) {
  const key = String(reason || "").trim().toLowerCase();
  if (!key) return "특별한 차단 사유는 없지만 아직 확정 신호가 약합니다.";
  return MV_REASON_LABELS[key] || String(key).replaceAll("_", " ");
}

function mvPositionText(interp = {}, energy = {}) {
  const primary = String(interp?.primary_label || "").toUpperCase();
  const conflict = String(interp?.conflict_kind || "").toUpperCase();
  const lowerForce = mvSafeFloat(energy?.lower_position_force);
  const upperForce = mvSafeFloat(energy?.upper_position_force);
  const middle = mvSafeFloat(energy?.middle_neutrality);
  if (conflict) return `축이 서로 충돌해 Position 단독 판단을 보류합니다. (${conflict.replaceAll("_", " ")})`;
  if (primary === "ALIGNED_MIDDLE") return "중앙 구간이라 Position 단독 진입보다 반응 확인이 우선입니다.";
  if (primary === "LOWER_BIAS") return "하단 쪽 bias는 있지만 아직 확정 하단은 아닙니다.";
  if (primary === "UPPER_BIAS") return "상단 쪽 bias는 있지만 아직 확정 상단은 아닙니다.";
  if (primary === "UNRESOLVED_POSITION") return "위치가 애매해 뒤 레이어로 넘겨야 합니다.";
  if (primary === "ALIGNED_LOWER_STRONG") return "하단 정렬이 강합니다.";
  if (primary === "ALIGNED_UPPER_STRONG") return "상단 정렬이 강합니다.";
  if (middle >= 0.55) return "중앙 비중이 커서 Response와 State 확인이 우선입니다.";
  if (lowerForce > upperForce) return "하단 쪽 압력이 우세하지만 확정은 아닙니다.";
  if (upperForce > lowerForce) return "상단 쪽 압력이 우세하지만 확정은 아닙니다.";
  return "위치 에너지가 비슷해 방향 판단을 뒤로 넘깁니다.";
}

function mvActionSummary(action, side, reason) {
  const actionKey = String(action || "WAIT").toUpperCase();
  const sideKey = String(side || "").toUpperCase();
  if (actionKey === "WAIT" && sideKey === "BUY") return { badge: "BUY 관찰", tone: "good" };
  if (actionKey === "WAIT" && sideKey === "SELL") return { badge: "SELL 관찰", tone: "bad" };
  if (actionKey === "BUY") return { badge: "BUY 후보", tone: "good" };
  if (actionKey === "SELL") return { badge: "SELL 후보", tone: "bad" };
  if (String(reason || "").toLowerCase().includes("conflict")) return { badge: "충돌 대기", tone: "warn" };
  return { badge: "중립 대기", tone: "neutral" };
}

function mvNextTrigger(action, side, reason, zones = {}, interp = {}) {
  const reasonKey = String(reason || "").toLowerCase();
  const sideKey = String(side || "").toUpperCase();
  const primary = String(interp?.primary_label || "").toUpperCase();
  const bb44Zone = String(zones?.bb44_zone || "").toUpperCase();
  if (reasonKey === "middle_wait" || primary === "ALIGNED_MIDDLE") {
    return "지지/저항 anchor나 상하단 재접촉이 나오기 전까지 대기합니다.";
  }
  if (reasonKey.includes("outer_band_reversal_support_required")) {
    return "BB44가 외곽으로 더 붙거나 S/R 지지가 더 분명해지면 반전 진입을 다시 봅니다.";
  }
  if (reasonKey.includes("lower") || sideKey === "BUY") {
    if (bb44Zone === "MIDDLE") return "하단 지지 유지가 더 선명해지면 BUY를 보고, 하단 붕괴가 이어지면 SELL로 전환합니다.";
    return "하단 지지 유지/재탈환이 더 강해지면 BUY, 하단 붕괴면 SELL로 전환합니다.";
  }
  if (reasonKey.includes("upper") || sideKey === "SELL") {
    return "상단 거절이 더 선명해지면 SELL을 보고, 상단 돌파가 이어지면 BUY로 전환합니다.";
  }
  return "다음 박스 끝단 접촉이나 명확한 반응이 나올 때까지 관찰합니다.";
}

function buildMarketViewFallback(runtimeStatus = {}) {
  const latestBySymbol = runtimeStatus?.latest_signal_by_symbol || {};
  const symbols = Array.isArray(runtimeStatus?.symbols) ? runtimeStatus.symbols : Object.keys(latestBySymbol || {});
  const items = symbols.map((symbol) => {
    const signal = latestBySymbol?.[symbol] || {};
    const context = signal?.current_entry_context_v1 || {};
    const meta = context?.metadata || {};
    const snapshot = signal?.position_snapshot_v2 || {};
    const zones = snapshot?.zones || meta?.position_zones_v2 || {};
    const interp = snapshot?.interpretation || meta?.position_interpretation_v2 || {};
    const energy = snapshot?.energy || meta?.position_energy_v2 || {};
    const obs = meta?.observe_confirm_v2 || meta?.observe_confirm_v1 || {};
    const state = meta?.state_raw_snapshot_v1 || {};
    const actionMeta = mvActionSummary(obs?.action, obs?.side, obs?.reason);
    const locationSummary = `박스 ${mvPick(MV_ZONE_LABELS, zones?.box_zone, "미확인")} / BB20 ${mvPick(MV_ZONE_LABELS, zones?.bb20_zone, "미확인")} / BB44 ${mvPick(MV_ZONE_LABELS, zones?.bb44_zone, "미확인")}`;
    const positionSummary = mvPositionText(interp, energy);
    const decisionSummary = mvReasonText(obs?.reason);
    return {
      symbol,
      market_mode: mvPick(MV_MARKET_MODE_LABELS, state?.market_mode || signal?.market_mode, "미확인"),
      liquidity: mvPick(MV_LIQUIDITY_LABELS, state?.liquidity_state || signal?.liquidity_state, "미확인"),
      location_summary: locationSummary,
      position_summary: positionSummary,
      action_badge: actionMeta.badge,
      action_tone: actionMeta.tone,
      decision_summary: decisionSummary,
      next_trigger: mvNextTrigger(obs?.action, obs?.side, obs?.reason, zones, interp),
      logs: [
        { label: "현재 위치", text: locationSummary },
        { label: "Position", text: positionSummary },
        { label: "현재 판단", text: `${actionMeta.badge} - ${decisionSummary}` },
        { label: "게이트", text: `Preflight ${String(meta?.preflight_allowed_action_raw || "UNKNOWN").toUpperCase()} / Observe ${String(obs?.state || "-").toUpperCase()}` },
        { label: "위치 에너지", text: `하단 ${mvSafeFloat(energy?.lower_position_force).toFixed(2)} / 상단 ${mvSafeFloat(energy?.upper_position_force).toFixed(2)} / 중립 ${mvSafeFloat(energy?.middle_neutrality).toFixed(2)}` },
      ],
    };
  });
  return {
    updated_at: String(runtimeStatus?.updated_at || "-"),
    items,
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function withHardTimeout(promise, timeoutMs, label = "request") {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`${label} hard-timeout`)), Math.max(800, Number(timeoutMs || 5000)));
    Promise.resolve(promise)
      .then((v) => {
        clearTimeout(t);
        resolve(v);
      })
      .catch((e) => {
        clearTimeout(t);
        reject(e);
      });
  });
}

async function fetchJsonWithRetry(path, retries = 3, baseDelayMs = 300, timeoutMs = 12000) {
  let lastError = null;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), Math.max(300, Number(timeoutMs || 12000)));
    try {
      const res = await fetch(`${API_BASE}${path}`, { cache: "no-store", signal: ctrl.signal });
      clearTimeout(timeout);
      if (!res.ok) {
        const err = new Error(`${path} ${res.status}`);
        err.status = res.status;
        if (res.status >= 500 && attempt < retries) {
          await sleep(baseDelayMs * 2 ** attempt);
          lastError = err;
          continue;
        }
        throw err;
      }
      return res.json();
    } catch (e) {
      clearTimeout(timeout);
      lastError = e;
      const status = Number(e?.status || 0);
      if (status >= 400 && status < 500) throw lastError;
      if (attempt < retries) {
        await sleep(baseDelayMs * 2 ** attempt);
        continue;
      }
      throw lastError;
    }
  }
  throw lastError || new Error("Unknown fetch error");
}

function rowTs(row = {}) {
  const closeTs = Number(row?.close_ts || 0);
  const openTs = Number(row?.open_ts || 0);
  const rawTs = Number(row?.row_ts || 0);
  return Math.max(rawTs, closeTs, openTs, 0);
}

function rowKey(row = {}) {
  const ticket = Number(row?.ticket || 0);
  const status = String(row?.status || "").toUpperCase();
  const ts = rowTs(row);
  const symbol = String(row?.symbol || "").toUpperCase();
  return `${ticket}|${status}|${symbol}|${ts}`;
}

function mergeRows(existing = [], incoming = [], maxRows = TRADE_ROW_CACHE_LIMIT) {
  const merged = new Map();
  [...(existing || []), ...(incoming || [])].forEach((row) => {
    merged.set(rowKey(row), row);
  });
  return Array.from(merged.values())
    .sort((a, b) => rowTs(b) - rowTs(a))
    .slice(0, Math.max(50, Number(maxRows || TRADE_ROW_CACHE_LIMIT)));
}

function HelpTip({ text, corner = false }) {
  return (
    <span className={`help-tip ${corner ? "corner" : ""}`}>
      ?
      <span className="help-pop">{text}</span>
    </span>
  );
}

function CardHead({ title, help }) {
  return (
    <div className="card-head">
      <h2>{title}</h2>
      {help ? <HelpTip text={help} corner /> : null}
    </div>
  );
}

function Sparkline({
  points = [],
  labels = [],
  stroke = "#2563eb",
  fill = "rgba(37,99,235,0.15)",
  height = 160,
  valueFormatter = (v) => Number(v || 0).toFixed(2),
}) {
  const [hover, setHover] = useState(null);
  if (!points.length) return <div className="empty-chart">데이터 없음</div>;
  const width = 720;
  const values = points.map((p) => Number(p || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = values.length > 1 ? width / (values.length - 1) : width;
  const coords = values.map((v, i) => {
    const x = i * step;
    const y = height - ((v - min) / range) * (height - 20) - 10;
    return [x, y];
  });
  const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c[0]} ${c[1]}`).join(" ");
  const areaPath = `${linePath} L ${coords[coords.length - 1][0]} ${height} L 0 ${height} Z`;
  return (
    <div className="spark-wrap">
      <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <path d={areaPath} fill={fill} />
        <path d={linePath} stroke={stroke} strokeWidth="2.5" fill="none" />
        {coords.map(([x, y], i) => {
          const label = String(labels?.[i] || `${i + 1}`);
          const val = Number(values?.[i] || 0);
          return (
            <circle
              key={`dot-${i}`}
              className="spark-dot"
              cx={x}
              cy={y}
              r="3.1"
              fill={stroke}
              onMouseEnter={() => setHover({ x, y, label, val })}
              onMouseMove={() => setHover({ x, y, label, val })}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
      </svg>
      {hover ? (
        <div
          className="spark-tooltip"
          style={{
            left: `${(hover.x / width) * 100}%`,
            top: `${(hover.y / height) * 100}%`,
          }}
        >
          <strong>{hover.label}</strong>
          <span>{valueFormatter(hover.val)}</span>
        </div>
      ) : null}
    </div>
  );
}

function BlendMiniTimeline({ rows = [] }) {
  const data = (rows || [])
    .map((r) => ({
      ts: String(r?.ts || ""),
      rule: Number(r?.rule_weight || 0),
      model: Number(r?.model_weight || 0),
    }))
    .filter((r) => Number.isFinite(r.rule) && Number.isFinite(r.model));
  if (!data.length) return <div className="empty-chart">blend history 없음</div>;

  const width = 520;
  const height = 120;
  const pad = 10;
  const maxY = 1.0;
  const minY = 0.0;
  const range = maxY - minY || 1;
  const step = data.length > 1 ? (width - pad * 2) / (data.length - 1) : width - pad * 2;

  const toY = (v) => height - pad - ((Number(v) - minY) / range) * (height - pad * 2);
  const toPath = (arr, key) =>
    arr
      .map((d, i) => {
        const x = pad + i * step;
        const y = toY(d[key]);
        return `${i === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");

  const rulePath = toPath(data, "rule");
  const modelPath = toPath(data, "model");
  const last = data[data.length - 1] || { rule: 0, model: 0, ts: "" };

  return (
    <div>
      <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line x1={pad} y1={toY(0.5)} x2={width - pad} y2={toY(0.5)} stroke="rgba(148,163,184,0.35)" strokeWidth="1" />
        <path d={rulePath} stroke="#2563eb" strokeWidth="2.2" fill="none" />
        <path d={modelPath} stroke="#16a34a" strokeWidth="2.2" fill="none" />
      </svg>
      <div className="axis-note">
        <span>Rule(파랑): {Number(last.rule || 0).toFixed(3)}</span>
        <span>Model(초록): {Number(last.model || 0).toFixed(3)}</span>
        <span>최근: {String(last.ts || "-").slice(11, 19) || "-"}</span>
      </div>
    </div>
  );
}

function ExpectancyMiniTable({ title = "", data = {}, maxRows = 6 }) {
  const [sortBy, setSortBy] = useState("expectancy");
  const [sortDir, setSortDir] = useState("desc");
  const rows = Object.entries(data || {})
    .map(([key, raw]) => ({
      key: String(key || "-"),
      expectancy: Number(raw?.expectancy || 0),
      trades: Number(raw?.trades || 0),
      winRate: Number(raw?.win_rate || 0),
    }))
    .filter((r) => Number.isFinite(r.expectancy));

  const cmp = (a, b) => {
    let v = 0;
    if (sortBy === "key") v = a.key.localeCompare(b.key);
    else if (sortBy === "trades") v = a.trades - b.trades;
    else v = a.expectancy - b.expectancy;
    return sortDir === "asc" ? v : -v;
  };
  const sorted = [...rows].sort(cmp).slice(0, Math.max(1, Number(maxRows || 6)));

  if (!sorted.length) {
    return (
      <div>
        <strong>{title}</strong>: -
      </div>
    );
  }

  const scoreOrdered = [...sorted].sort((a, b) => b.expectancy - a.expectancy);
  const topKey = scoreOrdered[0]?.key;
  const bottomKey = scoreOrdered[scoreOrdered.length - 1]?.key;

  return (
    <div style={{ minWidth: 360 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <strong>{title}</strong>
        <button type="button" className={`pager-btn page-num ${sortBy === "expectancy" ? "active" : ""}`} onClick={() => setSortBy("expectancy")}>Expectancy</button>
        <button type="button" className={`pager-btn page-num ${sortBy === "trades" ? "active" : ""}`} onClick={() => setSortBy("trades")}>Trades</button>
        <button type="button" className={`pager-btn page-num ${sortBy === "key" ? "active" : ""}`} onClick={() => setSortBy("key")}>Key</button>
        <button type="button" className="pager-btn page-num" onClick={() => setSortDir((p) => (p === "desc" ? "asc" : "desc"))}>
          {sortDir === "desc" ? "Desc" : "Asc"}
        </button>
      </div>
      <div style={{ marginTop: 6, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid rgba(148,163,184,0.35)", padding: "4px 6px" }}>Key</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid rgba(148,163,184,0.35)", padding: "4px 6px" }}>Expectancy</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid rgba(148,163,184,0.35)", padding: "4px 6px" }}>Trades</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid rgba(148,163,184,0.35)", padding: "4px 6px" }}>Win%</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const isTop = r.key === topKey;
              const isBottom = r.key === bottomKey && sorted.length > 1;
              const bg = isTop ? "rgba(22,163,74,0.08)" : isBottom ? "rgba(220,38,38,0.08)" : "transparent";
              return (
                <tr key={`${title}-${r.key}`} style={{ background: bg }}>
                  <td style={{ padding: "4px 6px", whiteSpace: "nowrap" }}>{r.key}</td>
                  <td style={{ padding: "4px 6px", textAlign: "right" }}>
                    <span className={r.expectancy >= 0 ? "fg-good" : "fg-bad"}>{r.expectancy.toFixed(3)}</span>
                  </td>
                  <td style={{ padding: "4px 6px", textAlign: "right" }}>{r.trades}</td>
                  <td style={{ padding: "4px 6px", textAlign: "right" }}>{(r.winRate * 100).toFixed(1)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function blendSignalTone({ value = 0, warnMin = 0.3, warnMax = 0.7, badMin = 0.15, badMax = 0.85 }) {
  const v = Number(value || 0);
  if (!Number.isFinite(v)) return "warn";
  if (v <= badMin || v >= badMax) return "bad";
  if (v <= warnMin || v >= warnMax) return "warn";
  return "good";
}

function FourHourBars({ rows = [] }) {
  if (!rows.length) return <div className="empty-chart">데이터 없음</div>;
  const subset = rows.slice(-18);
  const maxAbs = Math.max(1, ...subset.map((r) => Math.abs(Number(r.pnl || 0))));
  return (
    <div className="pnl-bars">
      {subset.map((r) => {
        const v = Number(r.pnl || 0);
        const h = Math.max(8, Math.round((Math.abs(v) / maxAbs) * 86));
        return (
          <div className="pnl-col" key={r.bucket}>
            <div className="pnl-value">{v.toFixed(1)}</div>
            <div className="pnl-axis">
              <div className={`pnl-bar ${v >= 0 ? "good" : "bad"}`} style={{ height: `${h}px` }} />
            </div>
            <div className="pnl-day">{String(r.bucket || "").slice(6)}</div>
          </div>
        );
      })}
    </div>
  );
}

function ReasonBars({ rows = [] }) {
  if (!rows.length) return <div className="empty-chart">데이터 없음</div>;
  const maxCount = Math.max(...rows.map((r) => Number(r.count || 0)), 1);
  const labelOf = (reason) => {
    const raw = String(reason || "").trim();
    const primary = raw.split(",")[0]?.trim() || "UNKNOWN";
    return primary.replace(/\s*\([+-]?\d+[^)]*\)\s*$/, "");
  };
  return (
    <div className="bars">
      {rows.map((r) => {
        const width = Math.max(8, Math.round((Number(r.count || 0) / maxCount) * 100));
        const pnl = Number(r.pnl || 0);
        const label = labelOf(r.reason);
        return (
          <div key={r.reason} className="bar-row">
            <div className="bar-head">
              <strong title={String(r.reason || "")}>{label}</strong>
              <span>
                n={r.count} | 승률 {(Number(r.win_rate || 0) * 100).toFixed(1)}% | 손익 {pnl.toFixed(2)}
              </span>
            </div>
            <div className="bar-track">
              <div className={`bar-fill ${pnl >= 0 ? "good" : "bad"}`} style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RatioBars({ rows = [], labelKey = "label", valueKey = "ratio" }) {
  if (!rows.length) return <div className="empty-chart">데이터 없음</div>;
  return (
    <div className="bars">
      {rows.map((r) => {
        const ratio = Math.max(0, Math.min(1, Number(r[valueKey] || 0)));
        const width = Math.max(8, Math.round(ratio * 100));
        return (
          <div key={`${r[labelKey]}`} className="bar-row">
            <div className="bar-head">
              <strong title={r[labelKey]}>{r[labelKey]}</strong>
              <span>{(ratio * 100).toFixed(1)}%</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill good" style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function normalizeText(s) {
  return String(s || "").toLowerCase();
}

function containsAnyKeyword(text, keywords = []) {
  const src = normalizeText(text);
  return (keywords || []).some((k) => src.includes(normalizeText(k)));
}

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : NaN;
}

function ruleMatchedByIndicators(row = {}, ruleKey = "") {
  const close = toNum(row.close_price);
  const bb4Up = toNum(row.ind_bb_4_up);
  const bb4Dn = toNum(row.ind_bb_4_dn);
  const disp = toNum(row.ind_disparity);
  const ma20 = toNum(row.ind_ma_20);
  const ma60 = toNum(row.ind_ma_60);
  const ma120 = toNum(row.ind_ma_120);

  if (ruleKey === "double_bb_4_4") {
    if (!Number.isFinite(close) || !Number.isFinite(bb4Up) || !Number.isFinite(bb4Dn) || bb4Up <= bb4Dn) return false;
    const width = bb4Up - bb4Dn;
    const nearBand = Math.min(Math.abs(close - bb4Up), Math.abs(close - bb4Dn)) <= width * 0.20;
    const breakout = close >= bb4Up || close <= bb4Dn;
    return nearBand || breakout;
  }

  if (ruleKey === "disparity") {
    if (!Number.isFinite(disp)) return false;
    return Math.abs(disp - 100.0) >= 1.5;
  }

  if (ruleKey === "trendline") {
    if (!Number.isFinite(close) || !Number.isFinite(ma20) || !Number.isFinite(ma60)) return false;
    const slopePower = Math.abs(ma20 - ma60) / Math.max(1.0, Math.abs(close));
    const aligned3 = Number.isFinite(ma120) && ((ma20 > ma60 && ma60 > ma120) || (ma20 < ma60 && ma60 < ma120));
    return aligned3 || slopePower >= 0.0004;
  }

  return false;
}

function splitReasonText(reasonText = "") {
  return String(reasonText || "")
    .split(/,(?![^()]*\))/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function estimateReasonWeight(reasonText = "") {
  const s = String(reasonText || "").toLowerCase();
  if (!s) return 0;
  if (s.includes("rsi")) return 40;
  if (s.includes("bb 20/2")) return 80;
  if (s.includes("bb 4/4")) return 50;
  if (s.includes("4번") || s.includes("rule of 4")) return 80;
  if (s.includes("1분") || s.includes("1m")) return 20;
  if (s.includes("버퍼") || s.includes("buffer")) return 40;
  if (s.includes("당일 시가") || s.includes("daily open")) return 50;
  if (s.includes("돌파") || s.includes("break")) return 150;
  if (s.includes("지지") || s.includes("저항") || s.includes("support") || s.includes("resistance")) return 120;
  if (s.includes("이격") || s.includes("disparity") || s.includes("과열") || s.includes("침체")) return 60;
  if (s.includes("정배열") || s.includes("역배열") || s.includes("alignment")) return 80;
  if (s.includes("망치") || s.includes("캔들") || s.includes("wick")) return 60;
  if (s.includes("reversal")) return 150;
  if (s.includes("adverse stop")) return 70;
  if (s.includes("adverse reversal")) return 220;
  if (s.includes("target")) return 120;
  return 50;
}

function stripScoreSuffix(reasonText = "") {
  return String(reasonText || "").replace(/\s*\([+-]?\d+[^)]*\)\s*$/, "").trim();
}

function formatValue(v, digits = 2) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(digits);
}

function indicatorEntries(row = {}) {
  const defs = [
    ["ind_rsi", "RSI"],
    ["ind_adx", "ADX"],
    ["ind_plus_di", "+DI"],
    ["ind_minus_di", "-DI"],
    ["ind_disparity", "이격도"],
    ["ind_bb_20_up", "BB20 상단"],
    ["ind_bb_20_mid", "BB20 중심"],
    ["ind_bb_20_dn", "BB20 하단"],
    ["ind_bb_4_up", "BB4 상단"],
    ["ind_bb_4_dn", "BB4 하단"],
  ];
  return defs
    .map(([key, label]) => [key, label, row?.[key]])
    .filter(([, , value]) => Number.isFinite(Number(value)));
}

function decorateReasonsWithTotal(reasons = [], totalScore = 0) {
  const rows = (reasons || []).map((r) => {
    const raw = String(r || "").trim();
    const m = raw.match(/\(([+-]?\d+)[^)]*\)\s*$/);
    const explicit = m ? Number(m[1] || 0) : null;
    return {
      text: stripScoreSuffix(raw),
      explicit,
      weight: estimateReasonWeight(raw),
    };
  }).filter((x) => x.text);

  if (!rows.length) return [];

  const target = Number(totalScore || 0);
  const allExplicit = rows.every((x) => Number.isFinite(x.explicit));
  let scores = [];

  if (allExplicit) {
    const base = rows.map((x) => Number(x.explicit || 0));
    const sum = base.reduce((a, b) => a + b, 0);
    if (sum === target) {
      scores = base;
    } else if (sum !== 0) {
      scores = base.map((v) => Math.round((v / sum) * target));
      const diff = target - scores.reduce((a, b) => a + b, 0);
      scores[0] += diff;
    } else {
      scores = Array(rows.length).fill(0);
      scores[0] = target;
    }
  } else {
    const wSum = rows.reduce((a, b) => a + Math.max(1, Number(b.weight || 1)), 0);
    scores = rows.map((x) => Math.round((Math.max(1, Number(x.weight || 1)) / wSum) * target));
    const diff = target - scores.reduce((a, b) => a + b, 0);
    scores[0] += diff;
  }

  return rows.map((r, i) => `${r.text} (${scores[i] >= 0 ? "+" : ""}${scores[i]}점)`);
}

export default function HomePage() {
  const inFlightRef = useRef(false);
  const slowInFlightRef = useRef(false);
  const rowsInFlightRef = useRef(false);
  const lastLoadAtRef = useRef(0);
  const lastSlowAtRef = useRef(0);
  const lastAnyUpdateAtRef = useRef(0);
  const lastGoodPositionsRef = useRef({ connected: false, items: [], at: 0 });
  const lastRowTsRef = useRef({ OPEN: 0, CLOSED: 0 });
  const eventSourceRef = useRef(null);
  const sseStatsRef = useRef({ reconnect_count: 0, last_event_at: "", last_error_at: "", connected: false, connected_at: "" });
  const pollCountRef = useRef(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");
  const [apiStatus, setApiStatus] = useState({});
  const [apiPerf, setApiPerf] = useState({ endpoints: {}, rowsOpenMs: 0, rowsClosedMs: 0, lastPollMs: 0, updatedAt: "" });
  const [sseStatus, setSseStatus] = useState({ reconnect_count: 0, last_event_at: "", last_error_at: "", connected: false, connected_at: "" });
  const [slowRefreshing, setSlowRefreshing] = useState(false);
  const [positionsStaleStreak, setPositionsStaleStreak] = useState(0);
  const [tabSymbol, setTabSymbol] = useState("ALL");
  const [dockOpen, setDockOpen] = useState(false);
  const [historyPage, setHistoryPage] = useState({ BTCUSD: 1, NAS100: 1, XAUUSD: 1 });
  const [data, setData] = useState({
    summary: null,
    analytics: {
      daily: [],
      pnl_4h: [],
      pnl_4h_by_symbol: { BTCUSD: [], NAS100: [], XAUUSD: [] },
      fee_total: 0,
      entry_reasons: [],
      exit_reasons: [],
      quality: {},
    },
    positionsEnriched: { connected: false, items: [] },
    mt5: null,
    runtimeStatus: null,
    learningOverview: null,
    opsReadiness: null,
    runtimeObservability: null,
    recent: [],
    closedRecent: [],
  });

  const timedFetch = async (path, retries = 2, delay = 400, timeoutMs = 3500) => {
    const t0 = performance.now();
    try {
      const value = await fetchJsonWithRetry(path, retries, delay, timeoutMs);
      return { value, elapsedMs: Math.max(0, performance.now() - t0) };
    } catch (error0) {
      throw {
        error: error0,
        elapsedMs: Math.max(0, performance.now() - t0),
      };
    }
  };

  const loadIncrementalRows = async (includeFullSnapshot = false, forceSync = false) => {
    const openSince = includeFullSnapshot ? 0 : Number(lastRowTsRef.current.OPEN || 0);
    const closedSince = includeFullSnapshot ? 0 : Number(lastRowTsRef.current.CLOSED || 0);
    const syncQuery = forceSync ? "&sync=true" : "";
    const [openRowsResult, closedRowsResult] = await Promise.allSettled([
      timedFetch(`/trades/rows?status=OPEN&since_ts=${openSince}&limit=${includeFullSnapshot ? 800 : 300}${syncQuery}`, 1, 300, 9000),
      timedFetch(`/trades/rows?status=CLOSED&since_ts=${closedSince}&limit=${includeFullSnapshot ? 1200 : 500}${syncQuery}`, 1, 300, 9000),
    ]);

    return { openRowsResult, closedRowsResult };
  };

  const loadRowsOnly = async ({ fullRows = false, syncRows = false } = {}) => {
    if (rowsInFlightRef.current) return;
    rowsInFlightRef.current = true;
    try {
      const rowLoad = await loadIncrementalRows(Boolean(fullRows), Boolean(syncRows));
      let closedFallback = null;
      try {
        const closedOk = rowLoad.closedRowsResult.status === "fulfilled";
        const closedItems = closedOk
          ? (Array.isArray(rowLoad.closedRowsResult.value?.value?.items) ? rowLoad.closedRowsResult.value?.value?.items : [])
          : [];
        if (!closedOk || (Boolean(fullRows) && closedItems.length === 0)) {
          closedFallback = await timedFetch(
            `/trades/closed_recent?limit=${fullRows ? 1200 : 300}&lookback_days=30${syncRows ? "&sync=true" : ""}`,
            0,
            250,
            9000,
          );
        }
      } catch (_) {
        closedFallback = null;
      }
      const rowStatus = {};
      const rowPerf = {};
      setData((prev) => {
        const next = { ...prev };
        if (rowLoad.openRowsResult.status === "fulfilled") {
          const val = rowLoad.openRowsResult.value?.value || {};
          const elapsed = Number(rowLoad.openRowsResult.value?.elapsedMs || 0);
          const items = Array.isArray(val?.items) ? val.items : [];
          next.recent = mergeRows(fullRows ? [] : next.recent, items, TRADE_ROW_CACHE_LIMIT);
          lastRowTsRef.current.OPEN = Math.max(
            Number(lastRowTsRef.current.OPEN || 0),
            Number(val?.next_since_ts || 0),
            ...items.map((x) => rowTs(x)),
          );
          rowStatus.rowsOpen = { ok: true, message: `+${items.length} (${elapsed.toFixed(0)}ms)` };
          rowPerf.rowsOpen = elapsed;
        } else {
          const elapsed = Number(rowLoad.openRowsResult.reason?.elapsedMs || 0);
          const reasonText = String(rowLoad.openRowsResult.reason?.error || rowLoad.openRowsResult.reason || "").slice(0, 70);
          rowStatus.rowsOpen = { ok: false, message: `${reasonText} ${elapsed > 0 ? `(${elapsed.toFixed(0)}ms)` : ""}`.trim() };
          rowPerf.rowsOpen = elapsed;
        }

        if (rowLoad.closedRowsResult.status === "fulfilled") {
          const val = rowLoad.closedRowsResult.value?.value || {};
          const elapsed = Number(rowLoad.closedRowsResult.value?.elapsedMs || 0);
          const fromRows = Array.isArray(val?.items) ? val.items : [];
          const fromFallback = Array.isArray(closedFallback?.value?.items) ? closedFallback.value.items : [];
          const items = fromRows.length > 0 ? fromRows : fromFallback;
          next.closedRecent = mergeRows(fullRows ? [] : next.closedRecent, items, TRADE_ROW_CACHE_LIMIT);
          lastRowTsRef.current.CLOSED = Math.max(
            Number(lastRowTsRef.current.CLOSED || 0),
            Number(val?.next_since_ts || 0),
            ...items.map((x) => rowTs(x)),
          );
          const fallbackMs = Number(closedFallback?.elapsedMs || 0);
          const finalMs = elapsed > 0 ? elapsed : fallbackMs;
          rowStatus.rowsClosed = { ok: true, message: `+${items.length} (${finalMs.toFixed(0)}ms)` };
          rowPerf.rowsClosed = finalMs;
        } else {
          const fallbackItems = Array.isArray(closedFallback?.value?.items) ? closedFallback.value.items : [];
          if (fallbackItems.length > 0) {
            next.closedRecent = mergeRows(fullRows ? [] : next.closedRecent, fallbackItems, TRADE_ROW_CACHE_LIMIT);
            lastRowTsRef.current.CLOSED = Math.max(
              Number(lastRowTsRef.current.CLOSED || 0),
              ...fallbackItems.map((x) => rowTs(x)),
            );
            const fallbackMs = Number(closedFallback?.elapsedMs || 0);
            rowStatus.rowsClosed = { ok: true, message: `+${fallbackItems.length} (${fallbackMs.toFixed(0)}ms, fallback)` };
            rowPerf.rowsClosed = fallbackMs;
          } else {
            const elapsed = Number(rowLoad.closedRowsResult.reason?.elapsedMs || 0);
            const reasonText = String(rowLoad.closedRowsResult.reason?.error || rowLoad.closedRowsResult.reason || "").slice(0, 70);
            rowStatus.rowsClosed = { ok: false, message: `${reasonText} ${elapsed > 0 ? `(${elapsed.toFixed(0)}ms)` : ""}`.trim() };
            rowPerf.rowsClosed = elapsed;
          }
        }
        return next;
      });
      setApiStatus((prev) => ({ ...prev, ...rowStatus }));
      setApiPerf((prev) => ({
        ...prev,
        rowsOpenMs: Number(rowPerf.rowsOpen || 0),
        rowsClosedMs: Number(rowPerf.rowsClosed || 0),
      }));
    } catch (_) {
      // no-op
    } finally {
      rowsInFlightRef.current = false;
    }
  };

  const load = async ({ forceSlow = false, includeRows = false, fullRows = false, syncRows = false } = {}) => {
    if (inFlightRef.current) return;
    const now = Date.now();
    if (!forceSlow && (now - Number(lastLoadAtRef.current || 0)) < 2000) return;
    lastLoadAtRef.current = now;
    inFlightRef.current = true;
    pollCountRef.current += 1;
    const endpoints = FAST_ENDPOINTS;
    setLoading(true);
    setError("");
    try {
      const pollStart = performance.now();
      const fetchFastEndpoint = (ep) => {
        const p = FAST_ENDPOINT_POLICY[ep.key] || { retries: 0, delay: 180, timeoutMs: 3500 };
        return withHardTimeout(
          timedFetch(ep.path, p.retries, p.delay, p.timeoutMs),
          Number(p.timeoutMs || 3500) + 1600,
          `fast:${ep.key}`,
        );
      };
      const settled = await Promise.allSettled(endpoints.map((e) => fetchFastEndpoint(e)));
      const nextStatus = {};
      const perfEndpoints = {};
      setData((prev) => {
        const next = { ...prev };
        endpoints.forEach((ep, idx) => {
          const item = settled[idx];
          if (item.status === "fulfilled") {
            const elapsed = Number(item.value?.elapsedMs || 0);
            perfEndpoints[ep.key] = elapsed;
            nextStatus[ep.key] = { ok: true, message: `정상 ${elapsed.toFixed(0)}ms` };
            const val = item.value?.value;
            if (ep.key === "latest") next.summary = val.summary || next.summary;
            else if (ep.key === "analytics") next.analytics = val || next.analytics;
            else if (ep.key === "runtimeStatus") next.runtimeStatus = val.status || null;
            else if (ep.key === "learningOverview") next.learningOverview = val || null;
            else if (ep.key === "opsReadiness") next.opsReadiness = val || null;
            else if (ep.key === "runtimeObservability") next.runtimeObservability = val || null;
            else if (ep.key === "positionsEnriched") {
              next.positionsEnriched = val || next.positionsEnriched;
              const items = Array.isArray(val?.items) ? val.items : [];
              // Keep the last good snapshot to prevent UI flicker on transient MT5/API hiccups.
              if (val?.connected && items.length > 0) {
                lastGoodPositionsRef.current = {
                  connected: true,
                  items,
                  at: Date.now(),
                };
              }
            }
            else if (ep.key === "mt5") next.mt5 = val || null;
          } else {
            const elapsed = Number(item.reason?.elapsedMs || 0);
            perfEndpoints[ep.key] = elapsed;
            const reasonText = String(item.reason?.error || item.reason || "").slice(0, 70);
            nextStatus[ep.key] = { ok: false, message: `${reasonText} ${elapsed > 0 ? `(${elapsed.toFixed(0)}ms)` : ""}`.trim() };
          }
        });

        return next;
      });
      setApiStatus((prev) => ({ ...prev, ...nextStatus }));
      setApiPerf((prev) => ({
        ...prev,
        endpoints: perfEndpoints,
        lastPollMs: Math.max(0, performance.now() - pollStart),
        updatedAt: new Date().toISOString(),
      }));
      lastAnyUpdateAtRef.current = Date.now();
      setLastUpdated(new Date().toLocaleString("ko-KR"));
      const statusValues = Object.values(nextStatus);
      if (statusValues.length > 0 && statusValues.every((s) => !s.ok)) {
        setError("모든 API 호출이 실패했습니다. FastAPI 서버 상태를 확인하세요.");
      }
      if (includeRows) void loadRowsOnly({ fullRows, syncRows });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  };

  const loadSlow = async ({ force = false } = {}) => {
    const now = Date.now();
    if (!force && (now - Number(lastSlowAtRef.current || 0)) < SLOW_MIN_GAP_MS) return;
    if (slowInFlightRef.current) return;
    slowInFlightRef.current = true;
    lastSlowAtRef.current = now;
    setSlowRefreshing(true);
    try {
      const settled = await Promise.allSettled(
        SLOW_ENDPOINTS.map((e) =>
          withHardTimeout(
            timedFetch(e.path, 0, 250, 6500),
            8200,
            `slow:${e.key}`,
          ),
        ),
      );
      const slowStatus = {};
      setData((prev) => {
        const next = { ...prev };
        settled.forEach((item, idx) => {
          const ep = SLOW_ENDPOINTS[idx];
          if (item.status === "fulfilled") {
            const val = item.value?.value;
            const elapsed = Number(item.value?.elapsedMs || 0);
            slowStatus[ep.key] = { ok: true, message: `정상 ${elapsed.toFixed(0)}ms` };
            if (ep.key === "analytics") next.analytics = val || next.analytics;
            if (ep.key === "learningOverview") next.learningOverview = val || next.learningOverview;
            if (ep.key === "opsReadiness") next.opsReadiness = val || next.opsReadiness;
            if (ep.key === "runtimeObservability") next.runtimeObservability = val || next.runtimeObservability;
          } else {
            const elapsed = Number(item.reason?.elapsedMs || 0);
            const reasonText = String(item.reason?.error || item.reason || "").slice(0, 70);
            slowStatus[ep.key] = {
              ok: false,
              message: `${reasonText} ${elapsed > 0 ? `(${elapsed.toFixed(0)}ms)` : ""}`.trim(),
            };
          }
        });
        return next;
      });
      setApiStatus((prev) => ({ ...prev, ...slowStatus }));
      lastAnyUpdateAtRef.current = Date.now();
    } catch (_) {
      // no-op
    } finally {
      setSlowRefreshing(false);
      slowInFlightRef.current = false;
    }
  };

  useEffect(() => {
    setApiStatus(
      ENDPOINTS.reduce((acc, ep) => {
        if (STABILITY_MODE && SLOW_KEYS.has(ep.key)) {
          acc[ep.key] = { ok: true, message: "안정모드(수동 새로고침)" };
        } else {
          acc[ep.key] = { ok: false, message: "요청 시작" };
        }
        return acc;
      }, {}),
    );
    load({ includeRows: false });
    void loadRowsOnly({ fullRows: true, syncRows: false });
    const tWarmSync = setTimeout(() => {
      void loadRowsOnly({ fullRows: false, syncRows: true });
    }, 30000);
    if (!STABILITY_MODE) {
      loadSlow({ force: true });
    }
    const tFast = setInterval(() => load({ includeRows: false }), FAST_POLL_MS);
    const tRows = setInterval(() => loadRowsOnly(), ROWS_POLL_MS);
    const tSlow = STABILITY_MODE ? null : setInterval(() => loadSlow(), SLOW_POLL_MS);
    const tStale = setInterval(() => {
      const lastTs = Number(lastAnyUpdateAtRef.current || 0);
      if (!lastTs) return;
      if ((Date.now() - lastTs) >= STALE_RECOVERY_MS) {
        load({ includeRows: false });
        if (!STABILITY_MODE) {
          loadSlow({ force: true });
        }
      }
    }, 2000);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        load({ includeRows: false });
        if (!STABILITY_MODE) {
          loadSlow({ force: true });
        }
        void loadRowsOnly({ fullRows: false, syncRows: true });
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearTimeout(tWarmSync);
      clearInterval(tFast);
      clearInterval(tRows);
      if (tSlow) clearInterval(tSlow);
      clearInterval(tStale);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  useEffect(() => {
    let stopped = false;
    const connect = () => {
      if (stopped) return;
      const es = new EventSource(`${API_BASE}/trades/stream`);
      eventSourceRef.current = es;
      es.onopen = () => {
        const next = {
          ...sseStatsRef.current,
          connected: true,
          connected_at: new Date().toISOString(),
        };
        sseStatsRef.current = next;
        setSseStatus(next);
      };
      es.addEventListener("update", () => {
        const next = {
          ...sseStatsRef.current,
          last_event_at: new Date().toISOString(),
          connected: true,
        };
        sseStatsRef.current = next;
        setSseStatus(next);
        load({ includeRows: false });
        loadSlow();
      });
      es.addEventListener("ping", () => {
        const next = {
          ...sseStatsRef.current,
          last_event_at: new Date().toISOString(),
          connected: true,
        };
        sseStatsRef.current = next;
        setSseStatus(next);
      });
      es.onerror = () => {
        const next = {
          ...sseStatsRef.current,
          connected: false,
          reconnect_count: Number(sseStatsRef.current.reconnect_count || 0) + 1,
          last_error_at: new Date().toISOString(),
        };
        sseStatsRef.current = next;
        setSseStatus(next);
        try {
          es.close();
        } catch (_) {
          // no-op
        }
        eventSourceRef.current = null;
        if (!stopped) {
          setTimeout(connect, 2500);
        }
      };
    };
    connect();
    return () => {
      stopped = true;
      try {
        eventSourceRef.current?.close();
      } catch (_) {
        // no-op
      }
      eventSourceRef.current = null;
    };
  }, []);

  const summaryCards = useMemo(() => {
    const s = data.summary;
    const aliases = SYMBOL_ALIASES[tabSymbol] || [tabSymbol];
    const isMatch = (symbol) => {
      if (tabSymbol === "ALL") return true;
      const src = String(symbol || "").toUpperCase();
      return aliases.some((k) => src.includes(String(k).toUpperCase()));
    };
    const closedRows = Array.isArray(data.closedRecent) ? data.closedRecent.filter((r) => isMatch(r?.symbol)) : [];
    const openRows = Array.isArray(data.positionsEnriched?.items) ? data.positionsEnriched.items.filter((r) => isMatch(r?.symbol)) : [];
    const closedCount = closedRows.length;
    const openCount = openRows.length;
    const winCount = closedRows.filter((r) => Number(r?.profit || 0) > 0).length;
    const winRate = closedCount > 0 ? winCount / closedCount : Number(s?.win_rate || 0);
    const totalPnl = closedCount > 0
      ? closedRows.reduce((acc, r) => acc + Number(r?.profit || 0), 0)
      : Number(s?.total_pnl || 0);
    if (!s && closedCount === 0 && openCount === 0) {
      return [
        { label: "종료 거래", value: "-" },
        { label: "오픈 거래", value: "-" },
        { label: "승률", value: "-" },
        { label: "누적 손익", value: "-" },
      ];
    }
    return [
      { label: "종료 거래", value: tabSymbol === "ALL" ? (s?.closed_count ?? closedCount) : closedCount },
      { label: "오픈 거래", value: tabSymbol === "ALL" ? (s?.open_count ?? openCount) : openCount },
      { label: "승률", value: `${(winRate * 100).toFixed(1)}%`, tone: winRate >= 0.5 ? "good" : "warn" },
      { label: "누적 손익", value: Number(totalPnl || 0).toFixed(2), tone: Number(totalPnl || 0) >= 0 ? "good" : "bad" },
    ];
  }, [data.summary, data.closedRecent, data.positionsEnriched, tabSymbol]);

  const feeCard = useMemo(() => {
    const fee = Number(data.analytics?.fee_total || 0);
    return { label: "누적 수수료 합계", value: fee.toFixed(2), tone: fee > 0 ? "warn" : "neutral" };
  }, [data.analytics]);

  const daily = data.analytics?.daily || [];
  const cumPnlSeries = daily.map((d) => Number(d.cum_pnl || 0));
  const winRateSeries = daily.map((d) => Number(d.win_rate || 0) * 100);
  const tabAliases = SYMBOL_ALIASES[tabSymbol] || [tabSymbol];
  const isTabSymbol = (symbol) => {
    if (tabSymbol === "ALL") return true;
    const src = String(symbol || "").toUpperCase();
    return tabAliases.some((k) => src.includes(String(k).toUpperCase()));
  };
  const rows4hBySymbol = data.analytics?.pnl_4h_by_symbol || {};
  const rows4hTab = tabSymbol === "ALL" ? (data.analytics?.pnl_4h || []) : (rows4hBySymbol[tabSymbol] || []);
  const aiTracesTab = (data.runtimeStatus?.ai_entry_traces || [])
    .filter((r) => isTabSymbol(r?.symbol))
    .slice()
    .reverse()
    .slice(0, 8);
  const dailyByTab = useMemo(() => {
    const rows = Array.isArray(data.closedRecent) ? data.closedRecent : [];
    const aliases = SYMBOL_ALIASES[tabSymbol] || [tabSymbol];
    const filtered = rows.filter((r) => {
      const src = String(r?.symbol || "").toUpperCase();
      return aliases.some((k) => src.includes(String(k).toUpperCase()));
    });
    if (!filtered.length) return [];
    const byDay = new Map();
    filtered.forEach((row) => {
      const day = String(row?.close_time || row?.open_time || "").slice(0, 10) || "-";
      const prev = byDay.get(day) || { pnl: 0, wins: 0, total: 0 };
      const pnl = Number(row?.profit || 0);
      byDay.set(day, {
        pnl: prev.pnl + pnl,
        wins: prev.wins + (pnl > 0 ? 1 : 0),
        total: prev.total + 1,
      });
    });
    let cum = 0;
    return Array.from(byDay.entries())
      .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
      .map(([day, agg]) => {
        cum += Number(agg.pnl || 0);
        return {
          day,
          cum_pnl: cum,
          win_rate: Number(agg.total || 0) > 0 ? Number(agg.wins || 0) / Number(agg.total || 1) : 0,
        };
      });
  }, [data.closedRecent, tabSymbol]);
  const dailyLabelsTab = dailyByTab.length
    ? dailyByTab.map((d) => String(d.day || "-"))
    : daily.map((d) => String(d.day || d.date || d.bucket || "-"));
  const cumPnlSeriesTab = dailyByTab.length ? dailyByTab.map((d) => Number(d.cum_pnl || 0)) : cumPnlSeries;
  const winRateSeriesTab = dailyByTab.length ? dailyByTab.map((d) => Number(d.win_rate || 0) * 100) : winRateSeries;
  const conditionCoverage = data.analytics?.condition_coverage || [];
  const learnedEffect = data.analytics?.learned_effect || {};
  const learnedTimeline = learnedEffect.timeline || [];
  const conditionCoverageBySymbol = data.analytics?.condition_coverage_by_symbol;
  const learnedEffectBySymbol = data.analytics?.learned_effect_by_symbol;
  const rulePerformanceBySymbol = data.analytics?.rule_performance_by_symbol;
  const indicatorLatestBySymbol = data.analytics?.indicator_latest_by_symbol;
  const conditionCoverageTab = conditionCoverageBySymbol?.[tabSymbol] || conditionCoverage;
  const learnedEffectTab = learnedEffectBySymbol?.[tabSymbol] || learnedEffect;
  const learnedTimelineTab = learnedEffectTab.timeline || learnedTimeline;
  const rulePerformanceTab = useMemo(
    () => rulePerformanceBySymbol?.[tabSymbol] || data.analytics?.rule_performance || [],
    [rulePerformanceBySymbol, tabSymbol, data.analytics]
  );
  const indicatorLatestTab = useMemo(() => {
    if (tabSymbol !== "ALL") return indicatorLatestBySymbol?.[tabSymbol] || [];
    const out = [];
    const bySym = indicatorLatestBySymbol || {};
    Object.entries(bySym).forEach(([sym, rows]) => {
      (rows || []).forEach((r) => out.push({ ...r, symbol: sym }));
    });
    return out;
  }, [indicatorLatestBySymbol, tabSymbol]);
  const learningOverview = data.learningOverview || {};
  const learningSymbols = Array.isArray(learningOverview?.symbol_adjustments) ? learningOverview.symbol_adjustments : [];
  const entryBeforeAfter = learningOverview?.entry_before_after || {};
  const exitBeforeAfter = learningOverview?.exit_before_after || {};
  const learningModelMetrics = learningOverview?.model_metrics || {};
  const exitMetrics = data.runtimeStatus?.exit_metrics || {};
  const exitThresholds = data.runtimeStatus?.exit_metric_thresholds || {};
  const exitExecProfile = data.runtimeStatus?.exit_execution_profile || {};
  const stageSelection = data.runtimeStatus?.stage_selection_distribution || {};
  const stageWinloss = data.runtimeStatus?.stage_winloss_snapshot || {};
  const invalidLearningSamples = Number(data.runtimeStatus?.invalid_learning_sample_count || 0);
  const labelClipAppliedCount = Number(data.runtimeStatus?.label_clip_applied_count || 0);
  const netVsGrossGapAvg = Number(data.runtimeStatus?.net_vs_gross_gap_avg || 0);
  const expectancyBySymbol = data.runtimeStatus?.expectancy_by_symbol || {};
  const expectancyByRegime = data.runtimeStatus?.expectancy_by_regime || {};
  const expectancyByHourBucket = data.runtimeStatus?.expectancy_by_hour_bucket || {};
  const learningFallbackSummary = data.runtimeStatus?.learning_fallback_summary || {};
  const dExecutionState = data.runtimeStatus?.d_execution_state || {};
  const dAcceptanceSnapshot = data.runtimeStatus?.d_acceptance_snapshot || {};
  const learningApplyLoop = data.runtimeStatus?.learning_apply_loop || {};
  const kpiEvaluation = data.runtimeStatus?.kpi_evaluation || {};
  const d7SymbolTrendChecks = dAcceptanceSnapshot?.symbol_trend_checks || {};
  const d7TrendTone = (status) => {
    const s = String(status || "monitoring").toLowerCase();
    if (s === "pass") return { bg: "#113b22", fg: "#7DFFB3", bd: "#1f6b3f", icon: "OK" };
    if (s === "warn") return { bg: "#4a3a12", fg: "#FFD36A", bd: "#7c6218", icon: "WARN" };
    if (s === "fail") return { bg: "#4b1b1b", fg: "#FF9D9D", bd: "#7a2d2d", icon: "FAIL" };
    return { bg: "#1c2533", fg: "#C6D4EA", bd: "#32445f", icon: "MON" };
  };
  const kpiGradeTone = (grade) => d7TrendTone(String(grade || "monitoring").toLowerCase());
  const kpiOverallTone = kpiGradeTone(kpiEvaluation?.overall);
  const kpiMetricRows = [
    {
      key: "expectancy_overall",
      label: "Expectancy Overall",
      grade: kpiEvaluation?.metrics?.expectancy_overall?.grade,
      value: Number(kpiEvaluation?.metrics?.expectancy_overall?.value || 0).toFixed(4),
    },
    {
      key: "plus_to_minus_ratio",
      label: "Plus->Minus",
      grade: kpiEvaluation?.metrics?.plus_to_minus_ratio?.grade,
      value: `${Number(kpiEvaluation?.metrics?.plus_to_minus_ratio?.current || 0).toFixed(3)} / ${Number(kpiEvaluation?.metrics?.plus_to_minus_ratio?.baseline || 0).toFixed(3)}`,
    },
    {
      key: "adverse_stop_ratio",
      label: "Adverse Stop",
      grade: kpiEvaluation?.metrics?.adverse_stop_ratio?.grade,
      value: `${Number(kpiEvaluation?.metrics?.adverse_stop_ratio?.current || 0).toFixed(3)} / ${Number(kpiEvaluation?.metrics?.adverse_stop_ratio?.baseline || 0).toFixed(3)}`,
    },
    {
      key: "stage_profit_health",
      label: "Stage Profit Health",
      grade: kpiEvaluation?.metrics?.stage_profit_health?.grade,
      value: `positive=${Number(kpiEvaluation?.metrics?.stage_profit_health?.positive_stage_count || 0)}`,
    },
    {
      key: "symbol_expectancy_health",
      label: "Symbol Expectancy Health",
      grade: kpiEvaluation?.metrics?.symbol_expectancy_health?.grade,
      value: `non_negative=${Number(kpiEvaluation?.metrics?.symbol_expectancy_health?.non_negative_symbol_count || 0)}`,
    },
  ];
  const d7GlobalPlusTone = d7TrendTone(dAcceptanceSnapshot?.plus_to_minus_trend_check);
  const d7GlobalAdverseTone = d7TrendTone(dAcceptanceSnapshot?.adverse_stop_trend_check);
  const d7SymbolRows = SYMBOLS.map(({ key, label }) => {
    const row = d7SymbolTrendChecks?.[key] || {};
    return {
      key,
      label,
      plusCheck: String(row?.plus_to_minus_trend_check || "monitoring"),
      adverseCheck: String(row?.adverse_stop_trend_check || "monitoring"),
      plusCurrent: Number(row?.plus_to_minus_ratio_current ?? 0),
      plusBaseline: Number(row?.plus_to_minus_ratio_baseline ?? 0),
      adverseCurrent: Number(row?.adverse_stop_ratio_current ?? 0),
      adverseBaseline: Number(row?.adverse_stop_ratio_baseline ?? 0),
      plusTone: d7TrendTone(row?.plus_to_minus_trend_check),
      adverseTone: d7TrendTone(row?.adverse_stop_trend_check),
    };
  });
  const policySnapshot = data.runtimeStatus?.policy_snapshot || {};
  const policyRuntime = policySnapshot?.policy_runtime || {};
  const policyRollbackCount = Number(policyRuntime?.rollback_count || 0);
  const blendRuntime = data.runtimeStatus?.exit_blend_runtime || {};
  const symbolPolicySnapshot = data.runtimeStatus?.symbol_policy_snapshot || policySnapshot?.symbol_policy_snapshot || {};
  const symbolDefaultSnapshot = data.runtimeStatus?.symbol_default_snapshot || {};
  const symbolAppliedVsDefault = data.runtimeStatus?.symbol_applied_vs_default || {};
  const symbolLearningSplit = data.runtimeStatus?.symbol_learning_split || {};
  const symbolBlendRuntimeAll = data.runtimeStatus?.symbol_blend_runtime || blendRuntime?.symbol_blend_runtime || {};
  const tabPolicy = symbolPolicySnapshot?.[tabSymbol] || {};
  const tabBlendRuntime = symbolBlendRuntimeAll?.[tabSymbol] || {};
  const symbolTuneWarnRatio = Number(exitThresholds?.symbol_tune_warn_ratio ?? 0.10);
  const symbolTuneBadRatio = Number(exitThresholds?.symbol_tune_bad_ratio ?? 0.25);
  const symbolTuneRows = SYMBOLS.map(({ key, label }) => {
    const applied = symbolAppliedVsDefault?.[key] || {};
    const defaults = symbolDefaultSnapshot?.[key] || {};
    const metrics = [
      { key: "entry_threshold", label: "Entry" },
      { key: "exit_threshold", label: "Exit" },
      { key: "adverse_loss_usd", label: "Adverse USD" },
      { key: "reverse_signal_threshold", label: "Reverse" },
    ].map((m) => {
      const appliedValue = Number(applied?.[`${m.key}_applied`]);
      const defaultValue = Number(defaults?.[m.key]);
      const deltaValue = Number(applied?.[`${m.key}_delta`]);
      return {
        key: m.key,
        label: m.label,
        applied: Number.isFinite(appliedValue) ? appliedValue : 0,
        default: Number.isFinite(defaultValue) ? defaultValue : 0,
        delta: Number.isFinite(deltaValue) ? deltaValue : 0,
        deltaRatio: Number.isFinite(defaultValue) && Math.abs(defaultValue) > 1e-9
          ? Math.abs(Number.isFinite(deltaValue) ? deltaValue : 0) / Math.abs(defaultValue)
          : 0,
      };
    }).map((m) => {
      const grade = m.deltaRatio >= symbolTuneBadRatio ? "fail" : (m.deltaRatio >= symbolTuneWarnRatio ? "warn" : "pass");
      const tone = grade === "fail" ? "bad" : (grade === "warn" ? "warn" : "good");
      return { ...m, grade, tone };
    }).sort((a, b) => b.deltaRatio - a.deltaRatio);
    const worstGrade = metrics.some((m) => m.grade === "fail")
      ? "fail"
      : (metrics.some((m) => m.grade === "warn") ? "warn" : "pass");
    return {
      key,
      label,
      policyScope: String(applied?.policy_scope || "-"),
      sampleConfidence: Number(applied?.sample_confidence ?? 0),
      sampleCount: Number(applied?.sample_count ?? 0),
      metrics,
      maxDeltaRatio: Math.max(...metrics.map((m) => Number(m.deltaRatio || 0)), 0),
      worstGrade,
    };
  }).sort((a, b) => b.maxDeltaRatio - a.maxDeltaRatio);
  const symbolLearningRows = SYMBOLS.map(({ key, label }) => {
    const row = symbolLearningSplit?.[key] || {};
    const srcN = Number(row?.source_sample_count || 0);
    const polN = Number(row?.policy_sample_count || 0);
    const gap = Number(row?.sample_gap || (srcN - polN));
    const scope = String(row?.policy_scope || "-");
    const conf = Number(row?.sample_confidence || 0);
    const ready = Boolean(row?.ready);
    const domRegime = String(row?.dominant_regime || "UNKNOWN");
    const regimeCount = Number(row?.regime_count || 0);
    const grade = !ready ? "FAIL" : (Math.abs(gap) > 0 ? "WARN" : "PASS");
    return {
      key,
      label,
      srcN,
      polN,
      gap,
      scope,
      conf,
      ready,
      domRegime,
      regimeCount,
      grade,
    };
  }).sort((a, b) => Math.abs(b.gap) - Math.abs(a.gap));
  const blendHistory = tabBlendRuntime?.blend_history || blendRuntime?.history || [];
  const blendRuleW = Number(tabBlendRuntime?.blend_rule_weight ?? blendRuntime?.rule_weight ?? 0);
  const blendModelW = Number(tabBlendRuntime?.blend_model_weight ?? blendRuntime?.model_weight ?? 0);
  const blendLast = Array.isArray(blendHistory) && blendHistory.length ? blendHistory[blendHistory.length - 1] : null;
  const blendFirst = Array.isArray(blendHistory) && blendHistory.length ? blendHistory[0] : null;
  const blendDrift = blendLast && blendFirst
    ? Math.abs(Number(blendLast.rule_weight || 0) - Number(blendFirst.rule_weight || 0))
    : 0;
  const blendRuleWarnLow = Number(exitThresholds?.blend_rule_warn_low ?? 0.30);
  const blendRuleWarnHigh = Number(exitThresholds?.blend_rule_warn_high ?? 0.70);
  const blendRuleBadLow = Number(exitThresholds?.blend_rule_bad_low ?? 0.15);
  const blendRuleBadHigh = Number(exitThresholds?.blend_rule_bad_high ?? 0.85);
  const blendModelWarnLow = Number(exitThresholds?.blend_model_warn_low ?? 0.30);
  const blendModelWarnHigh = Number(exitThresholds?.blend_model_warn_high ?? 0.70);
  const blendModelBadLow = Number(exitThresholds?.blend_model_bad_low ?? 0.15);
  const blendModelBadHigh = Number(exitThresholds?.blend_model_bad_high ?? 0.85);
  const blendDriftWarn = Number(exitThresholds?.blend_drift_warn ?? 0.20);
  const blendDriftBad = Number(exitThresholds?.blend_drift_bad ?? 0.40);
  const blendStickyMinHistory = Number(exitThresholds?.blend_sticky_min_history ?? 8);
  const blendStickyMaxDrift = Number(exitThresholds?.blend_sticky_max_drift ?? 0.03);
  const blendRuleTone = blendSignalTone({
    value: blendRuleW,
    warnMin: blendRuleWarnLow,
    warnMax: blendRuleWarnHigh,
    badMin: blendRuleBadLow,
    badMax: blendRuleBadHigh,
  });
  const blendModelTone = blendSignalTone({
    value: blendModelW,
    warnMin: blendModelWarnLow,
    warnMax: blendModelWarnHigh,
    badMin: blendModelBadLow,
    badMax: blendModelBadHigh,
  });
  const blendDriftTone = blendDrift >= blendDriftBad ? "bad" : (blendDrift >= blendDriftWarn ? "warn" : "good");
  const blendStickyTone = (blendHistory.length >= blendStickyMinHistory && blendDrift <= blendStickyMaxDrift) ? "warn" : "good";
  const blendQualitySignals = [
    {
      label: "Blend Rule Weight",
      value: Number.isFinite(blendRuleW) ? blendRuleW.toFixed(3) : "-",
      tone: blendRuleTone,
    },
    {
      label: "Blend Model Weight",
      value: Number.isFinite(blendModelW) ? blendModelW.toFixed(3) : "-",
      tone: blendModelTone,
    },
    {
      label: "Blend Drift(최근 구간)",
      value: Number(blendDrift || 0).toFixed(3),
      tone: blendDriftTone,
    },
    {
      label: "Blend 고정화 위험",
      value: blendStickyTone === "warn" ? "주의(고정화)" : "정상",
      tone: blendStickyTone,
    },
  ];
  const runtimeUiFieldMap = data.runtimeStatus?.ui_card_field_map?.cards || {};
  const opsReadiness = data.opsReadiness || {};
  const releaseGate = opsReadiness?.release_gate || {};
  const releaseGateGrade = String(releaseGate?.grade || "unknown").toLowerCase();
  const releaseGateReasons = Array.isArray(releaseGate?.reasons) ? releaseGate.reasons : [];
  const obsSnapshot = data.runtimeObservability?.snapshot || {};
  const obsCounters = obsSnapshot?.counters || {};
  const obsCounterRows = Object.entries(obsCounters || {})
    .filter(([k]) => String(k) !== "updated_at")
    .slice(0, 8);
  const obsEventsCount = Number(obsSnapshot?.events_count || 0);
  const positionsSnapshot = data.positionsEnriched || {};
  const positionsIsStale = Boolean(positionsSnapshot?._stale);
  const positionsCacheAgeSec = Number(positionsSnapshot?._cache_age_sec || 0);
  const positionsSource = String(positionsSnapshot?.source || "-");
  const positionsStaleTone = positionsIsStale
    ? (positionsStaleStreak >= 3 ? "bad" : "warn")
    : (data.positionsEnriched?.connected ? "good" : "warn");
  const positionsFreshnessCard = positionsIsStale
    ? {
        label: "현재 포지션 신선도",
        value: `STALE ${positionsCacheAgeSec.toFixed(1)}s`,
        tone: positionsStaleTone,
        help: `source=${positionsSource} | streak=${positionsStaleStreak}`,
      }
    : {
        label: "현재 포지션 신선도",
        value: data.positionsEnriched?.connected ? "LIVE" : "FALLBACK",
        tone: positionsStaleTone,
        help: `source=${positionsSource} | streak=0`,
      };
  const currentMarketViewPayload = (Array.isArray(data.runtimeStatus?.current_market_view?.items) && data.runtimeStatus?.current_market_view?.items.length)
    ? data.runtimeStatus.current_market_view
    : buildMarketViewFallback(data.runtimeStatus || {});
  const currentMarketViewItemsAll = Array.isArray(currentMarketViewPayload?.items) ? currentMarketViewPayload.items : [];
  const currentMarketViewItems = (tabSymbol === "ALL"
    ? currentMarketViewItemsAll
    : currentMarketViewItemsAll.filter((item) => String(item?.symbol || "").toUpperCase() === String(tabSymbol).toUpperCase())
  ).sort((a, b) => {
    const ai = SYMBOLS.findIndex((row) => row.key === String(a?.symbol || "").toUpperCase());
    const bi = SYMBOLS.findIndex((row) => row.key === String(b?.symbol || "").toUpperCase());
    return ai - bi;
  });
  const currentMarketViewUpdatedAt = String(currentMarketViewPayload?.updated_at || data.runtimeStatus?.updated_at || "-");

  useEffect(() => {
    setPositionsStaleStreak((prev) => (positionsIsStale ? prev + 1 : 0));
  }, [positionsIsStale, apiPerf.updatedAt]);
  const runtimeWarningCounters = data.runtimeStatus?.runtime_warning_counters || {};
  const apiLatencySnapshot = data.runtimeStatus?.api_latency_snapshot || {};
  const apiLatencyThresholds = data.runtimeStatus?.api_latency_thresholds || {};
  const runtimeAlerts = data.runtimeStatus?.alerts || {};
  const sqliteMirrorStatus = data.runtimeStatus?.sqlite_mirror_status || {};
  const sqliteMirrorHealthy = Boolean(sqliteMirrorStatus?.healthy ?? true);
  const sqliteMirrorTone = sqliteMirrorHealthy
    ? { bg: "#113b22", fg: "#7DFFB3", bd: "#1f6b3f", icon: "OK", label: "HEALTHY" }
    : { bg: "#4b1b1b", fg: "#FF9D9D", bd: "#7a2d2d", icon: "WARN", label: "DEGRADED" };
  const exitTotal = Number(exitMetrics?.exit_total || 0);
  const sseIdleSec = sseStatus?.last_event_at ? Math.max(0, Math.floor((Date.now() - new Date(sseStatus.last_event_at).getTime()) / 1000)) : -1;
  const backendLatencyRows = Object.entries(apiLatencySnapshot || {})
    .map(([k, v]) => ({
      key: String(k),
      count: Number(v?.count || 0),
      err: Number(v?.error_count || 0),
      last: Number(v?.last_ms || 0),
      ema: Number(v?.ema_ms || 0),
      max: Number(v?.max_ms || 0),
      updated_at: String(v?.updated_at || ""),
    }))
    .filter((r) => Number(r.count || 0) >= 3)
    .filter((r) => {
      const ts = Date.parse(String(r.updated_at || ""));
      if (!Number.isFinite(ts)) return true;
      return (Date.now() - ts) <= 180000;
    })
    .filter((r) => !String(r.key || "").includes("/trades/stream"))
    .sort((a, b) => b.last - a.last)
    .slice(0, 8);
  const latencyWarnMs = Number(apiLatencyThresholds?.warn_ms || 300);
  const latencyBadMs = Number(apiLatencyThresholds?.bad_ms || 800);
  const latencyErrWarn = Number(apiLatencyThresholds?.error_warn_count || 1);
  const latencyErrBad = Number(apiLatencyThresholds?.error_bad_count || 3);
  const latencyToneOf = (row) => {
    const k = String(row?.key || "");
    const isBatchEndpoint = k.includes("/trades/analytics") || k.includes("/ml/learning-overview");
    const warnMs = isBatchEndpoint ? Math.max(1200, latencyWarnMs * 2) : latencyWarnMs;
    const badMs = isBatchEndpoint ? Math.max(2200, latencyBadMs * 2) : latencyBadMs;
    const last = Number(row?.last || 0);
    const err = Number(row?.err || 0);
    if (last >= badMs || err >= latencyErrBad) {
      return { label: "BAD", bg: "#4b1b1b", fg: "#FF9D9D", bd: "#7a2d2d" };
    }
    if (last >= warnMs || err >= latencyErrWarn) {
      return { label: "WARN", bg: "#4a3a12", fg: "#FFD36A", bd: "#7c6218" };
    }
    return { label: "GOOD", bg: "#113b22", fg: "#7DFFB3", bd: "#1f6b3f" };
  };
  const latencyToneSummary = (backendLatencyRows || []).reduce(
    (acc, r) => {
      const tone = latencyToneOf(r).label;
      if (tone === "BAD") acc.bad += 1;
      else if (tone === "WARN") acc.warn += 1;
      else acc.good += 1;
      return acc;
    },
    { good: 0, warn: 0, bad: 0 },
  );
  const riskGuardTotal = Number(exitMetrics?.risk_guard_triggered_total || 0);
  const riskGuardPlusToMinus = Number(exitMetrics?.risk_guard_plus_to_minus || 0);
  const riskGuardAdverse = Number(exitMetrics?.risk_guard_adverse || 0);
  const entryMetaCapHits = Number(exitMetrics?.entry_meta_cap_hits || 0);
  const stageExecShort = Number(exitMetrics?.stage_exec_short || 0);
  const stageExecMid = Number(exitMetrics?.stage_exec_mid || 0);
  const stageExecLong = Number(exitMetrics?.stage_exec_long || 0);
  const stageExecAuto = Number(exitMetrics?.stage_exec_auto || 0);
  const stopLikeExits = Number(exitMetrics?.exit_protect || 0)
    + Number(exitMetrics?.exit_adverse_stop || 0)
    + Number(exitMetrics?.exit_time_stop || 0)
    + Number(exitMetrics?.exit_emergency_stop || 0);
  const captureExits = Number(exitMetrics?.exit_lock || 0) + Number(exitMetrics?.exit_target || 0);
  const reversalExits = Number(exitMetrics?.exit_reversal || 0) + Number(exitMetrics?.exit_adverse_reversal || 0);
  const scalpExits = Number(exitMetrics?.exit_rsi_scalp || 0) + Number(exitMetrics?.exit_bb_scalp || 0);
  const stopLikeRatio = exitTotal > 0 ? stopLikeExits / exitTotal : 0;
  const captureRatio = exitTotal > 0 ? captureExits / exitTotal : 0;
  const adverseReversalRatio = exitTotal > 0 ? Number(exitMetrics?.exit_adverse_reversal || 0) / exitTotal : 0;
  const reversalRatio = exitTotal > 0 ? reversalExits / exitTotal : 0;
  const scalpRatio = exitTotal > 0 ? scalpExits / exitTotal : 0;
  const stoplikeWarnRatio = Number(exitThresholds?.stoplike_warn_ratio ?? 0.30);
  const stoplikeBadRatio = Number(exitThresholds?.stoplike_bad_ratio ?? 0.45);
  const captureWarnRatio = Number(exitThresholds?.capture_warn_ratio ?? 0.20);
  const captureGoodRatio = Number(exitThresholds?.capture_good_ratio ?? 0.35);
  const adverseRevWarnRatio = Number(exitThresholds?.adverse_reversal_warn_ratio ?? 0.06);
  const adverseRevBadRatio = Number(exitThresholds?.adverse_reversal_bad_ratio ?? 0.12);
  const reversalWarnRatio = Number(exitThresholds?.reversal_warn_ratio ?? 0.30);
  const scalpGoodRatio = Number(exitThresholds?.scalp_good_ratio ?? 0.15);
  const toneClass = (tone) => {
    if (tone === "good") return "fg-good";
    if (tone === "bad") return "fg-bad";
    if (tone === "warn") return "fg-warn";
    return "";
  };
  const pct = (v) => `${(Number(v || 0) * 100).toFixed(1)}%`;
  const exitQualitySignals = [
    {
      label: "손절계열 비중(낮을수록 좋음)",
      value: pct(stopLikeRatio),
      tone: stopLikeRatio >= stoplikeBadRatio ? "bad" : stopLikeRatio >= stoplikeWarnRatio ? "warn" : "good",
    },
    {
      label: "이익확정 비중(Lock+Target)",
      value: pct(captureRatio),
      tone: captureRatio >= captureGoodRatio ? "good" : captureRatio >= captureWarnRatio ? "warn" : "bad",
    },
    {
      label: "Adverse Reversal 비중(낮을수록 좋음)",
      value: pct(adverseReversalRatio),
      tone: adverseReversalRatio >= adverseRevBadRatio ? "bad" : adverseReversalRatio >= adverseRevWarnRatio ? "warn" : "good",
    },
    {
      label: "Reversal 전체 비중",
      value: pct(reversalRatio),
      tone: reversalRatio >= reversalWarnRatio ? "warn" : "good",
    },
    {
      label: "Scalp 비중(RSI+BB)",
      value: pct(scalpRatio),
      tone: scalpRatio >= scalpGoodRatio ? "good" : "warn",
    },
  ];
  const exitMetricPairs = [
    ["총 청산", Number(exitMetrics?.exit_total || 0)],
    ["Protect", Number(exitMetrics?.exit_protect || 0)],
    ["Lock", Number(exitMetrics?.exit_lock || 0)],
    ["Target", Number(exitMetrics?.exit_target || 0)],
    ["Reversal", Number(exitMetrics?.exit_reversal || 0)],
    ["Adverse Stop", Number(exitMetrics?.exit_adverse_stop || 0)],
    ["Adverse Reversal", Number(exitMetrics?.exit_adverse_reversal || 0)],
    ["Time Stop", Number(exitMetrics?.exit_time_stop || 0)],
    ["Emergency", Number(exitMetrics?.exit_emergency_stop || 0)],
    ["RSI Scalp", Number(exitMetrics?.exit_rsi_scalp || 0)],
    ["BB Scalp", Number(exitMetrics?.exit_bb_scalp || 0)],
    ["Stage Protect", Number(exitMetrics?.stage_select_protect || 0)],
    ["Stage Lock", Number(exitMetrics?.stage_select_lock || 0)],
    ["Stage Hold", Number(exitMetrics?.stage_select_hold || 0)],
    ["Adverse Recheck Hit", Number(exitMetrics?.adverse_recheck_hits || 0)],
  ];
  const stageRows = [
    {
      label: "Short",
      count: Number(stageSelection?.protect?.count || 0),
      ratio: Number(stageSelection?.protect?.ratio || 0),
      wr: Number(stageWinloss?.short?.win_rate || 0),
      pnl: Number(stageWinloss?.short?.pnl || 0),
    },
    {
      label: "Mid",
      count: Number(stageSelection?.lock?.count || 0),
      ratio: Number(stageSelection?.lock?.ratio || 0),
      wr: Number(stageWinloss?.mid?.win_rate || 0),
      pnl: Number(stageWinloss?.mid?.pnl || 0),
    },
    {
      label: "Long",
      count: Number(stageSelection?.hold?.count || 0),
      ratio: Number(stageSelection?.hold?.ratio || 0),
      wr: Number(stageWinloss?.long?.win_rate || 0),
      pnl: Number(stageWinloss?.long?.pnl || 0),
    },
  ];
  const selectedLearningSymbol = learningSymbols.find((x) => String(x.symbol || "").toUpperCase() === String(tabSymbol).toUpperCase()) || null;

  const scoringDetailRows = useMemo(() => {
    // Prefer backend analytics aggregation for consistency with CSV pipeline.
    if ((rulePerformanceTab || []).length) {
      return RULE_GROUPS.map((r) => {
        const perf = (rulePerformanceTab || []).find((x) => String(x.key) === String(r.key)) || {};
        return {
          key: r.key,
          label: RULE_LABEL_MAP[r.key] || r.key,
          ratio: Number(perf.ratio || 0),
          count: Number(perf.count || 0),
          reason_count: Number(perf.reason_count || 0),
          reason_ratio: Number(perf.reason_ratio || 0),
          indicator_count: Number(perf.indicator_count || 0),
          indicator_ratio: Number(perf.indicator_ratio || 0),
          win_rate: Number(perf.win_rate || 0),
          pnl: Number(perf.pnl || 0),
          avg_entry_score: Number(perf.avg_entry_score || 0),
          avg_exit_score: Number(perf.avg_exit_score || 0),
        };
      });
    }

    const closedRows = (data.closedRecent || []).filter((x) => {
      if (tabSymbol === "ALL") return true;
      const src = String(x?.symbol || "").toUpperCase();
      const keys = SYMBOL_ALIASES[tabSymbol] || [tabSymbol];
      return keys.some((k) => src.includes(String(k).toUpperCase()));
    });
    const total = Math.max(1, closedRows.length);

    return RULE_GROUPS.map((r) => {
      const matched = closedRows.filter((row) => {
        const reasonText = `${String(row?.entry_reason || "")} | ${String(row?.exit_reason || "")}`;
        return containsAnyKeyword(reasonText, r.keywords) || ruleMatchedByIndicators(row, r.key);
      });
      const wins = matched.filter((row) => Number(row?.profit || 0) > 0).length;
      const sumPnl = matched.reduce((acc, row) => acc + Number(row?.profit || 0), 0);
      const avgEntry = matched.length
        ? matched.reduce((acc, row) => acc + Number(row?.entry_score || 0), 0) / matched.length
        : 0;
      const avgExit = matched.length
        ? matched.reduce((acc, row) => acc + Number(row?.exit_score || 0), 0) / matched.length
        : 0;
      return {
        key: r.key,
        label: RULE_LABEL_MAP[r.key] || r.key,
        ratio: Number(matched.length / total || 0),
        count: Number(matched.length || 0),
        reason_count: Number(matched.length || 0),
        reason_ratio: Number(matched.length / total || 0),
        indicator_count: 0,
        indicator_ratio: 0,
        win_rate: matched.length ? Number(wins / matched.length) : 0,
        pnl: Number(sumPnl || 0),
        avg_entry_score: Number(avgEntry || 0),
        avg_exit_score: Number(avgExit || 0),
      };
    });
  }, [data.closedRecent, tabSymbol, rulePerformanceTab]);

  const symbolPanels = useMemo(() => {
    const now = Date.now();
    const currentRaw = data.positionsEnriched?.items || [];
    const recentRows = Array.isArray(data.recent) ? data.recent : [];
    const closedRows = Array.isArray(data.closedRecent) ? data.closedRecent : [];
    const csvByTicket = new Map();
    [...recentRows, ...closedRows].forEach((r) => {
      const t = Number(r?.ticket || 0);
      if (!t) return;
      if (!csvByTicket.has(t)) csvByTicket.set(t, r);
    });
    const mt5Positions = Array.isArray(data.mt5?.positions) ? data.mt5.positions : [];
    const mt5Fallback = mt5Positions.map((p) => ({
      ...(csvByTicket.get(Number(p.ticket || 0)) || {}),
      ticket: Number(p.ticket || 0),
      symbol: String(p.symbol || ""),
      direction: Number(p.type) === 0 ? "BUY" : "SELL",
      lot: Number(p.volume || 0),
      profit: Number(p.profit || 0),
      price_open: Number(p.price_open || 0),
      open_time: String((csvByTicket.get(Number(p.ticket || 0)) || {}).open_time || ""),
      entry_score: Number((csvByTicket.get(Number(p.ticket || 0)) || {}).entry_score || 0),
      contra_score_at_entry: Number((csvByTicket.get(Number(p.ticket || 0)) || {}).contra_score_at_entry || 0),
      entry_reasons: (() => {
        const arr = String((csvByTicket.get(Number(p.ticket || 0)) || {}).entry_reason || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        return arr.length ? arr : ["[SNAPSHOT] 대기 중"];
      })(),
    }));
    const currentConnected = !!data.positionsEnriched?.connected;
    const sticky = lastGoodPositionsRef.current || { items: [], at: 0 };
    const stickyAgeSec = (now - Number(sticky.at || 0)) / 1000;
    const useSticky =
      sticky.items.length > 0 &&
      stickyAgeSec <= POSITION_STICKY_MAX_SEC &&
      (!currentConnected || currentRaw.length === 0);
    const current = useSticky
      ? sticky.items
      : (currentRaw.length ? currentRaw : mt5Fallback);
    const recentClosed = data.closedRecent || [];

    const matches = (symbol, baseKey) => {
      const src = String(symbol || "").toUpperCase();
      const keys = SYMBOL_ALIASES[baseKey] || [baseKey];
      return keys.some((k) => src.includes(String(k).toUpperCase()));
    };

    return SYMBOLS.map((sym) => {
      const openRows = current
        .filter((x) => matches(x.symbol, sym.key))
        .map((x) => {
          const c = csvByTicket.get(Number(x.ticket || 0)) || {};
          return { ...c, ...x, entry_reason: x.entry_reason || c.entry_reason || "", exit_reason: x.exit_reason || c.exit_reason || "" };
        });
      const histRowsAll = recentClosed
        .filter((x) => matches(x.symbol, sym.key))
        .map((x) => {
          const c = csvByTicket.get(Number(x.ticket || 0)) || {};
          return { ...c, ...x };
        })
        .sort((a, b) => {
          const ta = Number(a.close_ts || 0) || (Date.parse(a.close_time || a.open_time || 0) || 0);
          const tb = Number(b.close_ts || 0) || (Date.parse(b.close_time || b.open_time || 0) || 0);
          return tb - ta;
        });
      const totalPages = Math.max(1, Math.ceil(histRowsAll.length / HISTORY_PAGE_SIZE));
      const page = Math.max(1, Math.min(totalPages, Number(historyPage[sym.key] || 1)));
      const start = (page - 1) * HISTORY_PAGE_SIZE;
      const histRows = histRowsAll.slice(start, start + HISTORY_PAGE_SIZE);
      const groupIndex = Math.floor((page - 1) / PAGE_GROUP_SIZE);
      const groupStart = groupIndex * PAGE_GROUP_SIZE + 1;
      const groupEnd = Math.min(totalPages, groupStart + PAGE_GROUP_SIZE - 1);
      const pageNumbers = Array.from({ length: groupEnd - groupStart + 1 }, (_, i) => groupStart + i);

      return {
        ...sym,
        openRows,
        histRows,
        histRowsAllCount: histRowsAll.length,
        page,
        totalPages,
        groupStart,
        groupEnd,
        pageNumbers,
        usedSticky: useSticky,
      };
    });
  }, [data.positionsEnriched, data.mt5, data.recent, data.closedRecent, historyPage]);


  const scoringBoard = useMemo(() => {
    const current = data.positionsEnriched?.items || [];
    const traces = data.runtimeStatus?.ai_entry_traces || [];
    const aliases = SYMBOL_ALIASES[tabSymbol] || [tabSymbol];
    const isMatch = (symbol) => {
      const src = String(symbol || "").toUpperCase();
      return aliases.some((k) => src.includes(String(k).toUpperCase()));
    };

    const currentRows = current.filter((x) => isMatch(x.symbol));
    const reasonTexts = currentRows.flatMap((r) => (r.entry_reasons || []).map((x) => String(x || "")));
    const joined = normalizeText(reasonTexts.join(" | "));
    const baseScoreAvg = currentRows.length
      ? currentRows.reduce((acc, r) => acc + Number(r.entry_score || 0), 0) / currentRows.length
      : 0;

    const coverageMap = new Map((conditionCoverageTab || []).map((r) => [String(r.key), r]));

    const preliminaryRules = RULE_GROUPS.map((g) => {
      const hits = reasonTexts.filter((t) => g.keywords.some((kw) => normalizeText(t).includes(normalizeText(kw))));
      const score = hits.reduce((acc, h) => {
        const m = String(h || "").match(/\(([+-]?\d+)[^)]*\)\s*$/);
        if (m) return acc + Number(m[1] || 0);
        return acc + estimateReasonWeight(h);
      }, 0);
      const perf = scoringDetailRows.find((r) => r.key === g.key) || {};
      const cov = coverageMap.get(g.key) || {};
      return {
        ...g,
        matched: hits.length > 0,
        hits: hits.slice(0, 2),
        baseScore: Number(g.baseScore || 0),
        actualScore: Number(score || 0),
        historyAvgScore: Number(perf.avg_entry_score || 0),
        historyRatio: Number(perf.ratio || 0),
        reasonHitCount: Number(cov.reason_count || 0),
        reasonHitRatio: Number(cov.reason_ratio || 0),
        indicatorHitCount: Number(cov.indicator_count || 0),
        indicatorHitRatio: Number(cov.indicator_ratio || 0),
      };
    });

    // If a rule is unmet, still display a small "current score" estimate.
    // This keeps the board informative instead of showing zeros only.
    const matchedScoreTotal = preliminaryRules
      .filter((r) => r.matched)
      .reduce((acc, r) => acc + Number(r.actualScore || 0), 0);
    const residual = Math.max(0, Number(baseScoreAvg || 0) - matchedScoreTotal);
    const unmet = preliminaryRules.filter((r) => !r.matched);
    const weightSum = unmet.reduce((acc, r) => {
      const ratioWeight = Number(r.historyRatio || 0) > 0 ? Number(r.historyRatio || 0) : 0.02;
      const baseWeight = Math.max(0.2, Number(r.baseScore || 0) / 100);
      return acc + ratioWeight * baseWeight;
    }, 0);

    const matchedRules = preliminaryRules.map((r) => {
      if (r.matched) {
        return {
          ...r,
          currentScore: Number(r.actualScore || 0),
          unmetScore: 0,
        };
      }
      let est = 0;
      if (residual > 0 && weightSum > 0) {
        const ratioWeight = Number(r.historyRatio || 0) > 0 ? Number(r.historyRatio || 0) : 0.02;
        const baseWeight = Math.max(0.2, Number(r.baseScore || 0) / 100);
        est = Math.round((residual * ratioWeight * baseWeight) / weightSum);
      } else {
        const ratioWeight = Number(r.historyRatio || 0) > 0 ? Number(r.historyRatio || 0) : 0.02;
        est = Math.max(1, Math.round(Number(r.baseScore || 0) * ratioWeight * 0.2));
      }
      est = Math.max(1, Number(est || 0));
      return {
        ...r,
        currentScore: est,
        unmetScore: Number(r.baseScore || 0),
      };
    });

    const matchedCount = matchedRules.filter((x) => x.matched).length;
    const marketScore = Math.round((matchedCount / RULE_GROUPS.length) * 100);

    const traceRows = traces.filter((t) => isMatch(t.symbol)).slice(-20);
    const learnedAdjAvg = traceRows.length
      ? traceRows.reduce((acc, r) => acc + Number(r.score_adj || 0), 0) / traceRows.length
      : 0;
    const learnedFinalAvg = traceRows.length
      ? traceRows.reduce((acc, r) => acc + Number(r.final_score || 0), 0) / traceRows.length
      : 0;

    return {
      baseScoreAvg,
      marketScore,
      matchedRules,
      learnedAdjAvg,
      learnedFinalAvg,
      traceCount: traceRows.length,
      hasCurrentReason: joined.length > 0,
    };
  }, [data.positionsEnriched, data.runtimeStatus, tabSymbol, scoringDetailRows, conditionCoverageTab]);

  const selectedSymbolPanel = symbolPanels.find((p) => p.key === tabSymbol) || null;
  const tabOpenCount = tabSymbol === "ALL"
    ? symbolPanels.reduce((acc, p) => acc + Number(p?.openRows?.length || 0), 0)
    : Number(selectedSymbolPanel?.openRows?.length || 0);
  const tabClosedCount = tabSymbol === "ALL"
    ? symbolPanels.reduce((acc, p) => acc + Number(p?.histRowsAllCount || 0), 0)
    : Number(selectedSymbolPanel?.histRowsAllCount || 0);
  const tabCumPnl = Number(cumPnlSeriesTab[cumPnlSeriesTab.length - 1] || 0);
  const tabWinRateNow = Number(winRateSeriesTab[winRateSeriesTab.length - 1] || 0);
  const tabCoverageAvg = (conditionCoverageTab || []).length
    ? ((conditionCoverageTab || []).reduce((acc, r) => acc + Number(r?.ratio || 0), 0) / conditionCoverageTab.length) * 100
    : 0;
  const tabAnalysisLine = [
    `${tabSymbol} OPEN ${tabOpenCount}건`,
    `CLOSED ${tabClosedCount}건`,
    `누적손익 ${tabCumPnl.toFixed(2)}`,
    `승률 ${tabWinRateNow.toFixed(1)}%`,
    `조건커버리지 ${tabCoverageAvg.toFixed(1)}%`,
  ].join(" | ");
  const tabLabel = (SYMBOLS.find((s) => s.key === tabSymbol)?.label || tabSymbol);
  const quickLinks = [
    { href: "#sec-trading-dashboard", label: "트레이딩운영대시보드" },
    { href: "#sec-market-view", label: "현재 시장 해석" },
    { href: "#sec-learning-summary", label: "학습반영 요약" },
    { href: "#sec-score-board", label: "공식점수보드" },
    { href: "#sec-score-detail", label: "공식 항목별 성과상세" },
    { href: "#sec-learning-trend", label: "학습반영추이" },
    { href: "#sec-daily-cumpnl", label: "일자별 누적 손익" },
    { href: "#sec-current-positions", label: "현재 포지션" },
    { href: "#sec-api-status", label: "API 상태" },
  ];

  return (
    <main className={`container ${dockOpen ? "dock-open" : "dock-closed"}`}>
      <div className="content-stack">
      <header className="header jump-section" id="sec-trading-dashboard">
        <h1>트레이딩 운영 대시보드</h1>
        <div className="actions">
          <span className="badge">API: {API_BASE}</span>
          <span className="badge">업데이트: {lastUpdated || "-"}</span>
          <button onClick={load} disabled={loading}>{loading ? "불러오는 중.." : "새로고침"}</button>
        </div>
      </header>

      {error ? <div className="error">오류: {error}</div> : null}

      <div className="ops-layout">
      <button
        type="button"
        className={`ops-dock-toggle ${dockOpen ? "open" : "closed"}`}
        onClick={() => setDockOpen((v) => !v)}
        aria-label={dockOpen ? "사이드바 접기" : "사이드바 펼치기"}
        title={dockOpen ? "사이드바 접기" : "사이드바 펼치기"}
      >
        <span className="ops-dock-icon">{dockOpen ? "‹" : "›"}</span>
      </button>
        <aside className={`ops-rail ${dockOpen ? "open" : "collapsed"}`}>
      <section className="card sticky-symbol-tabs">
        <CardHead title="심볼 분석 탭" help="요청하신 핵심 지표를 NAS100/XAUUSD/BTCUSD 단위로 즉시 분리해서 확인합니다." />
        <div className="tab-row">
          {SYMBOLS.map((s) => (
            <button key={s.key} type="button" className={`tab-btn ${tabSymbol === s.key ? "active" : ""}`} onClick={() => setTabSymbol(s.key)}>
              {s.label}
            </button>
          ))}
        </div>
        <div className="grid two">
          <StatCard label={`${tabSymbol} OPEN`} value={tabOpenCount} tone={tabOpenCount > 0 ? "good" : "neutral"} />
          <StatCard label={`${tabSymbol} CLOSED`} value={tabClosedCount} tone="neutral" />
          <StatCard label={`${tabSymbol} 누적손익`} value={tabCumPnl.toFixed(2)} tone={tabCumPnl >= 0 ? "good" : "bad"} />
          <StatCard label={`${tabSymbol} AI 로그`} value={aiTracesTab.length} tone={aiTracesTab.length > 0 ? "good" : "warn"} />
        </div>
      </section>

      <section className="card fold-card">
        <details open>
          <summary>핵심 지표</summary>
          <div className="fold-content">
            <div className="grid two">
              {summaryCards.map((c) => <StatCard key={c.label} label={c.label} value={c.value} tone={c.tone || "neutral"} />)}
              <StatCard label={feeCard.label} value={feeCard.value} tone={feeCard.tone} help="데모 계좌는 대부분 수수료 0입니다." />
              <StatCard label="선택 심볼 데이터" value={rows4hTab.length} tone="neutral" help="선택 심볼의 4시간 손익/거래 개수" />
            </div>
          </div>
        </details>
      </section>

      <section className="card fold-card">
        <details open>
          <summary>데이터 최신 시각</summary>
          <div className="fold-content">
            <div className="status-grid">
              <div className="status-pill ok">
                <strong>최근 청산 시각</strong>
                <span>{data.summary?.last_closed_time || "없음"}</span>
              </div>
              <div className="status-pill ok">
                <strong>최근 진입 시각</strong>
                <span>{data.summary?.last_open_time || "없음"}</span>
              </div>
              <div className="status-pill ok">
                <strong>히스토리 기준</strong>
                <span>CLOSED 우선 + 필요 시 MT5 HISTORY 보강</span>
              </div>
            </div>
          </div>
        </details>
      </section>

      <section className="card fold-card">
        <details>
          <summary>운영/업데이트 상태</summary>
          <div className="fold-content">
            <div className="kv-grid">
              <div><strong>마지막 업데이트</strong>: {lastUpdated || "-"}</div>
              <div><strong>폴링(전체)</strong>: {Number(apiPerf?.lastPollMs || 0).toFixed(0)}ms</div>
              <div><strong>Slow Refresh</strong>: {slowRefreshing ? "갱신 중" : "정상"}</div>
              <div><strong>SSE 연결</strong>: {sseStatus?.connected ? "연결됨" : "재연결중"}</div>
              <div><strong>현재 데이터 소스</strong>: {data.positionsEnriched?.connected ? "MT5 + CSV" : "CSV(보조)"}</div>
              <div><strong>{positionsFreshnessCard.label}</strong>: {positionsFreshnessCard.value}</div>
            </div>
          </div>
        </details>
      </section>

      </aside>
      <div className="ops-main">
      <nav className="quick-nav">
        <div className="quick-nav-title">바로가기</div>
        {quickLinks.map((item) => (
          <a key={item.href} href={item.href} className="quick-nav-link">
            <span className="quick-nav-hash">#</span>
            <span>{item.label}</span>
          </a>
        ))}
      </nav>

      <section className="card jump-section" id="sec-market-view">
        <CardHead title={`현재 시장 해석 (${tabLabel})`} help="엔진이 지금 시장을 어떻게 보는지, 왜 WAIT/BUY/SELL로 읽는지를 한국어 카드와 로그로 정리합니다." />
        <div className="market-view-topline">
          <span>기준 시각: {currentMarketViewUpdatedAt || "-"}</span>
          <span>카드 수: {currentMarketViewItems.length}</span>
          <span>소스: {runtimeUiFieldMap?.current_market_view ? "runtime/status.current_market_view" : "runtime/status"}</span>
        </div>
        {!currentMarketViewItems.length ? (
          <div className="history-empty">현재 시장 해석 데이터가 아직 없습니다.</div>
        ) : (
          <div className="market-view-grid">
            {currentMarketViewItems.map((item) => (
              <MarketViewCard key={`market-view-${item.symbol}`} item={item} />
            ))}
          </div>
        )}
      </section>

      <section className="card jump-section" id="sec-ops-dashboard">
        <CardHead title="공식 점수보드 / 운영 지표" help="ops/readiness + runtime/observability 최신 상태를 자동 갱신합니다." />
        <div className="kv-grid">
          <div>
            <strong>Release Gate</strong>: <span className={releaseGateGrade === "pass" ? "fg-good" : (releaseGateGrade === "warn" ? "fg-warn" : "fg-bad")}>{String(releaseGateGrade || "unknown").toUpperCase()}</span>
          </div>
          <div>
            <strong>Gate Reasons</strong>: {releaseGateReasons.length ? releaseGateReasons.join(", ") : "-"}
          </div>
          <div>
            <strong>Ops As-Of</strong>: {String(opsReadiness?.as_of || "-")}
          </div>
          <div>
            <strong>Active Alerts</strong>: {Number(opsReadiness?.runtime?.active_alerts || 0)}
          </div>
          <div>
            <strong>Policy Rollback</strong>: {Number(opsReadiness?.runtime?.policy_rollback_count || 0)}
          </div>
          <div>
            <strong>Runtime Warnings</strong>: {Number(opsReadiness?.runtime?.warning_total || 0)}
          </div>
          <div>
            <strong>Observability Events</strong>: {obsEventsCount}
          </div>
          <div>
            <strong>Slow Refresh</strong>: {slowRefreshing ? "갱신 중" : "정상"}
          </div>
          {obsCounterRows.map(([k, v]) => (
            <div key={`obs-counter-${k}`}>
              <strong>{k}</strong>: {Number(v || 0)}
            </div>
          ))}
        </div>
        <div className="analysis-strip">
          <div className="analysis-pill">
            <strong>{tabLabel} 요약</strong>
            <span>{tabAnalysisLine}</span>
          </div>
          <div className="analysis-meta">
            <span>기준 데이터</span>
            <code>/runtime/status.ai_entry_traces · /trades/analytics · closedRecent</code>
          </div>
        </div>
      </section>

      <section className="card">
        <CardHead title="AI 점수 반영 로그" help="선택 심볼 기준으로 원점수→보정점수 변화를 최근 건 순서로 표시합니다." />
        {!aiTracesTab.length ? (
          <div className="history-empty">{tabSymbol} 기준 AI 반영 로그가 없습니다.</div>
        ) : (
          <div className="history-list">
            {aiTracesTab.map((r, i) => (
              <div className="history-row" key={`ai-trace-${i}`}>
                <span>
                  {r.time} | {r.symbol} {r.action}
                </span>
                <strong>
                  {Number(r.raw_score || 0).toFixed(0)} + ({Number(r.score_adj || 0).toFixed(0)}) = {Number(r.final_score || 0).toFixed(0)}
                </strong>
                <span>
                  p={r.probability == null ? "-" : Number(r.probability).toFixed(3)} {r.blocked ? "| BLOCKED" : ""}
                </span>
                <span>
                  레짐={r.regime || "-"} | 유동성비={r.volume_ratio == null ? "-" : Number(r.volume_ratio).toFixed(2)} | 변동성비=
                  {r.volatility_ratio == null ? "-" : Number(r.volatility_ratio).toFixed(2)} | 스프레드비=
                  {r.spread_ratio == null ? "-" : Number(r.spread_ratio).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card jump-section" id="sec-learning-summary">
        <CardHead title="학습 반영 요약(전/후 + 심볼별 조정)" help="학습 전/후 지표 변화와 심볼별 적정 진입/청산 점수 추천을 함께 표시합니다." />
        <div className="grid four">
          <StatCard
            label="Entry 평균 원점수"
            value={Number(entryBeforeAfter.avg_raw_score || 0).toFixed(1)}
            tone="neutral"
            help={`trace ${Number(entryBeforeAfter.trace_count || 0)}건`}
          />
          <StatCard
            label="Entry 평균 최종점수"
            value={Number(entryBeforeAfter.avg_final_score || 0).toFixed(1)}
            tone="neutral"
          />
          <StatCard
            label="Entry 평균 가감점"
            value={Number(entryBeforeAfter.avg_score_adj || 0).toFixed(2)}
            tone={Number(entryBeforeAfter.avg_score_adj || 0) >= 0 ? "good" : "bad"}
          />
          <StatCard
            label="Exit AUC"
            value={Number(learningModelMetrics?.exit_metrics?.auc || 0).toFixed(3)}
            tone={Number(learningModelMetrics?.exit_metrics?.auc || 0) >= 0.6 ? "good" : "warn"}
          />
        </div>
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table>
            <thead>
              <tr>
                <th>구분</th>
                <th>이전 구간</th>
                <th>최근 구간</th>
                <th>변화</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>승률</td>
                <td>{(Number(exitBeforeAfter?.base_window?.win_rate || 0) * 100).toFixed(1)}%</td>
                <td>{(Number(exitBeforeAfter?.recent_window?.win_rate || 0) * 100).toFixed(1)}%</td>
                <td className={Number((exitBeforeAfter?.recent_window?.win_rate || 0) - (exitBeforeAfter?.base_window?.win_rate || 0)) >= 0 ? "fg-good" : "fg-bad"}>
                  {(((Number(exitBeforeAfter?.recent_window?.win_rate || 0) - Number(exitBeforeAfter?.base_window?.win_rate || 0)) * 100)).toFixed(1)}%p
                </td>
              </tr>
              <tr>
                <td>평균 손익</td>
                <td>{Number(exitBeforeAfter?.base_window?.avg_profit || 0).toFixed(3)}</td>
                <td>{Number(exitBeforeAfter?.recent_window?.avg_profit || 0).toFixed(3)}</td>
                <td className={Number((exitBeforeAfter?.recent_window?.avg_profit || 0) - (exitBeforeAfter?.base_window?.avg_profit || 0)) >= 0 ? "fg-good" : "fg-bad"}>
                  {(Number(exitBeforeAfter?.recent_window?.avg_profit || 0) - Number(exitBeforeAfter?.base_window?.avg_profit || 0)).toFixed(3)}
                </td>
              </tr>
              <tr>
                <td>Profit Factor</td>
                <td>{Number(exitBeforeAfter?.base_window?.profit_factor || 0).toFixed(3)}</td>
                <td>{Number(exitBeforeAfter?.recent_window?.profit_factor || 0).toFixed(3)}</td>
                <td className={Number((exitBeforeAfter?.recent_window?.profit_factor || 0) - (exitBeforeAfter?.base_window?.profit_factor || 0)) >= 0 ? "fg-good" : "fg-bad"}>
                  {(Number(exitBeforeAfter?.recent_window?.profit_factor || 0) - Number(exitBeforeAfter?.base_window?.profit_factor || 0)).toFixed(3)}
                </td>
              </tr>
              <tr>
                <td>평균 청산점수</td>
                <td>{Number(exitBeforeAfter?.base_window?.avg_exit_score || 0).toFixed(1)}</td>
                <td>{Number(exitBeforeAfter?.recent_window?.avg_exit_score || 0).toFixed(1)}</td>
                <td className={Number((exitBeforeAfter?.recent_window?.avg_exit_score || 0) - (exitBeforeAfter?.base_window?.avg_exit_score || 0)) >= 0 ? "fg-good" : "fg-bad"}>
                  {(Number(exitBeforeAfter?.recent_window?.avg_exit_score || 0) - Number(exitBeforeAfter?.base_window?.avg_exit_score || 0)).toFixed(1)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table>
            <thead>
              <tr>
                <th>심볼</th>
                <th>거래수</th>
                <th>현재 평균 진입점수</th>
                <th>현재 평균 청산점수</th>
                <th>추천 진입 임계치</th>
                <th>추천 청산 임계치</th>
                <th>PF 변화(최근-이전)</th>
              </tr>
            </thead>
            <tbody>
              {learningSymbols.map((row) => (
                <tr key={`learn-sym-${row.symbol}`}>
                  <td>{row.symbol}</td>
                  <td>{Number(row.trades || 0)}</td>
                  <td>{Number(row.current_avg_entry_score || 0).toFixed(1)}</td>
                  <td>{Number(row.current_avg_exit_score || 0).toFixed(1)}</td>
                  <td>{Number(row.suggested_entry_threshold || 0).toFixed(0)}</td>
                  <td>{Number(row.suggested_exit_threshold || 0).toFixed(0)}</td>
                  <td className={Number(row.delta_profit_factor || 0) >= 0 ? "fg-good" : "fg-bad"}>{Number(row.delta_profit_factor || 0).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selectedLearningSymbol ? (
          <div className="axis-note">
            <span>
              선택 심볼({tabSymbol}) 추천값: 진입 {Number(selectedLearningSymbol.suggested_entry_threshold || 0).toFixed(0)} /
              청산 {Number(selectedLearningSymbol.suggested_exit_threshold || 0).toFixed(0)}
            </span>
            <span>
              근거: 최근 구간 승률 {(Number(selectedLearningSymbol?.recent_window?.win_rate || 0) * 100).toFixed(1)}%,
              PF {Number(selectedLearningSymbol?.recent_window?.profit_factor || 0).toFixed(3)}
            </span>
          </div>
        ) : null}
      </section>

      <section className="card jump-section" id="sec-score-board">
        <CardHead title="공식 점수 보드" help="요청한 15분 공식 항목 기준으로 현재 시장 근거와 학습 반영 점수를 함께 보여줍니다. Reason-hit/Indicator-hit로 미발생 vs 미기록을 분리 확인할 수 있습니다." />
        <div className="grid four">
          <StatCard label="현재시장 점수(공식충족)" value={`${scoringBoard.marketScore}`} tone={scoringBoard.marketScore >= 60 ? "good" : "warn"} />
          <StatCard label="현재 진입점수 평균" value={Number(scoringBoard.baseScoreAvg || 0).toFixed(1)} tone="neutral" />
          <StatCard label="학습 가감점 평균" value={Number(scoringBoard.learnedAdjAvg || 0).toFixed(1)} tone={scoringBoard.learnedAdjAvg >= 0 ? "good" : "bad"} />
          <StatCard label="학습 반영 최종점수 평균" value={Number(scoringBoard.learnedFinalAvg || 0).toFixed(1)} tone="neutral" help={`최근 ${scoringBoard.traceCount}건 기준`} />
        </div>
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table>
            <thead>
              <tr>
                <th>공식 항목</th>
                <th>상태</th>
                <th>현재 점수</th>
                <th>미충족 점수(기준)</th>
                <th>미충족 기준점수(이력평균)</th>
                <th>커버리지</th>
                <th>Reason-hit</th>
                <th>Indicator-hit</th>
                <th>현재 근거</th>
              </tr>
            </thead>
            <tbody>
              {scoringBoard.matchedRules.map((r) => (
                <tr key={`rule-score-${r.key}`}>
                  <td>{r.label}</td>
                  <td className={r.matched ? "fg-good" : "fg-bad"}>{r.matched ? "충족" : "미충족"}</td>
                  <td>{Number(r.currentScore || 0).toFixed(0)}</td>
                  <td>{Number(r.unmetScore || 0).toFixed(0)}</td>
                  <td>{Number(r.historyAvgScore || 0).toFixed(1)}</td>
                  <td>{(Number(r.historyRatio || 0) * 100).toFixed(1)}%</td>
                  <td>{(Number(r.reasonHitRatio || 0) * 100).toFixed(1)}% ({Number(r.reasonHitCount || 0)})</td>
                  <td>{(Number(r.indicatorHitRatio || 0) * 100).toFixed(1)}% ({Number(r.indicatorHitCount || 0)})</td>
                  <td>{r.hits.length ? r.hits.join(" | ") : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!scoringBoard.hasCurrentReason ? (
          <div className="history-empty">현재 오픈 포지션의 진입근거가 아직 없어 공식 매핑을 만들지 못했습니다.</div>
        ) : null}
      </section>

      <section className="card jump-section" id="sec-score-detail">
        <CardHead title={`공식 항목별 성과 상세(${tabLabel})`} help="선택 탭 기준으로 공식 항목별 커버리지, 거래수, 승률, 손익, 평균 점수를 함께 보여줍니다." />
        <div className="table-wrap">
          <table className="rule-detail-table">
            <colgroup>
              <col style={{ width: "16%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "13%" }} />
              <col style={{ width: "13%" }} />
              <col style={{ width: "8%" }} />
              <col style={{ width: "8%" }} />
              <col style={{ width: "11%" }} />
              <col style={{ width: "11%" }} />
              <col style={{ width: "11%" }} />
            </colgroup>
            <thead>
              <tr>
                <th>공식 항목</th>
                <th>커버리지</th>
                <th>Reason-hit</th>
                <th>Indicator-hit</th>
                <th>거래수</th>
                <th>승률</th>
                <th>손익합</th>
                <th>평균 진입점수</th>
                <th>평균 청산점수</th>
              </tr>
            </thead>
            <tbody>
              {scoringDetailRows.map((r) => (
                <tr key={`rule-detail-${r.key}`}>
                  <td>{r.label}</td>
                  <td>{(r.ratio * 100).toFixed(1)}%</td>
                  <td>{(Number(r.reason_ratio || 0) * 100).toFixed(1)}% ({Number(r.reason_count || 0)})</td>
                  <td>{(Number(r.indicator_ratio || 0) * 100).toFixed(1)}% ({Number(r.indicator_count || 0)})</td>
                  <td>{r.count}</td>
                  <td>{(r.win_rate * 100).toFixed(1)}%</td>
                  <td className={r.pnl >= 0 ? "fg-good" : "fg-bad"}>{r.pnl.toFixed(2)}</td>
                  <td>{r.avg_entry_score.toFixed(1)}</td>
                  <td>{r.avg_exit_score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid two">
        <div className="card">
          <CardHead title={`공식 조건 커버리지(${tabLabel})`} help="선택 탭의 CLOSED 이력에서 진입/청산 근거 + 지표기반 매칭으로 계산한 공식 항목 기록 비율입니다." />
          <RatioBars rows={conditionCoverageTab} labelKey="label" valueKey="ratio" />
        </div>
        <div className="card">
          <CardHead title={`최신 지표값(${tabLabel})`} help="CSV에 저장된 최신 지표값과 최근 비영(0이 아닌) 값을 비교합니다. 모두 0이면 지표 수집이 비정상일 가능성이 큽니다." />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {tabSymbol === "ALL" ? <th>심볼</th> : null}
                  <th>지표</th>
                  <th>최신값</th>
                  <th>최근 비영값</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {indicatorLatestTab.map((r) => (
                  <tr key={`ind-latest-${r.symbol || tabSymbol}-${r.column}`}>
                    {tabSymbol === "ALL" ? <td>{String(r.symbol || "-")}</td> : null}
                    <td>{r.column}</td>
                    <td>{Number(r.latest || 0).toFixed(4)}</td>
                    <td>{Number(r.latest_nonzero || 0).toFixed(4)}</td>
                    <td className={r.has_nonzero ? "fg-good" : "fg-bad"}>{r.has_nonzero ? "정상" : "점검 필요"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="card jump-section" id="sec-learning-trend">
        <CardHead title="학습 반영 추이(심볼별)" help="선택 심볼의 AI 가감점/확률/최종점수 변화 추이입니다." />
        <div className="grid four">
          <StatCard label="반영 로그 수" value={Number(learnedEffectTab.trace_count || 0)} tone="neutral" />
          <StatCard label="평균 가감점" value={Number(learnedEffectTab.avg_adj || 0).toFixed(2)} tone={Number(learnedEffectTab.avg_adj || 0) >= 0 ? "good" : "bad"} />
          <StatCard label="평균 확률" value={Number(learnedEffectTab.avg_prob || 0).toFixed(3)} tone="neutral" />
          <StatCard label="평균(최종-원점수)" value={Number(learnedEffectTab.avg_final_minus_raw || 0).toFixed(2)} tone={Number(learnedEffectTab.avg_final_minus_raw || 0) >= 0 ? "good" : "bad"} />
        </div>
        <FourHourBars rows={(learnedTimelineTab || []).map((x) => ({ bucket: x.bucket, pnl: x.avg_adj }))} />
      </section>

      <section className="grid two jump-section" id="sec-daily-cumpnl">
        <div className="card">
          <CardHead title="일자별 누적 손익" help="선택 심볼의 종료 거래 기준으로 날짜별 손익 누적 추이를 표시합니다." />
          <Sparkline
            points={cumPnlSeriesTab}
            labels={dailyLabelsTab}
            stroke="#0f766e"
            fill="rgba(15,118,110,0.14)"
            valueFormatter={(v) => Number(v || 0).toFixed(2)}
          />
          <div className="axis-note">
            <span>X축: 날짜(일자 순)</span>
            <span>Y축: 누적 손익(계좌통화 기준, {tabSymbol})</span>
          </div>
        </div>
        <div className="card">
          <CardHead title="일자별 승률" help="선택 심볼의 해당 날짜 종료 거래 승리 비율입니다." />
          <Sparkline
            points={winRateSeriesTab}
            labels={dailyLabelsTab}
            stroke="#2563eb"
            fill="rgba(37,99,235,0.12)"
            valueFormatter={(v) => `${Number(v || 0).toFixed(2)}%`}
          />
          <div className="axis-note">
            <span>X축: 날짜(일자 순)</span>
            <span>Y축: 승률(%), {tabSymbol}</span>
          </div>
        </div>
      </section>

      <section className="card">
        <CardHead title="4시간 단위 손익(심볼별)" help="선택 심볼의 4시간 손익을 보여줍니다." />
        <div className="tab-row">
          {SYMBOLS.map((s) => (
            <button
              key={`fourh-${s.key}`}
              type="button"
              className={`tab-btn ${tabSymbol === s.key ? "active" : ""}`}
              onClick={() => setTabSymbol(s.key)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <FourHourBars rows={rows4hTab} />
      </section>

      <section className="grid two">
        <div className="card">
          <CardHead title="진입 근거 성과" help="진입 사유별 거래 횟수, 승률, 손익 요약입니다." />
          <ReasonBars rows={data.analytics?.entry_reasons || []} />
        </div>
        <div className="card">
          <CardHead title="청산 근거 성과" help="청산 사유별 거래 횟수, 승률, 손익 요약입니다." />
          <ReasonBars rows={data.analytics?.exit_reasons || []} />
        </div>
      </section>

      <section className="grid three jump-section" id="sec-current-positions">
        {symbolPanels.filter((panel) => panel.key !== "ALL").map((panel) => (
          <div className="card" key={`open-${panel.key}`}>
            <CardHead title={`${panel.label} 현재 포지션`} help="실시간 MT5 포지션. 실패 시 CSV OPEN 데이터로 보조 표시합니다." />
            {panel.usedSticky ? (
              <div className="history-empty">일시 연결 불안정: 최근 정상 스냅샷으로 표시 중</div>
            ) : null}
            {panel.openRows.length === 0 ? (
              <div className="empty-chart">현재 오픈 포지션 없음</div>
            ) : (
              <div className="symbol-list">
                {panel.openRows.slice(0, 20).map((r) => (
                  <details key={`open-${r.ticket}`} className="entry-detail">
                    <summary>
                      <span>{r.symbol} #{r.ticket}</span>
                      <span className={Number(r.profit) >= 0 ? "fg-good" : "fg-bad"}>{Number(r.profit || 0).toFixed(2)}</span>
                    </summary>
                    <div className="entry-grid">
                      <div>방향: <strong>{r.direction || "-"}</strong></div>
                      <div>진입 시점: <strong>{r.open_time || "-"}</strong></div>
                      <div>진입 랏: <strong>{Number(r.lot || 0).toFixed(2)}</strong></div>
                      <div>진입 점수: <strong>{Number(r.entry_score || 0).toFixed(0)}</strong></div>
                      <div>반대 점수: <strong>{Number(r.contra_score_at_entry || 0).toFixed(0)}</strong></div>
                      <div>현재 손익: <strong className={Number(r.profit) >= 0 ? "fg-good" : "fg-bad"}>{Number(r.profit || 0).toFixed(2)}</strong></div>
                      <div>진입 가격: <strong>{formatValue(r.price_open, 3)}</strong></div>
                      <div>상태: <strong>{String(r.status || "OPEN")}</strong></div>
                    </div>
                    <details className="reason-toggle">
                      <summary>진입 사유 펼치기/접기</summary>
                      <div className="reason-group">
                        <div className="reason-title">진입</div>
                        <ul className="reason-list">
                          {(r.entry_reasons || []).length ? (
                            decorateReasonsWithTotal(r.entry_reasons || [], Number(r.entry_score || 0)).map((x, i) => <li key={i}>{x}</li>)
                          ) : (
                            <li>근거 데이터 없음</li>
                          )}
                        </ul>
                      </div>
                    </details>
                    <details className="reason-toggle">
                      <summary>지표/원본 데이터 펼치기/접기</summary>
                      <div className="kv-grid">
                        {indicatorEntries(r).length ? (
                          indicatorEntries(r).map(([key, label, value]) => (
                            <div key={`${r.ticket}-${key}`}>
                              {label}: <strong>{formatValue(value, 4)}</strong>
                            </div>
                          ))
                        ) : (
                          <div>지표 데이터 없음</div>
                        )}
                      </div>
                    </details>
                  </details>
                ))}
              </div>
            )}
          </div>
        ))}
      </section>

      <section className="grid three jump-section" id="sec-history-positions">
        {symbolPanels.filter((panel) => panel.key !== "ALL").map((panel) => (
          <div className="card" key={`hist-${panel.key}`}>
            <CardHead title={`${panel.label} 과거 포지션`} help="CLOSED 이력 기준, 최신순 정렬, 10개 단위 페이지." />
            <div className="history-wrap no-top">
              {panel.histRowsAllCount === 0 ? (
                <div className="history-empty">최근 종료 이력 없음</div>
              ) : (
                <>
                  <div className="history-list">
                    {panel.histRows.map((h, idx) => (
                      <details className="entry-detail" key={`hist-${panel.key}-${idx}`}>
                        <summary>
                          <span>{h.symbol} #{h.ticket} | {h.close_time || h.open_time}</span>
                          <span className={Number(h.profit || 0) >= 0 ? "fg-good" : "fg-bad"}>
                            {Number(h.profit || 0).toFixed(2)}
                          </span>
                        </summary>
                        <div className="entry-grid">
                          <div>방향: <strong>{h.direction || "-"}</strong></div>
                          <div>진입 시점: <strong>{h.open_time || "-"}</strong></div>
                          <div>청산 시점: <strong>{h.close_time || "-"}</strong></div>
                          <div>진입 랏: <strong>{Number(h.lot || 0).toFixed(2)}</strong></div>
                          <div>진입 점수: <strong>{Number(h.entry_score || 0).toFixed(0)}</strong></div>
                          <div>청산 점수: <strong>{Number(h.exit_score || 0).toFixed(0)}</strong></div>
                          <div>진입 가격: <strong>{formatValue(h.open_price, 3)}</strong></div>
                          <div>청산 가격: <strong>{formatValue(h.close_price, 3)}</strong></div>
                          <div>포인트: <strong>{formatValue(h.points, 1)}</strong></div>
                          <div>
                            최종 손익:
                            <strong className={Number(h.profit || 0) >= 0 ? "fg-good" : "fg-bad"}>
                              {" "}{Number(h.profit || 0).toFixed(2)}
                            </strong>
                          </div>
                        </div>
                        <details className="reason-toggle">
                          <summary>진입/청산 사유 펼치기/접기</summary>
                          <div className="reason-group">
                            <div className="reason-title">진입</div>
                            <ul className="reason-list">
                              {splitReasonText(h.entry_reason || "").length ? (
                                decorateReasonsWithTotal(
                                  splitReasonText(h.entry_reason || ""),
                                  Number(h.entry_score || 0),
                                ).map((x, i) => <li key={`entry-${i}`}>{x}</li>)
                              ) : (
                                <li>UNKNOWN</li>
                              )}
                            </ul>
                          </div>
                          <div className="reason-group">
                            <div className="reason-title">청산</div>
                            <ul className="reason-list">
                              {splitReasonText(h.exit_reason || "").length ? (
                                decorateReasonsWithTotal(
                                  splitReasonText(h.exit_reason || ""),
                                  Number(h.exit_score || 0),
                                ).map((x, i) => <li key={`exit-${i}`}>{x}</li>)
                              ) : (
                                <li>UNKNOWN</li>
                              )}
                            </ul>
                          </div>
                        </details>
                        <details className="reason-toggle">
                          <summary>지표/원본 데이터 펼치기/접기</summary>
                          <div className="kv-grid">
                            {indicatorEntries(h).length ? (
                              indicatorEntries(h).map(([key, label, value]) => (
                                <div key={`${h.ticket}-${key}`}>
                                  {label}: <strong>{formatValue(value, 4)}</strong>
                                </div>
                              ))
                            ) : (
                              <div>지표 데이터 없음</div>
                            )}
                          </div>
                        </details>
                      </details>
                    ))}
                  </div>
                  {panel.totalPages > 1 ? (
                    <div className="pager">
                      <button
                        type="button"
                        className="pager-btn arrow-btn"
                        disabled={panel.page === 1}
                        onClick={() =>
                          setHistoryPage((prev) => ({
                            ...prev,
                            [panel.key]: 1,
                          }))
                        }
                      >
                        {"<<"}
                      </button>
                      <button
                        type="button"
                        className="pager-btn arrow-btn"
                        disabled={panel.page === 1}
                        onClick={() =>
                          setHistoryPage((prev) => ({
                            ...prev,
                            [panel.key]: Math.max(1, panel.page - 1),
                          }))
                        }
                      >
                        {"<"}
                      </button>
                      {panel.pageNumbers.map((p) => (
                        <button
                          key={`${panel.key}-p-${p}`}
                          type="button"
                          className={`pager-btn page-num ${panel.page === p ? "active" : ""}`}
                          onClick={() =>
                            setHistoryPage((prev) => ({
                              ...prev,
                              [panel.key]: p,
                            }))
                          }
                        >
                          {p}
                        </button>
                      ))}
                      <button
                        type="button"
                        className="pager-btn arrow-btn"
                        disabled={panel.page === panel.totalPages}
                        onClick={() =>
                          setHistoryPage((prev) => ({
                            ...prev,
                            [panel.key]: Math.min(panel.totalPages, panel.groupEnd + 1),
                          }))
                        }
                      >
                        {">"}
                      </button>
                      <button
                        type="button"
                        className="pager-btn arrow-btn"
                        disabled={panel.page === panel.totalPages}
                        onClick={() =>
                          setHistoryPage((prev) => ({
                            ...prev,
                            [panel.key]: panel.totalPages,
                          }))
                        }
                      >
                        {">>"}
                      </button>
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </div>
        ))}
      </section>
      <section className="card jump-section" id="sec-api-status">
        <CardHead title="API 상태" help="각 API 엔드포인트의 응답 상태를 표시합니다." />
        {STABILITY_MODE ? (
          <div style={{ marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
            <button
              type="button"
              onClick={() => loadSlow()}
              disabled={slowRefreshing}
              style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid #5b6780", background: "#121b2b", color: "#e8eefc", cursor: slowRefreshing ? "default" : "pointer" }}
            >
              {slowRefreshing ? "분석 API 갱신 중..." : "분석 API 수동 새로고침"}
            </button>
            <span className="fg-warn" style={{ fontSize: 12 }}>안정모드: slow endpoint 자동 폴링 비활성화</span>
          </div>
        ) : null}
        <div className="kv-grid" style={{ marginBottom: 10 }}>
          <div>
            <strong>Last Poll</strong>: {Number(apiPerf?.lastPollMs || 0).toFixed(0)}ms
          </div>
          <div>
            <strong>Rows(Open/Closed)</strong>: {Number(apiPerf?.rowsOpenMs || 0).toFixed(0)} / {Number(apiPerf?.rowsClosedMs || 0).toFixed(0)} ms
          </div>
          <div>
            <strong>SSE Connected</strong>: <span className={sseStatus?.connected ? "fg-good" : "fg-warn"}>{sseStatus?.connected ? "YES" : "NO"}</span>
          </div>
          <div>
            <strong>SSE Reconnect</strong>: {Number(sseStatus?.reconnect_count || 0)}
          </div>
          <div>
            <strong>SSE Idle</strong>: {sseIdleSec >= 0 ? `${sseIdleSec}s` : "-"}
          </div>
          <div>
            <strong>Backend Latency Keys</strong>: {Object.keys(apiLatencySnapshot || {}).length}
          </div>
          <div>
            <strong>Latency Tone</strong>:{" "}
            <span className="fg-good">GOOD {Number(latencyToneSummary.good || 0)}</span>
            {" / "}
            <span className="fg-warn">WARN {Number(latencyToneSummary.warn || 0)}</span>
            {" / "}
            <span className="fg-bad">BAD {Number(latencyToneSummary.bad || 0)}</span>
          </div>
        </div>
        {Object.keys(kpiEvaluation || {}).length ? (
          <div className="kv-grid" style={{ marginBottom: 10 }}>
            <div>
              <strong>KPI Overall</strong>:&nbsp;
              <span
                style={{
                  display: "inline-block",
                  padding: "2px 8px",
                  borderRadius: 999,
                  border: `1px solid ${kpiOverallTone.bd}`,
                  background: kpiOverallTone.bg,
                  color: kpiOverallTone.fg,
                  fontWeight: 700,
                }}
              >
                {kpiOverallTone.icon} {String(kpiEvaluation?.overall || "monitoring").toUpperCase()}
              </span>
              {kpiEvaluation?.hard_triggered ? (
                <span className="fg-bad" style={{ marginLeft: 8 }}>
                  HARD TRIGGER
                </span>
              ) : null}
            </div>
            {kpiMetricRows.map((row) => {
              const tone = kpiGradeTone(row.grade);
              return (
                <div key={`kpi-row-${row.key}`}>
                  <strong>{row.label}</strong>:&nbsp;
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 999,
                      border: `1px solid ${tone.bd}`,
                      background: tone.bg,
                      color: tone.fg,
                      fontWeight: 700,
                    }}
                  >
                    {tone.icon} {String(row.grade || "monitoring").toUpperCase()}
                  </span>
                  &nbsp;{row.value}
                </div>
              );
            })}
            <div>
              <strong>KPI Thresholds</strong>:&nbsp;
              <details style={{ display: "inline-block", verticalAlign: "top" }}>
                <summary style={{ cursor: "pointer" }}>보기</summary>
                <pre style={{ margin: "6px 0 0", whiteSpace: "pre-wrap", maxWidth: 560 }}>
{JSON.stringify(kpiEvaluation?.thresholds || {}, null, 2)}
                </pre>
              </details>
            </div>
          </div>
        ) : null}
        <div className="status-grid">
          {ENDPOINTS.map((e) => {
            const s = apiStatus[e.key];
            const manualPending = false;
            const pillOk = manualPending ? true : Boolean(s?.ok);
            return (
              <div key={e.key} className={`status-pill ${pillOk ? "ok" : "err"}`}>
                <strong>{e.key}</strong>
                <span>{manualPending ? "수동(필요 시 새로고침)" : (s?.message || "대기 중")}</span>
              </div>
            );
          })}
        </div>
        {!!backendLatencyRows.length && (
          <div className="table-wrap" style={{ marginTop: 10 }}>
            <table>
              <thead>
                <tr>
                  <th>Tone</th>
                  <th>Endpoint</th>
                  <th>EMA ms</th>
                  <th>Last ms</th>
                  <th>Max ms</th>
                  <th>Errors</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {backendLatencyRows.map((r) => {
                  const tone = latencyToneOf(r);
                  return (
                  <tr key={`lat-${r.key}`}>
                    <td>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 999,
                          border: `1px solid ${tone.bd}`,
                          background: tone.bg,
                          color: tone.fg,
                          fontWeight: 700,
                        }}
                      >
                        {tone.label}
                      </span>
                    </td>
                    <td>{r.key}</td>
                    <td>{r.ema.toFixed(1)}</td>
                    <td>{r.last.toFixed(1)}</td>
                    <td>{r.max.toFixed(1)}</td>
                    <td className={r.err > 0 ? "fg-bad" : "fg-good"}>{r.err}</td>
                    <td>{r.count}</td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {Object.keys(exitMetrics || {}).length ? (
          <div className="history-wrap">
            <h3>Exit Metrics (runtimeStatus)</h3>
            <div className="kv-grid">
              <div>
                <strong>Runtime Warnings</strong>:{" "}
                <span className={Object.keys(runtimeWarningCounters || {}).length > 0 ? "fg-warn" : "fg-good"}>
                  {Object.keys(runtimeWarningCounters || {}).length}
                </span>
              </div>
              {Object.entries(runtimeWarningCounters || {})
                .sort((a, b) => Number(b?.[1]?.count || 0) - Number(a?.[1]?.count || 0))
                .slice(0, 6)
                .map(([k, v]) => (
                  <div key={`rt-warn-${k}`}>
                    <strong>{k}</strong>:{" "}
                    <span className={Number(v?.count || 0) >= 5 ? "fg-bad" : "fg-warn"}>
                      x{Number(v?.count || 0)}
                    </span>{" "}
                    | 최근 {String(v?.last_at || "-")}
                  </div>
                ))}
            </div>
            <div className="kv-grid">
              {Object.entries(runtimeUiFieldMap).map(([k, v]) => (
                <div key={`ui-map-${k}`}>
                  <strong>{k}</strong>: {String(v?.frontend_read || "-")} {"<="} {String(v?.source || "-")}
                </div>
              ))}
            </div>
            <div className="kv-grid">
              <div>
                <strong>Execution Profile</strong>: {String(exitExecProfile?.effective || "-")}
              </div>
              <div>
                <strong>Profile Source</strong>: {String(exitExecProfile?.configured || "-")}
              </div>
              <div>
                <strong>Regime</strong>: {String(exitExecProfile?.regime || "-")}
              </div>
              <div>
                <strong>Invalid Learning Samples</strong>: <span className={invalidLearningSamples > 0 ? "fg-warn" : "fg-good"}>{invalidLearningSamples}</span>
              </div>
              <div>
                <strong>Label Clip Applied</strong>: <span className={labelClipAppliedCount > 0 ? "fg-warn" : "fg-good"}>{labelClipAppliedCount}</span>
              </div>
              <div>
                <strong>Net vs Gross Gap Avg</strong>: {netVsGrossGapAvg.toFixed(4)}
              </div>
              <div>
                <strong>Fallback Ready(Symbol+Regime)</strong>: {Number(learningFallbackSummary?.symbol_regime_ready_count || 0)}
              </div>
              <div>
                <strong>Fallback Ready(Symbol)</strong>: {Number(learningFallbackSummary?.symbol_ready_count || 0)}
              </div>
              <div>
                <strong>Fallback Global Samples</strong>: {Number(learningFallbackSummary?.global_samples || 0)}
              </div>
              <div>
                <strong>Fallback Global Ready</strong>: <span className={learningFallbackSummary?.global_ready ? "fg-good" : "fg-warn"}>{learningFallbackSummary?.global_ready ? "YES" : "NO"}</span>
              </div>
              <div>
                <strong>SQLite Mirror</strong>:&nbsp;
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: 999,
                    border: `1px solid ${sqliteMirrorTone.bd}`,
                    background: sqliteMirrorTone.bg,
                    color: sqliteMirrorTone.fg,
                    fontWeight: 700,
                  }}
                >
                  {sqliteMirrorTone.icon} {sqliteMirrorTone.label}
                </span>
              </div>
              <div>
                <strong>SQLite Mirror Failures</strong>: {Number(sqliteMirrorStatus?.failure_count || 0)}
              </div>
              <div>
                <strong>SQLite Last Failure</strong>: {String(sqliteMirrorStatus?.last_failure_at || "-")}
              </div>
              <div>
                <strong>SQLite Last Failure Op</strong>: {String(sqliteMirrorStatus?.last_failure_op || "-")}
              </div>
              <div>
                <strong>SQLite Last Failure Error</strong>:&nbsp;
                {String(sqliteMirrorStatus?.last_failure_error || "").trim() ? (
                  <details style={{ display: "inline-block", verticalAlign: "top" }}>
                    <summary style={{ cursor: "pointer" }}>보기</summary>
                    <pre style={{ margin: "6px 0 0", whiteSpace: "pre-wrap", maxWidth: 520 }}>
                      {String(sqliteMirrorStatus?.last_failure_error || "")}
                    </pre>
                  </details>
                ) : (
                  "-"
                )}
              </div>
              <div>
                <strong>Risk Guard Total</strong>: <span className={riskGuardTotal > 0 ? "fg-warn" : "fg-good"}>{riskGuardTotal}</span>
              </div>
              <div>
                <strong>Risk Guard Plus-&gt;Minus</strong>: {riskGuardPlusToMinus}
              </div>
              <div>
                <strong>Risk Guard Adverse</strong>: {riskGuardAdverse}
              </div>
              <div>
                <strong>Entry Meta Cap Hits</strong>: <span className={entryMetaCapHits > 0 ? "fg-warn" : "fg-good"}>{entryMetaCapHits}</span>
              </div>
              <div>
                <strong>Stage Exec (S/M/L/A)</strong>: {stageExecShort} / {stageExecMid} / {stageExecLong} / {stageExecAuto}
              </div>
              <div>
                <strong>Runtime Alerts</strong>: <span className={Number(runtimeAlerts?.active_count || 0) > 0 ? "fg-warn" : "fg-good"}>{Number(runtimeAlerts?.active_count || 0)}</span>
              </div>
              <div>
                <strong>Policy Rollback Count</strong>: <span className={policyRollbackCount > 0 ? "fg-warn" : "fg-good"}>{policyRollbackCount}</span>
              </div>
              <div>
                <strong>Learning Apply Status</strong>: <span className={String(learningApplyLoop?.status || "bootstrap") === "ok" ? "fg-good" : (String(learningApplyLoop?.status || "bootstrap") === "warn" ? "fg-warn" : "fg-bad")}>{String(learningApplyLoop?.status || "bootstrap").toUpperCase()}</span>
              </div>
              <div>
                <strong>Loop/Policy Update</strong>: #{Number(learningApplyLoop?.runtime_loop_count || 0)} / {String(learningApplyLoop?.runtime_updated_at || "-")}
              </div>
              <div>
                <strong>Policy Updated At</strong>: {String(learningApplyLoop?.policy_updated_at || "-")}
              </div>
              <div>
                <strong>Policy Age/ETA(s)</strong>: {learningApplyLoop?.policy_age_sec == null ? "-" : Number(learningApplyLoop?.policy_age_sec || 0).toFixed(1)} / {learningApplyLoop?.policy_next_refresh_eta_sec == null ? "-" : Number(learningApplyLoop?.policy_next_refresh_eta_sec || 0).toFixed(1)}
              </div>
              <div>
                <strong>Policy Cnt(U/R/RB)</strong>: {Number(learningApplyLoop?.policy_update_count || 0)} / {Number(learningApplyLoop?.policy_update_rejected_count || 0)} / {Number(learningApplyLoop?.policy_rollback_count || 0)}
              </div>
              <div>
                <strong>C3 Block(remain/count/streak)</strong>: {Number(learningApplyLoop?.policy_blocked_remaining_sec || 0).toFixed(1)}s / {Number(learningApplyLoop?.policy_guard_block_count || 0)} / {Number(learningApplyLoop?.policy_update_reject_streak || 0)}
              </div>
              <div>
                <strong>Policy Samples/Conf</strong>: {Number(learningApplyLoop?.samples_total || 0)} / {Number(learningApplyLoop?.sample_confidence || 0).toFixed(3)}
              </div>
              <div>
                <strong>Policy Fallback</strong>: <span className={learningApplyLoop?.fallback_applied ? "fg-warn" : "fg-good"}>{learningApplyLoop?.fallback_applied ? "ON" : "OFF"}</span>
              </div>
              <ExpectancyMiniTable title="Expectancy(Symbol)" data={expectancyBySymbol} />
              <ExpectancyMiniTable title="Expectancy(Regime)" data={expectancyByRegime} />
              <ExpectancyMiniTable title="Expectancy(Hour)" data={expectancyByHourBucket} />
              {Array.isArray(runtimeAlerts?.items) ? runtimeAlerts.items.slice(0, 4).map((a, idx) => (
                <div key={`rt-alert-${idx}`}>
                  <strong>{String(a?.code || "alert")}</strong>: <span className={String(a?.severity || "").toLowerCase() === "fail" ? "fg-bad" : "fg-warn"}>{String(a?.message || "-")}</span>
                </div>
              )) : null}
              <div>
                <strong>D6 Execution Guard</strong>: <span className={dExecutionState?.d6_execution_order_guard ? "fg-good" : "fg-warn"}>{dExecutionState?.d6_execution_order_guard ? "OK" : "CHECK"}</span>
              </div>
              <div>
                <strong>D7 Runtime Visibility</strong>: <span className={dAcceptanceSnapshot?.runtime_visibility_ready ? "fg-good" : "fg-warn"}>{dAcceptanceSnapshot?.runtime_visibility_ready ? "OK" : "CHECK"}</span>
              </div>
              <div>
                <strong>D7 Policy Independence</strong>: <span className={dAcceptanceSnapshot?.symbol_policy_independent ? "fg-good" : "fg-warn"}>{dAcceptanceSnapshot?.symbol_policy_independent ? "OK" : "CHECK"}</span>
              </div>
              <div>
                <strong>D7 Plus-&gt;Minus</strong>:&nbsp;
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: 999,
                    border: `1px solid ${d7GlobalPlusTone.bd}`,
                    background: d7GlobalPlusTone.bg,
                    color: d7GlobalPlusTone.fg,
                    fontWeight: 700,
                  }}
                >
                  {d7GlobalPlusTone.icon} {String(dAcceptanceSnapshot?.plus_to_minus_trend_check || "monitoring").toUpperCase()}
                </span>
              </div>
              <div>
                <strong>D7 Adverse Stop</strong>:&nbsp;
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: 999,
                    border: `1px solid ${d7GlobalAdverseTone.bd}`,
                    background: d7GlobalAdverseTone.bg,
                    color: d7GlobalAdverseTone.fg,
                    fontWeight: 700,
                  }}
                >
                  {d7GlobalAdverseTone.icon} {String(dAcceptanceSnapshot?.adverse_stop_trend_check || "monitoring").toUpperCase()}
                </span>
              </div>
              <div>
                <strong>Plus-&gt;Minus(Current/Base)</strong>: {Number(dAcceptanceSnapshot?.plus_to_minus_ratio_current || 0).toFixed(3)} / {Number(dAcceptanceSnapshot?.plus_to_minus_ratio_baseline || 0).toFixed(3)}
              </div>
              <div>
                <strong>Adverse Stop(Current/Base)</strong>: {Number(dAcceptanceSnapshot?.adverse_stop_ratio_current || 0).toFixed(3)} / {Number(dAcceptanceSnapshot?.adverse_stop_ratio_baseline || 0).toFixed(3)}
              </div>
              {d7SymbolRows.map((row) => (
                <div key={`d7-symbol-${row.key}`}>
                  <strong>D7 {row.label}</strong>:&nbsp;
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 999,
                      border: `1px solid ${row.plusTone.bd}`,
                      background: row.plusTone.bg,
                      color: row.plusTone.fg,
                      fontWeight: 700,
                    }}
                  >
                    {row.plusTone.icon} P2M
                  </span>
                  &nbsp;{row.plusCurrent.toFixed(3)} / {row.plusBaseline.toFixed(3)}
                  &nbsp;|&nbsp;
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 999,
                      border: `1px solid ${row.adverseTone.bd}`,
                      background: row.adverseTone.bg,
                      color: row.adverseTone.fg,
                      fontWeight: 700,
                    }}
                  >
                    {row.adverseTone.icon} ADV
                  </span>
                  &nbsp;{row.adverseCurrent.toFixed(3)} / {row.adverseBaseline.toFixed(3)}
                </div>
              ))}
              <div>
                <strong>D7 Baseline At</strong>: {String(dAcceptanceSnapshot?.baseline_established_at || "-")}
              </div>
              <div>
                <strong>Policy Sample Confidence</strong>: {Number(policyRuntime?.sample_confidence || 0).toFixed(3)}
              </div>
              <div>
                <strong>Policy Samples Total</strong>: {Number(policyRuntime?.samples_total || 0)}
              </div>
              <div>
                <strong>{tabSymbol} Policy Scope</strong>: {String(tabPolicy?.policy_scope || "-")}
              </div>
              <div>
                <strong>{tabSymbol} Sample Confidence</strong>: {Number(tabPolicy?.sample_confidence || 0).toFixed(3)}
              </div>
              <div>
                <strong>{tabSymbol} Entry/Exit</strong>: {Number(tabPolicy?.entry_threshold || 0)} / {Number(tabPolicy?.exit_threshold || 0)}
              </div>
              <div>
                <strong>{tabSymbol} Adverse/Reverse</strong>: {Number(tabPolicy?.adverse_loss_usd || 0).toFixed(2)} / {Number(tabPolicy?.reverse_signal_threshold || 0)}
              </div>
              <div style={{ gridColumn: "1 / -1", marginTop: 6 }}>
                <strong>Symbol Applied vs Default</strong>
              </div>
              {symbolTuneRows.map((row) => (
                <div key={`symbol-tune-${row.key}`} style={{ gridColumn: "1 / -1", border: "1px solid #2b3950", borderRadius: 8, padding: "8px 10px" }}>
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>
                    {row.label} | scope={row.policyScope} | conf={row.sampleConfidence.toFixed(3)} | n={row.sampleCount}
                    &nbsp;
                    <span className={row.worstGrade === "fail" ? "fg-bad" : (row.worstGrade === "warn" ? "fg-warn" : "fg-good")}>
                      [{row.worstGrade.toUpperCase()}]
                    </span>
                  </div>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Metric</th>
                        <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Default</th>
                        <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Applied</th>
                        <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Delta</th>
                        <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {row.metrics.map((m) => (
                        <tr key={`${row.key}-${m.key}`}>
                          <td style={{ padding: "2px 4px" }}>{m.label}</td>
                          <td style={{ textAlign: "right", padding: "2px 4px" }}>{m.default.toFixed(4)}</td>
                          <td style={{ textAlign: "right", padding: "2px 4px" }}>{m.applied.toFixed(4)}</td>
                          <td className={m.delta === 0 ? "fg-neutral" : (m.delta > 0 ? "fg-good" : "fg-warn")} style={{ textAlign: "right", padding: "2px 4px" }}>
                            {m.delta > 0 ? "+" : ""}{m.delta.toFixed(4)}
                          </td>
                          <td className={m.tone === "bad" ? "fg-bad" : (m.tone === "warn" ? "fg-warn" : "fg-good")} style={{ textAlign: "right", padding: "2px 4px", fontWeight: 700 }}>
                            {m.grade.toUpperCase()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
              <div style={{ gridColumn: "1 / -1", marginTop: 6 }}>
                <strong>C2 Symbol Learning Split (1:1)</strong>
              </div>
              <div style={{ gridColumn: "1 / -1", border: "1px solid #2b3950", borderRadius: 8, padding: "8px 10px" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Symbol</th>
                      <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Source N</th>
                      <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Policy N</th>
                      <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Gap</th>
                      <th style={{ textAlign: "left", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Scope</th>
                      <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Conf</th>
                      <th style={{ textAlign: "left", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Regime</th>
                      <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Slots</th>
                      <th style={{ textAlign: "right", padding: "2px 4px", borderBottom: "1px solid #2b3950" }}>Grade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {symbolLearningRows.map((r) => (
                      <tr key={`c2-split-${r.key}`}>
                        <td style={{ padding: "2px 4px" }}>{r.label}</td>
                        <td style={{ textAlign: "right", padding: "2px 4px" }}>{r.srcN}</td>
                        <td style={{ textAlign: "right", padding: "2px 4px" }}>{r.polN}</td>
                        <td className={r.gap === 0 ? "fg-good" : "fg-warn"} style={{ textAlign: "right", padding: "2px 4px", fontWeight: 700 }}>{r.gap}</td>
                        <td style={{ padding: "2px 4px" }}>{r.scope}</td>
                        <td style={{ textAlign: "right", padding: "2px 4px" }}>{r.conf.toFixed(3)}</td>
                        <td style={{ padding: "2px 4px" }}>{r.domRegime}</td>
                        <td style={{ textAlign: "right", padding: "2px 4px" }}>{r.regimeCount}</td>
                        <td className={r.grade === "PASS" ? "fg-good" : (r.grade === "WARN" ? "fg-warn" : "fg-bad")} style={{ textAlign: "right", padding: "2px 4px", fontWeight: 700 }}>{r.grade}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <strong>{tabSymbol} Blend Rule:Model</strong>: {Number(blendRuleW || 0).toFixed(3)} : {Number(blendModelW || 0).toFixed(3)}
              </div>
              <div>
                <strong>{tabSymbol} Blend Mode</strong>: {String(tabBlendRuntime?.blend_mode || blendRuntime?.mode || "-")}
              </div>
            </div>
            <BlendMiniTimeline rows={blendHistory} />
            <div className="kv-grid">
              {blendQualitySignals.map((row) => (
                <div key={row.label}>
                  <strong>{row.label}</strong>: <span className={toneClass(row.tone)}>{row.value}</span>
                </div>
              ))}
            </div>
            <div className="kv-grid">
              {stageRows.map((r) => (
                <div key={r.label}>
                  <strong>{r.label}</strong>: n={r.count}, 비중={pct(r.ratio)}, 승률={pct(r.wr)}, 손익={r.pnl.toFixed(2)}
                </div>
              ))}
            </div>
            <div className="kv-grid">
              {exitQualitySignals.map((row) => (
                <div key={row.label}>
                  <strong>{row.label}</strong>: <span className={toneClass(row.tone)}>{row.value}</span>
                </div>
              ))}
            </div>
            <div className="kv-grid">
              {exitMetricPairs.map(([k, v]) => (
                <div key={k}>
                  <strong>{k}</strong>: {v}
                </div>
              ))}
              <div>
                <strong>업데이트</strong>: {String(exitMetrics?.updated_at || "-")}
              </div>
            </div>
          </div>
        ) : null}
      </section>
      </div>
      </div>
      </div>
    </main>
  );
}

