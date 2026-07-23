import { useEffect, useState } from 'react';
import api, { errorMessage } from '../../api';
import { Card, Loading, ErrorNote, fmtDate } from '../../components/Bits';

export default function Announcements() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ title: '', body: '', audience: 'all', publish: false });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    api.get('/admin/announcements')
      .then(({ data }) => setItems(data.announcements))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/admin/announcements', form);
      setForm({ title: '', body: '', audience: 'all', publish: false });
      load();
    } catch (err) { setError(errorMessage(err)); }
  };

  if (loading) return <Loading />;

  return (
    <main className="page page-narrow">
      <div className="page-head">
        <p className="eyebrow">Comms</p>
        <h1>Announcements</h1>
      </div>
      <ErrorNote>{error}</ErrorNote>

      <Card style={{ marginBottom: 20 }}>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="at">Title</label>
            <input id="at" value={form.title} required
              onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="ab">Message</label>
            <textarea id="ab" value={form.body} required
              onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="aa">Audience</label>
            <select id="aa" value={form.audience}
              onChange={(e) => setForm({ ...form, audience: e.target.value })}>
              <option value="all">Everyone</option>
              <option value="subscribers">Subscribers</option>
              <option value="trialing">People on a trial</option>
            </select>
          </div>
          <label className="row" style={{ marginBottom: 14, cursor: 'pointer' }}>
            <input type="checkbox" checked={form.publish} style={{ width: 18, height: 18 }}
              onChange={(e) => setForm({ ...form, publish: e.target.checked })} />
            <span>Publish immediately</span>
          </label>
          <button className="btn btn-primary">Save announcement</button>
        </form>
      </Card>

      <div className="stack">
        {items.map((a) => (
          <Card key={a.id}>
            <div className="row-between">
              <b>{a.title}</b>
              <span className="chip">{a.published_at ? 'Published' : 'Draft'}</span>
            </div>
            <p className="muted" style={{ marginTop: 8 }}>{a.body}</p>
            <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
              {a.audience} · {fmtDate(a.created_at)}
            </p>
          </Card>
        ))}
      </div>
    </main>
  );
}
