export const formatFileSize = (bytes?: number): string => {
  if (bytes === undefined || bytes === null || bytes === 0) return '-';

  const sizes = ['B', 'KB', 'MB', 'GB'];
  const index = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, index)).toFixed(2)} ${sizes[index]}`;
};

export const getStatusText = (status: string): string => {
  switch (status) {
    case 'pending':
      return '等待中';
    case 'running':
    case 'processing':
      return '处理中';
    case 'completed':
      return '完成';
    case 'failed':
      return '失败';
    default:
      return status;
  }
};

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'running':
    case 'processing':
      return 'blue';
    default:
      return 'default';
  }
};
