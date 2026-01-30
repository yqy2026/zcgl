/**
 * Contact Service 单元测试
 * 测试联系人管理服务的 CRUD 操作
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { contactService, ContactType } from '../contactService';

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

const mockContact = {
  id: 'contact-1',
  entity_type: 'ownership',
  entity_id: 'ownership-1',
  name: '张三',
  title: '经理',
  department: '财务部',
  phone: '13800138000',
  office_phone: '010-12345678',
  email: 'zhangsan@example.com',
  wechat: 'zhangsan_wx',
  address: '北京市朝阳区',
  contact_type: ContactType.PRIMARY,
  is_primary: true,
  notes: '主要联系人',
  preferred_contact_time: '工作日 9:00-18:00',
  preferred_contact_method: 'phone',
  is_active: true,
  created_at: '2026-01-30T00:00:00Z',
  updated_at: '2026-01-30T00:00:00Z',
  created_by: 'admin',
  updated_by: 'admin',
};

// =============================================================================
// createContact 测试
// =============================================================================

describe('ContactService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createContact', () => {
    it('should create contact successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: mockContact,
      });

      const createData = {
        entity_type: 'ownership',
        entity_id: 'ownership-1',
        name: '张三',
        phone: '13800138000',
        contact_type: ContactType.PRIMARY,
      };

      const result = await contactService.createContact(createData);

      expect(result).toEqual(mockContact);
      expect(apiClient.post).toHaveBeenCalledWith('/contacts', createData);
    });

    it('should throw error when creation fails', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: undefined,
      });

      await expect(
        contactService.createContact({
          entity_type: 'ownership',
          entity_id: 'ownership-1',
          name: '测试',
        })
      ).rejects.toThrow();
    });
  });

  // =============================================================================
  // getContact 测试
  // =============================================================================

  describe('getContact', () => {
    it('should get contact by id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: mockContact,
      });

      const result = await contactService.getContact('contact-1');

      expect(result).toEqual(mockContact);
      expect(apiClient.get).toHaveBeenCalledWith('/contacts/contact-1');
    });

    it('should throw error when contact not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: undefined,
      });

      await expect(contactService.getContact('invalid-id')).rejects.toThrow();
    });
  });

  // =============================================================================
  // getEntityContacts 测试
  // =============================================================================

  describe('getEntityContacts', () => {
    it('should get contacts for entity', async () => {
      const mockResponse = {
        items: [mockContact],
        total: 1,
        page: 1,
        page_size: 10,
        pages: 1,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        data: mockResponse,
      });

      const result = await contactService.getEntityContacts('ownership', 'ownership-1');

      expect(result).toEqual(mockResponse);
      expect(apiClient.get).toHaveBeenCalledWith('/contacts/entity/ownership/ownership-1', {
        params: { page: 1, page_size: 10 },
      });
    });

    it('should support pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0, page: 2, page_size: 20, pages: 0 },
      });

      await contactService.getEntityContacts('ownership', 'ownership-1', 2, 20);

      expect(apiClient.get).toHaveBeenCalledWith('/contacts/entity/ownership/ownership-1', {
        params: { page: 2, page_size: 20 },
      });
    });
  });

  // =============================================================================
  // getPrimaryContact 测试
  // =============================================================================

  describe('getPrimaryContact', () => {
    it('should get primary contact for entity', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: mockContact,
      });

      const result = await contactService.getPrimaryContact('ownership', 'ownership-1');

      expect(result).toEqual(mockContact);
      expect(apiClient.get).toHaveBeenCalledWith('/contacts/entity/ownership/ownership-1/primary');
    });

    it('should return null when no primary contact exists', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: undefined,
      });

      const result = await contactService.getPrimaryContact('ownership', 'ownership-1');

      expect(result).toBeNull();
    });

    it('should return null on 404 error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Not found'));

      const result = await contactService.getPrimaryContact('ownership', 'ownership-1');

      expect(result).toBeNull();
    });
  });

  // =============================================================================
  // updateContact 测试
  // =============================================================================

  describe('updateContact', () => {
    it('should update contact successfully', async () => {
      const updatedContact = { ...mockContact, name: '李四' };

      vi.mocked(apiClient.put).mockResolvedValue({
        data: updatedContact,
      });

      const result = await contactService.updateContact('contact-1', { name: '李四' });

      expect(result.name).toBe('李四');
      expect(apiClient.put).toHaveBeenCalledWith('/contacts/contact-1', { name: '李四' });
    });

    it('should update multiple fields', async () => {
      const updateData = {
        name: '王五',
        phone: '13900139000',
        email: 'wangwu@example.com',
        is_primary: false,
      };

      vi.mocked(apiClient.put).mockResolvedValue({
        data: { ...mockContact, ...updateData },
      });

      const result = await contactService.updateContact('contact-1', updateData);

      expect(result.name).toBe('王五');
      expect(result.phone).toBe('13900139000');
    });

    it('should throw error when update fails', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        data: undefined,
      });

      await expect(contactService.updateContact('contact-1', { name: '测试' })).rejects.toThrow();
    });
  });

  // =============================================================================
  // deleteContact 测试
  // =============================================================================

  describe('deleteContact', () => {
    it('should delete contact successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        data: mockContact,
      });

      const result = await contactService.deleteContact('contact-1');

      expect(result).toEqual(mockContact);
      expect(apiClient.delete).toHaveBeenCalledWith('/contacts/contact-1');
    });

    it('should throw error when delete fails', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        data: undefined,
      });

      await expect(contactService.deleteContact('contact-1')).rejects.toThrow();
    });
  });

  // =============================================================================
  // createContactsBatch 测试
  // =============================================================================

  describe('createContactsBatch', () => {
    it('should create multiple contacts successfully', async () => {
      const contacts = [
        { entity_type: 'ownership', entity_id: 'ownership-1', name: '联系人1' },
        { entity_type: 'ownership', entity_id: 'ownership-1', name: '联系人2' },
      ];

      const createdContacts = contacts.map((c, i) => ({
        ...mockContact,
        id: `contact-${i + 1}`,
        name: c.name,
      }));

      vi.mocked(apiClient.post).mockResolvedValue({
        data: createdContacts,
      });

      const result = await contactService.createContactsBatch('ownership', 'ownership-1', contacts);

      expect(result).toHaveLength(2);
      expect(apiClient.post).toHaveBeenCalledWith(
        '/contacts/batch/ownership/ownership-1',
        contacts
      );
    });

    it('should throw error when batch creation fails', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: undefined,
      });

      await expect(
        contactService.createContactsBatch('ownership', 'ownership-1', [])
      ).rejects.toThrow();
    });
  });

  // =============================================================================
  // ContactType 枚举测试
  // =============================================================================

  describe('ContactType enum', () => {
    it('should have correct values', () => {
      expect(ContactType.PRIMARY).toBe('primary');
      expect(ContactType.FINANCE).toBe('finance');
      expect(ContactType.OPERATIONS).toBe('operations');
      expect(ContactType.LEGAL).toBe('legal');
      expect(ContactType.GENERAL).toBe('general');
    });
  });
});
