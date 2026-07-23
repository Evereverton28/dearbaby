import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api, { errorMessage } from '../api';
import { Card, Loading, ErrorNote, fmtDate } from '../components/Bits';

export default function PostDetail() {
  const { id } = useParams();
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.get(`/community/posts/${id}`)
      .then(({ data }) => { setPost(data.post); setComments(data.comments); })
      .catch((err) => setError(errorMessage(err, 'This post is not available.')))
      .finally(() => setLoading(false));
  };
  useEffect(load, [id]);

  const reply = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    try {
      await api.post(`/community/posts/${id}/comments`, { body });
      setBody(''); load();
    } catch (err) { setError(errorMessage(err)); }
  };

  const report = async () => {
    const reason = window.prompt('What\'s wrong with this post?');
    if (!reason) return;
    await api.post('/community/reports',
      { entity_type: 'post', entity_id: id, reason });
    window.alert('Thanks — a moderator will take a look.');
  };

  if (loading) return <Loading />;
  if (!post) return <main className="page page-narrow"><ErrorNote>{error}</ErrorNote></main>;

  return (
    <main className="page page-narrow">
      <Link to="/app/community" className="muted"
        style={{ textDecoration: 'none' }}>← Back to community</Link>

      <Card style={{ marginTop: 14 }}>
        <div className="post-meta">
          <div className="avatar">{(post.author?.display_name || '?').charAt(0)}</div>
          <span>{post.author?.display_name}</span>
          <span>·</span>
          <span>{fmtDate(post.created_at)}</span>
        </div>
        <h1 style={{ fontSize: 24, margin: '12px 0 8px' }}>{post.title || 'Untitled'}</h1>
        <p style={{ whiteSpace: 'pre-wrap' }}>{post.body}</p>
        <div className="row" style={{ marginTop: 14 }}>
          <span className="chip">♥ {post.like_count}</span>
          <button className="btn btn-ghost" style={{ padding: '6px 14px', fontSize: 13 }}
            onClick={report}>Report</button>
        </div>
      </Card>

      <h2 style={{ fontSize: 17, margin: '24px 0 12px' }}>
        {comments.length} {comments.length === 1 ? 'reply' : 'replies'}
      </h2>

      <div className="stack">
        {comments.map((c) => (
          <Card key={c.id}>
            <div className="post-meta">
              <div className="avatar">{(c.author?.display_name || '?').charAt(0)}</div>
              <span>{c.author?.display_name}</span>
              <span>·</span><span>{fmtDate(c.created_at)}</span>
            </div>
            <p style={{ marginTop: 8 }}>{c.body}</p>
          </Card>
        ))}
      </div>

      <Card style={{ marginTop: 18 }}>
        <ErrorNote>{error}</ErrorNote>
        <form onSubmit={reply}>
          <div className="field">
            <label htmlFor="r">Your reply</label>
            <textarea id="r" value={body} style={{ minHeight: 80 }}
              onChange={(e) => setBody(e.target.value)} />
          </div>
          <button className="btn btn-primary">Reply</button>
        </form>
      </Card>
    </main>
  );
}
