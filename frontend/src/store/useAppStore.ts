import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { ThemeMode } from '@/types/theme';

// 通知ID计数器，确保唯一性
let notificationIdCounter = 0;
const generateNotificationId = (): string => {
  return `${Date.now()}-${++notificationIdCounter}`;
};

interface AppState {
  // 应用全局状态
  sidebarCollapsed: boolean;
  theme: ThemeMode;
  useSystemPreference: boolean;
  language: 'zh-CN' | 'en-US';

  // 用户偏好设置
  preferences: {
    pageSize: number;
    autoRefresh: boolean;
    showAdvancedSearch: boolean;
  };

  // 通知状态
  notifications: Notification[];

  // Actions
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  setUseSystemPreference: (useSystem: boolean) => void;
  setLanguage: (language: 'zh-CN' | 'en-US') => void;
  setPreferences: (preferences: Partial<AppState['preferences']>) => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  timestamp: number;
}

const initialState = {
  sidebarCollapsed: false,
  theme: 'light' as const,
  useSystemPreference: false,
  language: 'zh-CN' as const,
  preferences: {
    pageSize: 20,
    autoRefresh: false,
    showAdvancedSearch: false,
  },
  notifications: [],
};

/**
 * Get system theme preference
 */
const getSystemTheme = (): ThemeMode => {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const notificationTimers = new Map<string, ReturnType<typeof setTimeout>>();

const clearNotificationTimer = (id: string): void => {
  const timer = notificationTimers.get(id);
  if (timer) {
    clearTimeout(timer);
    notificationTimers.delete(id);
  }
};

const clearAllNotificationTimers = (): void => {
  notificationTimers.forEach(timer => {
    clearTimeout(timer);
  });
  notificationTimers.clear();
};

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        setSidebarCollapsed: collapsed => set({ sidebarCollapsed: collapsed }),

        setTheme: theme => {
          // Apply theme to document
          if (typeof document !== 'undefined') {
            document.documentElement.setAttribute('data-theme', theme);
          }
          set({ theme });
        },

        toggleTheme: () => {
          const currentTheme = get().theme;
          const newTheme: ThemeMode = currentTheme === 'light' ? 'dark' : 'light';
          get().setTheme(newTheme);
        },

        setUseSystemPreference: useSystem => {
          set({ useSystemPreference: useSystem });
          // If enabling system preference, immediately apply system theme
          if (useSystem) {
            const systemTheme = getSystemTheme();
            get().setTheme(systemTheme);
          }
        },

        setLanguage: language => set({ language }),

        setPreferences: preferences =>
          set(state => ({
            preferences: { ...state.preferences, ...preferences },
          })),

        addNotification: notification => {
          const id = generateNotificationId();
          const newNotification: Notification = {
            ...notification,
            id,
            timestamp: Date.now(),
          };

          set(state => {
            if (notification.duration !== 0) {
              const timerId = setTimeout(() => {
                get().removeNotification(id);
              }, notification.duration ?? 4500);
              notificationTimers.set(id, timerId);
            }

            return {
              notifications: [...state.notifications, newNotification],
            };
          });
        },

        removeNotification: id =>
          set(state => {
            clearNotificationTimer(id);

            return {
              notifications: state.notifications.filter(n => n.id !== id),
            };
          }),

        clearNotifications: () =>
          set(() => {
            clearAllNotificationTimers();

            return {
              notifications: [],
            };
          }),
      }),
      {
        name: 'app-store',
        partialize: state => ({
          sidebarCollapsed: state.sidebarCollapsed,
          theme: state.theme,
          useSystemPreference: state.useSystemPreference,
          language: state.language,
          preferences: state.preferences,
        }),
      }
    ),
    {
      name: 'app-store',
    }
  )
);
