import { lazy, Suspense } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SearchProvider } from './state/SearchContext';
import { Toaster } from 'react-hot-toast';
import { HomePage } from './pages/HomePage';
import { OAuthCallback } from './pages/OAuthCallback';
import { RootLayout } from './layouts/RootLayout';
import './styles/app.css';
import './i18n/config';

const HistoryPage = lazy(() =>
  import('./pages/HistoryPage').then((m) => ({ default: m.HistoryPage }))
);
const SearchPage = lazy(() => import('./pages/SearchPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));

function PageLoader() {
  return (
    <div className="page-loading" aria-busy="true">
      <div className="skeleton-card" style={{ width: 240, margin: '4rem auto' }} />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <SearchProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/oauth/callback" element={<OAuthCallback />} />
                <Route element={<RootLayout />}>
                  <Route path="/search" element={<SearchPage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="/analytics" element={<AnalyticsPage />} />
                  <Route path="/admin" element={<AdminPage />} />
                  <Route path="/history" element={<HistoryPage />} />
                </Route>
                <Route path="/legacy" element={<LegacyRedirect />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
          <Toaster position="bottom-right" toastOptions={{ duration: 3000 }} />
        </SearchProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

function LegacyRedirect() {
  window.location.href = '/legacy/index.html';
  return null;
}
