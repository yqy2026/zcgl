import { useLocation } from 'react-router-dom';
import type { Perspective } from '@/types/capability';

export type RoutePerspective = Extract<Perspective, 'owner' | 'manager'> | null;

export const getRoutePerspective = (pathname: string): RoutePerspective => {
  if (pathname.startsWith('/owner/')) {
    return 'owner';
  }

  if (pathname.startsWith('/manager/')) {
    return 'manager';
  }

  return null;
};

export const isPerspectiveRoute = (pathname: string): boolean => {
  return getRoutePerspective(pathname) != null;
};

export const useRoutePerspective = (): {
  perspective: RoutePerspective;
  isPerspectiveRoute: boolean;
} => {
  const location = useLocation();
  const perspective = getRoutePerspective(location.pathname);

  return {
    perspective,
    isPerspectiveRoute: perspective != null,
  };
};
