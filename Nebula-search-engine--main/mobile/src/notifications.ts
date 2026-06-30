import { PushNotifications } from '@capacitor/push-notifications';
import { isNative } from './config';

export interface NebulaNotification {
  id: string;
  title: string;
  body: string;
  type: 'search_complete' | 'index_done' | 'ai_answer' | 'system';
  data?: Record<string, unknown>;
  receivedAt: number;
}

type NotificationListener = (notification: NebulaNotification) => void;
const listeners: Set<NotificationListener> = new Set();

export function onNotification(listener: NotificationListener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export async function setupPushNotifications() {
  if (!isNative) return;

  PushNotifications.addListener('registration', (token: { value: string }) => {
    console.log('[Nebula Push] Device registered:', token.value);
  });

  PushNotifications.addListener('registrationError', (err: any) => {
    console.error('[Nebula Push] Registration error:', err);
  });

  PushNotifications.addListener('pushNotificationReceived', (notification: any) => {
    const nebulaNotif: NebulaNotification = {
      id: notification.id || String(Date.now()),
      title: notification.title || 'Nebula',
      body: notification.body || '',
      type: notification.data?.type || 'system',
      data: notification.data,
      receivedAt: Date.now(),
    };
    listeners.forEach((listener) => listener(nebulaNotif));
  });
}
