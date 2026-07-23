import { useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth';
import { getTheme, toggleTheme } from '../../theme';

/* Mirrors the server permission map. Hiding a link the user can't use is a
   courtesy — the API returns 403 either way. */
const ITEMS = [
  ['/admin', 'Overview', 'analytics'],
  ['/admin/users', 'Users', 'users'],
  ['/admin/moderation', 'Moderation', 'moderation'],
  ['/admin/subscriptions', 'Subscriptions', 'subscriptions'],
  ['/admin/announcements', 'Announcements', 'announcements'],
];

export default function AdminLayout({ children }) {
  const { can, user, signOut } = useAuth();
  const [theme, setThemeState] = useState(getTheme());
  const [open, setOpen] = useState(false);
  const [userMenu, setUserMenu] = useState(false);
  const navigate = useNavigate();

  const flip = () => { toggleTheme(); setThemeState(getTheme()); };
  const out = () => { signOut(); navigate('/login'); };
  const items = ITEMS.filter(([, , cap]) => can(cap));

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/admin" className="brand">Dear<span>♥</span>Baby</Link>
        <span className="chip">Admin</span>
        <nav className="navlinks">
          {items.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/admin'}
              className={({ isActive }) => (isActive ? 'active' : '')}>{label}</NavLink>
          ))}
        </nav>
        <div className="topbar-spacer" />

        {/* An admin is also a parent. This is the doorway back to their own
            memory book — same app every other user sees. */}
        <Link to="/app" className="btn btn-ghost admin-switch"
          style={{ padding: '8px 16px', fontSize: 13 }}>My app</Link>

        <button className="icon-btn" onClick={flip} aria-label="Toggle theme">
          {theme === 'dark' ? '☀' : '☾'}
        </button>

        <div className="user-menu-wrap">
          <button className="avatar" onClick={() => setUserMenu(!userMenu)}
            title={user?.display_name} aria-expanded={userMenu} aria-label="User menu">
            {(user?.display_name || '?').charAt(0).toUpperCase()}
          </button>
          {userMenu && (
            <div className="user-dropdown">
              <div className="user-dropdown-name">{user?.display_name}</div>
              <div className="user-dropdown-email">{user?.email}</div>
              <hr />
              <Link to="/app" onClick={() => setUserMenu(false)}>My memory book</Link>
              <Link to="/app/settings" onClick={() => setUserMenu(false)}>Settings</Link>
              <hr />
              <a href="#signout" onClick={(e) => { e.preventDefault(); setUserMenu(false); out(); }}>
                Sign out
              </a>
            </div>
          )}
        </div>

        <button className="icon-btn hamburger" onClick={() => setOpen(!open)}
          aria-expanded={open} aria-label="Menu">☰</button>
      </header>

      <div className={`mobile-menu ${open ? 'open' : ''}`}>
        {items.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === '/admin'} onClick={() => setOpen(false)}
            className={({ isActive }) => (isActive ? 'active' : '')}>{label}</NavLink>
        ))}
        <Link to="/app" onClick={() => setOpen(false)}>My memory book</Link>
        <a href="#signout" onClick={(e) => { e.preventDefault(); setOpen(false); out(); }}>
          Sign out
        </a>
      </div>

      {children}
    </div>
  );
}
