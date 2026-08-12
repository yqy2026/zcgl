/**
 * Property Certificate Service
 * 产权证服务
 */

import { apiClient } from '@/api/client';
import type {
  PropertyCertificate,
  PropertyCertificateCreate,
  PropertyCertificateListParams,
  PropertyCertificateUpdate,
} from '@/types/propertyCertificate';

export const propertyCertificateService = {
  /**
   * List certificates
   */
  async listCertificates(
    params?: PropertyCertificateListParams
  ): Promise<PropertyCertificate[]> {
    const result = await apiClient.get<PropertyCertificate[]>('/property-certificates', {
      params: params,
    });
    return result.data ?? [];
  },

  /**
   * Get certificate by ID
   */
  async getCertificate(id: string): Promise<PropertyCertificate> {
    const result = await apiClient.get<PropertyCertificate>(`/property-certificates/${id}`);
    if (result.data == null) {
      throw new Error('Certificate not found');
    }
    return result.data;
  },

  /**
   * Create certificate manually
   */
  async createCertificate(certificate: PropertyCertificateCreate): Promise<PropertyCertificate> {
    const result = await apiClient.post<PropertyCertificate>(
      '/property-certificates',
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
    const result = await apiClient.put<PropertyCertificate>(
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
    const result = await apiClient.delete<{ status: string }>(`/property-certificates/${id}`);
    if (result.data == null) {
      throw new Error('Failed to delete certificate');
    }
    return result.data;
  },
};
