import { useEffect, useState } from 'react';
import api, { errorMessage } from '../api';
import { Card, ErrorNote } from '../components/Bits';
import { track } from '../analytics';

const money = (cents, cur) => cur === 'KES'
  ? `KSh ${(cents / 100).toLocaleString()}`
  : `$${(cents / 100).toFixed(2)}`;

export default function Upgrade() {
  const [plans, setPlans] = useState(null);
  const [plan, setPlan] = useState('annual');
  const [error, setError] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [sub, setSub] = useState(null);

  const loadSub = () =>
    api.get('/billing/subscription').then(({ data }) => setSub(data)).catch(() => {});

  useEffect(() => {
    api.get('/billing/plans').then(({ data }) => setPlans(data)).catch(() => {});
    loadSub();
  }, []);

  const startTrial = async () => {
    setBusy(true); setError(''); setNote('');
    try {
      await api.post('/billing/subscription/trial', { plan });
      setNote('Your 30-day free trial has started.');
      track('subscribed');
      loadSub();
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const payCard = async () => {
    setBusy(true); setError(''); setNote('');
    try {
      const { data } = await api.post('/billing/subscription/checkout',
        { plan, currency: 'KES' });
      setNote(`Checkout ready for ${money(data.amount_cents, data.currency)}. `
        + 'Stripe is scaffolded — wire it in backend/dearbaby/billing/routes.py.');
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const cancel = async () => {
    if (!window.confirm('Cancel at the end of the current period?')) return;
    setError(''); setNote('');
    try {
      await api.post('/billing/subscription/cancel');
      setNote('Cancelled. You keep access until the period ends.');
      loadSub();
    } catch (err) { setError(errorMessage(err)); }
  };

  if (!plans) return null;

  return (
    <main className="page page-narrow">
      <div className="page-head center">
        <p className="eyebrow">DearBaby Premium</p>
        <h1>Keep every memory</h1>
        <p>Free for {plans.trial_days} days. Cancel any time.</p>
      </div>

      <ErrorNote>{error}</ErrorNote>
      {note && <div className="alert alert-info">{note}</div>}

      {sub?.subscription && (
        <Card style={{ marginBottom: 20 }}>
          <div className="row-between">
            <div>
              <b style={{ textTransform: 'capitalize' }}>{sub.subscription.plan} plan</b>
              <p className="muted">
                {sub.subscription.status}
                {sub.subscription.cancel_at_period_end && ' · cancels at period end'}
              </p>
            </div>
            {sub.premium && <span className="chip chip-sage">Active</span>}
          </div>
          {!sub.subscription.cancel_at_period_end && (
            <button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={cancel}>
              Cancel subscription
            </button>
          )}
        </Card>
      )}

      <div className="grid grid-2" style={{ marginBottom: 20 }}>
        {plans.plans.map((p) => (
          <button key={p.key} onClick={() => setPlan(p.key)}
            className="card" style={{
              textAlign: 'left', cursor: 'pointer',
              borderColor: plan === p.key ? 'var(--accent-solid)' : 'var(--border)',
              borderWidth: 2,
            }}>
            <b style={{ fontFamily: 'var(--font-display)', fontSize: 20 }}>{p.label}</b>
            <p style={{ fontSize: 19, margin: '6px 0' }}>{money(p.prices.KES, 'KES')}</p>
            {p.note && <span className="chip chip-sage">{p.note}</span>}
          </button>
        ))}
      </div>

      <Card style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 17, marginBottom: 10 }}>What you get</h2>
        <ul className="muted" style={{ paddingLeft: 18 }}>
          {plans.premium_features.map((f) => <li key={f} style={{ marginBottom: 5 }}>{f}</li>)}
        </ul>
      </Card>

      {!sub?.subscription && (
        <button className="btn btn-primary" style={{ width: '100%', marginBottom: 18 }}
          onClick={startTrial} disabled={busy}>
          Start your free {plans.trial_days}-day trial
        </button>
      )}

      <Card>
        <h2 style={{ fontSize: 17, marginBottom: 8 }}>Pay by card</h2>
        <p className="muted" style={{ marginBottom: 14 }}>
          Card, Apple Pay and Google Pay all run through Stripe.
        </p>
        <button className="btn btn-primary" onClick={payCard} disabled={busy}>
          {busy ? 'Working…' : 'Continue to payment'}
        </button>
      </Card>
    </main>
  );
}
