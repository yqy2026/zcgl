import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const currentFilePath = fileURLToPath(import.meta.url);
const currentDir = resolve(currentFilePath, '..');
const systemPagesDir = resolve(currentDir, '..');

const readSystemPageFile = (relativePath: string): string =>
  readFileSync(resolve(systemPagesDir, relativePath), 'utf8');

describe('System active page data fetching boundaries', () => {
  const activePages = [
    {
      name: 'UserManagement',
      page: 'UserManagement/index.tsx',
      hook: 'UserManagement/hooks/useUserManagementData.ts',
      forbiddenPageCalls: [
        'userService.getUsers(',
        'userService.getUserStatistics(',
        'organizationService.getOrganizations(',
        'roleService.getRoles(',
      ],
    },
    {
      name: 'RoleManagement',
      page: 'RoleManagement/index.tsx',
      hook: 'RoleManagement/hooks/useRoleManagementData.ts',
      forbiddenPageCalls: [
        'roleService.getRoles(',
        'roleService.getPermissions(',
        'roleService.getRoleStatistics(',
      ],
    },
    {
      name: 'Organization',
      page: 'Organization/index.tsx',
      hook: 'Organization/hooks/useOrganizationData.ts',
      forbiddenPageCalls: [
        'organizationService.getOrganizations(',
        'organizationService.searchOrganizations(',
        'organizationService.getOrganizationTree(',
        'organizationService.getStatistics(',
        'organizationService.getOrganizationHistory(',
      ],
    },
    {
      name: 'OperationLog',
      page: 'OperationLog/index.tsx',
      hook: 'OperationLog/hooks/useOperationLogData.ts',
      forbiddenPageCalls: ['logService.getLogs('],
    },
  ];

  it.each(activePages)(
    '$name fetches server data through its React Query hook',
    ({ page, hook, forbiddenPageCalls }) => {
      const pageSource = readSystemPageFile(page);
      const hookSource = readSystemPageFile(hook);

      expect(hookSource).toMatch(/from\s+["']@tanstack\/react-query["']/);
      expect(hookSource).toContain('useQuery');

      for (const forbiddenCall of forbiddenPageCalls) {
        expect(pageSource).not.toContain(forbiddenCall);
      }
    }
  );
});
