export * from './src/services/pdfImportService';
export { default as useMessage } from './src/hooks/useMessage';
export { UnifiedDictionaryService } from './src/services/dictionary';
export * from './src/types/asset';

// Ambient declaration for process.env to satisfy type parsing in constants
declare const process: { env: Record<string, string | undefined> };
