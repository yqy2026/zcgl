/**
 * Shared type definitions for chart components
 * Provides type-safe interfaces for @ant-design/plots components
 */

/**
 * Base data point for all chart types
 * Supports flexible key-value pairs for different chart configurations
 */
export interface ChartDataPoint {
  [key: string]: string | number | undefined | null
}

/**
 * Data point for trend/line charts
 */
export interface TrendDataPoint extends ChartDataPoint {
  month: string
  rate: number
  total_area?: number
  rented_area?: number
}

/**
 * Data point for pie/donut charts showing distribution
 */
export interface DistributionDataPoint extends ChartDataPoint {
  type: string
  value: number
  percentage?: number
  total_area?: number
  rented_area?: number
}

/**
 * Data point for column/bar charts
 */
export interface ColumnDataPoint extends ChartDataPoint {
  name?: string
  value: number
  count?: number
  rate?: number
  percentage?: number
  total_area?: number
  full_name?: string
}

/**
 * Data point for dual-axis charts (column + line)
 */
export interface DualAxesDataPoint extends ChartDataPoint {
  entity: string
  total_area: number
  occupancy_rate: number
  full_name?: string
}

/**
 * Data point for area range charts
 */
export interface AreaRangeDataPoint extends ChartDataPoint {
  range: string
  count: number
  total_area: number
  percentage: number
}

/**
 * Tooltip formatter return type
 */
export interface TooltipFormatterResult {
  name: string
  value: string
}

/**
 * Custom content props for tooltips
 */
export interface TooltipCustomContentProps {
  title?: string
  data?: Array<{
    name?: string
    value?: string | number
    data?: ChartDataPoint
  }>
}

/**
 * Generic chart configuration props
 */
export interface BaseChartProps {
  data: ChartDataPoint[]
  loading?: boolean
  height?: number
  xField?: string
  yField?: string | string[]
  seriesField?: string
  angleField?: string
  colorField?: string
}

/**
 * Color function type for chart series
 */
export type ChartColorFunction = (datum: ChartDataPoint) => string
