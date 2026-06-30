import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ProtectedRoute } from '../auth/guards/ProtectedRoute';
import { useAuth } from '../auth/AuthContext';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { FiUser, FiLock, FiKey } from 'react-icons/fi';
import toast from 'react-hot-toast';

function ProfileContent() {
  const { t } = useTranslation();
  const { user, api } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSaveProfile(e) {
    e.preventDefault();
    setSaving(true);
    try {
      if (api.updateProfile) {
        await api.updateProfile({ name });
      }
      toast.success(t('common.save'));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    if (!currentPassword || !newPassword) {
      toast.error('Both fields are required');
      return;
    }
    setSaving(true);
    try {
      if (api.changePassword) {
        await api.changePassword(currentPassword, newPassword);
      }
      toast.success('Password changed');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="profile-page">
      <h1 className="page-title">{t('profile.title')}</h1>

      <div className="profile-grid">
        <Card className="profile-section">
          <h2 className="section-title"><FiUser size={18} /> {t('profile.editProfile')}</h2>
          <form onSubmit={handleSaveProfile} className="profile-form">
            <Input label={t('profile.name')} value={name} onChange={(e) => setName(e.target.value)} />
            <Input label={t('profile.email')} value={user?.email || ''} disabled />
            <Button type="submit" loading={saving}>{t('profile.save')}</Button>
          </form>
        </Card>

        <Card className="profile-section">
          <h2 className="section-title"><FiLock size={18} /> {t('profile.changePassword')}</h2>
          <form onSubmit={handleChangePassword} className="profile-form">
            <Input label={t('profile.currentPassword')} type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            <Input label={t('profile.newPassword')} type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            <Button type="submit" loading={saving}>{t('profile.save')}</Button>
          </form>
        </Card>

        <Card className="profile-section">
          <h2 className="section-title"><FiKey size={18} /> {t('profile.apiKeys')}</h2>
          <p className="muted">API key management coming soon.</p>
        </Card>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}
