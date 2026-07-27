import { apiClient } from '@/api/client';
import { createApiUrl } from '@/api/config';

export interface PropertyCertificateAttachment {
  id: string;
  file_name: string;
  file_type: 'pdf' | 'jpg' | 'jpeg' | 'png';
  file_size: number;
  created_at: string;
}

export interface PropertyCertificateAttachmentAppendResult {
  file_name: string;
  attachment?: PropertyCertificateAttachment;
  error?: string;
}

const basePath = (certificateId: string) => `/property-certificates/${certificateId}/attachments`;

export const propertyCertificateAttachmentService = {
  async list(certificateId: string): Promise<PropertyCertificateAttachment[]> {
    const response = await apiClient.get<PropertyCertificateAttachment[]>(basePath(certificateId));
    return response.data ?? [];
  },

  async appendMany(
    certificateId: string,
    files: File[]
  ): Promise<PropertyCertificateAttachmentAppendResult[]> {
    const form = new FormData();
    for (const file of files) {
      form.append('files', file);
    }
    const response = await apiClient.post<{ results: PropertyCertificateAttachmentAppendResult[] }>(
      basePath(certificateId),
      form
    );
    if (response.data == null) {
      throw new Error('Empty property certificate attachment response');
    }
    return response.data.results;
  },

  async append(certificateId: string, file: File): Promise<PropertyCertificateAttachment> {
    const [result] = await this.appendMany(certificateId, [file]);
    if (result?.attachment == null) {
      throw new Error(result?.error ?? 'Property certificate attachment upload failed');
    }
    return result.attachment;
  },

  async replace(
    certificateId: string,
    attachmentId: string,
    file: File
  ): Promise<PropertyCertificateAttachment> {
    const form = new FormData();
    form.append('file', file);
    const response = await apiClient.put<PropertyCertificateAttachment>(
      `${basePath(certificateId)}/${attachmentId}`,
      form
    );
    if (response.data == null) {
      throw new Error('Empty property certificate attachment replacement response');
    }
    return response.data;
  },

  async remove(certificateId: string, attachmentId: string): Promise<void> {
    await apiClient.delete(`${basePath(certificateId)}/${attachmentId}`);
  },

  previewUrl(certificateId: string, attachmentId: string): string {
    return createApiUrl(`${basePath(certificateId)}/${attachmentId}/preview`);
  },

  downloadUrl(certificateId: string, attachmentId: string): string {
    return createApiUrl(`${basePath(certificateId)}/${attachmentId}/download`);
  },
};
