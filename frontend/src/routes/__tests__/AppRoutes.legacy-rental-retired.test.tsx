import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { protectedRoutes } from '@/routes/AppRoutes';

describe('legacy rental frontend removal', () => {
  it('does not keep any protected /rental routes', () => {
    const legacyRentalRoutes = protectedRoutes.filter(route => route.path.startsWith('/rental'));

    expect(legacyRentalRoutes).toEqual([]);
  });

  it('does not keep legacy owner/manager prefixed business routes in protectedRoutes', () => {
    const legacyScopedRoutes = protectedRoutes.filter(
      route => route.path.startsWith('/owner/') || route.path.startsWith('/manager/')
    );

    expect(legacyScopedRoutes).toEqual([]);
  });

  it('registers legacy list aliases before dynamic detail routes as canonical redirects', () => {
    const protectedRoutePaths = protectedRoutes.map(route => route.path);
    const contractListAliasIndex = protectedRoutePaths.indexOf('/contract-center/list');
    const contractDetailIndex = protectedRoutePaths.indexOf('/contract-center/:id');
    const projectListAliasIndex = protectedRoutePaths.indexOf('/project/list');
    const projectDetailIndex = protectedRoutePaths.indexOf('/project/:id');

    expect(contractListAliasIndex).toBeGreaterThanOrEqual(0);
    expect(projectListAliasIndex).toBeGreaterThanOrEqual(0);
    expect(contractListAliasIndex).toBeLessThan(contractDetailIndex);
    expect(projectListAliasIndex).toBeLessThan(projectDetailIndex);
  });

  it('removes the legacy rental retired page from disk', () => {
    const source = resolve(process.cwd(), 'src/pages/Rental/LegacyRentalRetiredPage.tsx');

    expect(existsSync(source)).toBe(false);
  });

  it('retires the legacy rental list page and hook modules from disk', () => {
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractListPage.tsx'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/hooks/useContractList.ts'))).toBe(false);
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/RentContractExcelImport.tsx'))
    ).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/services/rentContractExcelService.ts'))).toBe(
      false
    );
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/ContractList/ContractFilterBar.tsx'))
    ).toBe(false);
    expect(
      existsSync(
        resolve(process.cwd(), 'src/components/Rental/ContractList/ContractStatsCards.tsx')
      )
    ).toBe(false);
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/ContractList/ContractTable.tsx'))
    ).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/RentStatisticsPage.tsx'))).toBe(
      false
    );
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/RentLedgerPage.tsx'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractCreatePage.tsx'))).toBe(
      false
    );
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractRenewPage.tsx'))).toBe(
      false
    );
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractDetailPage.tsx'))).toBe(
      false
    );
    expect(existsSync(resolve(process.cwd(), 'src/components/Rental/ContractDetailInfo.tsx'))).toBe(
      false
    );
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/DepositLedgerHistory.tsx'))
    ).toBe(false);
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/ServiceFeeLedgerTable.tsx'))
    ).toBe(false);
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/ContractTerminateModal.tsx'))
    ).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/services/rentContractService.ts'))).toBe(false);
  });
});
