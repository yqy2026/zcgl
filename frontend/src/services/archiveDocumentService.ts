import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { AssetOperationsError } from '@/services/assetOperationsService';

export type ArchiveTargetType =
  | 'property_certificate'
  | 'contract_supplement'
  | 'contract_lifecycle_event'
  | 'upstream_contract'
  | 'terminal_contract'
  | 'management_fee_statement';

function documentTypeOf(targetType: ArchiveTargetType): string {
  if (targetType === 'contract_lifecycle_event') return 'handover';
  if (targetType === 'contract_supplement') return 'supplement';
  if (targetType === 'upstream_contract' || targetType === 'terminal_contract') {
    return targetType;
  }
  if (targetType === 'management_fee_statement') return 'management_fee_statement';
  return 'property_certificate';
}
export interface ArchiveDocument {
  id: string;
  attachment_id: string;
  document_type: string;
  target_type: string;
  target_id: string;
  file_name: string;
  content_type: string;
  file_size: number;
  document_version: number;
  replaces_document_id: string | null;
  uploaded_at: string;
  is_current: boolean;
}

export interface BatchMatchCandidate {
  target_type: 'upstream_contract' | 'terminal_contract';
  target_id: string;
  label: string;
}
export interface BatchMatchPreviewItem {
  staging_id: string;
  file_name: string;
  file_size: number;
  detected: BatchMatchCandidate | null;
  ambiguous: BatchMatchCandidate[];
  already_archived: boolean;
}
export interface BatchMatchPreview {
  preview_token: string;
  expires_at: string;
  items: BatchMatchPreviewItem[];
}
export interface BatchMatchSelection {
  staging_id: string;
  target_type: 'upstream_contract' | 'terminal_contract';
  target_id: string;
}
export const archiveDocumentService = {
  async upload(
    certificateId: string,
    file: File,
    targetType: ArchiveTargetType = 'property_certificate'
  ): Promise<ArchiveDocument> {
    const data = new FormData();
    data.append('target_type', targetType);
    data.append('target_id', certificateId);
    data.append('document_type', documentTypeOf(targetType));
    data.append('file', file);
    return writeDocument('/api/v1/archive/documents', data);
  },
  async replace(documentId: string, file: File): Promise<ArchiveDocument> {
    const data = new FormData();
    data.append('file', file);
    return writeDocument(
      `/api/v1/archive/documents/${encodeURIComponent(documentId)}/replacement`,
      data
    );
  },
  async list(
    certificateId: string,
    targetType: ArchiveTargetType = 'property_certificate'
  ): Promise<ArchiveDocument[]> {
    try {
      const result = await apiClient.get<{ items: ArchiveDocument[] }>(
        '/api/v1/archive/documents',
        {
          params: {
            target_type: targetType,
            target_id: certificateId,
            document_type: documentTypeOf(targetType),
            include_history: true,
          },
          cache: false,
        }
      );
      if (!result.success || result.data == null || !Array.isArray(result.data.items)) {
        throw new AssetOperationsError('档案加载失败，请重新加载。', 'ARCHIVE_READ_FAILED');
      }
      return result.data.items;
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      const enhanced = ApiErrorHandler.handleError(error);
      const original = isAxiosError(error) ? error : enhanced.originalError;
      const code = isAxiosError<{ error?: { code?: string } }>(original)
        ? original.response?.data.error?.code
        : undefined;
      throw new AssetOperationsError('档案加载失败，请重新加载。', code ?? enhanced.code);
    }
  },
  async previewBatchMatch(files: File[]): Promise<BatchMatchPreview> {
    const data = new FormData();
    for (const file of files) {
      data.append('files', file, file.name);
    }
    return writeDocument<BatchMatchPreview>('/api/v1/archive/batch-matches/preview', data);
  },
  async commitBatchMatch(
    previewToken: string,
    matches: BatchMatchSelection[]
  ): Promise<{ items: ArchiveDocument[] }> {
    try {
      const result = await apiClient.post<{ items: ArchiveDocument[] }>(
        '/api/v1/archive/batch-matches',
        { preview_token: previewToken, matches },
        { retry: false }
      );
      if (!result.success || result.data == null)
        throw new AssetOperationsError('批量配对提交失败，请重试。', 'ARCHIVE_WRITE_FAILED');
      return result.data;
    } catch (error) {
      if (error instanceof AssetOperationsError) throw error;
      const enhanced = ApiErrorHandler.handleError(error);
      const original = isAxiosError(error) ? error : enhanced.originalError;
      const code = isAxiosError<{ error?: { code?: string } }>(original)
        ? original.response?.data.error?.code
        : undefined;
      throw new AssetOperationsError(
        '批量配对提交失败，请检查所选目标后重试。',
        code ?? enhanced.code
      );
    }
  },
  async download(documentId: string): Promise<Blob> {
    try {
      const result = await apiClient
        .getAxiosInstance()
        .get<Blob>(`/api/v1/archive/documents/${encodeURIComponent(documentId)}/content`, {
          responseType: 'blob',
        });
      return result.data;
    } catch (error) {
      const enhanced = ApiErrorHandler.handleError(error);
      const original = isAxiosError(error) ? error : enhanced.originalError;
      if (isAxiosError(original)) {
        let data: unknown = original.response?.data;
        if (data instanceof Blob) {
          try {
            data = JSON.parse(await data.text()) as unknown;
          } catch {
            data = null;
          }
        }
        const body = data as { error?: { code?: string } } | null;
        throw new AssetOperationsError(
          '档案下载失败，请检查访问范围后重试。',
          body?.error?.code ?? enhanced.code
        );
      }
      throw new AssetOperationsError('档案下载失败，请重试。', enhanced.code);
    }
  },
};

async function writeDocument<T = ArchiveDocument>(url: string, data: FormData): Promise<T> {
  try {
    const result = await apiClient.post<T>(url, data, { retry: false });
    if (!result.success || result.data == null)
      throw new AssetOperationsError('档案保存失败，请重试。', 'ARCHIVE_WRITE_FAILED');
    return result.data;
  } catch (error) {
    if (error instanceof AssetOperationsError) throw error;
    const enhanced = ApiErrorHandler.handleError(error);
    const original = isAxiosError(error) ? error : enhanced.originalError;
    const code = isAxiosError<{ error?: { code?: string } }>(original)
      ? original.response?.data.error?.code
      : undefined;
    throw new AssetOperationsError('档案保存失败，请检查文件后重试。', code ?? enhanced.code);
  }
}
