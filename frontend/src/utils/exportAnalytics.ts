/**
 * Analytics Data Export Utility
 *
 * Exports analytics data to various formats without external dependencies.
 * Uses native browser APIs for CSV export and provides PDF placeholder.
 */

// Simplified analytics data interface for export
interface ExportableAnalyticsData {
  area_summary: {
    total_assets: number;
    total_area: number;
    total_rentable_area: number;
    occupancy_rate: number;
  };
  financial_summary: {
    estimated_annual_income: number;
    total_monthly_rent: number;
    total_deposit: number;
  };
  property_nature_distribution?: Array<{ name: string; count: number; percentage?: number }>;
  ownership_status_distribution?: Array<{ status: string; count: number; percentage?: number }>;
  usage_status_distribution?: Array<{ status: string; count: number; percentage?: number }>;
  occupancy_distribution?: Array<{ range: string; count: number; percentage?: number }>;
  business_category_distribution?: Array<{
    category: string;
    occupancy_rate: number;
    count?: number;
  }>;
  occupancy_trend?: Array<{
    date: string;
    occupancy_rate: number;
    total_rented_area?: number;
    total_rentable_area?: number;
  }>;
}

/**
 * Export analytics data to various formats
 */
export async function exportAnalytics(
  data: ExportableAnalyticsData,
  format: 'excel' | 'pdf' | 'csv'
): Promise<void> {
  const timestamp = new Date().getTime();
  const filename = `analytics_${timestamp}`;

  switch (format) {
    case 'excel':
      await exportToCSV(data, `${filename}.csv`);
      break;
    case 'csv':
      await exportToCSV(data, `${filename}.csv`);
      break;
    case 'pdf':
      await exportToPDF(data, `${filename}.pdf`);
      break;
  }
}

/**
 * Export to CSV format
 */
