import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ProtectedRoute } from '../auth/guards/ProtectedRoute';
import { useAuth } from '../auth/AuthContext';
import { Card } from '../components/ui/Card';
import { Spinner } from '../components/ui/Spinner';
import { Badge } from '../components/ui/Badge';
import { FiSearch, FiDatabase, FiCpu, FiHardDrive } from 'react-icons/fi';

function DashboardContent() {
  const { t } = useTranslation();
  const { api } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const data = await api.me();
        if (active) setStats({ totalSearches: data?.totalSearches ?? 0, documentsIndexed: data?.documentsIndexed ?? 0, aiQueries: data?.aiQueries ?? 0, storageUsed: data?.storageUsed ?? 0, storageTotal: data?.storageTotal ?? 1024 });
      } catch { /* ignore */ }
      finally { if (active) setLoading(false); }
    }
    load();
    return () => { active = false; };
  }, [api]);

  if (loading) return <div className="page-loading"><Spinner size={32} /></div>;

  const statCards = [
    { icon: FiSearch, label: t('dashboard.totalSearches'), value: stats?.totalSearches ?? 0, color: '#7c5cfc' },
    { icon: FiDatabase, label: t('dashboard.documentsIndexed'), value: stats?.documentsIndexed ?? 0, color: '#22c55e' },
    { icon: FiCpu, label: t('dashboard.aiQueries'), value: stats?.aiQueries ?? 0, color: '#f59e0b' },
    { icon: FiHardDrive, label: t('dashboard.storageUsage'), value: `${stats?.storageUsed ?? 0}MB / ${stats?.storageTotal ?? 0}MB`, color: '#3b82f6' },
  ];

  return (
    <div className="dashboard-page">
      <h1 className="page-title">{t('dashboard.title')}</h1>

      <div className="stats-grid">
        {statCards.map((stat, i) => (
          <Card key={i} className="stat-card">
            <div className="stat-icon" style={{ background: `${stat.color}15`, color: stat.color }}>
              <stat.icon size={24} />
            </div>
            <div className="stat-info">
              <span className="stat-label">{stat.label}</span>
              <span className="stat-value">{stat.value}</span>
            </div>
          </Card>
        ))}
      </div>

      <div className="dashboard-grid">
        <Card className="dashboard-section">
          <h2 className="section-title">{t('dashboard.recentActivity')}</h2>
          <div className="activity-list">
            <div className="activity-item">
              <Badge variant="info">Search</Badge>
              <span>Quantum computing advances</span>
              <span className="activity-time">2 min ago</span>
            </div>
            <div className="activity-item">
              <Badge variant="success">AI</Badge>
              <span>Machine learning overview</span>
              <span className="activity-time">15 min ago</span>
            </div>
            <div className="activity-item">
              <Badge variant="warning">Search</Badge>
              <span>React 19 features</span>
              <span className="activity-time">1 hour ago</span>
            </div>
          </div>
        </Card>

        <Card className="dashboard-section">
          <h2 className="section-title">{t('dashboard.quickActions')}</h2>
          <div className="quick-actions">
            <button type="button" className="btn btn-primary" onClick={() => window.location.href = '/search'}>
              {t('nav.search')}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => window.location.href = '/settings'}>
              {t('nav.settings')}
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
