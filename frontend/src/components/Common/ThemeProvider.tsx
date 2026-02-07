/**
 * Theme Provider Component
 *
 * Initializes and manages theme application
 */

import React, { useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { getLightThemeCSSVariables } from '@/theme/light';
import { getDarkThemeCSSVariables } from '@/theme/dark';

/**
 * Theme Provider Props
 */
export interface ThemeProviderProps {
  children: React.ReactNode;
}

/**
 * Theme Provider Component
 *
 * Applies theme CSS variables to the document and handles theme initialization
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const { theme } = useAppStore();

  useEffect(() => {
    // Apply theme to document
    const applyTheme = () => {
      const root = document.documentElement;

      // Set data-theme attribute
      root.setAttribute('data-theme', theme);

      // Get CSS variables based on theme
      const cssVariables =
        theme === 'dark'
          ? getDarkThemeCSSVariables()
          : getLightThemeCSSVariables();

      // Apply CSS variables to root
      Object.entries(cssVariables).forEach(([key, value]) => {
        root.style.setProperty(key, value);
      });

      // Apply theme class to body for component-specific styling
      document.body.className = document.body.className
        .replace(/theme-\w+/g, '')
        .trim();
      document.body.classList.add(`theme-${theme}`);
    };

    applyTheme();

    // Listen for system theme changes if needed
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = (e: MediaQueryListEvent) => {
      const useSystemPreference = useAppStore.getState().useSystemPreference;
      if (useSystemPreference) {
        useAppStore.getState().setTheme(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleSystemThemeChange);

    return () => {
      mediaQuery.removeEventListener('change', handleSystemThemeChange);
    };
  }, [theme]);

  return <>{children}</>;
};

export default ThemeProvider;
