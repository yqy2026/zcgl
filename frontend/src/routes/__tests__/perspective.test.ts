import { describe, expect, it } from 'vitest';
import { getRoutePerspective, isPerspectiveRoute } from '../perspective';

describe('route perspective resolution', () => {
  it('maps owner-prefixed paths to owner', () => {
    expect(getRoutePerspective('/owner/assets')).toBe('owner');
    expect(getRoutePerspective('/owner/property-certificates/cert-1')).toBe('owner');
  });

  it('maps manager-prefixed paths to manager', () => {
    expect(getRoutePerspective('/manager/projects')).toBe('manager');
    expect(getRoutePerspective('/manager/contract-groups/group-1')).toBe('manager');
  });

  it('returns null for shared and legacy paths', () => {
    expect(getRoutePerspective('/dashboard')).toBeNull();
    expect(getRoutePerspective('/assets/list')).toBeNull();
    expect(getRoutePerspective('/project')).toBeNull();
  });

  it('reports whether the pathname is a canonical perspective route', () => {
    expect(isPerspectiveRoute('/owner/assets')).toBe(true);
    expect(isPerspectiveRoute('/manager/projects')).toBe(true);
    expect(isPerspectiveRoute('/assets/list')).toBe(false);
  });
});
