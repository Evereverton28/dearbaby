/* Small shared pieces. Kept together so the import list stays short. */
import { Link } from 'react-router-dom';

export const Card = ({ children, className = '', ...rest }) => (
  <div className={`card ${className}`} {...rest}>{children}</div>
);

export const Loading = ({ label = 'Loading…' }) => (
  <div className="empty"><p>{label}</p></div>
);

export const ErrorNote = ({ children }) =>
  children ? <div className="alert alert-error">{children}</div> : null;

/* Empty states are an invitation to act, never just a shrug. */
export const Empty = ({ title, body, action, to }) => (
  <div className="empty">
    <h3>{title}</h3>
    <p>{body}</p>
    {action && to && <p style={{ marginTop: 14 }}><Link className="btn btn-primary" to={to}>{action}</Link></p>}
  </div>
);

export const Stat = ({ value, label }) => (
  <div className="card stat"><b>{value}</b><small>{label}</small></div>
);

export function WeekRing({ week, total = 40, size = 92 }) {
  const r = size / 2 - 7;
  const c = 2 * Math.PI * r;
  const pct = Math.min(week / total, 1);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke="var(--accent-soft)" strokeWidth="8" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke="var(--accent-solid)" strokeWidth="8" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
        transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      <text x="50%" y="47%" textAnchor="middle" fontFamily="var(--font-display)"
        fontSize="21" fontWeight="600" fill="var(--text)">{week}</text>
      <text x="50%" y="64%" textAnchor="middle" fontSize="9" fontWeight="700"
        fill="var(--text-muted)">WEEKS</text>
    </svg>
  );
}

/* Data tables can't collapse meaningfully — scroll them instead. */
export const TableScroll = ({ children }) => (
  <div className="table-scroll">{children}</div>
);

export const fmtDate = (iso) => iso
  ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  : '';
