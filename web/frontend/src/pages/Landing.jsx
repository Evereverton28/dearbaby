import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">Dear<span>♥</span>Baby</Link>
        <div className="topbar-spacer" />
        <Link to="/login" className="btn btn-ghost">Sign in</Link>
      </header>
      <main className="page center">
        <p className="eyebrow">Pregnancy · Birth · Childhood</p>
        <h1 style={{ fontSize: 42, margin: '10px 0 12px' }}>
          Every little moment,<br />gently kept.
        </h1>
        <p className="muted" style={{ maxWidth: 520, margin: '0 auto 26px' }}>
          Track your pregnancy week by week, keep every first, and build a memory
          book your family can hold onto. Free for 30 days.
        </p>
        <Link to="/register" className="btn btn-primary">Start your memory book</Link>

        <div className="grid grid-3" style={{ marginTop: 48, textAlign: 'left' }}>
          {[
            ['Pregnancy journey', 'Weekly tracker, journal, scans, kick counter and contraction timer.'],
            ['Memory book', 'First smile, first word, first steps — with photos, growth and teeth.'],
            ['Made to share', 'Invite family to view, and turn it all into a printable book.'],
          ].map(([t, b]) => (
            <div className="card" key={t}>
              <h3 style={{ fontSize: 18, marginBottom: 6 }}>{t}</h3>
              <p className="muted">{b}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
