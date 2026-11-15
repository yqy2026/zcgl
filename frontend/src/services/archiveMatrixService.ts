import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { AssetOperationsError } from '@/services/assetOperationsService';
export interface ArchiveCategory {
  document_type: string;
  label: string;
  supported: boolean;
  required: number | null;
  existing: number | null;
  missing: number | null;
  completion_rate: number | null;
}
export interface ArchiveMissingItem {
  document_type: string;
  target_type: string;
  target_id: string;
  label: string;
  href: string;
}
export interface ArchiveMatrixRow {
  unit_id: string;
  unit_code: string;
  unit_name: string;
  categories: ArchiveCategory[];
  missing_items: ArchiveMissingItem[];
}
export interface ArchiveCompletion {
  as_of: string;
  categories: ArchiveCategory[];
  unlinked_unit_count: number;
}
export interface ArchiveMatrix {
  as_of: string;
  items: ArchiveMatrixRow[];
  total: number;
}
export interface ArchiveFilters {
  project_id?: string;
  q?: string;
  offset?: number;
  limit?: number;
  as_of?: string;
}
async function read<T>(path: string, params: ArchiveFilters): Promise<T> {
  try {
    const response = await apiClient.get<T>(path, { params, cache: false });
    if (!response.success || response.data == null)
      throw new AssetOperationsError('档案统计加载失败，请重新加载。', 'ARCHIVE_READ_FAILED');
    return response.data;
  } catch (error) {
    if (error instanceof AssetOperationsError) throw error;
    const enhanced = ApiErrorHandler.handleError(error);
    const original = isAxiosError(error) ? error : enhanced.originalError;
    const code = isAxiosError<{ error?: { code?: string } }>(original)
      ? original.response?.data.error?.code
      : undefined;
    throw new AssetOperationsError('档案统计加载失败，请重新加载。', code ?? enhanced.code);
  }
}
export const archiveMatrixService = {
  completion: (params: ArchiveFilters) =>
    read<ArchiveCompletion>('/api/v1/archive/completion', params),
  matrix: (params: ArchiveFilters) => read<ArchiveMatrix>('/api/v1/archive/matrix', params),
};
