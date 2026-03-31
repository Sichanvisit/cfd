export default function StatCard({ label, value, tone = "neutral", help = "" }) {
  return (
    <div className={`card stat ${tone}`}>
      <p className="label">{label}</p>
      <p className="value">{value}</p>
      {help ? <p className="help">{help}</p> : null}
    </div>
  );
}
