import { useEffect, useState } from 'react';
import api from '../api';
import { Card, Loading, Empty } from '../components/Bits';

const CATEGORIES = [['', 'All'], ['puree', 'Purees'], ['finger_food', 'Finger food'],
                    ['toddler', 'Toddler meals']];

export default function Recipes() {
  const [recipes, setRecipes] = useState([]);
  const [q, setQ] = useState('');
  const [category, setCategory] = useState('');
  const [favOnly, setFavOnly] = useState(false);
  const [open, setOpen] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const qs = new URLSearchParams();
    if (q) qs.set('q', q);
    if (category) qs.set('category', category);
    if (favOnly) qs.set('favorites', '1');
    api.get(`/recipes?${qs}`)
      .then(({ data }) => setRecipes(data.recipes))
      .finally(() => setLoading(false));
  };
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); },
    [q, category, favOnly]);

  const fav = async (r) => {
    const { data } = await api.post(`/recipes/${r.id}/favorite`);
    setRecipes(recipes.map((x) => x.id === r.id ? { ...x, favorited: data.favorited } : x));
  };

  return (
    <main className="page">
      <div className="page-head">
        <p className="eyebrow">Weaning & baby food</p>
        <h1>Recipes</h1>
      </div>

      <div className="field">
        <input value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Search recipes…" aria-label="Search recipes" />
      </div>
      <div className="row" style={{ marginBottom: 18, flexWrap: 'wrap' }}>
        {CATEGORIES.map(([k, label]) => (
          <button key={k} onClick={() => { setCategory(k); setFavOnly(false); }}
            className={`btn ${category === k && !favOnly ? 'btn-primary' : 'btn-ghost'}`}>
            {label}
          </button>
        ))}
        <button onClick={() => { setFavOnly(!favOnly); setCategory(''); }}
          className={`btn ${favOnly ? 'btn-primary' : 'btn-ghost'}`}>♥ Saved</button>
      </div>

      {loading ? <Loading /> : recipes.length === 0 ? (
        <Empty title="No recipes found" body="Try a different search or category." />
      ) : (
        <div className="grid grid-3">
          {recipes.map((r) => (
            <Card key={r.id}>
              <div className="row-between">
                <span style={{ fontSize: 26 }}>{r.emoji}</span>
                <button className="icon-btn" onClick={() => fav(r)}
                  aria-label={r.favorited ? 'Remove from saved' : 'Save recipe'}>
                  {r.favorited ? '♥' : '♡'}
                </button>
              </div>
              <h3 style={{ fontSize: 17, margin: '8px 0 4px' }}>{r.title}</h3>
              <p className="muted">{r.description}</p>
              <div className="row" style={{ marginTop: 10, flexWrap: 'wrap' }}>
                <span className="chip chip-sage">{r.min_age_months}m+</span>
                <span className="chip">{r.prep_minutes} min</span>
              </div>
              {r.allergens?.length > 0 && (
                <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
                  Contains: {r.allergens.join(', ')}
                </p>
              )}
              <button className="btn btn-ghost" style={{ marginTop: 12, width: '100%' }}
                onClick={() => setOpen(open === r.id ? null : r.id)}>
                {open === r.id ? 'Hide' : 'View recipe'}
              </button>
              {open === r.id && (
                <div style={{ marginTop: 14 }}>
                  <h4 style={{ fontSize: 14, marginBottom: 6 }}>Ingredients</h4>
                  <ul className="muted" style={{ paddingLeft: 18, marginBottom: 12 }}>
                    {r.ingredients.map((i, n) => <li key={n}>{i}</li>)}
                  </ul>
                  <h4 style={{ fontSize: 14, marginBottom: 6 }}>Method</h4>
                  <ol className="muted" style={{ paddingLeft: 18 }}>
                    {r.steps.map((s, n) => <li key={n} style={{ marginBottom: 4 }}>{s}</li>)}
                  </ol>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
