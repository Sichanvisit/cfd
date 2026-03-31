export default function MarketViewCard({ item }) {
  if (!item) return null;
  const tone = String(item.action_tone || "neutral");
  const logs = Array.isArray(item.logs) ? item.logs : [];

  return (
    <div className={`card market-view-card tone-${tone}`}>
      <div className="market-view-head">
        <div>
          <div className="market-view-symbol">{item.symbol}</div>
          <div className="market-view-meta">
            <span>{item.market_mode || "-"}</span>
            <span>{item.liquidity || "-"}</span>
          </div>
        </div>
        <div className={`market-view-badge ${tone}`}>{item.action_badge || "대기"}</div>
      </div>

      <div className="market-view-location">{item.location_summary || "-"}</div>
      <div className="market-view-summary">
        <strong>Position</strong>
        <span>{item.position_summary || "-"}</span>
      </div>
      <div className="market-view-summary">
        <strong>현재 해석</strong>
        <span>{item.decision_summary || "-"}</span>
      </div>
      <div className="market-view-summary">
        <strong>다음 트리거</strong>
        <span>{item.next_trigger || "-"}</span>
      </div>

      <div className="market-view-log">
        {logs.map((log, idx) => (
          <div className="market-view-log-item" key={`${item.symbol}-log-${idx}`}>
            <strong>{log.label || "로그"}</strong>
            <span>{log.text || "-"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
