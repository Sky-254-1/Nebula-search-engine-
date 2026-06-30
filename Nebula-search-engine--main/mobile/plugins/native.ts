import { Network } from '@capacitor/network';
import { Share } from '@capacitor/share';
import { Clipboard } from '@capacitor/clipboard';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { PushNotifications } from '@capacitor/push-notifications';
import { isNative } from '../src/config';

export async function isOnline(): Promise<boolean> {
  if (!isNative) return navigator.onLine;
  const status = await Network.getStatus();
  return status.connected;
}

export async function shareContent(title: string, text: string, url: string) {
  if (!isNative) {
    if (navigator.share) await navigator.share({ title, text, url });
    return;
  }
  await Share.share({ title, text, url });
}

export async function copyToClipboard(text: string) {
  if (!isNative) {
    await navigator.clipboard.writeText(text);
    return;
  }
  await Clipboard.write({ string: text });
}

export async function saveFile(filename: string, data: string) {
  if (!isNative) {
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    return;
  }
  await Filesystem.writeFile({
    path: filename,
    data,
    directory: Directory.Documents,
  });
}

export async function registerPushNotifications() {
  if (!isNative) return;
  try {
    const permResult = await PushNotifications.requestPermissions();
    if (permResult.receive === 'granted') {
      await PushNotifications.register();
    }
  } catch (err) {
    console.warn('[Nebula Mobile] Push registration failed:', err);
  }
}

export async function getNetworkStatus() {
  if (!isNative) return { connected: navigator.onLine, connectionType: 'unknown' };
  const status = await Network.getStatus();
  return { connected: status.connected, connectionType: status.connectionType };
}
