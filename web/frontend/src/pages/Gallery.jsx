import { useEffect, useRef, useState } from 'react';
import api, { errorMessage } from '../api';
import { useChild } from '../child';
import { Card, Loading, Empty, ErrorNote } from '../components/Bits';
import { track } from '../analytics';

export default function Gallery() {
  const { active } = useChild();
  const [groups, setGroups] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef();

  const load = () => {
    if (!active) { setLoading(false); return; }
    setLoading(true);
    Promise.all([
      api.get(`/media/children/${active.id}/gallery`),
      api.get(`/media/children/${active.id}/albums`),
    ]).then(([g, a]) => { setGroups(g.data.groups); setAlbums(a.data.albums); })
      .finally(() => setLoading(false));
  };
  useEffect(load, [active]);

  const upload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true); setError('');
    try {
      for (const f of files) {
        const fd = new FormData();
        fd.append('file', f);
        fd.append('child_id', active.id);
        await api.post('/media/upload', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }
      track('first_memory_added');
      load();
    } catch (err) { setError(errorMessage(err, 'Upload failed.')); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  };

  const newAlbum = async () => {
    const title = window.prompt('Album name');
    if (!title) return;
    await api.post(`/media/children/${active.id}/albums`, { title });
    load();
  };

  const label = (period) => period === 'undated' ? 'Undated'
    : new Date(`${period}-01`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  if (!active) return <Empty title="No gallery yet" body="Add a baby or pregnancy first."
    action="Get started" to="/app/setup" />;

  return (
    <main className="page">
      <div className="page-head row-between">
        <div>
          <p className="eyebrow">{active.name || 'Baby'}</p>
          <h1>Gallery</h1>
        </div>
        <div className="row">
          <button className="btn btn-ghost" onClick={newAlbum}>New album</button>
          <button className="btn btn-primary" onClick={() => fileRef.current?.click()}
            disabled={uploading}>{uploading ? 'Uploading…' : 'Add photos'}</button>
        </div>
      </div>
      <input ref={fileRef} type="file" multiple accept="image/*,video/*" hidden onChange={upload} />

      <ErrorNote>{error}</ErrorNote>

      {albums.length > 0 && (
        <>
          <h2 style={{ fontSize: 17, margin: '4px 0 10px' }}>Albums</h2>
          <div className="grid grid-4" style={{ marginBottom: 26 }}>
            {albums.map((a) => (
              <Card key={a.id}>
                <b>{a.title}</b>
                <p className="muted">{a.item_count} item{a.item_count === 1 ? '' : 's'}</p>
              </Card>
            ))}
          </div>
        </>
      )}

      {loading ? <Loading /> : groups.length === 0 ? (
        <Empty title="No photos yet"
          body="Add your first photo and it'll be organised by month automatically." />
      ) : groups.map((g) => (
        <section key={g.period} style={{ marginBottom: 26 }}>
          <h2 style={{ fontSize: 17, marginBottom: 10 }}>{label(g.period)}</h2>
          <div className="gallery-grid">
            {g.items.map((m) => (
              m.kind === 'video'
                ? <video key={m.id} src={m.url} controls
                    style={{ width: '100%', aspectRatio: 1, objectFit: 'cover',
                             borderRadius: 'var(--radius-sm)' }} />
                : <img key={m.id} src={m.url} alt={m.caption || ''} loading="lazy" />
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
