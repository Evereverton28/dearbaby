import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../auth';
import { useChild } from '../child';
import { Card, Loading, Empty, WeekRing, fmtDate } from '../components/Bits';

export default function Dashboard() {
  const { user } = useAuth();
  const { active, list, loading, setActiveId, error } = useChild();
  const [week, setWeek] = useState(null);
  const [summary, setSummary] = useState(null);
  const [appts, setAppts] = useState([]);

  useEffect(() => {
    if (!active) return;
    api.get(`/children/${active.id}/summary`).then(({ data }) => setSummary(data)).catch(() => {});
    api.get(`/pregnancy/children/${active.id}/appointments`)
      .then(({ data }) => setAppts(data.appointments.slice(0, 2))).catch(() => {});
    if (active.current_week) {
      api.get(`/pregnancy/weeks/${active.current_week}`)
        .then(({ data }) => setWeek(data)).catch(() => setWeek(null));
    } else setWeek(null);
  }, [active]);

  if (loading) return <Loading />;

  if (error) return (
    <main className="page">
      <div className="empty">
        <h3>Can't reach the server</h3>
        <p>{error}</p>
        <p style={{ marginTop: 12 }}>
          Start the backend first:
        </p>
        <pre style={{
          textAlign: 'left', maxWidth: 420, margin: '12px auto', padding: 16,
          background: 'var(--surface-sunken)', borderRadius: 'var(--radius-sm)',
          fontSize: 13, lineHeight: 1.8, overflow: 'auto',
        }}>
{`cd web/backend
python seed.py
python wsgi.py`}
        </pre>
        <p className="muted" style={{ marginTop: 8 }}>Then refresh this page.</p>
      </div>
    </main>
  );

  if (!list.length) return <Navigate to="/app/setup" replace />;

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">{new Date().toLocaleDateString(undefined,
          { weekday: 'long', day: 'numeric', month: 'long' })}</p>
        <h1>{greeting}, {user?.display_name?.split(' ')[0]}</h1>
      </div>

      {list.length > 1 && (
        <div className="row" style={{ marginBottom: 16, flexWrap: 'wrap' }}>
          {list.map((c) => (
            <button key={c.id} onClick={() => setActiveId(c.id)}
              className={`btn ${c.id === active?.id ? 'btn-primary' : 'btn-ghost'}`}>
              {c.name || 'Baby'}
            </button>
          ))}
        </div>
      )}

      {active?.stage === 'pregnancy' && week && (
        <Card className="weekcard">
          <WeekRing week={active.current_week} />
          <div className="meta">
            <span className="chip">Trimester {week.trimester}</span>
            <b>Hello, {week.size_label}!</b>
            <p className="muted">{week.summary}</p>
          </div>
        </Card>
      )}

      {active?.stage === 'baby' && (
        <Card className="weekcard">
          <div className="meta">
            <span className="chip-sage chip">
              {Math.floor(active.age_days / 30)} months old
            </span>
            <b>{active.name || 'Baby'}</b>
            <p className="muted">Born {fmtDate(active.birth_date)}</p>
          </div>
        </Card>
      )}

      <div className="grid grid-4" style={{ marginTop: 16 }}>
        {[['/app/pregnancy/journal', '📝', 'Journal'],
          ['/app/gallery', '📸', 'Photos'],
          ['/app/memories', '✨', 'Milestones'],
          ['/app/pregnancy/tools', '👣', 'Tools']].map(([to, icon, label]) => (
          <Link key={to} to={to} className="card center" style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 24 }}>{icon}</div>
            <small className="muted" style={{ fontWeight: 700 }}>{label}</small>
          </Link>
        ))}
      </div>

      {summary && (
        <div className="grid grid-3" style={{ marginTop: 16 }}>
          <div className="card stat"><b>{summary.counts.milestones}</b><small>Milestones</small></div>
          <div className="card stat"><b>{summary.counts.journal}</b><small>Journal entries</small></div>
          <div className="card stat"><b>{summary.counts.media}</b><small>Photos & videos</small></div>
        </div>
      )}

      {appts.length > 0 && (
        <>
          <h2 style={{ fontSize: 18, margin: '26px 0 10px' }}>Coming up</h2>
          <div className="stack">
            {appts.map((a) => (
              <Card key={a.id} className="row-between">
                <div>
                  <b>{a.title}</b>
                  <p className="muted">{a.location}</p>
                </div>
                <span className="chip">{fmtDate(a.starts_at)}</span>
              </Card>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
