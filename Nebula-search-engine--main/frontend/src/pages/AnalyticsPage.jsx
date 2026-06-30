import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ProtectedRoute } from '../auth/guards/ProtectedRoute';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { FiBarChart2, FiTrendingUp, FiServer, FiCpu } from 'react-icons/fi';

function AnalyticsContent() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState('7');

  const topQueries = [
    { query: 'quantum computing', count: 128 },
    { query: 'machine learning', count: 96 },
    { query: 'react framework', count: 72 },
    { query: 'typescript tutorial', count: 55 },
    { query: 'python backend', count: 41 },
  ];

  const backends = [
    { name: 'Wikipedia', usage: 45 },
    { name: 'Brave', usage: 32 },
    { name: 'SerpAPI', usage: 23 },
  ];

  return (
    <div className="analytics-page">
      <div className="page-header">
        <h1 className="page-title">{t('analytics.title')}</h1>
        <div className="period-toggle">
          {['7', '30', '90'].map((d) => (
            <Button key={d} variant={period === d ? 'primary' : 'secondary'} size="sm" onClick={() => setPeriod(d)}>
              {t(`analytics.last${d}`)}
            </Button>
          ))}
        </div>
      </div>

      <div className="stats-grid">
        <Card className="stat-card">
          <div className="stat-icon" style={{ background: '#7c5cfc15', color: '#7c5cfc' }}>
            <FiBarChart2 size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">{t('analytics.searchVolume')}</span>
            <span className="stat-value">1,247</span>
          </div>
        </Card>
        <Card className="stat-card">
          <div className="stat-icon" style={{ background: '#22c55e15', color: '#22c55e' }}>
            <FiTrendingUp size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">{t('analytics.topQueries')}</span>
            <span className="stat-value">5</span>
          </div>
        </Card>
        <Card className="stat-card">
          <div className="stat-icon" style={{ background: '#f59e0b15', color: '#f59e0b' }}>
            <FiServer size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">{t('analytics.popularBackends')}</span>
            <span className="stat-value">3</span>
          </div>
        </Card>
        <Card className="stat-card">
          <div className="stat-icon" style={{ background: '#3b82f615', color: '#3b82f6' }}>
            <FiCpu size={24} />
          </div>
          <div className="stat-info">
            <span className="stat-label">{t('analytics.aiUsage')}</span>
            <span className="stat-value">342</span>
          </div>
        </Card>
      </div>

      <div className="analytics-grid">
        <Card className="analytics-section">
          <h2 className="section-title">{t('analytics.topQueries')}</h2>
          <div className="top-queries-list">
            {topQueries.map((item, i) => (
              <div key={i} className="top-query-item">
                <span className="top-query-rank">#{i + 1}</span>
                <span className="top-query-text">{item.query}</span>
                <Badge variant="info">{item.count}</Badge>
              </div>
            ))}
          </div>
        </Card>

        <Card className="analytics-section">
          <h2 className="section-title">{t('analytics.popularBackends')}</h2>
          <div className="backend-usage-list">
            {backends.map((item, i) => (
              <div key={i} className="backend-usage-item">
                <span className="backend-name">{item.name}</span>
                <div className="backend-bar-bg">
                  <div className="backend-bar-fill" style={{ width: `${item.usage}%` }} />
                </div>
                <span className="backend-percent">{item.usage}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <ProtectedRoute>
      <AnalyticsContent />
    </ProtectedRoute>
  );
}
