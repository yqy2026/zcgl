import * as XLSX from 'xlsx'

export interface ExportData {
  sheetName: string
  data: Record<string, unknown>[]
  headers: string[]
}

export interface AnalyticsExportData {
  summary: {
    total_assets: number
    total_area: number
    total_rentable_area: number
    occupancy_rate: number
    total_annual_income: number
    total_annual_expense: number
    total_net_income: number
    total_monthly_rent: number
  }
  property_nature_distribution: Array<{
    name: string
    count: number
    percentage: number | string
  }>
  ownership_status_distribution: Array<{
    status: string
    count: number
    percentage: number | string
  }>
  usage_status_distribution: Array<{
    status: string
    count: number
    percentage: number | string
  }>
  business_category_distribution: Array<{
    category: string
    count: number
    occupancy_rate: number | string
  }>
  occupancy_trend?: Array<{
    date: string
    occupancy_rate: number
    total_rented_area: number
    total_rentable_area: number
  }>
}

class AnalyticsExportService {
  /**
   * 导出分析数据到Excel
   */
  async exportToExcel(data: AnalyticsExportData, filename?: string): Promise<void> {
    try {
      const workbook = XLSX.utils.book_new()

      // 创建概览数据工作表
      const summaryData = [
        ['指标', '数值', '单位'],
        ['资产总数', data.summary.total_assets, '个'],
        ['总面积', data.summary.total_area.toFixed(2), '㎡'],
        ['可租面积', data.summary.total_rentable_area.toFixed(2), '㎡'],
        ['整体出租率', data.summary.occupancy_rate.toFixed(2), '%'],
        ['年收入', data.summary.total_annual_income.toFixed(2), '元'],
        ['年支出', data.summary.total_annual_expense.toFixed(2), '元'],
        ['净收益', data.summary.total_net_income.toFixed(2), '元'],
        ['月租金', data.summary.total_monthly_rent.toFixed(2), '元']
      ]
      const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
      XLSX.utils.book_append_sheet(workbook, summarySheet, '概览统计')

      // 创建物业性质分布工作表
      const propertyNatureData = [
        ['物业性质', '数量', '占比(%)'],
        ...data.property_nature_distribution.map(item => [
          item.name,
          item.count,
          item.percentage
        ])
      ]
      const propertyNatureSheet = XLSX.utils.aoa_to_sheet(propertyNatureData)
      XLSX.utils.book_append_sheet(workbook, propertyNatureSheet, '物业性质分布')

      // 创建确权状态分布工作表
      const ownershipStatusData = [
        ['确权状态', '数量', '占比(%)'],
        ...data.ownership_status_distribution.map(item => [
          item.status,
          item.count,
          item.percentage
        ])
      ]
      const ownershipStatusSheet = XLSX.utils.aoa_to_sheet(ownershipStatusData)
      XLSX.utils.book_append_sheet(workbook, ownershipStatusSheet, '确权状态分布')

      // 创建使用状态分布工作表
      const usageStatusData = [
        ['使用状态', '数量', '占比(%)'],
        ...data.usage_status_distribution.map(item => [
          item.status,
          item.count,
          item.percentage
        ])
      ]
      const usageStatusSheet = XLSX.utils.aoa_to_sheet(usageStatusData)
      XLSX.utils.book_append_sheet(workbook, usageStatusSheet, '使用状态分布')

      // 创建业态类别分布工作表
      const businessCategoryData = [
        ['业态类别', '数量', '出租率(%)'],
        ...data.business_category_distribution.map(item => [
          item.category,
          item.count,
          item.occupancy_rate
        ])
      ]
      const businessCategorySheet = XLSX.utils.aoa_to_sheet(businessCategoryData)
      XLSX.utils.book_append_sheet(workbook, businessCategorySheet, '业态类别分布')

      // 创建出租率趋势工作表（如果有数据）
      if (data.occupancy_trend && data.occupancy_trend.length > 0) {
        const occupancyTrendData = [
          ['日期', '出租率(%)', '已租面积(㎡)', '可租面积(㎡)'],
          ...data.occupancy_trend.map(item => [
            item.date,
            item.occupancy_rate,
            item.total_rented_area,
            item.total_rentable_area
          ])
        ]
        const occupancyTrendSheet = XLSX.utils.aoa_to_sheet(occupancyTrendData)
        XLSX.utils.book_append_sheet(workbook, occupancyTrendSheet, '出租率趋势')
      }

      // 设置列宽
      const columnWidths = [{ wch: 15 }, { wch: 12 }, { wch: 12 }]
      workbook.Sheets['概览统计']['!cols'] = columnWidths
      workbook.Sheets['物业性质分布']['!cols'] = columnWidths
      workbook.Sheets['确权状态分布']['!cols'] = columnWidths
      workbook.Sheets['使用状态分布']['!cols'] = columnWidths
      workbook.Sheets['业态类别分布']['!cols'] = columnWidths

      if (workbook.Sheets['出租率趋势']) {
        workbook.Sheets['出租率趋势']['!cols'] = [{ wch: 12 }, { wch: 12 }, { wch: 15 }, { wch: 15 }]
      }

      // 生成文件名
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
      const defaultFilename = `资产分析报告_${timestamp}.xlsx`
      const finalFilename = filename || defaultFilename

      // 导出文件
      XLSX.writeFile(workbook, finalFilename)

    } catch (error) {
      console.error('导出Excel失败:', error)
      throw new Error('导出失败，请重试')
    }
  }

