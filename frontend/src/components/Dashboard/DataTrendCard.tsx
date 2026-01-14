import React from 'react'
import { Card, Statistic } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons'
import styles from './DataTrendCard.module.css'
import { COLORS } from '@/styles/colorMap'

interface DataTrendCardProps {
  title: string
  value: number
  suffix?: string
  precision?: number
  trend?: {
    value: number
    period: string
    isPositive: boolean
  }
  icon?: React.ReactNode
  color?: 'primary' | 'success' | 'warning' | 'error' | 'default'
  loading?: boolean
  size?: 'small' | 'default' | 'large'
}

const DataTrendCard: React.FC<DataTrendCardProps> = ({
  title,
  value,
  suffix = '',
  precision = 0,
  trend,
  icon,
  color = 'default',
  loading = false,
  size = 'default'
}) => {
  const getTrendIcon = () => {
    if (!trend) return null

    if (trend.isPositive) {
      return <ArrowUpOutlined />
    } else if (trend.value < 0) {
      return <ArrowDownOutlined />
    }
    return <MinusOutlined />
  }

  const getTrendText = () => {
    if (!trend) return ''
    const absValue = Math.abs(trend.value)
    const sign = trend.isPositive ? '+' : trend.value < 0 ? '-' : ''
    return `${sign}${absValue.toFixed(1)}%`
  }

  const getTrendClass = () => {
    if (!trend) return styles.trendNeutral
    if (trend.isPositive) return styles.trendUp
    return trend.value < 0 ? styles.trendDown : styles.trendNeutral
  }

  const getCardClassName = () => {
    const baseClass = styles.trendCard
    return `${baseClass} ${styles[color]} ${styles[size]}`
  }

  return (
    <Card
      className={getCardClassName()}
      loading={loading}
      variant="borderless"
    >
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}>{title}</div>
        {icon !== undefined && icon !== null && <div className={styles.cardIcon}>{icon}</div>}
      </div>

      <div className={styles.cardContent}>
        <Statistic
          value={value}
          precision={precision}
          suffix={suffix}
          valueStyle={{
            fontSize: size === 'large' ? 28 : size === 'small' ? 20 : 24,
            fontWeight: 600,
            color: color === 'default' ? COLORS.textPrimary : undefined
          }}
        />

        {trend && (
          <div className={getTrendClass()}>
            <span className={styles.trendIcon}>{getTrendIcon()}</span>
            <span className={styles.trendText}>{getTrendText()}</span>
            <span className={styles.trendPeriod}>{trend.period}</span>
          </div>
        )}
      </div>
    </Card>
  )
}

export default DataTrendCard