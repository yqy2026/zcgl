import React, { useState } from "react";
import {
  Card,
  Typography,
  Upload,
  Button,
  Progress,
  Space,
  Alert,
  Steps,
  Table,
  Row,
  Col,
  Statistic,
  Divider,
  Switch,
  Form,
  InputNumber,
  Select,
} from "antd";
import { MessageManager } from "@/utils/messageManager";
import type { ColumnsType } from "antd/es/table";
import {
  UploadOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import type { UploadProps, UploadFile } from "antd";
import { enhancedApiClient } from "@/api/client";
import { STANDARD_SHEET_NAME, IMPORT_INSTRUCTIONS } from "../../config/excelConfig";
import { createLogger } from "@/utils/logger";
import { COLORS } from "@/styles/colorMap";

const importLogger = createLogger('AssetImport');

const { Title, Text } = Typography;
const { Step } = Steps;
const { Option } = Select;

interface ImportResult {
  success: number;
  failed: number;
  total: number;
  errors: string[];
  message: string;
  processing_time?: number;
  filename?: string;
  performance_metrics?: {
    records_per_second: number;
    estimated_time_for_1000: number;
  };
}

interface ImportConfig {
  useOptimized: boolean;
  batchSize: number;
  skipErrors: boolean;
  timeout: number;
}

const OptimizedAssetImport: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [progress, setProgress] = useState(0);
  const [showConfig, setShowConfig] = useState(false);
  const [config, setConfig] = useState<ImportConfig>({
    useOptimized: true,
    batchSize: 100,
    skipErrors: true,
    timeout: 600, // 10分钟
  });

  // 下载模板
  const handleDownloadTemplate = async () => {
    try {
      const response = await enhancedApiClient.get("/excel/template", {
        responseType: "blob",
      });

      const blob = new Blob([response.data as BlobPart]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "land_property_asset_template.xlsx";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      MessageManager.success("模板下载成功");
    } catch {
      MessageManager.error("模板下载失败");
    }
  };

  // 文件上传配置
  const uploadProps: UploadProps = {
    fileList,
    beforeUpload: (file) => {
      const isExcel =
        file.type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
        file.type === "application/vnd.ms-excel";

      if (!isExcel) {
        MessageManager.error("只能上传Excel文件(.xlsx, .xls)");
        return false;
      }

      const isLt50M = file.size / 1024 / 1024 < 50;
      if (!isLt50M) {
        MessageManager.error("文件大小不能超过50MB");
        return false;
      }

      setFileList([file]);
      setCurrentStep(1);
      return false;
    },
    onRemove: () => {
      setFileList([]);
      setCurrentStep(0);
      setImportResult(null);
    },
    maxCount: 1,
  };

  // 模拟进度条
  const simulateProgress = () => {
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) {
          clearInterval(interval);
          return 95;
        }
        return prev + Math.random() * 10;
      });
    }, 500);
    return interval;
  };

  // 执行导入
  const handleImport = async () => {
    if (fileList.length === 0) {
      MessageManager.error("请先选择要导入的文件");
      return;
    }

    setUploading(true);
    const progressInterval = simulateProgress();

    try {
      const formData = new FormData();
      // Get the actual File object from UploadFile
      const file = fileList[0]?.originFileObj;
      if (file) {
        formData.append("file", file);
      }

      // Start enhanced import process
      setUploading(true);

      const endpoint = config.useOptimized ? "/excel/import/optimized" : "/excel/import";

      const response = await enhancedApiClient.post(endpoint, formData, {
        params: {
          sheet_name: STANDARD_SHEET_NAME,
          skip_errors: config.skipErrors,
        },
        timeout: config.timeout * 1000,
      });

      clearInterval(progressInterval);
      setProgress(100);

      const result = response.data as ImportResult;
      // Import completed successfully
      // console.log('=== 导入结果 ===')
      // console.log('响应数据:', result)

      setImportResult(result);
      setCurrentStep(2);

      // 显示性能信息
      if (result.processing_time !== undefined && result.processing_time !== null) {
        MessageManager.success(`🎉 导入完成！用时 ${result.processing_time} 秒`);
      } else {
        MessageManager.success(`🎉 导入完成！成功导入 ${result.success} 条记录`);
      }
    } catch (err: unknown) {
      clearInterval(progressInterval);
      importLogger.error('导入错误', err instanceof Error ? err : new Error(String(err)));

      interface ErrorResponse {
        response?: { data?: Partial<ImportResult> };
        message?: string;
      }
      const error = err as ErrorResponse;
      importLogger.error('错误响应', error.response?.data ? new Error(JSON.stringify(error.response.data)) : new Error('Unknown error'));

      const errorResult: ImportResult = {
        success: 0,
        failed: 0,
        total: 0,
        errors: [error.message ?? '网络错误'],
        message: '导入失败',
        processing_time: 0,
        filename: fileList[0]?.name,
      };

      setImportResult(errorResult);
      setCurrentStep(2);
      MessageManager.error(`❌ 导入失败: ${errorResult.errors[0] ?? '未知错误'}`);
    } finally {
      setUploading(false);
    }
  };

  // 重新开始
  const handleReset = () => {
    setCurrentStep(0);
    setFileList([]);
    setImportResult(null);
    setProgress(0);
  };

  // 错误信息表格列
  const errorColumns: ColumnsType<Record<string, unknown>> = [
    {
      title: "序号",
      dataIndex: "index",
      key: "index",
      width: 80,
      render: (_: unknown, __: unknown, index: number) => index + 1,
    },
    {
      title: "错误信息",
      dataIndex: "error",
      key: "error",
      ellipsis: true,
    },
  ];

  const errorData =
    importResult?.errors?.map((error, index) => ({
      key: index,
      error,
    })) || [];

  return (
    <div style={{ padding: "24px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <Title level={2}>
          <FileExcelOutlined /> 数据导入
        </Title>
        <Button type="dashed" icon={<SettingOutlined />} onClick={() => setShowConfig(!showConfig)}>
          {showConfig ? "隐藏配置" : "显示配置"}
        </Button>
      </div>

      {/* 配置面板 */}
      {showConfig && (
        <Card title="导入配置" size="small" style={{ marginBottom: "24px" }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="使用优化导入">
                <Switch
                  checked={config.useOptimized}
                  onChange={(checked) => setConfig((prev) => ({ ...prev, useOptimized: checked }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="超时时间(秒)">
                <InputNumber
                  min={60}
                  max={1800}
                  value={config.timeout}
                  onChange={(value) => setConfig((prev) => ({ ...prev, timeout: value ?? 600 }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="跳过错误">
                <Switch
                  checked={config.skipErrors}
                  onChange={(checked) => setConfig((prev) => ({ ...prev, skipErrors: checked }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="批量大小">
                <Select
                  value={config.batchSize}
                  onChange={(value) => setConfig((prev) => ({ ...prev, batchSize: value || 100 }))}
                >
                  <Option value={50}>50</Option>
                  <Option value={100}>100</Option>
                  <Option value={200}>200</Option>
                  <Option value={500}>500</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>
      )}

      <Card>
        <Steps current={currentStep} style={{ marginBottom: "32px" }}>
          <Step title="选择文件" description="上传Excel文件" />
          <Step title="执行导入" description="处理数据" />
          <Step title="查看结果" description="导入完成" />
        </Steps>

        {/* 步骤0: 选择文件 */}
        {currentStep === 0 && (
          <div>
            <Alert
              message="导入说明"
              description={
                <div>
                  <p>• 支持Excel文件批量导入资产数据</p>
                  <p>• 智能数据验证和错误处理</p>
                  <p>• 实时导入进度反馈</p>
                  <p>• 支持大文件导入 (最大50MB)</p>
                  {IMPORT_INSTRUCTIONS.map((instruction, index) => (
                    <p key={index}>
                      {index + 1}. {instruction}
                    </p>
                  ))}
                </div>
              }
              type="info"
              showIcon
              style={{ marginBottom: "24px" }}
            />

            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12}>
                <Card size="small" title="第一步：下载模板">
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Text>下载标准的Excel导入模板</Text>
                    <Button
                      type="primary"
                      icon={<DownloadOutlined />}
                      onClick={handleDownloadTemplate}
                      block
                    >
                      下载Excel模板
                    </Button>
                  </Space>
                </Card>
              </Col>

              <Col xs={24} sm={12}>
                <Card size="small" title="第二步：上传文件">
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Text>选择填写好的Excel文件</Text>
                    <Upload.Dragger {...uploadProps}>
                      <p className="ant-upload-drag-icon">
                        <FileExcelOutlined style={{ fontSize: "48px", color: COLORS.primary }} />
                      </p>
                      <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                      <p className="ant-upload-hint">
                        支持单个文件上传，仅支持.xlsx和.xls格式，最大50MB
                      </p>
                    </Upload.Dragger>
                  </Space>
                </Card>
              </Col>
            </Row>
          </div>
        )}

        {/* 步骤1: 执行导入 */}
        {currentStep === 1 && (
          <div style={{ textAlign: "center" }}>
            <FileExcelOutlined
              style={{ fontSize: "64px", color: COLORS.success, marginBottom: "16px" }}
            />
            <Title level={4}>文件已选择</Title>
            <Text>文件名：{fileList[0]?.name}</Text>
            <br />
            <Text type="secondary">
              文件大小：{(((fileList[0]?.size ?? 0)) / 1024 / 1024).toFixed(2)} MB
            </Text>

            {uploading && (
              <div style={{ marginTop: "24px" }}>
                <Progress percent={Math.round(progress)} status="active" />
                <Text type="secondary">导入中...</Text>
              </div>
            )}

            <Divider />

            <Space size="large">
              <Button onClick={() => setCurrentStep(0)}>重新选择</Button>
              <Button
                type="primary"
                icon={<UploadOutlined />}
                onClick={handleImport}
                loading={uploading}
                size="large"
              >
                {uploading ? "导入中..." : "开始导入"}
              </Button>
            </Space>
          </div>
        )}

        {/* 步骤2: 查看结果 */}
        {currentStep === 2 && importResult && (
          <div>
            {/* 导入状态概览 */}
            <Card
              size="small"
              style={{
                marginBottom: "24px",
                backgroundColor:
                  importResult.success > 0
                    ? "#f6ffed"
                    : importResult.failed > 0
                      ? "#fff2f0"
                      : "#f0f2f5",
                border:
                  importResult.success > 0
                    ? "1px solid #b7eb8f"
                    : importResult.failed > 0
                      ? "1px solid #ffccc7"
                      : "1px solid #d9d9d9",
              }}
            >
              <div style={{ textAlign: "center", padding: "16px" }}>
                {importResult.success > 0 && importResult.failed === 0 ? (
                  <CheckCircleOutlined style={{ fontSize: "64px", color: COLORS.success }} />
                ) : importResult.success > 0 && importResult.failed > 0 ? (
                  <ExclamationCircleOutlined style={{ fontSize: "64px", color: COLORS.warning }} />
                ) : (
                  <ExclamationCircleOutlined style={{ fontSize: "64px", color: COLORS.error }} />
                )}

                <Title level={3} style={{ marginTop: "8px" }}>
                  {importResult.success > 0 && importResult.failed === 0
                    ? "🎉 导入成功！"
                    : importResult.success > 0 && importResult.failed > 0
                      ? "⚠️ 部分成功"
                      : importResult.failed > 0
                        ? "❌ 导入失败"
                        : "📄 导入完成"}
                </Title>

                <Text type="secondary" style={{ fontSize: "16px" }}>
                  {importResult.processing_time !== undefined && importResult.processing_time !== null && (
                    <span>处理时间: {importResult.processing_time}秒 | </span>
                  )}
                  {importResult.success > 0 && importResult.failed === 0
                    ? `成功导入 ${importResult.success} 条资产记录`
                    : importResult.success > 0 && importResult.failed > 0
                      ? `成功 ${importResult.success} 条，失败 ${importResult.failed} 条，总计 ${importResult.total} 条`
                      : importResult.failed > 0
                        ? `${importResult.failed} 条记录导入失败`
                        : "没有数据被导入，请检查文件格式和内容"}
                </Text>

                {/* 性能指标 */}
                {importResult.performance_metrics && (
                  <div style={{ marginTop: "16px" }}>
                    <Text type="secondary">
                      性能指标: {importResult.performance_metrics.records_per_second} 记录/秒
                      {importResult.performance_metrics.estimated_time_for_1000 > 0 && (
                        <span>
                          {" "}
                          | 预估1000条记录需{" "}
                          {importResult.performance_metrics.estimated_time_for_1000} 秒
                        </span>
                      )}
                    </Text>
                  </div>
                )}
              </div>
            </Card>

            {/* 详细统计 */}
            <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
              <Col xs={24} sm={8}>
                <Card size="small" variant="borderless">
                  <Statistic
                    title="成功记录"
                    value={importResult.success}
                    valueStyle={{ color: "#3f8600" }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card size="small" variant="borderless">
                  <Statistic
                    title="失败记录"
                    value={importResult.failed}
                    valueStyle={{ color: importResult.failed > 0 ? "#cf1322" : "#d9d9d9" }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card size="small" variant="borderless">
                  <Statistic
                    title="总计"
                    value={importResult.total}
                    valueStyle={{ color: COLORS.primary }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 错误详情 */}
            {importResult.failed > 0 && importResult.errors.length > 0 && (
              <Card
                title={`错误详情 (${importResult.errors.length} 条)`}
                size="small"
                style={{ marginBottom: "16px" }}
                extra={
                  <Button
                    type="link"
                    onClick={() => {
                      const errorText = importResult.errors.join("\\n");
                      navigator.clipboard.writeText(errorText);
                      MessageManager.success("错误信息已复制到剪贴板");
                    }}
                  >
                    复制错误信息
                  </Button>
                }
              >
                <Table
                  columns={errorColumns}
                  dataSource={errorData}
                  pagination={{ pageSize: 10 }}
                  size="small"
                  scroll={{ y: 300 }}
                />
              </Card>
            )}

            <div style={{ textAlign: "center", marginTop: "24px" }}>
              <Space size="large">
                <Button onClick={handleReset}>重新导入</Button>
                <Button type="primary" onClick={() => (window.location.href = "/assets")}>
                  查看资产列表
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default OptimizedAssetImport;
