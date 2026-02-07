import React, { useState } from 'react';
import { Form } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { useMutation, useQuery } from '@tanstack/react-query';

import type { AssetSearchParams } from '@/types/asset';
import { assetService } from '@/services/assetService';
import type { ExportTask } from '@/services/assetService';

import AssetExportForm from './AssetExportForm';
import AssetExportHistoryModal from './AssetExportHistoryModal';
import AssetExportProgress from './AssetExportProgress';
import {
  AVAILABLE_EXPORT_FIELDS,
  type ExportFormValues,
  type ExportOptions,
  type ExportTaskWithApiFields,
} from './assetExportConfig';

interface AssetExportProps {
  searchParams?: AssetSearchParams;
  selectedAssetIds?: string[];
  onExportComplete?: (task: ExportTask) => void;
}

const AssetExport: React.FC<AssetExportProps> = ({
  searchParams,
  selectedAssetIds,
  onExportComplete,
}) => {
  const [form] = Form.useForm();
  const [exportTask, setExportTask] = useState<ExportTaskWithApiFields | null>(null);
  const [historyVisible, setHistoryVisible] = useState(false);

  // 获取导出历史
  const { data: exportHistory, refetch: refetchHistory } = useQuery({
    queryKey: ['export-history'],
    queryFn: () => assetService.getExportHistory(),
    refetchInterval: 5000, // 每5秒刷新一次
  });

  // 轮询导出状态
  const pollExportStatus = (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const task = await assetService.getExportStatus(taskId);
        setExportTask(task);

        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(interval);
          refetchHistory();

          if (task.status === 'completed') {
            MessageManager.success('导出完成！');
            onExportComplete?.(task);
          } else {
            MessageManager.error(task.error_message ?? '导出失败');
          }
        }
      } catch {
        clearInterval(interval);
        MessageManager.error('获取导出状态失败');
      }
    }, 2000);
  };

  // 导出数据
  const exportMutation = useMutation({
    mutationFn: async (options: ExportOptions): Promise<ExportTaskWithApiFields> => {
      const blob =
        selectedAssetIds !== undefined && selectedAssetIds !== null && selectedAssetIds.length > 0
          ? await assetService.exportSelectedAssets(selectedAssetIds, options)
          : await assetService.exportAssets(options.filters || searchParams, options);

      // 如果返回的是Blob，说明没有任务ID，直接下载
      if (blob instanceof Blob) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `assets_export_${new Date().toISOString().split('T')[0]}.${options.format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        const task: ExportTaskWithApiFields = {
          id: `direct_${Date.now()}`,
          status: 'completed',
          progress: 100,
          download_url: url,
          filename: `assets_export_${new Date().toISOString().split('T')[0]}.${options.format}`,
          total_records: 0,
          file_size: blob.size,
          created_at: new Date().toISOString(),
        };
        return task;
      }

      // 否则应该返回任务对象，但这里返回Blob是错误的设计
      throw new Error('导出服务返回了意外的响应格式');
    },
    onSuccess: task => {
      setExportTask(task);
      MessageManager.success('导出任务已创建，正在处理...');

      // 开始轮询导出状态
      pollExportStatus(task.id);
    },
    onError: (error: unknown) => {
      MessageManager.error((error as Error).message || '导出失败');
    },
  });

  // 开始导出
  const handleExport = () => {
    form.validateFields().then((values: ExportFormValues) => {
      const options: ExportOptions = {
        format: values.format ?? 'xlsx',
        includeHeaders: values.includeHeaders !== false,
        selectedFields: values.selectedFields ?? AVAILABLE_EXPORT_FIELDS.map(field => field.key),
        filters: searchParams,
      };

      exportMutation.mutate(options);
    });
  };

  // 下载文件
  const handleDownload = async (task: ExportTaskWithApiFields) => {
    const downloadUrl = task.download_url ?? '';
    if (downloadUrl === '') return;

    try {
      await assetService.downloadExportFile(downloadUrl);
      MessageManager.success('下载成功');
    } catch (error: unknown) {
      MessageManager.error((error as Error).message || '下载失败');
    }
  };

  // 删除导出记录
  const handleDeleteExportRecord = async (id: string) => {
    try {
      await assetService.deleteExportRecord(id);
      MessageManager.success('删除成功');
      refetchHistory();
    } catch (error: unknown) {
      MessageManager.error((error as Error).message || '删除失败');
    }
  };

  return (
    <div>
      <AssetExportForm
        form={form}
        availableFields={AVAILABLE_EXPORT_FIELDS}
        selectedAssetIds={selectedAssetIds}
        searchParams={searchParams}
        isExporting={exportMutation.isPending}
        onExport={handleExport}
        onShowHistory={() => setHistoryVisible(true)}
      >
        {exportTask && (
          <AssetExportProgress exportTask={exportTask} onDownload={handleDownload} />
        )}
      </AssetExportForm>

      <AssetExportHistoryModal
        open={historyVisible}
        exportHistory={exportHistory}
        onClose={() => setHistoryVisible(false)}
        onDownload={handleDownload}
        onDelete={handleDeleteExportRecord}
      />
    </div>
  );
};

export default AssetExport;
