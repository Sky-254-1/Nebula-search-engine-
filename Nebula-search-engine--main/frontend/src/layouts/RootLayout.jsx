import { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../auth/AuthContext';
import { useAppStore } from '../store/app-store';
import { FiHome, FiSearch, FiGrid, FiUser, FiSettings, FiBarChart2, FiShield, FiClock, FiMenu, FiX, FiSun, FiMoon, FiLogOut } from 'react-icons/fi';

const navItems = [
  { to: '/', icon: FiHome, labelKey: 'nav.home' },
  { to: '/search', icon: FiSearch, labelKey: 'nav.search' },
  { to: '/dashboard', icon: FiGrid, labelKey: 'nav.dashboard' },
  { to: '/profile', icon: FiUser, labelKey: 'nav.profile' },
  { to: '/settings', icon: FiSettings, labelKey: 'nav.settings' },
  { to: '/analytics', icon: FiBarChart2, labelKey: 'nav.analytics' },
  { to: '/admin', icon: FiShield, labelKey: 'nav.admin' },
  { to: '/history', icon: FiClock, labelKey: 'nav.history' },
];

export function RootLayout() {
  const { t } = useTranslation();
  const { user, isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme, sidebarOpen, toggleSidebar } = useAppStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="root-layout">
      <AnimatePresence mode="wait">
        {mobileOpen && (
          <motion.div
            className="mobile-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'} ${mobileOpen ? 'sidebar-mobile-open' : ''}`}>
        <div className="sidebar-header">
          <NavLink to="/" className="sidebar-logo">Nebula</NavLink>
          <button type="button" className="sidebar-close-btn" onClick={() => setMobileOpen(false)} aria-label="Close menu">
            <FiX size={20} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map(({ to, icon: Icon, labelKey }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`}
              onClick={() => setMobileOpen(false)}
            >
              <Icon size={20} />
              <span>{t(labelKey)}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button type="button" className="sidebar-link" onClick={toggleTheme}>
            {theme === 'dark' ? <FiSun size={20} /> : <FiMoon size={20} />}
            <span>{theme === 'dark' ? t('settings.theme') : t('settings.theme')}</span>
          </button>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button type="button" className="topbar-menu-btn" onClick={() => setMobileOpen(true)} aria-label="Open menu">
              <FiMenu size={22} />
            </button>
          </div>
          <div className="topbar-right">
            {isAuthenticated ? (
              <>
                <span className="topbar-user">{user?.email}</span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>
                  <FiLogOut size={16} />
                  <span>{t('nav.signOut')}</span>
                </button>
              </>
            ) : (
              <NavLink to="/?auth=1" className="btn btn-primary btn-sm">{t('nav.signIn')}</NavLink>
            )}
          </div>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default RootLayout;
