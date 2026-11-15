/**
 * Import Service
 * 资产运营 v5 V4：三表导入批次（模板下载、扫描件暂存、上传校验、差异选择、提交与撤销）。
 */

import { isAxiosError } from 'axios';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';

const API_BASE = '/api/v1';

export interface ImportBatchStatus {
  id: string;
  mode: 'create' | 'update';
  status: 'uploaded' | 'validating' | 'invalid' | 'ready' | 'committed' | 'reverted';
  template_version: string;
  row_count: number;
  valid_count: number;
  error_count: number;
  warning_count: number;
  proposal_hash: string | null;
  version: number;
  committed_at: string | null;
  reverted_at: string | null;
}

export interface ImportBatchChange {
  id: string;
  sheet_name: string;
  row_number: number;
  target_type: 'asset_unit' | 'upstream_contract' | 'terminal_contract';
  target_key: string;
  field_name: string;
  old_value: { value?: string } | null;
  new_value: { value?: string } | null;
  selected: boolean;
  severity: 'change' | 'warning' | 'error';
  effect_summary: string;
}

export interface ImportChangePage {
  items: ImportBatchChange[];
  total: number;
}

export interface ImportCommitPreview {
  batch_id: string;
  change_count: number;
  warning_count: number;
  proposal_hash: string;
  commit_token: string;
  expires_at: string;
}

export interface ImportRevertPreview {
  batch_id: string;
  deadline: string;
  blockers: Array<{ type: string; count: string }>;
  revert_token: string;
}

/** 带稳定 code 的导入错误；页面按 code 显示恢复提示。 */
export class ImportError extends Error {
  readonly code: string;

  constructor(message: string, code: string) {
    super(message);
    this.name = 'ImportError';
    this.code = code;
  }
}

const ERROR_TEXT: Record<string, string> = {
  IMPORT_FILE_INVALID: '工作簿无法解析：表头、工作表或模板版本不符',
  IMPORT_HAS_ERRORS: '批次存在错误，修正后重新上传',
  IMPORT_PROPOSAL_CHANGED: '批次内容已变化，请重新预览',
  IMPORT_PREVIEW_EXPIRED: '预览已过期，请重新预览',
  IMPORT_BATCH_STATE_INVALID: '批次状态不允许该操作',
  IMPORT_REVERT_WINDOW_EXPIRED: '撤销窗口已过（七个自然日）',
  IMPORT_REVERT_DEPENDENCY_CONFLICT: '对象存在后继依赖，拒绝撤销',
};

const fail: (prefix: string, error: unknown) => never = (prefix, error) => {
  if (error instanceof ImportError) {
    throw error;
  }
  const enhanced = ApiErrorHandler.handleError(error);
  const original = isAxiosError(error) ? error : enhanced.originalError;
  let code = enhanced.code;
  if (isAxiosError<{ error?: { code?: unknown } }>(original)) {
    const raw = original.response?.data?.error?.code;
    if (typeof raw === 'string' && raw !== '') {
      code = raw;
    }
  }
  throw new ImportError(`${prefix}: ${ERROR_TEXT[code] ?? enhanced.message}`, code);
};

type FailedResult = {
  rawResponse?: { data?: { error?: { code?: unknown } } };
};

function extractErrorCode(result: { success: boolean } & FailedResult): string {
  const raw = result.rawResponse?.data?.error?.code;
  return typeof raw === 'string' ? raw : 'UNKNOWN';
}

