/**
 * useOwnership Hook 测试
 * 测试权属方管理相关的自定义Hooks（简化版本）
 */

import { describe, it, expect, vi } from 'vitest'

// =============================================================================
// Mock ownershipService
// =============================================================================

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipOptions: vi.fn(() => Promise.resolve([
      { label: '权属方1', value: '1' },
      { label: '权属方2', value: '2' }
    ])),
    getOwnership: vi.fn(() => Promise.resolve({
      id: '1',
      name: '权属方1',
      code: 'OWN001'
    }))
  }
}))

// =============================================================================
// useOwnership Hook 测试
// =============================================================================

describe('useOwnership - Hook验证', () => {
  it('应该导出useOwnershipOptions hook', async () => {
    const { useOwnershipOptions } = await import('../useOwnership')
    expect(typeof useOwnershipOptions).toBe('function')
  })

  it('应该导出useOwnershipDetail hook', async () => {
    const { useOwnershipDetail } = await import('../useOwnership')
    expect(typeof useOwnershipDetail).toBe('function')
  })
})
