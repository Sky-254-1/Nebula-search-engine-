import { apiClient } from './client';
import { AuthRequest, AuthResponse, UserInfo, RefreshRequest } from '@/types';

export const authApi = {
  async login(data: AuthRequest): Promise<AuthResponse> {
    return apiClient.login(data.email, data.password);
  }

  async signup(data: AuthRequest): Promise<void> {
    return apiClient.signup(data.email, data.password);
  }

  async logout(): Promise<void> {
    return apiClient.logout();
  }

  async logoutAll(): Promise<void> {
    return apiClient.logoutAll();
  }

  async refreshToken(data: RefreshRequest): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/auth/refresh', data);
  }

  async getCurrentUser(): Promise<UserInfo> {
    return apiClient.getCurrentUser();
  }

  async verifyEmail(token: string): Promise<void> {
    return apiClient.post('/auth/verify-email', { token });
  }

  async requestPasswordReset(email: string): Promise<void> {
    return apiClient.post('/auth/forgot-password', { email });
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    return apiClient.post('/auth/reset-password', { token, new_password: newPassword });
  }
};