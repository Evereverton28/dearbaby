import { useEffect, useState } from 'react';
import api from '../api';
import { useChild } from '../child';
import { Card, Loading, Empty, WeekRing } from '../components/Bits';

export default function Pregnancy() {
  const { active } = useChild();
  const [week, setWeek] = useState(active?.current_week || 20);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/pregnancy/weeks/${week}`)
      .then(({ data }) => setData(data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [week]);

  if (!active) return <Empty title="No pregnancy yet"
    body="Add a due date to start the weekly tracker." action="Add one" to="/app/setup" />;

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">Pregnancy</p>
        <h1>Week {week}</h1>
      </div>

      {loading ? <Loading /> : !data ? (
        <Empty title="No content for that week" body="Try a week between 4 and 42." />
      ) : (
        <>
          <Card className="weekcard">
            <WeekRing week={week} size={110} />
            <div className="meta">
              <span className="chip">Trimester {data.trimester}</span>
              <b>The size of {data.size_label} {data.emoji}</b>
              <p className="muted">{data.summary}</p>
              <div className="row" style={{ marginTop: 12, gap: 24 }}>
                <div><small className="muted">Length</small>
                  <p style={{ fontFamily: 'var(--font-display)', fontSize: 18 }}>{data.length_cm} cm</p></div>
                <div><small className="muted">Weight</small>
                  <p style={{ fontFamily: 'var(--font-display)', fontSize: 18 }}>{data.weight_g} g</p></div>
              </div>
            </div>
          </Card>

          <Card style={{ marginTop: 16 }}>
            <span className="chip chip-sage">This week</span>
            <p style={{ marginTop: 10 }}>{data.tip}</p>
          </Card>
        </>
      )}

      <div className="row" style={{ marginTop: 22, overflowX: 'auto', paddingBottom: 6 }}>
        {Array.from({ length: 39 }, (_, i) => i + 4).map((w) => (
          <button key={w} onClick={() => setWeek(w)}
            className={`btn ${w === week ? 'btn-primary' : 'btn-ghost'}`}
            style={{ flex: '0 0 auto', padding: '8px 14px' }}>{w}</button>
        ))}
      </div>
    </main>
  );
}
