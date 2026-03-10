const API_PREFIX = '/api/v1';
const LEGACY_CONTRACT_RESOURCE_SEGMENT = ['rental', 'contracts'].join('-');
const LEGACY_RENTAL_BASE_PATH = ['', 'rental', 'contracts'].join('/');

export const LEGACY_CONTRACT_EXCEL_IMPORT_API = [
  API_PREFIX,
  LEGACY_CONTRACT_RESOURCE_SEGMENT,
  'excel',
  'import',
].join('/');

export const buildLegacyContractWorkbookFilename = (contractNumber: string): string =>
  `${['rent', 'contract'].join('_')}_${contractNumber}.xlsx`;

export const LEGACY_CONTRACT_ROUTES = {
  LIST: LEGACY_RENTAL_BASE_PATH,
  PDF_IMPORT: `${LEGACY_RENTAL_BASE_PATH}/pdf-import`,
} as const;

export const legacyContractRoutePattern = (path: string): RegExp =>
  new RegExp(path.replaceAll('/', '\\/'));
