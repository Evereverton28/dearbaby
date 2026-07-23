import { useEffect, useState } from 'react';
import api, { errorMessage } from '../../api';
import { useAuth } from '../../auth';
import { Card, Loading, ErrorNote, TableScroll, fmtDate } from '../../components/Bits';

function UserDetail({ userId, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  const load = () => api.get(`/admin/users/${userId}`)
    .then(({ data }) => setData(data))
    .catch((err) => setError(errorMessage(err)));
  useEffect(() => { load(); }, [userId]);

  const act = async (action) => {
    setError('');
    try {
      await api.post(`/admin/users/${userId}/${action}`);
      await load(); onChanged();
    } catch (err) { setError(errorMessage(err)); }
  };

  if (error) return <Card><ErrorNote>{error}</ErrorNote></Card>;
  if (!data) return <Card><Loading /></Card>;

  const { user, activity, subscriptions, payments, posts, moderation } = data;
  const sub = subscriptions[0];

  return (
    <Card style={{ marginBottom: 20, borderColor: 'var(--accent-solid)' }}>
      <div className="row-between" style={{ marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20 }}>{user.display_name}</h2>
          <p className="muted">{user.email}</p>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close">✕</button>
      </div>

      <div className="row" style={{ flexWrap: 'wrap', marginBottom: 18 }}>
        <span className="chip">{user.role}</span>
        {user.is_active
          ? <span className="chip chip-sage">Active</span>
          : <span className="chip">Deactivated</span>}
        <span className="muted" style={{ fontSize: 12 }}>Joined {fmtDate(user.created_at)}</span>
      </div>

      <h3 style={{ fontSize: 15, marginBottom: 10 }}>Activity</h3>
      <div className="grid grid-3" style={{ marginBottom: 8 }}>
        <div className="card stat"><b>{activity.children}</b><small>Children</small></div>
        <div className="card stat"><b>{activity.milestones}</b><small>Milestones</small></div>
        <div className="card stat"><b>{activity.journal_entries}</b><small>Journal entries</small></div>
        <div className="card stat"><b>{activity.media_items}</b><small>Photos & videos</small></div>
        <div className="card stat"><b>{activity.albums}</b><small>Albums</small></div>
        <div className="card stat"><b>{activity.community_posts}</b><small>Community posts</small></div>
      </div>
      <p className="muted" style={{ fontSize: 12, marginBottom: 20 }}>
        {data.privacy_note}
      </p>

      <h3 style={{ fontSize: 15, marginBottom: 10 }}>Billing</h3>
      {sub ? (
        <div className="row-between" style={{ padding: '6px 0', marginBottom: 6 }}>
          <span style={{ textTransform: 'capitalize' }}>{sub.plan} · {sub.status}</span>
          <span className="muted" style={{ fontSize: 12 }}>
            {fmtDate(sub.current_period_end || sub.trial_ends_at) || '—'}
          </span>
        </div>
      ) : <p className="muted" style={{ marginBottom: 6 }}>Free plan.</p>}
      {payments.slice(0, 4).map((p) => (
        <div key={p.id} className="row-between" style={{ padding: '5px 0', fontSize: 13 }}>
          <span className="muted">{p.provider} · {p.status}</span>
          <span>{p.currency} {(p.amount_cents / 100).toLocaleString()}</span>
        </div>
      ))}

      {posts.length > 0 && (
        <>
          <h3 style={{ fontSize: 15, margin: '20px 0 10px' }}>
            Community posts <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>
              (public)</span>
          </h3>
          {posts.slice(0, 6).map((p) => (
            <div key={p.id} className="row-between" style={{ padding: '5px 0', fontSize: 13 }}>
              <span>{p.title || 'Untitled'}</span>
              <span className="muted" style={{ fontSize: 12 }}>{p.status}</span>
            </div>
          ))}
        </>
      )}

      {moderation.reports_against > 0 && (
        <p className="muted" style={{ marginTop: 16, fontSize: 13 }}>
          {moderation.reports_against} report(s) filed against this account.
        </p>
      )}

      <ErrorNote>{error}</ErrorNote>
      {data.manageable ? (
        <div className="row" style={{ marginTop: 20, flexWrap: 'wrap' }}>
          <button className={`btn ${user.is_active ? 'btn-danger' : 'btn-secondary'}`}
            onClick={() => act(user.is_active ? 'deactivate' : 'reactivate')}>
            {user.is_active ? 'Deactivate account' : 'Reactivate account'}
          </button>
        </div>
      ) : (
        <p className="muted" style={{ marginTop: 20, fontSize: 13 }}>
          This account is outside your management scope.
        </p>
      )}
    </Card>
  );
}

export default function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [assignable, setAssignable] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.get('/admin/users')
      .then(({ data }) => { setUsers(data.users); setAssignable(data.assignable_roles); })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  if (loading) return <Loading />;

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">Accounts</p>
        <h1>Users</h1>
        <p>You can manage: {assignable.join(', ') || 'no one'}. Click a row for detail.</p>
      </div>

      <ErrorNote>{error}</ErrorNote>

      {selected && (
        <UserDetail userId={selected} onClose={() => setSelected(null)} onChanged={load} />
      )}

      <Card>
        <TableScroll>
          <table>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} onClick={() => setSelected(u.id)}
                  style={{
                    cursor: 'pointer',
                    background: selected === u.id ? 'var(--accent-soft)' : 'transparent',
                  }}>
                  <td>{u.display_name}{u.id === me.id && (
                    <span className="muted" style={{ fontSize: 12 }}> (you)</span>)}</td>
                  <td className="muted">{u.email}</td>
                  <td><span className="chip">{u.role}</span></td>
                  <td>{u.is_active
                    ? <span className="chip chip-sage">Active</span>
                    : <span className="chip">Deactivated</span>}</td>
                  <td className="muted">{fmtDate(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
      </Card>

      <p className="muted" style={{ marginTop: 14, fontSize: 13 }}>
        Deactivating blocks sign-in and ends any live session immediately. Nothing is
        deleted. Administrators can see account and activity data, never the contents
        of a family's journal, photos or scans.
      </p>
    </main>
  );
}