  /**
   * 导出为CSV格式
   */
  async exportToCSV(data: AnalyticsExportData, filename?: string): Promise<void> {
    try {
      // 合并所有数据到一个CSV
      const csvData = []

      // 添加概览数据
      csvData.push(['概览统计'])
      csvData.push(['指标', '数值', '单位'])
      csvData.push(['资产总数', data.summary.total_assets, '个'])
      csvData.push(['总面积', data.summary.total_area.toFixed(2), '㎡'])
      csvData.push(['可租面积', data.summary.total_rentable_area.toFixed(2), '㎡'])
      csvData.push(['整体出租率', data.summary.occupancy_rate.toFixed(2), '%'])
      csvData.push(['年收入', data.summary.total_annual_income.toFixed(2), '元'])
      csvData.push(['年支出', data.summary.total_annual_expense.toFixed(2), '元'])
      csvData.push(['净收益', data.summary.total_net_income.toFixed(2), '元'])
      csvData.push(['月租金', data.summary.total_monthly_rent.toFixed(2), '元'])
      csvData.push([])

      // 添加物业性质分布
      csvData.push(['物业性质分布'])
      csvData.push(['物业性质', '数量', '占比(%)'])
      data.property_nature_distribution.forEach(item => {
        csvData.push([item.name, item.count, item.percentage])
      })
      csvData.push([])

      // 添加确权状态分布
      csvData.push(['确权状态分布'])
      csvData.push(['确权状态', '数量', '占比(%)'])
      data.ownership_status_distribution.forEach(item => {
        csvData.push([item.status, item.count, item.percentage])
      })
      csvData.push([])

      // 添加使用状态分布
      csvData.push(['使用状态分布'])
      csvData.push(['使用状态', '数量', '占比(%)'])
      data.usage_status_distribution.forEach(item => {
        csvData.push([item.status, item.count, item.percentage])
      })
      csvData.push([])

      // 添加业态类别分布
      csvData.push(['业态类别分布'])
      csvData.push(['业态类别', '数量', '出租率(%)'])
      data.business_category_distribution.forEach(item => {
        csvData.push([item.category, item.count, item.occupancy_rate])
      })

      // 转换为CSV格式
      const csvContent = csvData
        .map(row => row.map(cell => `"${cell}"`).join(','))
        .join('\n')

      // 添加BOM以支持中文
      const BOM = '\uFEFF'
      const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })

      // 生成文件名
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
      const defaultFilename = `资产分析报告_${timestamp}.csv`
      const finalFilename = filename || defaultFilename

