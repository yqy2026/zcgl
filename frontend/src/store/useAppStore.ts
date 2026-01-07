import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// 通知ID计数器，确保唯一性
let notificationIdCounter = 0;
const generateNotificationId = (): string => {
  return `${Date.now()}-${++notificationIdCounter}`;
};

interface AppState {
  // 应用全局状态
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
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
  setTheme: (theme: 'light' | 'dark') => void;
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
  language: 'zh-CN' as const,
  preferences: {
    pageSize: 20,
    autoRefresh: false,
    showAdvancedSearch: false,
  },
  notifications: [],
};

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        setSidebarCollapsed: collapsed => set({ sidebarCollapsed: collapsed }),

        setTheme: theme => set({ theme }),

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

          set(state => ({
            notifications: [...state.notifications, newNotification],
          }));

          // 自动移除通知
          if (notification.duration !== 0) {
            setTimeout(
              () => {
                get().removeNotification(id);
              },
              notification.duration !== null && notification.duration !== undefined
                ? notification.duration
                : 4500
            );
          }
        },

        removeNotification: id =>
          set(state => ({
            notifications: state.notifications.filter(n => n.id !== id),
          })),

        clearNotifications: () => set({ notifications: [] }),
      }),
      {
        name: 'app-store',
        partialize: state => ({
          sidebarCollapsed: state.sidebarCollapsed,
          theme: state.theme,
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
