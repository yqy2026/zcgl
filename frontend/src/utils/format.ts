// 格式化工具函数

/**
 * 格式化数字为千分位
 */
export const formatNumber = (value: number | string | undefined | null): string => {
  if (value === undefined || value === null || value === '') {
    return '-';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return '-';
  }

  return num.toLocaleString();
};

/**
 * 格式化面积（平方米）
 */
export const formatArea = (value: number | string | undefined | null): string => {
  if (value === undefined || value === null || value === '') {
    return '-';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return '-';
  }

  return `${formatNumber(num)} ㎡`;
};

/**
 * 格式化百分比
 */
export const formatPercentage = (value: number | string | undefined | null): string => {
  if (value === undefined || value === null || value === '') {
    return '-';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return '-';
  }

  return `${num.toFixed(2)}%`;
};

/**
 * 格式化日期
 */
export const formatDate = (
  date: string | Date | undefined | null,
  format: 'date' | 'datetime' | 'time' = 'date'
): string => {
  if (date === null || date === undefined) {
    return '-';
  }

  const d = new Date(date);
  if (isNaN(d.getTime())) {
    return '-';
  }

  switch (format) {
    case 'date':
      return d.toLocaleDateString('zh-CN');
    case 'datetime':
      return d.toLocaleString('zh-CN');
    case 'time':
      return d.toLocaleTimeString('zh-CN');
    default:
      return d.toLocaleDateString('zh-CN');
  }
};

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) {
    return '0 B';
  }

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

/**
 * 格式化货币
 */
export const formatCurrency = (value: number | undefined | null, currency = '¥'): string => {
  if (value === undefined || value === null) {
    return '-';
  }

  return `${currency}${formatNumber(value)}`;
};

/**
 * 截断文本
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.substring(0, maxLength)}...`;
};

/**
 * 获取状态颜色
 */
export const getStatusColor = (
  status: string,
  type: 'ownership' | 'property' | 'usage'
): string => {
  const colorMaps = {
    ownership: {
      已确权: 'green',
      未确权: 'red',
      部分确权: 'orange',
    },
    property: {
      经营性: 'blue',
      非经营性: 'default',
    },
    usage: {
      出租: 'green',
      空置: 'red',
      自用: 'blue',
      公房: 'purple',
      待移交: 'orange',
      待处置: 'orange',
      其他: 'default',
    },
  };

  const colorMap = colorMaps[type] as Record<string, string>;
  return colorMap[status] || 'default';
};

/**
 * 计算出租率
 */
export const calculateOccupancyRate = (
  rentedArea: number | string | undefined | null,
  rentableArea: number | string | undefined | null
): number => {
  if (
    rentedArea === null ||
    rentedArea === undefined ||
    rentableArea === null ||
    rentableArea === undefined ||
    rentedArea === 0 ||
    rentedArea === ''
  ) {
    return 0;
  }

  const rented = typeof rentedArea === 'string' ? parseFloat(rentedArea) : rentedArea;
  const rentable = typeof rentableArea === 'string' ? parseFloat(rentableArea) : rentableArea;

  if (isNaN(rented) || isNaN(rentable) || rentable === 0) {
    return 0;
  }

  return (rented / rentable) * 100;
};

/**
 * 验证是否为有效的数字
 */
export const isValidNumber = (value: unknown): boolean => {
  return !isNaN(parseFloat(value as string)) && isFinite(value as number);
};

/**
 * 安全的数字转换
 */
export const safeNumber = (value: unknown, defaultValue = 0): number => {
  if (isValidNumber(value)) {
    return typeof value === 'string' ? parseFloat(value) : Number(value);
  }
  return defaultValue;
};

/**
 * React Hook for formatting functions
 */
export const useFormat = () => {
  return {
    currency: formatCurrency,
  };
};