export const importService = {
  async downloadCreateTemplate(): Promise<Blob> {
    const response = await apiClient.get<Blob>(`${API_BASE}/imports/templates/create`, {
      responseType: 'blob',
      smartExtract: false,
    });
    if (!response.success) {
      throw new ImportError('模板下载失败', extractErrorCode(response));
    }
    return response.data as Blob;
  },

  async stageScanFiles(files: File[]): Promise<Array<{ id: string; file_name: string }>> {
    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append('files', file);
      }
      const result = await apiClient.post<{
        files: Array<{ id: string; file_name: string }>;
      }>(`${API_BASE}/import-batches/scan-staging`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        retry: false,
      });
      if (!result.success) {
        throw new ImportError('扫描件暂存失败', extractErrorCode(result));
      }
      return result.data?.files ?? [];
    } catch (error) {
      fail('扫描件暂存失败', error);
    }
  },

  async uploadBatch(
    mode: 'create' | 'update',
    file: File,
    idempotencyKey: string
  ): Promise<ImportBatchStatus> {
    try {
      const formData = new FormData();
      formData.append('mode', mode);
      formData.append('file', file);
      const result = await apiClient.post<ImportBatchStatus>(
        `${API_BASE}/import-batches`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Idempotency-Key': idempotencyKey,
          },
          retry: false,
        }
      );
      if (!result.success) {
        throw new ImportError('批次上传失败', extractErrorCode(result));
      }
      return result.data as ImportBatchStatus;
    } catch (error) {
      fail('批次上传失败', error);
    }
  },

  async getBatch(batchId: string): Promise<ImportBatchStatus> {
    try {
      const result = await apiClient.get<ImportBatchStatus>(
        `${API_BASE}/import-batches/${batchId}`,
        { cache: false }
      );
      if (!result.success) {
        throw new ImportError('批次读取失败', extractErrorCode(result));
      }
      return result.data as ImportBatchStatus;
    } catch (error) {
      fail('批次读取失败', error);
    }
  },

  async listChanges(
    batchId: string,
    params: { severity?: string; offset?: number; limit?: number }
  ): Promise<ImportChangePage> {
    try {
      const result = await apiClient.get<ImportChangePage>(
        `${API_BASE}/import-batches/${batchId}/changes`,
        { params, cache: false }
      );
      if (!result.success) {
        throw new ImportError('差异读取失败', extractErrorCode(result));
      }
      return result.data ?? { items: [], total: 0 };
    } catch (error) {
      fail('差异读取失败', error);
    }
  },

  async updateSelection(
    batchId: string,
    selections: Record<string, boolean>
  ): Promise<ImportBatchStatus> {
    try {
      const result = await apiClient.put<ImportBatchStatus>(
        `${API_BASE}/import-batches/${batchId}/selection`,
        { selections }
      );
      if (!result.success) {
        throw new ImportError('选择更新失败', extractErrorCode(result));
      }
      return result.data as ImportBatchStatus;
    } catch (error) {
      fail('选择更新失败', error);
    }
  },

  async commitPreview(batchId: string): Promise<ImportCommitPreview> {
    try {
      const result = await apiClient.post<ImportCommitPreview>(
        `${API_BASE}/import-batches/${batchId}/commit-preview`
      );
      if (!result.success) {
        throw new ImportError('提交预览失败', extractErrorCode(result));
      }
      return result.data as ImportCommitPreview;
    } catch (error) {
      fail('提交预览失败', error);
    }
  },

  async commit(
    batchId: string,
    payload: {
      commit_token: string;
      expected_version: number;
      proposal_hash: string;
      idempotency_key: string;
    }
  ): Promise<{ batch_id: string; status: string; idempotent: boolean }> {
    try {
      const result = await apiClient.post<{
        batch_id: string;
        status: string;
        idempotent: boolean;
      }>(`${API_BASE}/import-batches/${batchId}/commit`, payload, {
        headers: { 'Idempotency-Key': payload.idempotency_key },
        retry: false,
      });
      if (!result.success) {
        throw new ImportError('提交失败', extractErrorCode(result));
      }
      return result.data as {
        batch_id: string;
        status: string;
        idempotent: boolean;
      };
    } catch (error) {
      fail('提交失败', error);
    }
  },

  async revertPreview(batchId: string): Promise<ImportRevertPreview> {
    try {
      const result = await apiClient.post<ImportRevertPreview>(
        `${API_BASE}/import-batches/${batchId}/revert-preview`
      );
      if (!result.success) {
        throw new ImportError('撤销预览失败', extractErrorCode(result));
      }
      return result.data as ImportRevertPreview;
    } catch (error) {
      fail('撤销预览失败', error);
    }
  },

  async revert(
    batchId: string,
    payload: { revert_token: string; reason: string; idempotency_key: string }
  ): Promise<{ batch_id: string; status: string; idempotent: boolean }> {
    try {
      const result = await apiClient.post<{
        batch_id: string;
        status: string;
        idempotent: boolean;
      }>(`${API_BASE}/import-batches/${batchId}/revert`, payload, {
        headers: { 'Idempotency-Key': payload.idempotency_key },
        retry: false,
      });
      if (!result.success) {
        throw new ImportError('撤销失败', extractErrorCode(result));
      }
      return result.data as {
        batch_id: string;
        status: string;
        idempotent: boolean;
      };
    } catch (error) {
      fail('撤销失败', error);
    }
  },
};
