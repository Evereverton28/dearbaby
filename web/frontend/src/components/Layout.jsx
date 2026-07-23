import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { getTheme, toggleTheme } from '../theme';

const LINKS = [
  ['/app', 'Home'],
  ['/app/pregnancy', 'Pregnancy'],
  ['/app/memories', 'Memories'],
  ['/app/gallery', 'Gallery'],
  ['/app/community', 'Community'],
  ['/app/recipes', 'Recipes'],
];

export default function Layout({ children }) {
  const { user, signOut, can } = useAuth();
  const [open, setOpen] = useState(false);
  const [userMenu, setUserMenu] = useState(false);
  const [theme, setThemeState] = useState(getTheme());
  const navigate = useNavigate();

  const flip = () => { toggleTheme(); setThemeState(getTheme()); };
  const out = () => { signOut(); navigate('/login'); };

  const links = [...LINKS];
  if (can('moderation') || can('users')) links.push(['/admin', 'Admin']);

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/app" className="brand">Dear<span>♥</span>Baby</Link>
        <nav className="navlinks">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/app'}
              className={({ isActive }) => (isActive ? 'active' : '')}>{label}</NavLink>
          ))}
        </nav>
        <div className="topbar-spacer" />
        <button className="icon-btn" onClick={flip}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
          {theme === 'dark' ? '☀' : '☾'}
        </button>

        {/* User menu — visible on desktop and mobile */}
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
              <Link to="/app/settings" onClick={() => setUserMenu(false)}>Settings</Link>
              <Link to="/app/upgrade" onClick={() => setUserMenu(false)}>Subscription</Link>
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
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === '/app'} onClick={() => setOpen(false)}
            className={({ isActive }) => (isActive ? 'active' : '')}>{label}</NavLink>
        ))}
        <Link to="/app/settings" onClick={() => setOpen(false)}>Settings</Link>
        <a href="#signout" onClick={(e) => { e.preventDefault(); setOpen(false); out(); }}>Sign out</a>
      </div>

      {children}
    </div>
  );
}
