import type { ThemeTokens } from '@/types/theme';

type SharedScaleTokens = Pick<ThemeTokens, 'spacing' | 'fontSize' | 'borderRadius'>;

export const sharedScaleTokens: SharedScaleTokens = {
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    xxl: '2rem',
  },
  fontSize: {
    xs: '0.75rem',
    sm: '0.8125rem',
    base: '0.875rem',
    lg: '1rem',
    xl: '1.125rem',
    xxl: '1.25rem',
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
  },
};
