import React, { useState } from "react";
import {
  Card,
  Form,
  Select,
  Checkbox,
  Button,
  Space,
  Alert,
  Progress,
  Typography,
  Divider,
  Row,
  Col,
  Tag,
  Modal,
  List,
  Tooltip,
} from "antd";
import { MessageManager } from "@/utils/messageManager";
import {
  DownloadOutlined,
  FileExcelOutlined,
  HistoryOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { COLORS } from "@/styles/colorMap";

import type { AssetSearchParams } from "@/types/asset";
import { assetService } from "@/services/assetService";
import type { ExportTask } from "@/services/assetService";

const { Option } = Select;
const { Title, Text } = Typography;

interface ExportOptions {
  format: "xlsx" | "csv";
  includeHeaders: boolean;
  selectedFields: string[];
  filters?: AssetSearchParams;
}

interface ExportFormValues {
  format?: "xlsx" | "csv";
  includeHeaders?: boolean;
  selectedFields?: string[];
}

// 扩展ExportTask接口以匹配API返回的实际字段名
interface ExportTaskWithApiFields {
  id: string;
  status: "pending" | "running" | "processing" | "completed" | "failed";
  progress: number;
  download_url?: string;
  downloadUrl?: string;  // 兼容原有字段
  filename?: string;
  total_records?: number;
  file_size?: number;
  created_at: string;
  createdAt?: string;  // 兼容原有字段
  completedAt?: string;
  errorMessage?: string;
}

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

  // 可导出的字段配置
  const availableFields = [
    { key: "property_name", label: "物业名称", required: true },
    { key: "ownership_entity", label: "权属方", required: true },
    { key: "management_entity", label: "经营管理方" },
    { key: "address", label: "所在地址", required: true },
    { key: "land_area", label: "土地面积" },
    { key: "actual_property_area", label: "实际房产面积" },
    { key: "rentable_area", label: "可出租面积" },
    { key: "rented_area", label: "已出租面积" },
    { key: "unrented_area", label: "未出租面积" },
    { key: "non_commercial_area", label: "非经营物业面积" },
    { key: "ownership_status", label: "确权状态", required: true },
    { key: "property_nature", label: "物业性质", required: true },
    { key: "usage_status", label: "使用状态", required: true },
    { key: "certificated_usage", label: "证载用途" },
    { key: "actual_usage", label: "实际用途" },
    { key: "business_category", label: "业态类别" },
    { key: "business_model", label: "接收模式" },
    { key: "occupancy_rate", label: "出租率" },
    { key: "tenant_name", label: "租户名称" },
    { key: "lease_contract", label: "承租合同" },
    { key: "current_contract_start_date", label: "合同开始日期" },
    { key: "current_contract_end_date", label: "合同结束日期" },
    { key: "is_litigated", label: "是否涉诉" },
    { key: "include_in_occupancy_rate", label: "是否计入出租率" },
    { key: "wuyang_project_name", label: "五羊项目名称" },
    { key: "agreement_start_date", label: "接收协议开始日期" },
    { key: "agreement_end_date", label: "接收协议结束日期" },
    { key: "description", label: "说明" },
    { key: "notes", label: "其他备注" },
    { key: "created_at", label: "创建时间" },
    { key: "updated_at", label: "更新时间" },
  ];

  // 获取导出历史
  const { data: exportHistory, refetch: refetchHistory } = useQuery({
    queryKey: ["export-history"],
    queryFn: () => assetService.getExportHistory() as Promise<ExportTaskWithApiFields[]>,
    refetchInterval: 5000, // 每5秒刷新一次
  });

  // 导出数据
  const exportMutation = useMutation({
    mutationFn: async (options: ExportOptions): Promise<ExportTaskWithApiFields> => {
      const blob = selectedAssetIds !== undefined && selectedAssetIds !== null && selectedAssetIds.length > 0
        ? await assetService.exportSelectedAssets(selectedAssetIds, options)
        : await assetService.exportAssets(options.filters || searchParams, options);

      // 如果返回的是Blob，说明没有任务ID，直接下载
      if (blob instanceof Blob) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `assets_export_${new Date().toISOString().split('T')[0]}.${options.format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        const task: ExportTaskWithApiFields = {
          id: `direct_${Date.now()}`,
          status: "completed",
          progress: 100,
          downloadUrl: url,
          createdAt: new Date().toISOString(),
          filename: `assets_export_${new Date().toISOString().split('T')[0]}.${options.format}`,
          total_records: 0,
          file_size: blob.size,
          created_at: new Date().toISOString(),
        };
        return task;
      }

      // 否则应该返回任务对象，但这里返回Blob是错误的设计
      throw new Error("导出服务返回了意外的响应格式");
    },
    onSuccess: (task) => {
      setExportTask(task);
      MessageManager.success("导出任务已创建，正在处理...");

      // 开始轮询导出状态
      pollExportStatus(task.id);
    },
    onError: (error: unknown) => {
      MessageManager.error((error as Error).message || "导出失败");
    },
  });

  // 轮询导出状态
  const pollExportStatus = (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const task = await assetService.getExportStatus(taskId) as ExportTaskWithApiFields;
        setExportTask(task);

        if (task.status === "completed" || task.status === "failed") {
          clearInterval(interval);
          refetchHistory();

          if (task.status === "completed") {
            MessageManager.success("导出完成！");
            // 转换为标准ExportTask类型
            const standardTask: ExportTask = {
              id: task.id,
              status: task.status,
              progress: task.progress,
              downloadUrl: task.download_url ?? task.downloadUrl,
              createdAt: task.created_at ?? task.createdAt ?? new Date().toISOString(),
              completedAt: task.completedAt,
              errorMessage: task.errorMessage,
            };
            onExportComplete?.(standardTask);
          } else {
            MessageManager.error(task.errorMessage ?? "导出失败");
          }
        }
      } catch {
        clearInterval(interval);
        MessageManager.error("获取导出状态失败");
      }
    }, 2000);
  };

  // 开始导出
  const handleExport = () => {
    form.validateFields().then((values: ExportFormValues) => {
      const options: ExportOptions = {
        format: values.format ?? "xlsx",
        includeHeaders: values.includeHeaders !== false,
        selectedFields: values.selectedFields ?? availableFields.map((f) => f.key),
        filters: searchParams,
      };

      exportMutation.mutate(options);
    });
  };

  // 下载文件
  const handleDownload = async (task: ExportTaskWithApiFields) => {
    const downloadUrl = task.download_url ?? task.downloadUrl ?? '';
    if (downloadUrl === '') return;

    try {
      await assetService.downloadExportFile(downloadUrl);
      MessageManager.success("下载成功");
    } catch (error: unknown) {
      MessageManager.error((error as Error).message || "下载失败");
    }
  };

  // 删除导出记录
  const handleDeleteExportRecord = async (id: string) => {
    try {
      await assetService.deleteExportRecord(id);
      MessageManager.success("删除成功");
      refetchHistory();
    } catch (error: unknown) {
      MessageManager.error((error as Error).message || "删除失败");
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes?: number) => {
    if (bytes === undefined || bytes === null || bytes === 0) return "-";

    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  // 获取状态显示文本
  const getStatusText = (status: string) => {
    switch (status) {
      case "pending":
        return "等待中";
      case "running":
      case "processing":
        return "处理中";
      case "completed":
        return "完成";
      case "failed":
        return "失败";
      default:
        return status;
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "green";
      case "failed":
        return "red";
      case "running":
      case "processing":
        return "blue";
      default:
        return "default";
    }
  };

  return (
    <div>
      {/* 导出配置 */}
      <Card
        title={
          <Space>
            <FileExcelOutlined />
            数据导出
            {selectedAssetIds !== undefined && selectedAssetIds !== null && selectedAssetIds.length > 0 && (
              <Tag color="blue">已选择 {selectedAssetIds.length} 条记录</Tag>
            )}
          </Space>
        }
        extra={
          <Button icon={<HistoryOutlined />} onClick={() => setHistoryVisible(true)}>
            导出历史
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            format: "xlsx",
            includeHeaders: true,
            selectedFields: availableFields.filter((f) => f.required === true).map((f) => f.key),
          }}
        >
          <Row gutter={16}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item name="format" label="导出格式">
                <Select>
                  <Option value="xlsx">Excel (.xlsx)</Option>
                  <Option value="csv">CSV (.csv)</Option>
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={8}>
              <Form.Item name="includeHeaders" valuePropName="checked">
                <Checkbox>包含表头</Checkbox>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="selectedFields" label="选择导出字段">
            <Checkbox.Group style={{ width: "100%" }}>
              <Row gutter={[16, 8]}>
                {availableFields.map((field) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={field.key}>
                    <Checkbox value={field.key} disabled={field.required}>
                      {field.label}
                      {field.required === true && <Text type="secondary"> *</Text>}
                    </Checkbox>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
          </Form.Item>

          {/* 筛选条件预览 */}
          {(searchParams !== undefined || (selectedAssetIds !== undefined && selectedAssetIds !== null && selectedAssetIds.length > 0)) && (
            <div>
              <Divider orientation="left">导出范围</Divider>

              {selectedAssetIds !== undefined && selectedAssetIds !== null && selectedAssetIds.length > 0 ? (
                <Alert
                  message={`将导出已选择的 ${selectedAssetIds.length} 条资产记录`}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              ) : (
                searchParams && (
                  <Alert
                    message="将根据当前搜索条件导出匹配的资产记录"
                    description={
                      <div style={{ marginTop: 8 }}>
                        <Space wrap>
                          {Object.entries(searchParams).map(([key, value]) => {
                            if (value === undefined || value === null || value === "") {
                              return null;
                            }

                            const fieldNames: Record<string, string> = {
                              search: "关键词",
                              ownership_status: "确权状态",
                              property_nature: "物业性质",
                              usage_status: "使用状态",
                              ownership_entity: "权属方",
                              management_entity: "管理方",
                              business_category: "业态类别",
                            };

                            const displayKey = fieldNames[key] || key;
                            const displayValue =
                              typeof value === "boolean" ? (value ? "是" : "否") : String(value);

                            return (
                              <Tag key={key}>
                                {displayKey}: {displayValue}
                              </Tag>
                            );
                          })}
                        </Space>
                      </div>
                    }
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )
              )}
            </div>
          )}

          <Form.Item>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={exportMutation.isPending}
              size="large"
            >
              开始导出
            </Button>
          </Form.Item>
        </Form>

        {/* 导出进度 */}
        {exportTask && (
          <div style={{ marginTop: 24, padding: 16, background: "#fafafa", borderRadius: 8 }}>
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Title level={5} style={{ margin: 0 }}>
                  {exportTask.status === "completed"
                    ? "导出完成"
                    : exportTask.status === "failed"
                      ? "导出失败"
                      : "正在导出..."}
                </Title>
                {(exportTask.status === "running" || exportTask.status === "processing") && <LoadingOutlined />}
                {exportTask.status === "completed" && (
                  <CheckCircleOutlined style={{ color: COLORS.success }} />
                )}
              </Space>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <Text>文件名: {exportTask.filename}</Text>
                <Text>记录数: {exportTask.total_records ?? 0}</Text>
              </div>

              {(exportTask.status === "running" || exportTask.status === "processing") && (
                <Progress
                  percent={exportTask.progress}
                  status="active"
                  format={(percent) => `${percent}%`}
                />
              )}

              {exportTask.status === "completed" && (
                <div>
                  <div style={{ marginBottom: 8 }}>
                    <Text type="secondary">文件大小: {formatFileSize(exportTask.file_size)}</Text>
                  </div>
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    onClick={() => handleDownload(exportTask)}
                  >
                    下载文件
                  </Button>
                </div>
              )}

              {exportTask.status === "failed" && (
                <Alert
                  message="导出失败"
                  description={exportTask.errorMessage}
                  type="error"
                  showIcon
                />
              )}
            </div>
          </div>
        )}
      </Card>

      {/* 导出历史模态框 */}
      <Modal
        title="导出历史"
        open={historyVisible}
        onCancel={() => setHistoryVisible(false)}
        footer={[
          <Button key="close" onClick={() => setHistoryVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        <List
          dataSource={exportHistory}
          renderItem={(item: ExportTaskWithApiFields) => (
            <List.Item
              actions={[
                item.status === "completed" && (item.download_url !== undefined || item.downloadUrl !== undefined) && (
                  <Tooltip key="download" title="下载文件">
                    <Button
                      type="text"
                      icon={<DownloadOutlined />}
                      onClick={() => handleDownload(item)}
                    />
                  </Tooltip>
                ),
                <Tooltip key="delete" title="删除记录">
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => {
                      Modal.confirm({
                        title: "确认删除",
                        content: "确定要删除这条导出记录吗？",
                        onOk: () => handleDeleteExportRecord(item.id),
                      });
                    }}
                  />
                </Tooltip>,
              ].filter(Boolean)}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{item.filename}</Text>
                    <Tag color={getStatusColor(item.status)}>
                      {getStatusText(item.status)}
                    </Tag>
                  </Space>
                }
                description={
                  <div>
                    <div>创建时间: {new Date(item.created_at).toLocaleString()}</div>
                    <div>
                      记录数: {item.total_records ?? 0} | 文件大小: {formatFileSize(item.file_size)}
                    </div>
                    {(item.status === "running" || item.status === "processing") && (
                      <Progress percent={item.progress} size="small" style={{ marginTop: 4 }} />
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
};

export default AssetExport;
