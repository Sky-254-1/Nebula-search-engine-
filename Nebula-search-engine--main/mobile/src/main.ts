import { initMobileShell } from './app';
import { config } from './config';

async function startup() {
  const start = Date.now();
  try {
    await initMobileShell();
    console.log(`[Nebula Mobile] Initialized in ${Date.now() - start}ms`);
  } catch (err) {
    console.error('[Nebula Mobile] Startup failed:', err);
  }
  if (Date.now() - start > config.startupTimeoutMs) {
    console.warn('[Nebula Mobile] Startup exceeded 2s threshold');
  }
}
document.addEventListener('DOMContentLoaded', startup);
