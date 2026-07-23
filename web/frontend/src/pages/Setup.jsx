import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { errorMessage } from '../api';
import { useChild } from '../child';
import { ErrorNote } from '../components/Bits';

export default function Setup() {
  const [stage, setStage] = useState('pregnancy');
  const [form, setForm] = useState({ name: '', due_date: '', birth_date: '', sex: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const { reload, setActiveId } = useChild();
  const navigate = useNavigate();

  /* Fills this account with a sample pregnancy and a sample baby, so every
     screen has something in it while you're looking around. */
  const loadSample = async () => {
    setDemoBusy(true); setError('');
    try {
      const { data } = await api.post('/demo');
      await reload();
      setActiveId(data.children[0].id);
      navigate('/app', { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Could not load the sample data.'));
    } finally { setDemoBusy(false); }
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    const payload = { name: form.name || null, sex: form.sex || null };
    if (stage === 'pregnancy') payload.due_date = form.due_date;
    else payload.birth_date = form.birth_date;
    try {
      const { data } = await api.post('/children', payload);
      await api.post(`/notifications/children/${data.id}/schedule-defaults`).catch(() => {});
      await reload();
      setActiveId(data.id);
      navigate('/app', { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Could not save that.'));
    } finally { setBusy(false); }
  };

  return (
    <div className="page page-narrow" style={{ maxWidth: 460 }}>
      <div className="page-head center">
        <p className="eyebrow">One quick step</p>
        <h1>Who are we remembering?</h1>
        <p>You can change any of this later.</p>
      </div>
      <div className="card">
        <ErrorNote>{error}</ErrorNote>
        <div className="row" style={{ marginBottom: 18 }}>
          <button type="button" onClick={() => setStage('pregnancy')}
            className={`btn ${stage === 'pregnancy' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ flex: 1 }}>I'm expecting</button>
          <button type="button" onClick={() => setStage('baby')}
            className={`btn ${stage === 'baby' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ flex: 1 }}>Baby is here</button>
        </div>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="nm">Name {stage === 'pregnancy' && '(or a nickname)'}</label>
            <input id="nm" value={form.name} onChange={set('name')}
              placeholder={stage === 'pregnancy' ? 'Baby' : 'Maya'} />
          </div>
          {stage === 'pregnancy' ? (
            <div className="field">
              <label htmlFor="dd">Due date</label>
              <input id="dd" type="date" value={form.due_date} required onChange={set('due_date')} />
            </div>
          ) : (
            <div className="field">
              <label htmlFor="bd">Date of birth</label>
              <input id="bd" type="date" value={form.birth_date} required onChange={set('birth_date')} />
            </div>
          )}
          <button className="btn btn-primary" style={{ width: '100%' }} disabled={busy}>
            {busy ? 'Saving…' : 'Continue'}
          </button>
        </form>
      </div>

      <div className="center" style={{ marginTop: 22 }}>
        <p className="muted" style={{ marginBottom: 10 }}>
          Just looking around?
        </p>
        <button className="btn btn-ghost" onClick={loadSample} disabled={demoBusy}>
          {demoBusy ? 'Loading…' : 'Load sample data instead'}
        </button>
        <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>
          Adds a 24-week pregnancy and an 8-month-old, with milestones,
          journal entries, growth history and appointments.
        </p>
      </div>
    </div>
  );
}
