/**
 * 示例测试 - 验证Vitest配置
 * 这个测试验证测试基础设施是否正常工作
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils/test-helpers'

describe('Vitest配置验证', () => {
  it('应该正确渲染测试组件', () => {
    const TestComponent = () => <div data-testid="test">Hello Vitest</div>
    render(<TestComponent />)
    
    expect(screen.getByTestId('test')).toBeInTheDocument()
    expect(screen.getByTestId('test')).toHaveTextContent('Hello Vitest')
  })

  it('应该正确执行断言', () => {
    expect(1 + 1).toBe(2)
    expect({ name: 'test' }).toHaveProperty('name', 'test')
    expect([1, 2, 3]).toHaveLength(3)
  })

  it('应该正确处理异步操作', async () => {
    const promise = Promise.resolve('async result')
    const result = await promise
    expect(result).toBe('async result')
  })
})
