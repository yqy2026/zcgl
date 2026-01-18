/**
 * Property Certificate Service
 * 产权证服务
 */

import { enhancedApiClient } from '@/api/client';
import type {
  PropertyCertificate,
  PropertyCertificateCreate,
  PropertyCertificateUpdate,
  CertificateExtractionResult,
  CertificateImportConfirm,
} from '@/types/propertyCertificate';

export const propertyCertificateService = {
  /**
   * Upload and extract certificate from file
   */
  async uploadCertificate(file: File): Promise<CertificateExtractionResult> {
    const formData = new FormData();
    formData.append('file', file);

    const result = await enhancedApiClient.post<CertificateExtractionResult>(
      '/property-certificates/upload',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    if (result.data == null) {
      throw new Error('Failed to upload certificate');
    }
    return result.data;
  },

  /**
   * Confirm import and create certificate
   */
  async confirmImport(
    confirmData: CertificateImportConfirm
  ): Promise<{ certificate_id: string; status: string }> {
    const result = await enhancedApiClient.post<{ certificate_id: string; status: string }>(
      '/property-certificates/confirm-import',
      confirmData
    );
    if (result.data == null) {
      throw new Error('Failed to confirm import');
    }
    return result.data;
  },

  /**
   * List certificates
   */
  async listCertificates(params?: {
    skip?: number;
    limit?: number;
  }): Promise<PropertyCertificate[]> {
    const result = await enhancedApiClient.get<PropertyCertificate[]>('/property-certificates/', {
      params,
    });
    return result.data ?? [];
  },

  /**
   * Get certificate by ID
   */
  async getCertificate(id: string): Promise<PropertyCertificate> {
    const result = await enhancedApiClient.get<PropertyCertificate>(`/property-certificates/${id}`);
    if (result.data == null) {
      throw new Error('Certificate not found');
    }
    return result.data;
  },

  /**
   * Create certificate manually
   */
  async createCertificate(certificate: PropertyCertificateCreate): Promise<PropertyCertificate> {
    const result = await enhancedApiClient.post<PropertyCertificate>(
      '/property-certificates/',
      certificate
    );
    if (result.data == null) {
      throw new Error('Failed to create certificate');
    }
    return result.data;
  },

  /**
   * Update certificate
   */
  async updateCertificate(
    id: string,
    certificate: PropertyCertificateUpdate
  ): Promise<PropertyCertificate> {
    const result = await enhancedApiClient.put<PropertyCertificate>(
      `/property-certificates/${id}`,
      certificate
    );
    if (result.data == null) {
      throw new Error('Failed to update certificate');
    }
    return result.data;
  },

  /**
   * Delete certificate
   */
  async deleteCertificate(id: string): Promise<{ status: string }> {
    const result = await enhancedApiClient.delete<{ status: string }>(
      `/property-certificates/${id}`
    );
    if (result.data == null) {
      throw new Error('Failed to delete certificate');
    }
    return result.data;
  },
};
