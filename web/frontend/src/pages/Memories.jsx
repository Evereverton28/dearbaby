import { useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useChild } from '../child';
import { Card, Loading, Empty, ErrorNote, fmtDate } from '../components/Bits';

export default function Memories() {
  const { active } = useChild();
  const [tab, setTab] = useState('timeline');
  const [timeline, setTimeline] = useState([]);
  const [milestones, setMilestones] = useState([]);
  const [types, setTypes] = useState([]);
  const [growth, setGrowth] = useState([]);
  const [teeth, setTeeth] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ type_id: '', title: '', note: '', occurred_on: '' });

  const load = () => {
    if (!active) { setLoading(false); return; }
    setLoading(true);
    Promise.all([
      api.get(`/memories/children/${active.id}/timeline`),
      api.get(`/memories/children/${active.id}/milestones`),
      api.get(`/memories/milestone-types?stage=${active.stage}`),
      api.get(`/memories/children/${active.id}/growth`),
      api.get(`/memories/children/${active.id}/teeth`),
    ]).then(([t, m, ty, g, th]) => {
      setTimeline(t.data.timeline); setMilestones(m.data.milestones);
      setTypes(ty.data.types); setGrowth(g.data.measurements); setTeeth(th.data.teeth);
    }).finally(() => setLoading(false));
  };
  useEffect(load, [active]);

  const addMilestone = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.post(`/memories/children/${active.id}/milestones`, form);
      setForm({ type_id: '', title: '', note: '', occurred_on: '' });
      load();
    } catch (err) { setError(errorMessage(err)); }
  };

  const addGrowth = async (kind, value) => {
    if (!value) return;
    await api.post(`/memories/children/${active.id}/growth`, { kind, value: Number(value) });
    load();
  };

  const toggleTooth = async (code, has) => {
    await api.post(`/memories/children/${active.id}/teeth`, {
      tooth_code: code,
      erupted_on: has ? null : new Date().toISOString().slice(0, 10),
    });
    load();
  };

  if (!active) return <Empty title="No memory book yet" body="Add a baby or pregnancy to begin."
    action="Get started" to="/app/setup" />;
  if (loading) return <Loading />;

  const TABS = [['timeline', 'Timeline'], ['milestones', 'Milestones'],
                ['growth', 'Growth'], ['teeth', 'Teeth']];

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">{active.name || 'Baby'}'s memory book</p>
        <h1>Memories</h1>
      </div>

      <div className="row" style={{ marginBottom: 18, flexWrap: 'wrap' }}>
        {TABS.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`btn ${tab === k ? 'btn-primary' : 'btn-ghost'}`}>{label}</button>
        ))}
      </div>

      {tab === 'timeline' && (
        timeline.length === 0
          ? <Empty title="Nothing recorded yet" body="Add a milestone to start the timeline." />
          : <div className="timeline">
              {timeline.map((e) => (
                <div className="tl-item" key={`${e.type}-${e.id}`}>
                  <time>{fmtDate(e.date)}</time>
                  <h4>{e.emoji} {e.title}</h4>
                  {e.note && <p className="muted">{e.note}</p>}
                </div>
              ))}
            </div>
      )}

      {tab === 'milestones' && (
        <>
          <Card style={{ marginBottom: 18 }}>
            <ErrorNote>{error}</ErrorNote>
            <form onSubmit={addMilestone}>
              <div className="grid grid-2">
                <div className="field">
                  <label htmlFor="ty">Milestone</label>
                  <select id="ty" value={form.type_id}
                    onChange={(e) => setForm({ ...form, type_id: e.target.value, title: '' })}>
                    <option value="">Custom…</option>
                    {types.map((t) => <option key={t.id} value={t.id}>{t.emoji} {t.label}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="on">When</label>
                  <input id="on" type="date" value={form.occurred_on}
                    onChange={(e) => setForm({ ...form, occurred_on: e.target.value })} />
                </div>
              </div>
              {!form.type_id && (
                <div className="field">
                  <label htmlFor="ti">What happened?</label>
                  <input id="ti" value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </div>
              )}
              <div className="field">
                <label htmlFor="no">Note (optional)</label>
                <textarea id="no" value={form.note} style={{ minHeight: 70 }}
                  onChange={(e) => setForm({ ...form, note: e.target.value })} />
              </div>
              <button className="btn btn-primary">Add milestone</button>
            </form>
          </Card>
          <div className="grid grid-2">
            {milestones.map((m) => (
              <Card key={m.id}>
                <div style={{ fontSize: 26 }}>{m.emoji}</div>
                <h3 style={{ fontSize: 17, margin: '4px 0' }}>{m.title}</h3>
                <time className="muted" style={{ fontSize: 12 }}>{fmtDate(m.occurred_on)}</time>
                {m.note && <p className="muted" style={{ marginTop: 8 }}>{m.note}</p>}
              </Card>
            ))}
          </div>
        </>
      )}

      {tab === 'growth' && (
        <div className="grid grid-2">
          {['weight', 'height'].map((kind) => {
            const points = growth.filter((g) => g.kind === kind);
            const unit = kind === 'weight' ? 'kg' : 'cm';
            return (
              <Card key={kind}>
                <h3 style={{ fontSize: 17, marginBottom: 4, textTransform: 'capitalize' }}>{kind}</h3>
                <p className="muted" style={{ marginBottom: 12 }}>
                  {points.length ? `Latest: ${points[points.length - 1].value}${unit}` : 'Nothing recorded'}
                </p>
                <form onSubmit={(e) => {
                  e.preventDefault();
                  addGrowth(kind, e.target.elements[`v_${kind}`].value);
                  e.target.reset();
                }}>
                  <div className="row">
                    <input name={`v_${kind}`} type="number" step="0.01"
                      placeholder={`New ${kind} (${unit})`} />
                    <button className="btn btn-primary">Add</button>
                  </div>
                </form>
                <div style={{ marginTop: 14 }}>
                  {points.slice(-6).reverse().map((p) => (
                    <div key={p.id} className="row-between" style={{ padding: '6px 0' }}>
                      <span className="muted">{fmtDate(p.measured_on)}</span>
                      <b>{p.value}{unit}</b>
                    </div>
                  ))}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {tab === 'teeth' && (
        <Card>
          <h3 style={{ fontSize: 17, marginBottom: 4 }}>Teeth tracker</h3>
          <p className="muted" style={{ marginBottom: 14 }}>
            Tap a tooth as it comes through. {teeth.filter((t) => t.erupted_on).length} of 20 so far.
          </p>
          <div className="grid grid-4">
            {teeth.map((t) => (
              <button key={t.tooth_code}
                onClick={() => toggleTooth(t.tooth_code, !!t.erupted_on)}
                className={`btn ${t.erupted_on ? 'btn-secondary' : 'btn-ghost'}`}
                style={{ fontSize: 11, padding: '10px 6px' }}>
                {t.tooth_code.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </Card>
      )}
    </main>
  );
}
