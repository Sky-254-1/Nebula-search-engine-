import { useTranslation } from 'react-i18next';
import { ProtectedRoute } from '../auth/guards/ProtectedRoute';
import { useAuth } from '../auth/AuthContext';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { FiUsers, FiActivity, FiFlag, FiServer } from 'react-icons/fi';

function AdminContent() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const metrics = [
    { icon: FiUsers, label: t('admin.users'), value: '128', color: '#7c5cfc' },
    { icon: FiServer, label: t('admin.serverMetrics'), value: '98% uptime', color: '#22c55e' },
    { icon: FiActivity, label: t('admin.auditLog'), value: '1,024 entries', color: '#3b82f6' },
    { icon: FiFlag, label: t('admin.featureFlags'), value: '6 active', color: '#f59e0b' },
  ];

  return (
    <div className="admin-page">
      <div className="page-header">
        <h1 className="page-title">{t('admin.title')}</h1>
        <Badge variant="success">{t('admin.statusOperational')}</Badge>
      </div>

      <div className="stats-grid">
        {metrics.map((m, i) => (
          <Card key={i} className="stat-card">
            <div className="stat-icon" style={{ background: `${m.color}15`, color: m.color }}>
              <m.icon size={24} />
            </div>
            <div className="stat-info">
              <span className="stat-label">{m.label}</span>
              <span className="stat-value">{m.value}</span>
            </div>
          </Card>
        ))}
      </div>

      <div className="admin-grid">
        <Card className="admin-section">
          <h2 className="section-title">{t('admin.users')}</h2>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Status</th>
                <th>Role</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{user?.email || 'admin@nebula.dev'}</td>
                <td><Badge variant="success">Active</Badge></td>
                <td>Admin</td>
                <td>Jan 2025</td>
              </tr>
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}

export default function AdminPage() {
  return (
    <ProtectedRoute>
      <AdminContent />
    </ProtectedRoute>
  );
}
