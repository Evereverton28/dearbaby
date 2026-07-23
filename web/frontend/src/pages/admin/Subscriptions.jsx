import { useEffect, useState } from 'react';
import api, { errorMessage } from '../../api';
import { Card, Loading, ErrorNote, TableScroll, fmtDate } from '../../components/Bits';

export default function Subscriptions() {
  const [subs, setSubs] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/subscriptions/list')
      .then(({ data }) => setSubs(data.subscriptions))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">Billing</p>
        <h1>Subscriptions</h1>
      </div>
      <ErrorNote>{error}</ErrorNote>
      <Card>
        <TableScroll>
          <table>
            <thead>
              <tr><th>User</th><th>Plan</th><th>Status</th><th>Provider</th>
                  <th>Renews</th></tr>
            </thead>
            <tbody>
              {subs.map((s) => (
                <tr key={s.id}>
                  <td>{s.user?.display_name || '—'}</td>
                  <td style={{ textTransform: 'capitalize' }}>{s.plan}</td>
                  <td><span className="chip">{s.status}</span></td>
                  <td className="muted">{s.provider}</td>
                  <td className="muted">
                    {fmtDate(s.current_period_end || s.trial_ends_at) || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
      </Card>
    </main>
  );
}
