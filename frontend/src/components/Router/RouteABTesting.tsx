/**
 * 路由级A/B测试组件
 * 支持路由组件、布局和功能的A/B测试
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'

interface ABTestVariant {
  id: string
  name: string
  description?: string
  weight: number // 权重 (0-100)
  component?: React.ComponentType<Record<string, unknown>>
  props?: Record<string, unknown>
  enabled: boolean
}

interface ABTestConfig {
  id: string
  name: string
  description?: string
  route: string
  variants: ABTestVariant[]
  startDate?: Date
  endDate?: Date
  targetAudience?: string[]
  metrics: string[]
}

interface ABTestContextType {
  currentTests: Map<string, string> // testId -> variantId
  getVariant: (testId: string) => ABTestVariant | null
  trackConversion: (testId: string, metric: string, value?: unknown) => void
  isTestActive: (testId: string) => boolean
  getAllActiveTests: () => ABTestConfig[]
  loading: boolean
}

const ABTestContext = createContext<ABTestContextType | null>(null)

class ABTestManager {
  private tests: Map<string, ABTestConfig>
  private userVariants: Map<string, Record<string, string>> // userId -> {testId -> variantId}
  private conversions: Map<string, Map<string, unknown>> // testId -> metric -> value
  private userId: string | null = null

  constructor() {
    this.tests = new Map()
    this.userVariants = new Map()
    this.conversions = new Map()
    this.userId = this.getUserId()
    this.loadTests()
  }

  private getUserId(): string {
    // 获取或生成用户ID用于A/B测试分组
    let userId = localStorage.getItem('abtest_user_id')
    if (userId == null) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('abtest_user_id', userId)
    }
    return userId
  }

  private loadTests() {
    // 这里应该从API加载A/B测试配置
    // 简化版本，使用本地配置
    const defaultTests: ABTestConfig[] = [
      {
        id: 'dashboard_layout_v2',
        name: 'Dashboard Layout V2',
        description: '测试新的仪表板布局设计',
        route: '/dashboard',
        variants: [
          {
            id: 'original',
            name: '原始布局',
            weight: 50,
            enabled: true
          },
          {
            id: 'new_layout',
            name: '新布局',
            weight: 50,
            enabled: true
          }
        ],
        metrics: ['engagement_time', 'click_through_rate']
      },
      {
        id: 'asset_list_density',
        name: 'Asset List Density',
        description: '测试资产列表的不同密度显示',
        route: '/assets/list',
        variants: [
          {
            id: 'standard',
            name: '标准密度',
            weight: 40,
            enabled: true
          },
          {
            id: 'compact',
            name: '紧凑密度',
            weight: 30,
            enabled: true
          },
          {
            id: 'detailed',
            name: '详细密度',
            weight: 30,
            enabled: true
          }
        ],
        metrics: ['scroll_depth', 'interaction_rate']
      }
    ]

    defaultTests.forEach(test => {
      this.tests.set(test.id, test)
    })
  }

  private getAssignedVariant(testId: string): ABTestVariant | null {
    const test = this.tests.get(testId)
    if (test == null || this.userId == null) return null

    // 检查是否已经分配过变体
    const savedVariants = this.userVariants.get(this.userId)
    if (savedVariants != null && savedVariants[testId] != null) {
      return test.variants.find(v => v.id === savedVariants[testId]) ?? null
    }

    // 检查测试是否有效
    if (!this.isTestActive(testId)) {
      return null
    }

    // 分配变体
    const variant = this.assignVariant(test)

    // 保存分配结果
    if (!this.userVariants.has(this.userId)) {
      this.userVariants.set(this.userId, {})
    }
    const variants = this.userVariants.get(this.userId)!
    variants[testId] = variant.id

    // 记录分配事件
    this.trackEvent('variant_assigned', {
      testId,
      variantId: variant.id,
      userId: this.userId
    })

    return variant
  }

  private assignVariant(test: ABTestConfig): ABTestVariant {
    // 根据权重分配变体
    const enabledVariants = test.variants.filter(v => v.enabled)
    if (enabledVariants.length === 0) {
      throw new Error('No enabled variants for test')
    }

    if (enabledVariants.length === 1) {
      return enabledVariants[0]
    }

    // 使用用户ID进行一致性哈希分配
    const hash = this.hashString(`${this.userId}_${test.id}`)
    const totalWeight = enabledVariants.reduce((sum, v) => sum + v.weight, 0)
    const randomValue = (hash % 100) + 1

    let cumulativeWeight = 0
    for (const variant of enabledVariants) {
      cumulativeWeight += (variant.weight / totalWeight) * 100
      if (randomValue <= cumulativeWeight) {
        return variant
      }
    }

    return enabledVariants[0] // 回退到第一个变体
  }

  private hashString(str: string): number {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // 转换为32位整数
    }
    return Math.abs(hash)
  }

  public isTestActive(testId: string): boolean {
    const test = this.tests.get(testId)
    if (test == null) return false

    const now = new Date()

    // 检查日期范围
    if (test.startDate != null && now < test.startDate) return false
    if (test.endDate != null && now > test.endDate) return false

    // 检查目标受众
    if (test.targetAudience != null && test.targetAudience.length > 0) {
      // 这里可以实现用户群体匹配逻辑
      // 简化版本，假设所有用户都符合
    }

    return true
  }

  public getVariant(testId: string): ABTestVariant | null {
    return this.getAssignedVariant(testId)
  }

  public trackConversion(testId: string, metric: string, value?: unknown) {
    if (!this.conversions.has(testId)) {
      this.conversions.set(testId, new Map())
    }

    this.conversions.get(testId)!.set(metric, value)

    // 记录转化事件
    this.trackEvent('conversion', {
      testId,
      metric,
      value,
      userId: this.userId,
      timestamp: new Date().toISOString()
    })

    // 上报转化数据
    this.reportConversion(testId, metric, value)
  }

  private trackEvent(eventType: string, data: Record<string, unknown>) {
    // A/B Test Event

    // 这里可以发送到分析服务
    if (process.env.NODE_ENV === 'production') {
      // 实际项目中发送到分析服务
      fetch('/api/analytics/abtest-events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          eventType,
          data,
          timestamp: new Date().toISOString()
        })
      }).catch(error => {
        console.warn('A/B Test event reporting failed:', error)
      })
    }
  }

  private async reportConversion(testId: string, metric: string, value?: unknown) {
    try {
      await fetch('/api/analytics/abtest-conversions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          testId,
          metric,
          value,
          userId: this.userId,
          timestamp: new Date().toISOString()
        })
      })
    } catch (error) {
      console.warn('A/B Test conversion reporting failed:', error)
    }
  }

  public getTestResults(testId: string) {
    const conversions = this.conversions.get(testId) ?? new Map()
    return {
      conversions: Object.fromEntries(conversions),
      testId,
      userId: this.userId
    }
  }

  public getAllActiveTests(): ABTestConfig[] {
    return Array.from(this.tests.values()).filter(test =>
      this.isTestActive(test.id)
    )
  }
}

// A/B测试提供者组件
interface ABTestProviderProps {
  children: ReactNode
  userId?: string
  _userId?: string
}

export const ABTestProvider: React.FC<ABTestProviderProps> = ({ children, _userId }) => {
  const [manager] = useState(() => new ABTestManager())
  const [currentTests, setCurrentTests] = useState<Map<string, string>>(new Map())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 初始化当前用户的测试变体
    const tests = manager.getAllActiveTests()
    const variants = new Map<string, string>()

    tests.forEach(test => {
      const variant = manager.getVariant(test.id)
      if (variant !== undefined && variant !== null) {
        variants.set(test.id, variant.id)
      }
    })

    setCurrentTests(variants)
    setLoading(false)
  }, [manager])

  const contextValue: ABTestContextType = {
    currentTests,
    getVariant: (testId: string) => manager.getVariant(testId),
    trackConversion: (testId: string, metric: string, value?: unknown) =>
      manager.trackConversion(testId, metric, value),
    isTestActive: (testId: string) => manager.isTestActive(testId),
    getAllActiveTests: () => manager.getAllActiveTests(),
    loading
  }

  return (
    <ABTestContext.Provider value={contextValue}>
      {children}
    </ABTestContext.Provider>
  )
}

// A/B测试Hook
export const useABTest = () => {
  const context = useContext(ABTestContext)
  if (!context) {
    throw new Error('useABTest must be used within ABTestProvider')
  }

  return context
}

// A/B测试包装器组件
interface ABTestWrapperProps {
  testId: string
  fallback?: React.ComponentType<any>
  children: ReactNode
  loadingComponent?: React.ComponentType
}

export const ABTestWrapper: React.FC<ABTestWrapperProps> = ({
  testId,
  fallback: FallbackComponent,
  children,
  loadingComponent: LoadingComponent
}) => {
  const { getVariant, isTestActive, loading } = useABTest()

  if (loading !== undefined && loading !== null) {
    return LoadingComponent != null ? <LoadingComponent /> : null
  }

  if (!isTestActive(testId)) {
    return <>{children}</>
  }

  const variant = getVariant(testId)

  if (variant == null) {
    return FallbackComponent != null ? <FallbackComponent /> : <>{children}</>
  }

  // 如果变体有自定义组件，使用它
  if (variant.component != null) {
    const VariantComponent = variant.component
    return <VariantComponent {...variant.props}>{children}</VariantComponent>
  }

  // 否则渲染子组件
  return <>{children}</>
}

// 路由级A/B测试Hook
export const useRouteABTest = (route: string) => {
  const { getAllActiveTests, getVariant, trackConversion } = useABTest()

  // 获取适用于当前路由的测试
  const routeTests = getAllActiveTests().filter((test: ABTestConfig) => test.route === route)

  const getRouteVariant = (testId: string) => {
    return getVariant(testId)
  }

  const trackRouteConversion = (testId: string, metric: string, value?: unknown) => {
    trackConversion(testId, metric, value)
  }

  return {
    tests: routeTests,
    getVariant: getRouteVariant,
    trackConversion: trackRouteConversion,
    hasTests: routeTests.length > 0
  }
}

// A/B测试分析Hook
export const useABTestAnalytics = (testId: string) => {
  const { getVariant, trackConversion, currentTests } = useABTest()

  const currentVariant = getVariant(testId)

  const trackView = () => {
    if (currentVariant !== undefined && currentVariant !== null) {
      trackConversion(testId, 'view', {
        variant: currentVariant.id,
        timestamp: new Date().toISOString()
      })
    }
  }

  const trackEngagement = (duration: number) => {
    if (currentVariant !== undefined && currentVariant !== null) {
      trackConversion(testId, 'engagement_time', {
        variant: currentVariant.id,
        duration,
        timestamp: new Date().toISOString()
      })
    }
  }

  const trackClick = (element: string, data?: unknown) => {
    if (currentVariant !== undefined && currentVariant !== null) {
      trackConversion(testId, 'click', {
        variant: currentVariant.id,
        element,
        data,
        timestamp: new Date().toISOString()
      })
    }
  }

  return {
    currentVariant,
    trackView,
    trackEngagement,
    trackClick,
    isActive: currentTests.has(testId)
  }
}

// 预定义的A/B测试组件
export const DashboardABTest: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { currentVariant, trackView } = useABTestAnalytics('dashboard_layout_v2')

  useEffect(() => {
    // 自动跟踪页面浏览
    trackView()
  }, [trackView])

  // 根据变体应用不同的样式
  const getLayoutStyle = () => {
    if (!currentVariant) return {}

    switch (currentVariant.id) {
      case 'new_layout':
        return {
          display: 'grid',
          gridTemplateColumns: '300px 1fr',
          gap: '20px',
          padding: '20px'
        }
      default:
        return {
          padding: '20px'
        }
    }
  }

  return (
    <div style={getLayoutStyle()}>
      {children}
    </div>
  )
}

export const AssetListABTest: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { currentVariant, trackClick } = useABTestAnalytics('asset_list_density')

  const getDensityStyle = () => {
    if (!currentVariant) return {}

    switch (currentVariant.id) {
      case 'compact':
        return {
          fontSize: '14px',
          lineHeight: '1.2'
        }
      case 'detailed':
        return {
          fontSize: '16px',
          lineHeight: '1.6'
        }
      default:
        return {}
    }
  }

  const handleClick = (element: string, data?: unknown) => {
    trackClick(element, data)
  }

  return (
    <div style={getDensityStyle()} onClick={() => handleClick('asset_list')}>
      {children}
    </div>
  )
}

export default ABTestManager