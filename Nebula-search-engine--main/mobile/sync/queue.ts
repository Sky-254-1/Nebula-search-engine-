import { Preferences } from '@capacitor/preferences';
import { Network } from '@capacitor/network';
import { config } from '../src/config';

export interface SyncJob {
  id: string;
  type: 'upload' | 'search' | 'export' | 'bookmark' | 'settings';
  payload: Record<string, unknown>;
  createdAt: string;
  retries?: number;
  maxRetries?: number;
}

export async function enqueueJob(job: Omit<SyncJob, 'createdAt' | 'retries' | 'maxRetries'>) {
  const queue = await getQueue();
  queue.push({
    ...job,
    createdAt: new Date().toISOString(),
    retries: 0,
    maxRetries: 3,
  });
  await Preferences.set({ key: config.syncQueueKey, value: JSON.stringify(queue) });
  return queue.length;
}

export async function getQueue(): Promise<SyncJob[]> {
  const { value } = await Preferences.get({ key: config.syncQueueKey });
  return value ? JSON.parse(value) : [];
}

export async function flushQueue(apiBase: string, token: string) {
  const queue = await getQueue();
  if (queue.length === 0) return;

  const status = await Network.getStatus();
  if (!status.connected) {
    console.log('[Nebula Sync] Offline, deferring sync');
    return;
  }

  const remaining: SyncJob[] = [];
  for (const job of queue) {
    try {
      if (job.retries && job.retries >= (job.maxRetries || 3)) {
        console.warn(`[Nebula Sync] Dropping job ${job.id} after max retries`);
        continue;
      }
      switch (job.type) {
        case 'search':
          await fetch(
            `${apiBase}/api/v1/search/web?${new URLSearchParams(job.payload as Record<string, string>)}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          break;
        case 'bookmark':
          await fetch(`${apiBase}/api/v1/storage/bookmarks`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(job.payload),
          });
          break;
        case 'upload':
          await fetch(`${apiBase}/api/v1/storage/documents`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: JSON.stringify(job.payload),
          });
          break;
        case 'export':
          await fetch(`${apiBase}/api/v1/storage/exports`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(job.payload),
          });
          break;
      }
    } catch (err) {
      console.warn(`[Nebula Sync] Failed job ${job.id}:`, err);
      remaining.push({ ...job, retries: (job.retries || 0) + 1 });
    }
  }
  await Preferences.set({ key: config.syncQueueKey, value: JSON.stringify(remaining) });
  return remaining.length;
}

export async function clearQueue() {
  await Preferences.remove({ key: config.syncQueueKey });
}
