import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ACTIVE_FRONTEND_RUNTIME_FILES = [
  'src/constants/api.ts',
  'src/constants/routes.ts',
  'src/routes/AppRoutes.tsx',
  'src/pages/Rental/LegacyRentalRetiredPage.tsx',
  'src/pages/Ownership/OwnershipDetailPage.tsx',
  'src/services/apiHealthCheck.ts',
  'src/config/menuConfig.tsx',
  'src/config/breadcrumb.ts',
  'src/hooks/useSmartPreload.tsx',
  'src/pages/System/NotificationCenter.tsx',
  'src/pages/System/TemplateManagementPage.tsx',
  'src/components/index.ts',
] as const;

const LEGACY_TOKENS = [
  'rentContractService',
  'rentContractExcelService',
  'RENT_CONTRACT_API',
  '/rental-contracts/',
] as const;

describe('frontend legacy contract hygiene', () => {
  it('keeps active runtime files free of legacy contract tokens', () => {
    for (const relativePath of ACTIVE_FRONTEND_RUNTIME_FILES) {
      const source = readFileSync(resolve(process.cwd(), relativePath), 'utf8');

      for (const token of LEGACY_TOKENS) {
        expect(source).not.toContain(token);
      }
    }
  });
});
