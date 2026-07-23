import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { errorMessage } from '../api';
import { track } from '../analytics';
import { ErrorNote } from '../components/Bits';

export default function Register() {
  const { signUp } = useAuth();
  const [form, setForm] = useState({ display_name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  useEffect(() => { track('signup_started'); }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 8) { setError('Use at least 8 characters.'); return; }
    setBusy(true); setError('');
    try {
      await signUp(form);
      track('account_created');
      navigate('/app/setup', { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Could not create your account.'));
    } finally { setBusy(false); }
  };

  return (
    <div className="page page-narrow" style={{ maxWidth: 400, paddingTop: 64 }}>
      <div className="center" style={{ marginBottom: 26 }}>
        <Link to="/" className="brand">Dear<span>♥</span>Baby</Link>
        <p className="muted" style={{ marginTop: 8 }}>Start your memory book.</p>
      </div>
      <div className="card">
        <ErrorNote>{error}</ErrorNote>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="name">Your name</label>
            <input id="name" value={form.display_name} required onChange={set('display_name')} />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={form.email} required
              autoComplete="email" onChange={set('email')} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={form.password} required
              autoComplete="new-password" onChange={set('password')} />
            <small className="muted">At least 8 characters.</small>
          </div>
          <button className="btn btn-primary" style={{ width: '100%' }} disabled={busy}>
            {busy ? 'Creating…' : 'Create account'}
          </button>
        </form>
      </div>
      <p className="center muted" style={{ marginTop: 16 }}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  );
}
