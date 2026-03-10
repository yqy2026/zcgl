import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { CONTRACT_GROUP_ROUTES, LEGACY_RENTAL_ROUTES } from '@/constants/routes';
import { protectedRoutes } from '@/routes/AppRoutes';
import LegacyRentalRetiredPage from '@/pages/Rental/LegacyRentalRetiredPage';

const LocationProbe = () => {
  const location = useLocation();
  return <div data-testid="location-probe">{location.pathname}</div>;
};

describe('legacy rental frontend retirement routing', () => {
  it('keeps non-import /rental routes mapped to the retired page component', () => {
    const retiredRentalRoutes = protectedRoutes.filter(
      route =>
        route.path.startsWith('/rental/') && route.path !== LEGACY_RENTAL_ROUTES.CONTRACTS.PDF_IMPORT
    );

    expect(retiredRentalRoutes.length).toBeGreaterThan(0);
    expect(new Set(retiredRentalRoutes.map(route => route.element)).size).toBe(1);
  });

  it('redirects the legacy pdf import route to the new contract-group import page', () => {
    const redirectRoute = protectedRoutes.find(
      route => route.path === LEGACY_RENTAL_ROUTES.CONTRACTS.PDF_IMPORT
    );

    expect(redirectRoute).toBeDefined();
    const RedirectElement = redirectRoute?.element;
    expect(RedirectElement).toBeDefined();

    render(
      <MemoryRouter initialEntries={[LEGACY_RENTAL_ROUTES.CONTRACTS.PDF_IMPORT]}>
        {RedirectElement != null && <RedirectElement />}
        <LocationProbe />
      </MemoryRouter>
    );

    expect(screen.getByTestId('location-probe')).toHaveTextContent(CONTRACT_GROUP_ROUTES.IMPORT);
  });

  it('renders an explicit retirement notice instead of calling deleted legacy APIs', () => {
    render(
      <MemoryRouter>
        <LegacyRentalRetiredPage />
      </MemoryRouter>
    );

    expect(screen.getAllByText('租赁前端模块已退休')).toHaveLength(2);
    expect(
      screen.getByText(/合同组与台账前端正在切换到新 contract\/contract-group 体系/)
    ).toBeInTheDocument();
    expect(screen.getByText('当前状态')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '查看合同组' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'PDF导入' })).toBeInTheDocument();
  });

  it('does not keep raw legacy rental-contracts tokens in active retirement page source', () => {
    const source = resolve(process.cwd(), 'src/pages/Rental/LegacyRentalRetiredPage.tsx');

    expect(existsSync(source)).toBe(true);
    expect(readFileSync(source, 'utf8')).not.toContain('/rental-contracts/');
  });

  it('retires the legacy rental list page and hook modules from disk', () => {
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractListPage.tsx'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/hooks/useContractList.ts'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/components/Rental/RentContractExcelImport.tsx'))).toBe(
      false
    );
    expect(existsSync(resolve(process.cwd(), 'src/services/rentContractExcelService.ts'))).toBe(
      false
    );
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/ContractList/ContractFilterBar.tsx'))
    ).toBe(false);
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/ContractList/ContractStatsCards.tsx'))
    ).toBe(false);
    expect(
      existsSync(resolve(process.cwd(), 'src/components/Rental/ContractList/ContractTable.tsx'))
    ).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/RentStatisticsPage.tsx'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/RentLedgerPage.tsx'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractCreatePage.tsx'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractRenewPage.tsx'))).toBe(false);
    expect(existsSync(resolve(process.cwd(), 'src/pages/Rental/ContractDetailPage.tsx'))).toBe(false);
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
