import React from 'react'
import { Card, Empty } from 'antd'
import { ResponsiveContainer } from 'recharts'

interface AnalyticsCardProps {
  title: string
  children: React.ReactNode
  loading?: boolean
  hasData?: boolean
  size?: 'default' | 'small'
  className?: string
}

export const AnalyticsCard: React.FC<AnalyticsCardProps> = ({
  title,
  children,
  loading = false,
  hasData = true,
  size = 'small',
  className = ''
}) => {
  return (
    <Card
      title={title}
      size={size}
      className={className}
      loading={loading}
    >
      {!hasData ? (
        <Empty description="暂无数据" />
      ) : (
        children
      )}
    </Card>
  )
}

interface ChartCardProps extends AnalyticsCardProps {
  height?: number
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  children,
  height = 300,
  ...props
}) => {
  return (
    <AnalyticsCard title={title} {...props}>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </AnalyticsCard>
  )
}