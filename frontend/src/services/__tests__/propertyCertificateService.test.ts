/**
 * Property Certificate Service 单元测试
 * 测试产权证服务的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { propertyCertificateService } from '../propertyCertificateService';

// =============================================================================
// Mock API client
// =============================================================================

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from '@/api/client';

// =============================================================================
// Test data
// =============================================================================

const mockCertificate = {
  id: 'cert-1',
  certificate_number: '京(2026)朝阳区不动产权第0001号',
  property_type: '商业',
  owner_name: '测试公司',
  location: '北京市朝阳区xxx路xxx号',
  building_area: 1000.5,
  land_area: 500.25,
  usage: '商业服务',
  registration_date: '2026-01-15',
  valid_from: '2026-01-15',
  valid_to: '2076-01-14',
  status: 'active',
  created_at: '2026-01-30T00:00:00Z',
  updated_at: '2026-01-30T00:00:00Z',
};

const mockExtractionResult = {
  session_id: 'session-123',
  extracted_data: {
    certificate_number: '京(2026)朝阳区不动产权第0001号',
    owner_name: '测试公司',
    building_area: 1000.5,
  },
  confidence: 0.95,
  pages_processed: 2,
  extraction_time: 1.5,
};

// =============================================================================
// uploadCertificate 测试
// =============================================================================

describe('PropertyCertificateService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('uploadCertificate', () => {
    it('should upload and extract certificate successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: mockExtractionResult,
      });

      const file = new File(['test content'], 'certificate.pdf', {
        type: 'application/pdf',
      });

      const result = await propertyCertificateService.uploadCertificate(file);

      expect(result).toEqual(mockExtractionResult);
      expect(result.session_id).toBe('session-123');
      expect(result.confidence).toBe(0.95);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/property-certificates/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      );
    });

    it('should throw error when upload fails', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: null,
      });

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await expect(propertyCertificateService.uploadCertificate(file)).rejects.toThrow(
        'Failed to upload certificate'
      );
    });

    it('should handle API error', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Network error'));

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await expect(propertyCertificateService.uploadCertificate(file)).rejects.toThrow(
        'Network error'
      );
    });
  });

  // =============================================================================
  // confirmImport 测试
  // =============================================================================

  describe('confirmImport', () => {
    it('should confirm import successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { certificate_id: 'cert-1', status: 'created' },
      });

      const confirmData = {
        session_id: 'session-123',
        confirmed_data: {
          certificate_number: '京(2026)朝阳区不动产权第0001号',
          owner_name: '测试公司',
        },
      };

      const result = await propertyCertificateService.confirmImport(confirmData);

      expect(result.certificate_id).toBe('cert-1');
      expect(result.status).toBe('created');
      expect(apiClient.post).toHaveBeenCalledWith(
        '/property-certificates/confirm-import',
        confirmData
      );
    });

    it('should throw error when confirm fails', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: null,
      });

      await expect(
        propertyCertificateService.confirmImport({ session_id: 'invalid' })
      ).rejects.toThrow('Failed to confirm import');
    });
  });

  // =============================================================================
  // listCertificates 测试
  // =============================================================================

  describe('listCertificates', () => {
    it('should return certificate list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: [mockCertificate],
      });

      const result = await propertyCertificateService.listCertificates();

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual(mockCertificate);
    });

    it('should support pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: [],
      });

      await propertyCertificateService.listCertificates({ skip: 10, limit: 20 });

      expect(apiClient.get).toHaveBeenCalledWith('/property-certificates/', {
        params: { skip: 10, limit: 20 },
      });
    });

    it('should return empty array when no data', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: null,
      });

      const result = await propertyCertificateService.listCertificates();

      expect(result).toEqual([]);
    });
  });

  // =============================================================================
  // getCertificate 测试
  // =============================================================================

  describe('getCertificate', () => {
    it('should return certificate by id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: mockCertificate,
      });

      const result = await propertyCertificateService.getCertificate('cert-1');

      expect(result).toEqual(mockCertificate);
      expect(apiClient.get).toHaveBeenCalledWith('/property-certificates/cert-1');
    });

    it('should throw error when not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: null,
      });

      await expect(propertyCertificateService.getCertificate('invalid')).rejects.toThrow(
        'Certificate not found'
      );
    });
  });

  // =============================================================================
  // createCertificate 测试
  // =============================================================================

  describe('createCertificate', () => {
    it('should create certificate manually', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: mockCertificate,
      });

      const createData = {
        certificate_number: '京(2026)朝阳区不动产权第0001号',
        owner_name: '测试公司',
        building_area: 1000.5,
      };

      const result = await propertyCertificateService.createCertificate(createData);

      expect(result).toEqual(mockCertificate);
      expect(apiClient.post).toHaveBeenCalledWith('/property-certificates/', createData);
    });

    it('should throw error on creation failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: null,
      });

      await expect(
        propertyCertificateService.createCertificate({
          certificate_number: 'test',
        })
      ).rejects.toThrow('Failed to create certificate');
    });
  });

  // =============================================================================
  // updateCertificate 测试
  // =============================================================================

  describe('updateCertificate', () => {
    it('should update certificate successfully', async () => {
      const updated = { ...mockCertificate, owner_name: '新公司名称' };
      vi.mocked(apiClient.put).mockResolvedValue({
        data: updated,
      });

      const result = await propertyCertificateService.updateCertificate('cert-1', {
        owner_name: '新公司名称',
      });

      expect(result.owner_name).toBe('新公司名称');
      expect(apiClient.put).toHaveBeenCalledWith('/property-certificates/cert-1', {
        owner_name: '新公司名称',
      });
    });

    it('should update multiple fields', async () => {
      const updateData = {
        owner_name: '更新公司',
        building_area: 2000,
        status: 'inactive',
      };

      vi.mocked(apiClient.put).mockResolvedValue({
        data: { ...mockCertificate, ...updateData },
      });

      const result = await propertyCertificateService.updateCertificate('cert-1', updateData);

      expect(result.owner_name).toBe('更新公司');
      expect(result.building_area).toBe(2000);
    });

    it('should throw error on update failure', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        data: null,
      });

      await expect(
        propertyCertificateService.updateCertificate('cert-1', { owner_name: '测试' })
      ).rejects.toThrow('Failed to update certificate');
    });
  });

  // =============================================================================
  // deleteCertificate 测试
  // =============================================================================

  describe('deleteCertificate', () => {
    it('should delete certificate successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        data: { status: 'deleted' },
      });

      const result = await propertyCertificateService.deleteCertificate('cert-1');

      expect(result.status).toBe('deleted');
      expect(apiClient.delete).toHaveBeenCalledWith('/property-certificates/cert-1');
    });

    it('should throw error on delete failure', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        data: null,
      });

      await expect(propertyCertificateService.deleteCertificate('cert-1')).rejects.toThrow(
        'Failed to delete certificate'
      );
    });
  });
});
