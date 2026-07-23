import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { errorMessage } from '../api';
import { Card, Loading, Empty, ErrorNote, fmtDate } from '../components/Bits';

export default function Community() {
  const [groups, setGroups] = useState([]);
  const [posts, setPosts] = useState([]);
  const [filter, setFilter] = useState({ group: '', kind: '' });
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ title: '', body: '', kind: 'discussion', group_id: '' });
  const [error, setError] = useState('');
  const [composing, setComposing] = useState(false);

  useEffect(() => {
    api.get('/community/groups').then(({ data }) => setGroups(data.groups)).catch(() => {});
  }, []);

  const load = () => {
    setLoading(true);
    const qs = new URLSearchParams();
    if (filter.group) qs.set('group', filter.group);
    if (filter.kind) qs.set('kind', filter.kind);
    api.get(`/community/posts?${qs}`)
      .then(({ data }) => setPosts(data.posts))
      .finally(() => setLoading(false));
  };
  useEffect(load, [filter]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/community/posts', form);
      setForm({ title: '', body: '', kind: 'discussion', group_id: '' });
      setComposing(false);
      load();
    } catch (err) { setError(errorMessage(err)); }
  };

  const like = async (p) => {
    const { data } = await api.post('/community/likes',
      { entity_type: 'post', entity_id: p.id });
    setPosts(posts.map((x) => x.id === p.id
      ? { ...x, liked: data.liked, like_count: data.like_count } : x));
  };

  return (
    <main className="page">
      <div className="page-head row-between">
        <div>
          <p className="eyebrow">Community</p>
          <h1>Parenting talk</h1>
        </div>
        <button className="btn btn-primary" onClick={() => setComposing(!composing)}>
          {composing ? 'Cancel' : 'New post'}
        </button>
      </div>

      {composing && (
        <Card style={{ marginBottom: 20 }}>
          <ErrorNote>{error}</ErrorNote>
          <form onSubmit={submit}>
            <div className="grid grid-2">
              <div className="field">
                <label htmlFor="g">Group</label>
                <select id="g" value={form.group_id}
                  onChange={(e) => setForm({ ...form, group_id: e.target.value })}>
                  <option value="">No group</option>
                  {groups.map((g) => <option key={g.id} value={g.id}>{g.emoji} {g.name}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="k">Type</label>
                <select id="k" value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                  <option value="discussion">Discussion</option>
                  <option value="question">Question</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label htmlFor="pt">Title</label>
              <input id="pt" value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="pb">What's on your mind?</label>
              <textarea id="pb" value={form.body} required
                onChange={(e) => setForm({ ...form, body: e.target.value })} />
            </div>
            <button className="btn btn-primary">Post</button>
          </form>
        </Card>
      )}

      <div className="row" style={{ marginBottom: 18, flexWrap: 'wrap' }}>
        <button className={`btn ${!filter.group && !filter.kind ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setFilter({ group: '', kind: '' })}>All</button>
        <button className={`btn ${filter.kind === 'question' ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setFilter({ group: '', kind: 'question' })}>Questions</button>
        {groups.map((g) => (
          <button key={g.id}
            className={`btn ${filter.group === g.id ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setFilter({ group: g.id, kind: '' })}>{g.emoji} {g.name}</button>
        ))}
      </div>

      <div className="stack">
        {loading ? <Loading /> : posts.length === 0 ? (
          <Empty title="Nothing here yet" body="Be the first to start a conversation." />
        ) : posts.map((p) => (
          <Card key={p.id} className="post">
            <div className="post-meta">
              <div className="avatar">{(p.author?.display_name || '?').charAt(0)}</div>
              <span>{p.author?.display_name}</span>
              <span>·</span>
              <span>{fmtDate(p.created_at)}</span>
              {p.group && <span className="chip chip-sage">{p.group.name}</span>}
              {p.kind === 'question' && <span className="chip">Question</span>}
            </div>
            <h3 style={{ marginTop: 10 }}>
              <Link to={`/app/community/${p.id}`}
                style={{ color: 'var(--text)', textDecoration: 'none' }}>
                {p.title || 'Untitled'}
              </Link>
            </h3>
            <p className="muted">{p.body.slice(0, 200)}{p.body.length > 200 ? '…' : ''}</p>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="btn btn-ghost" style={{ padding: '6px 14px', fontSize: 13 }}
                onClick={() => like(p)}>{p.liked ? '♥' : '♡'} {p.like_count}</button>
              <Link className="btn btn-ghost" style={{ padding: '6px 14px', fontSize: 13 }}
                to={`/app/community/${p.id}`}>💬 {p.reply_count}</Link>
            </div>
          </Card>
        ))}
      </div>
    </main>
  );
}
