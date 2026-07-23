import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { errorMessage } from '../api';
import { useAuth } from '../auth';
import { Card, Loading, ErrorNote } from '../components/Bits';
import { setTheme, getTheme, useSystemTheme } from '../theme';

const TOGGLES = [
  ['notif_milestones', 'Milestone reminders'],
  ['notif_pregnancy', 'Pregnancy week updates'],
  ['notif_vaccination', 'Vaccination reminders'],
  ['notif_birthday', 'Birthday reminders'],
  ['notif_growth', 'Growth check-in reminders'],
  ['auto_backup', 'Back up photos automatically'],
  ['profile_public', 'Show my profile in the community'],
];

export default function Settings() {
  const { user, signOut, refreshUser } = useAuth();
  const [settings, setSettings] = useState(null);
  const [sub, setSub] = useState(null);
  const [name, setName] = useState(user?.display_name || '');
  const [error, setError] = useState('');
  const [note, setNote] = useState('');
  const [theme, setThemeState] = useState(getTheme());
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/settings').then(({ data }) => setSettings(data)).catch(() => {});
    api.get('/billing/subscription').then(({ data }) => setSub(data)).catch(() => {});
  }, []);

  const patch = async (key, value) => {
    setSettings({ ...settings, [key]: value });
    await api.patch('/settings', { [key]: value }).catch(() => {});
  };

  const pickTheme = (choice) => {
    if (choice === 'system') useSystemTheme(); else setTheme(choice);
    setThemeState(getTheme());
    patch('theme', choice);
  };

  const saveProfile = async (e) => {
    e.preventDefault();
    setError(''); setNote('');
    try {
      await api.patch('/settings/profile', { display_name: name });
      await refreshUser();
      setNote('Profile saved.');
    } catch (err) { setError(errorMessage(err)); }
  };

  const exportAll = async () => {
    const { data } = await api.get('/settings/export');
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `dearbaby-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const loadSample = async () => {
    setError(''); setNote('');
    try {
      await api.post('/demo');
      setNote('Sample data added. Head back to Home to see it.');
    } catch (err) { setError(errorMessage(err)); }
  };

  const clearSample = async () => {
    if (!window.confirm('This removes every child, milestone, journal entry and '
      + 'photo record on your account. Your login stays. Continue?')) return;
    setError(''); setNote('');
    try {
      await api.delete('/demo');
      setNote('Cleared. Your account is empty again.');
    } catch (err) { setError(errorMessage(err)); }
  };

  const deleteAccount = async () => {
    const password = window.prompt(
      'This permanently deletes your account and every memory in it.\n\nEnter your password to confirm:');
    if (!password) return;
    try {
      await api.delete('/settings/account', { data: { password } });
      signOut();
      navigate('/', { replace: true });
    } catch (err) { setError(errorMessage(err)); }
  };

  if (!settings) return <Loading />;

  return (
    <main className="page page-narrow">
      <div className="page-head">
        <p className="eyebrow">Your account</p>
        <h1>Settings</h1>
      </div>

      <ErrorNote>{error}</ErrorNote>
      {note && <div className="alert alert-info">{note}</div>}

      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 17, marginBottom: 12 }}>Profile</h2>
        <form onSubmit={saveProfile}>
          <div className="field">
            <label htmlFor="dn">Display name</label>
            <input id="dn" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <p className="muted" style={{ marginBottom: 12 }}>{user?.email}</p>
          <button className="btn btn-primary">Save</button>
        </form>
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 17, marginBottom: 12 }}>Appearance</h2>
        <div className="row">
          {['light', 'dark', 'system'].map((t) => (
            <button key={t} onClick={() => pickTheme(t)}
              className={`btn ${settings.theme === t ? 'btn-primary' : 'btn-ghost'}`}
              style={{ textTransform: 'capitalize' }}>{t}</button>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 10 }}>Currently showing {theme}.</p>
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 17, marginBottom: 12 }}>Notifications</h2>
        {TOGGLES.map(([key, label]) => (
          <label key={key} className="row-between"
            style={{ padding: '9px 0', cursor: 'pointer' }}>
            <span>{label}</span>
            <input type="checkbox" checked={!!settings[key]} style={{ width: 18, height: 18 }}
              onChange={(e) => patch(key, e.target.checked)} />
          </label>
        ))}
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 17, marginBottom: 8 }}>Subscription</h2>
        {sub?.subscription ? (
          <>
            <p className="muted">
              {sub.subscription.plan} · {sub.subscription.status}
              {sub.premium ? ' · premium active' : ''}
            </p>
            {sub.subscription.cancel_at_period_end &&
              <p className="muted">Cancels at the end of this period.</p>}
          </>
        ) : <p className="muted">You're on the free plan.</p>}
        <button className="btn btn-ghost" style={{ marginTop: 12 }}
          onClick={() => navigate('/app/upgrade')}>Manage plan</button>
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 17, marginBottom: 8 }}>Sample data</h2>
        <p className="muted" style={{ marginBottom: 12 }}>
          Fill this account with a sample pregnancy and baby to explore the app,
          or clear everything and start fresh.
        </p>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          <button className="btn btn-ghost" onClick={loadSample}>Load sample data</button>
          <button className="btn btn-ghost" onClick={clearSample}>Clear my data</button>
        </div>
      </Card>

      <Card>
        <h2 style={{ fontSize: 17, marginBottom: 8 }}>Your data</h2>
        <p className="muted" style={{ marginBottom: 12 }}>
          Download everything, or close your account for good.
        </p>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          <button className="btn btn-ghost" onClick={exportAll}>Export all memories</button>
          <button className="btn btn-danger" onClick={deleteAccount}>Delete account</button>
        </div>
      </Card>
    </main>
  );
}
