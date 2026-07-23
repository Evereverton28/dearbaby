import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../../api';
import { Card, Loading } from '../../components/Bits';

export default function Overview() {
  const [data, setData] = useState(null);
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    api.get('/admin/overview').then(({ data }) => setData(data)).catch(() => {});
    api.get('/admin/analytics/summary?days=30')
      .then(({ data }) => setAnalytics(data)).catch(() => {});
  }, []);

  if (!data) return <Loading />;

  const devices = Object.entries(analytics?.by_device || {})
    .map(([name, value]) => ({ name, value }));

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">Last 30 days</p>
        <h1>Overview</h1>
      </div>

      <div className="grid grid-4">
        <div className="card stat"><b>{data.users.total}</b><small>Users</small></div>
        <div className="card stat"><b>{data.content.children}</b><small>Children</small></div>
        <div className="card stat"><b>{data.content.milestones}</b><small>Milestones</small></div>
        <div className="card stat"><b>{data.moderation.open_reports}</b><small>Open reports</small></div>
      </div>

      <div className="grid grid-3" style={{ marginTop: 16 }}>
        <div className="card stat"><b>{data.subscriptions.trialing}</b><small>Trialing</small></div>
        <div className="card stat"><b>{data.subscriptions.active}</b><small>Active subs</small></div>
        <div className="card stat">
          <b>KSh {(data.revenue_cents / 100).toLocaleString()}</b><small>Revenue</small>
        </div>
      </div>

      {analytics && (
        <>
          <div className="grid grid-2" style={{ marginTop: 22 }}>
            <Card>
              <h2 style={{ fontSize: 17, marginBottom: 4 }}>Signup funnel</h2>
              <p className="muted" style={{ marginBottom: 14 }}>
                {analytics.unique_visitors} unique visitors
              </p>
              {analytics.funnel.map((f, i) => {
                const top = analytics.funnel[0].count || 1;
                const pct = Math.round((f.count / top) * 100);
                return (
                  <div key={f.step} style={{ marginBottom: 12 }}>
                    <div className="row-between" style={{ marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>
                        {f.step.replace(/_/g, ' ')}
                      </span>
                      <span className="muted" style={{ fontSize: 13 }}>{f.count} · {pct}%</span>
                    </div>
                    <div style={{ height: 8, borderRadius: 100,
                                  background: 'var(--surface-sunken)' }}>
                      <div style={{ width: `${pct}%`, height: '100%', borderRadius: 100,
                                    background: 'var(--accent-solid)' }} />
                    </div>
                  </div>
                );
              })}
            </Card>

            <Card>
              <h2 style={{ fontSize: 17, marginBottom: 14 }}>Devices</h2>
              <div style={{ height: 190 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={devices}>
                    <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                    <YAxis stroke="var(--text-muted)" fontSize={12} />
                    <Tooltip contentStyle={{ background: 'var(--surface)',
                      border: '1px solid var(--border)', borderRadius: 12,
                      color: 'var(--text)' }} />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                      {devices.map((_, i) => (
                        <Cell key={i} fill={i % 2 ? 'var(--secondary-solid)' : 'var(--accent-solid)'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card style={{ marginTop: 16 }}>
            <h2 style={{ fontSize: 17, marginBottom: 12 }}>Top pages</h2>
            {analytics.top_paths.map((p) => (
              <div key={p.path} className="row-between" style={{ padding: '7px 0' }}>
                <span className="muted">{p.path}</span>
                <b>{p.views}</b>
              </div>
            ))}
          </Card>
        </>
      )}
    </main>
  );
}
