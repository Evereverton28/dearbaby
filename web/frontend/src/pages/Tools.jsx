import { useEffect, useRef, useState } from 'react';
import api from '../api';
import { useChild } from '../child';
import { Card, Empty } from '../components/Bits';

const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

function KickCounter({ childId, onSaved }) {
  const [count, setCount] = useState(0);
  const [startedAt, setStartedAt] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef(null);

  useEffect(() => {
    if (!startedAt) return undefined;
    timer.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => clearInterval(timer.current);
  }, [startedAt]);

  const kick = () => {
    if (!startedAt) setStartedAt(Date.now());
    setCount((c) => c + 1);
  };
  const finish = async () => {
    clearInterval(timer.current);
    await api.post(`/pregnancy/children/${childId}/kicks`, {
      kick_count: count,
      started_at: new Date(startedAt).toISOString(),
      ended_at: new Date().toISOString(),
    });
    setCount(0); setStartedAt(null); setElapsed(0);
    onSaved();
  };

  return (
    <Card className="center">
      <h3 style={{ fontSize: 18 }}>Kick counter</h3>
      <p className="muted">Ten movements is the usual thing to look for.</p>
      <p style={{ fontFamily: 'var(--font-display)', fontSize: 52, margin: '14px 0 4px' }}>{count}</p>
      <p className="muted">{mmss(elapsed)}</p>
      <div className="row" style={{ justifyContent: 'center', marginTop: 16 }}>
        <button className="btn btn-primary" onClick={kick}>Kick</button>
        {startedAt && <button className="btn btn-ghost" onClick={finish}>Save session</button>}
      </div>
    </Card>
  );
}

function ContractionTimer({ childId, onSaved }) {
  const [running, setRunning] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef(null);

  useEffect(() => {
    if (!running) return undefined;
    timer.current = setInterval(() => setElapsed(Math.floor((Date.now() - running) / 1000)), 1000);
    return () => clearInterval(timer.current);
  }, [running]);

  const start = () => { setRunning(Date.now()); setElapsed(0); };
  const stop = async () => {
    const started = running;
    clearInterval(timer.current);
    setRunning(null);
    await api.post(`/pregnancy/children/${childId}/contractions`, {
      started_at: new Date(started).toISOString(),
      ended_at: new Date().toISOString(),
    });
    onSaved();
  };

  return (
    <Card className="center">
      <h3 style={{ fontSize: 18 }}>Contraction timer</h3>
      <p className="muted">Time each one; intervals are worked out for you.</p>
      <p style={{ fontFamily: 'var(--font-display)', fontSize: 44, margin: '14px 0' }}>{mmss(elapsed)}</p>
      {running
        ? <button className="btn btn-danger" onClick={stop}>Stop</button>
        : <button className="btn btn-primary" onClick={start}>Start</button>}
    </Card>
  );
}

export default function Tools() {
  const { active } = useChild();
  const [kicks, setKicks] = useState([]);
  const [contractions, setContractions] = useState([]);

  const load = () => {
    if (!active) return;
    api.get(`/pregnancy/children/${active.id}/kicks`)
      .then(({ data }) => setKicks(data.sessions)).catch(() => {});
    api.get(`/pregnancy/children/${active.id}/contractions`)
      .then(({ data }) => setContractions(data.contractions)).catch(() => {});
  };
  useEffect(load, [active]);

  if (!active) return <Empty title="Nothing to track yet" body="Add a pregnancy first."
    action="Get started" to="/app/setup" />;

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">Pregnancy</p>
        <h1>Tools</h1>
      </div>
      <div className="grid grid-2">
        <KickCounter childId={active.id} onSaved={load} />
        <ContractionTimer childId={active.id} onSaved={load} />
      </div>

      <div className="grid grid-2" style={{ marginTop: 18 }}>
        <Card>
          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Recent kick sessions</h3>
          {kicks.length === 0 ? <p className="muted">Nothing recorded yet.</p> : kicks.slice(0, 6).map((s) => (
            <div key={s.id} className="row-between" style={{ padding: '7px 0' }}>
              <span className="muted">{new Date(s.started_at).toLocaleString()}</span>
              <b>{s.kick_count} kicks</b>
            </div>
          ))}
        </Card>
        <Card>
          <h3 style={{ fontSize: 16, marginBottom: 10 }}>Recent contractions</h3>
          {contractions.length === 0 ? <p className="muted">Nothing recorded yet.</p> :
            contractions.slice(0, 6).map((c) => (
            <div key={c.id} className="row-between" style={{ padding: '7px 0' }}>
              <span className="muted">{new Date(c.started_at).toLocaleTimeString()}</span>
              <b>{c.duration_s ? `${c.duration_s}s` : '—'}
                {c.interval_s ? ` · every ${Math.round(c.interval_s / 60)}m` : ''}</b>
            </div>
          ))}
        </Card>
      </div>
    </main>
  );
}
