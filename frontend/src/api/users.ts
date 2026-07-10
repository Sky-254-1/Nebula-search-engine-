import { apiClient } from './client';
import { UserProfile, UserPreferences } from '@/types';

export interface UpdateProfileParams {
  first_name?: string;
  last_name?: string;
  phone_number?: string;
}

export interface UpdatePreferencesParams {
  preferences: Record<string, any>;
}

export const usersApi = {
  // Profile
  async getProfile(): Promise<UserProfile> {
    return apiClient.get<UserProfile>('/users/profile');
  },

  async updateProfile(params: UpdateProfileParams): Promise<UserProfile> {
    return apiClient.put<UserProfile>('/users/profile', params);
  },

  // Preferences
  async getPreferences(): Promise<UserPreferences> {
    return apiClient.get<UserPreferences>('/users/preferences');
  },

  async updatePreferences(params: UpdatePreferencesParams): Promise<UserPreferences> {
    return apiClient.put<UserPreferences>('/users/preferences', params);
  },

  // Activity
  async getActivity(limit: number = 20, actionType?: string): Promise<{ activities: any[]; total: number }> {
    const params: any = { limit };
    if (actionType) params.action_type = actionType;
    return apiClient.get('/users/activity', params);
  },

  // Avatar
  async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/users/avatar', formData);
  },

  async deleteAvatar(): Promise<void> {
    await apiClient.delete('/users/avatar');
  },

  // Account
  async deleteAccount(): Promise<void> {
    await apiClient.delete('/users/account');
  }
};