      // 下载文件
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', finalFilename)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

    } catch (error) {
      console.error('导出CSV失败:', error)
      throw new Error('导出失败，请重试')
    }
  }

  /**
   * 导出为PDF格式（简化版本，实际项目中可以使用jsPDF等库）
   */
  async exportToPDF(data: AnalyticsExportData, filename?: string): Promise<void> {
    try {
      // 这里创建一个HTML格式的报告，用户可以另存为PDF
      const htmlContent = this.generateHTMLReport(data)

      const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8;' })
      const url = URL.createObjectURL(blob)

      // 生成文件名
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
      const defaultFilename = `资产分析报告_${timestamp}.html`
      const finalFilename = filename || defaultFilename

      const link = document.createElement('a')
      link.setAttribute('href', url)
      link.setAttribute('download', finalFilename)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

    } catch (error) {
      console.error('导出PDF失败:', error)
      throw new Error('导出失败，请重试')
    }
  }

  /**
   * 生成HTML报告
   */
  private generateHTMLReport(data: AnalyticsExportData): string {
    return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>资产分析报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .section h2 { color: #333; border-bottom: 2px solid #1890ff; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f5f5f5; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .summary-card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .summary-card h3 { margin: 0 0 10px 0; color: #1890ff; }
        .summary-card .value { font-size: 24px; font-weight: bold; color: #333; }
        .summary-card .unit { font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>资产分析报告</h1>
        <p>生成时间: ${new Date().toLocaleString('zh-CN')}</p>
    </div>

    <div class="section">
        <h2>概览统计</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>资产总数</h3>
                <div class="value">${data.summary.total_assets}</div>
                <div class="unit">个</div>
            </div>
            <div class="summary-card">
                <h3>总面积</h3>
                <div class="value">${data.summary.total_area.toFixed(2)}</div>
                <div class="unit">㎡</div>
            </div>
            <div class="summary-card">
                <h3>可租面积</h3>
                <div class="value">${data.summary.total_rentable_area.toFixed(2)}</div>
                <div class="unit">㎡</div>
            </div>
            <div class="summary-card">
                <h3>整体出租率</h3>
                <div class="value">${data.summary.occupancy_rate.toFixed(2)}</div>
                <div class="unit">%</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>物业性质分布</h2>
        <table>
            <thead>
                <tr><th>物业性质</th><th>数量</th><th>占比(%)</th></tr>
            </thead>
            <tbody>
                ${data.property_nature_distribution.map(item =>
                  `<tr><td>${item.name}</td><td>${item.count}</td><td>${item.percentage}</td></tr>`
                ).join('')}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>确权状态分布</h2>
        <table>
            <thead>
                <tr><th>确权状态</th><th>数量</th><th>占比(%)</th></tr>
            </thead>
            <tbody>
                ${data.ownership_status_distribution.map(item =>
                  `<tr><td>${item.status}</td><td>${item.count}</td><td>${item.percentage}</td></tr>`
                ).join('')}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>使用状态分布</h2>
        <table>
            <thead>
                <tr><th>使用状态</th><th>数量</th><th>占比(%)</th></tr>
            </thead>
            <tbody>
                ${data.usage_status_distribution.map(item =>
                  `<tr><td>${item.status}</td><td>${item.count}</td><td>${item.percentage}</td></tr>`
                ).join('')}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>业态类别分布</h2>
        <table>
            <thead>
                <tr><th>业态类别</th><th>数量</th><th>出租率(%)</th></tr>
            </thead>
            <tbody>
                ${data.business_category_distribution.map(item =>
                  `<tr><td>${item.category}</td><td>${item.count}</td><td>${item.occupancy_rate}</td></tr>`
                ).join('')}
            </tbody>
        </table>
    </div>

    ${data.occupancy_trend && data.occupancy_trend.length > 0 ? `
    <div class="section">
        <h2>出租率趋势</h2>
        <table>
            <thead>
                <tr><th>日期</th><th>出租率(%)</th><th>已租面积(㎡)</th><th>可租面积(㎡)</th></tr>
            </thead>
            <tbody>
                ${data.occupancy_trend.map(item =>
                  `<tr><td>${item.date}</td><td>${item.occupancy_rate}</td><td>${item.total_rented_area}</td><td>${item.total_rentable_area}</td></tr>`
                ).join('')}
            </tbody>
        </table>
    </div>
    ` : ''}
</body>
</html>
    `.trim()
  }
}

// 导出单例实例
export const analyticsExportService = new AnalyticsExportService()

// 导出工具函数
export const exportAnalyticsData = async (
  data: AnalyticsExportData,
  format: 'excel' | 'csv' | 'pdf' = 'excel',
  filename?: string
): Promise<void> => {
  switch (format) {
    case 'excel':
      return analyticsExportService.exportToExcel(data, filename)
    case 'csv':
      return analyticsExportService.exportToCSV(data, filename)
    case 'pdf':
      return analyticsExportService.exportToPDF(data, filename)
    default:
      throw new Error('不支持的导出格式')
  }
}