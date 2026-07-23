import { useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { useChild } from '../child';
import { Card, Loading, Empty, ErrorNote, fmtDate } from '../components/Bits';
import { track } from '../analytics';

const MOODS = ['calm', 'excited', 'tired', 'grateful', 'overwhelmed', 'overjoyed'];

export default function Journal() {
  const { active } = useChild();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ title: '', body: '', mood: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = () => {
    if (!active) { setLoading(false); return; }
    setLoading(true);
    api.get(`/pregnancy/children/${active.id}/journal`)
      .then(({ data }) => setEntries(data.entries))
      .finally(() => setLoading(false));
  };
  useEffect(load, [active]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.body.trim()) { setError('Write something first.'); return; }
    setBusy(true); setError('');
    try {
      await api.post(`/pregnancy/children/${active.id}/journal`, form);
      track('first_memory_added');
      setForm({ title: '', body: '', mood: '' });
      load();
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const remove = async (id) => {
    await api.delete(`/pregnancy/journal/${id}`);
    setEntries(entries.filter((e) => e.id !== id));
  };

  if (!active) return <Empty title="Nothing to journal about yet"
    body="Add a pregnancy or a baby first." action="Get started" to="/app/setup" />;

  return (
    <main className="page page-narrow">
      <div className="page-head">
        <p className="eyebrow">Pregnancy</p>
        <h1>Journal</h1>
        <p>Write it down now — you won't remember the details later.</p>
      </div>

      <Card>
        <ErrorNote>{error}</ErrorNote>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="t">Title (optional)</label>
            <input id="t" value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="b">How are you doing?</label>
            <textarea id="b" value={form.body}
              onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="m">Mood</label>
            <select id="m" value={form.mood}
              onChange={(e) => setForm({ ...form, mood: e.target.value })}>
              <option value="">Not saying</option>
              {MOODS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save entry'}
          </button>
        </form>
      </Card>

      <div className="stack" style={{ marginTop: 22 }}>
        {loading ? <Loading /> : entries.length === 0 ? (
          <Empty title="No entries yet" body="Your first one is above." />
        ) : entries.map((e) => (
          <Card key={e.id}>
            <div className="row-between">
              <div>
                <time className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
                  {fmtDate(e.entry_date)}{e.week ? ` · week ${e.week}` : ''}
                </time>
                {e.title && <h3 style={{ fontSize: 18, margin: '4px 0' }}>{e.title}</h3>}
              </div>
              {e.mood && <span className="chip chip-sage">{e.mood}</span>}
            </div>
            <p style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{e.body}</p>
            <button className="btn btn-ghost" style={{ marginTop: 12, padding: '6px 14px', fontSize: 13 }}
              onClick={() => remove(e.id)}>Delete</button>
          </Card>
        ))}
      </div>
    </main>
  );
}
