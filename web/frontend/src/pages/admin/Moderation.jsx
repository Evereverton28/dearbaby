import { useEffect, useState } from 'react';
import api, { errorMessage } from '../../api';
import { Card, Loading, Empty, ErrorNote, fmtDate } from '../../components/Bits';

export default function Moderation() {
  const [reports, setReports] = useState([]);
  const [log, setLog] = useState([]);
  const [status, setStatus] = useState('open');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get(`/admin/reports?status=${status}`),
      api.get('/admin/moderation/log'),
    ]).then(([r, l]) => { setReports(r.data.reports); setLog(l.data.actions); })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  };
  useEffect(load, [status]);

  const act = async (report, action) => {
    setError('');
    try {
      await api.post(`/admin/reports/${report.id}/action`, { action });
      load();
    } catch (err) { setError(errorMessage(err)); }
  };

  if (loading) return <Loading />;

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">Community</p>
        <h1>Moderation</h1>
      </div>

      <ErrorNote>{error}</ErrorNote>

      <div className="row" style={{ marginBottom: 18 }}>
        {['open', 'actioned', 'dismissed'].map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            className={`btn ${status === s ? 'btn-primary' : 'btn-ghost'}`}
            style={{ textTransform: 'capitalize' }}>{s}</button>
        ))}
      </div>

      <div className="stack">
        {reports.length === 0 ? (
          <Empty title={`Nothing ${status}`} body="The queue is clear." />
        ) : reports.map((r) => (
          <Card key={r.id}>
            <div className="row-between">
              <span className="chip">{r.entity_type}</span>
              <time className="muted" style={{ fontSize: 12 }}>{fmtDate(r.created_at)}</time>
            </div>
            <p style={{ marginTop: 10 }}><b>Reason:</b> {r.reason || 'Not given'}</p>
            {r.snippet && (
              <p className="muted" style={{ marginTop: 8, padding: 12,
                background: 'var(--surface-sunken)', borderRadius: 12 }}>
                {r.snippet}
              </p>
            )}
            <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
              Reported by {r.reporter?.display_name || 'unknown'}
            </p>
            {status === 'open' && (
              <div className="row" style={{ marginTop: 14, flexWrap: 'wrap' }}>
                <button className="btn btn-ghost" onClick={() => act(r, 'hide')}>Hide</button>
                <button className="btn btn-danger" onClick={() => act(r, 'remove')}>Remove</button>
                <button className="btn btn-secondary" onClick={() => act(r, 'dismiss')}>Dismiss</button>
              </div>
            )}
          </Card>
        ))}
      </div>

      <h2 style={{ fontSize: 17, margin: '30px 0 12px' }}>Recent actions</h2>
      <Card>
        {log.length === 0 ? <p className="muted">No actions yet.</p> : log.slice(0, 12).map((a) => (
          <div key={a.id} className="row-between" style={{ padding: '8px 0' }}>
            <span>
              <b style={{ textTransform: 'capitalize' }}>{a.action}</b>{' '}
              <span className="muted">{a.entity_type}</span>
            </span>
            <span className="muted" style={{ fontSize: 12 }}>
              {a.moderator?.display_name} · {fmtDate(a.created_at)}
            </span>
          </div>
        ))}
      </Card>
    </main>
  );
}
