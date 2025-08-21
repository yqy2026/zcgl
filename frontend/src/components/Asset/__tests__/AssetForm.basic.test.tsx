import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import AssetForm from '../AssetForm'

// Mock the hooks and dependencies
vi.mock('@/hooks/useFormFieldVisibility', () => ({
  useFormFieldVisibility: () => ({
    isFieldVisible: vi.fn(() => true),
    isFieldHidden: vi.fn(() => false),
    getFieldDependencies: vi.fn(() => []),
    getAllVisibleFields: vi.fn(() => []),
    getAllHiddenFields: vi.fn(() => []),
    visibleFields: new Set(),
    hiddenFields: new Set(),
  }),
  useFormGroupVisibility: () => ({
    isGroupVisible: vi.fn(() => true),
    getVisibleFieldsInGroup: vi.fn(() => ['property_name', 'ownership_entity']),
    getHiddenFieldsInGroup: vi.fn(() => []),
  }),
}))

vi.mock('@/utils/format', () => ({
  calculateOccupancyRate: vi.fn(() => 80),
}))

describe('AssetForm Basic Tests', () => {
  const mockProps = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    loading: false,
    mode: 'create' as const,
  }

  it('renders without crashing', () => {
    render(<AssetForm {...mockProps} />)
    
    // Check if the form is rendered
    expect(screen.getByText('表单完成度')).toBeInTheDocument()
  })

  it('shows form completion progress', () => {
    render(<AssetForm {...mockProps} />)
    
    // Check if progress bar is present
    expect(screen.getByText('表单完成度')).toBeInTheDocument()
  })

  it('renders basic form sections', () => {
    render(<AssetForm {...mockProps} />)
    
    // Check if basic sections are rendered
    expect(screen.getByText('基本信息')).toBeInTheDocument()
    expect(screen.getByText('面积信息')).toBeInTheDocument()
    expect(screen.getByText('状态信息')).toBeInTheDocument()
  })

  it('shows action buttons', () => {
    render(<AssetForm {...mockProps} />)
    
    // Check if action buttons are present
    expect(screen.getByText('取消')).toBeInTheDocument()
    expect(screen.getByText('重置')).toBeInTheDocument()
    expect(screen.getByText('创建资产')).toBeInTheDocument()
  })

  it('shows edit mode button text', () => {
    render(<AssetForm {...mockProps} mode="edit" />)
    
    // Check if edit mode button text is correct
    expect(screen.getByText('更新资产')).toBeInTheDocument()
  })

  it('shows advanced options toggle', () => {
    render(<AssetForm {...mockProps} />)
    
    // Check if advanced options toggle is present
    expect(screen.getByText('显示高级选项')).toBeInTheDocument()
  })
})