import { create } from 'zustand';

function loadPrefs() {
  try {
    const raw = localStorage.getItem('nebula_prefs');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function savePrefs(prefs) {
  localStorage.setItem('nebula_prefs', JSON.stringify(prefs));
}

const initial = loadPrefs();

export const useAppStore = create((set, get) => ({
  theme: initial?.theme || 'dark',
  sidebarOpen: true,
  sidebarCollapsed: false,
  notifications: [],
  preferences: {
    language: initial?.language || 'en',
    reducedMotion: initial?.reducedMotion || false,
    fontSize: initial?.fontSize || 'normal',
    ...initial,
  },

  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark';
    document.body.dataset.theme = next;
    set({ theme: next });
    savePrefs({ ...get().preferences, theme: next });
  },

  setTheme: (theme) => {
    document.body.dataset.theme = theme;
    set({ theme });
    savePrefs({ ...get().preferences, theme });
  },

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  addNotification: (notification) =>
    set((s) => ({
      notifications: [
        ...s.notifications,
        { id: Date.now(), timestamp: Date.now(), read: false, ...notification },
      ],
    })),
  dismissNotification: (id) =>
    set((s) => ({
      notifications: s.notifications.filter((n) => n.id !== id),
    })),
  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
    })),

  updatePreferences: (prefs) => {
    const next = { ...get().preferences, ...prefs };
    set({ preferences: next });
    savePrefs(next);
  },
}));