async function exportToCSV(data: ExportableAnalyticsData, filename: string): Promise<void> {
  // Generate CSV content
  const csvRows: string[] = [];

  // Summary section
  csvRows.push('资产分析报告');
  csvRows.push(`导出时间,${new Date().toLocaleString('zh-CN')}`);
  csvRows.push('');

  // Area Summary
  csvRows.push('面积概览');
  csvRows.push('指标,数值');
  csvRows.push(`资产总数,${data.area_summary.total_assets}`);
  csvRows.push(`总面积(㎡),${data.area_summary.total_area.toFixed(2)}`);
  csvRows.push(`可租面积(㎡),${data.area_summary.total_rentable_area.toFixed(2)}`);
  csvRows.push(`出租率(%),${data.area_summary.occupancy_rate.toFixed(2)}`);
  csvRows.push('');

  // Financial Summary
  csvRows.push('财务概览');
  csvRows.push('指标,数值(元)');
  csvRows.push(`预估年收入,${data.financial_summary.estimated_annual_income.toFixed(2)}`);
  csvRows.push(`月租金总额,${data.financial_summary.total_monthly_rent.toFixed(2)}`);
  csvRows.push(`押金总额,${data.financial_summary.total_deposit.toFixed(2)}`);
  csvRows.push('');

  // Distributions
  if (data.property_nature_distribution && data.property_nature_distribution.length > 0) {
    csvRows.push('物业性质分布');
    csvRows.push('类型,数量,占比(%)');
    data.property_nature_distribution.forEach(item => {
      csvRows.push(`${item.name},${item.count},${item.percentage?.toFixed(2) ?? '0.00'}`);
    });
    csvRows.push('');
  }

  if (data.ownership_status_distribution && data.ownership_status_distribution.length > 0) {
    csvRows.push('确权状态分布');
    csvRows.push('状态,数量,占比(%)');
    data.ownership_status_distribution.forEach(item => {
      csvRows.push(`${item.status},${item.count},${item.percentage?.toFixed(2) ?? '0.00'}`);
    });
    csvRows.push('');
  }

  if (data.usage_status_distribution && data.usage_status_distribution.length > 0) {
    csvRows.push('使用状态分布');
    csvRows.push('状态,数量,占比(%)');
    data.usage_status_distribution.forEach(item => {
      csvRows.push(`${item.status},${item.count},${item.percentage?.toFixed(2) ?? '0.00'}`);
    });
    csvRows.push('');
  }

  if (data.occupancy_distribution && data.occupancy_distribution.length > 0) {
    csvRows.push('出租率区间分布');
    csvRows.push('区间,数量,占比(%)');
    data.occupancy_distribution.forEach(item => {
      csvRows.push(`${item.range},${item.count},${item.percentage?.toFixed(2) ?? '0.00'}`);
    });
    csvRows.push('');
  }

  if (data.business_category_distribution && data.business_category_distribution.length > 0) {
    csvRows.push('业态类别出租率');
    csvRows.push('类别,出租率(%),数量');
    data.business_category_distribution.forEach(item => {
      csvRows.push(`${item.category},${item.occupancy_rate.toFixed(2)},${item.count ?? 0}`);
    });
    csvRows.push('');
  }

  if (data.occupancy_trend && data.occupancy_trend.length > 0) {
    csvRows.push('出租率趋势');
    csvRows.push('日期,出租率(%),已租面积(㎡),可租面积(㎡)');
    data.occupancy_trend.forEach(item => {
      csvRows.push(
        `${item.date},${item.occupancy_rate.toFixed(2)},${item.total_rented_area?.toFixed(2) ?? '0.00'},${item.total_rentable_area?.toFixed(2) ?? '0.00'}`
      );
    });
    csvRows.push('');
  }

  // Create CSV blob and download
  const csvContent = csvRows.join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export to PDF format (placeholder - requires external library)
 */
async function exportToPDF(data: ExportableAnalyticsData, filename: string): Promise<void> {
  // PDF export requires external library like jsPDF
  // For now, export as text file with formatted content
  const lines: string[] = [];

  lines.push('资产分析报告');
  lines.push(`=${'='.repeat(50)}`);
  lines.push(`导出时间: ${new Date().toLocaleString('zh-CN')}`);
  lines.push('');

  lines.push('面积概览');
  lines.push('-'.repeat(30));
  lines.push(`资产总数: ${data.area_summary.total_assets} 个`);
  lines.push(`总面积: ${data.area_summary.total_area.toFixed(2)} ㎡`);
  lines.push(`可租面积: ${data.area_summary.total_rentable_area.toFixed(2)} ㎡`);
  lines.push(`出租率: ${data.area_summary.occupancy_rate.toFixed(2)} %`);
  lines.push('');

  lines.push('财务概览');
  lines.push('-'.repeat(30));
  lines.push(`预估年收入: ¥${data.financial_summary.estimated_annual_income.toFixed(2)} 元`);
  lines.push(`月租金总额: ¥${data.financial_summary.total_monthly_rent.toFixed(2)} 元`);
  lines.push(`押金总额: ¥${data.financial_summary.total_deposit.toFixed(2)} 元`);
  lines.push('');

  if (data.property_nature_distribution && data.property_nature_distribution.length > 0) {
    lines.push('物业性质分布');
    lines.push('-'.repeat(30));
    data.property_nature_distribution.forEach(item => {
      lines.push(`  ${item.name}: ${item.count} (${item.percentage?.toFixed(2) ?? '0.00'}%)`);
    });
    lines.push('');
  }

  if (data.occupancy_trend && data.occupancy_trend.length > 0) {
    lines.push('出租率趋势');
    lines.push('-'.repeat(30));
    data.occupancy_trend.forEach(item => {
      lines.push(`  ${item.date}: ${item.occupancy_rate.toFixed(2)}%`);
    });
    lines.push('');
  }

  const content = lines.join('\n');
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename.replace('.pdf', '.txt'));
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  console.warn('PDF export requires external library (jsPDF). Exported as text file instead.');
  console.info('To enable PDF export, install jsPDF: pnpm add jspdf');
}

export default {
  exportAnalytics,
};
