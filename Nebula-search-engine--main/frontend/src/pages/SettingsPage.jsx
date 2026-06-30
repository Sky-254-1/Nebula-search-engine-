import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../store/app-store';
import { useSearchState } from '../state/SearchContext';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { FiSun, FiMoon, FiGlobe } from 'react-icons/fi';
import toast from 'react-hot-toast';

const languages = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
];

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { theme, setTheme, preferences, updatePreferences } = useAppStore();
  const { config, setConfig } = useSearchState();
  const [backend, setBackend] = useState(config.backends || 'wikipedia');
  const [pageSize, setPageSize] = useState(config.pageSize || 10);

  function handleThemeChange(newTheme) {
    setTheme(newTheme);
    toast.success(`Theme set to ${newTheme}`);
  }

  function handleLanguageChange(code) {
    i18n.changeLanguage(code);
    updatePreferences({ language: code });
    toast.success(`Language set to ${languages.find(l => l.code === code)?.label}`);
  }

  function handleSaveDefaults() {
    setConfig({ ...config, backends: backend, pageSize });
    toast.success('Search defaults saved');
  }

  return (
    <div className="settings-page">
      <h1 className="page-title">{t('settings.title')}</h1>

      <div className="settings-grid">
        <Card className="settings-section">
          <h2 className="section-title"><FiSun size={18} /> {t('profile.theme')}</h2>
          <div className="theme-toggle-group">
            <Button variant={theme === 'dark' ? 'primary' : 'secondary'} onClick={() => handleThemeChange('dark')}>
              <FiMoon size={16} /> Dark
            </Button>
            <Button variant={theme === 'light' ? 'primary' : 'secondary'} onClick={() => handleThemeChange('light')}>
              <FiSun size={16} /> Light
            </Button>
          </div>
        </Card>

        <Card className="settings-section">
          <h2 className="section-title"><FiGlobe size={18} /> {t('profile.language')}</h2>
          <div className="language-group">
            {languages.map((lang) => (
              <Button
                key={lang.code}
                variant={i18n.language === lang.code ? 'primary' : 'secondary'}
                onClick={() => handleLanguageChange(lang.code)}
              >
                {lang.label}
              </Button>
            ))}
          </div>
        </Card>

        <Card className="settings-section">
          <h2 className="section-title">{t('settings.searchDefaults')}</h2>
          <div className="settings-form">
            <label className="settings-label">
              {t('settings.defaultBackend')}
              <select className="settings-select" value={backend} onChange={(e) => setBackend(e.target.value)}>
                <option value="wikipedia">Wikipedia</option>
                <option value="wikipedia,brave">Wikipedia + Brave</option>
                <option value="wikipedia,serpapi">Wikipedia + SerpAPI</option>
              </select>
            </label>
            <label className="settings-label">
              {t('settings.pageSize')}
              <input className="settings-input" type="number" min={5} max={50} value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))} />
            </label>
            <Button onClick={handleSaveDefaults}>{t('common.save')}</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
