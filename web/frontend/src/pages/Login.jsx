import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';
import { errorMessage } from '../api';
import { landingFor } from '../config/roles';
import { track } from '../analytics';
import { ErrorNote } from '../components/Bits';

export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const data = await signIn(email, password);
      track('signed_in');
      /* Role-based landing: the server tells us where this account belongs. */
      navigate(location.state?.from || data.landing || landingFor(data.user.role),
               { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Could not sign you in.'));
    } finally { setBusy(false); }
  };

  return (
    <div className="page page-narrow" style={{ maxWidth: 400, paddingTop: 64 }}>
      <div className="center" style={{ marginBottom: 26 }}>
        <Link to="/" className="brand">Dear<span>♥</span>Baby</Link>
        <p className="muted" style={{ marginTop: 8 }}>Welcome back.</p>
      </div>
      <div className="card">
        <ErrorNote>{error}</ErrorNote>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} autoComplete="email" required
              onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={password} autoComplete="current-password"
              required onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn btn-primary" style={{ width: '100%' }} disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
      <p className="center muted" style={{ marginTop: 16 }}>
        New here? <Link to="/register">Create an account</Link>
      </p>
    </div>
  );
}
