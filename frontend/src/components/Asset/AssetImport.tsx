import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Typography,
  Upload,
  Button,
  Progress,
  Space,
  Alert,
  Steps,
  Row,
  Col,
  Statistic,
  Divider,
  Switch,
  Form,
  InputNumber,
  Select,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import type { ColumnsType } from 'antd/es/table';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import {
  UploadOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  CheckCircleOutlined,
  CheckCircleFilled,
  ExclamationCircleOutlined,
  ExclamationCircleFilled,
  CloseCircleFilled,
  FileTextFilled,
  SettingOutlined,
} from '@ant-design/icons';
import type { UploadProps, UploadFile } from 'antd';
import {
  assetImportService,
  type AssetImportResult,
  type AssetImportConfig as AssetImportServiceConfig,
} from '@/services/assetImportService';
import { STANDARD_SHEET_NAME, IMPORT_INSTRUCTIONS } from '@/config/excelConfig';
import { createLogger } from '@/utils/logger';
import { useArrayListData } from '@/hooks/useArrayListData';
import styles from './AssetImport.module.css';

const importLogger = createLogger('AssetImport');

const { Title, Text } = Typography;
const { Option } = Select;

type ImportConfig = Pick<AssetImportServiceConfig, 'useOptimized' | 'skipErrors'> & {
  batchSize: number;
  timeout: number;
};

type ImportResultTone = 'success' | 'warning' | 'error' | 'neutral';

const RESULT_CARD_CLASS_MAP: Record<ImportResultTone, string> = {
  success: styles.resultSummarySuccess,
  warning: styles.resultSummaryWarning,
  error: styles.resultSummaryError,
  neutral: styles.resultSummaryNeutral,
};

const RESULT_ICON_CLASS_MAP: Record<ImportResultTone, string> = {
  success: styles.resultSummaryIconSuccess,
  warning: styles.resultSummaryIconWarning,
  error: styles.resultSummaryIconError,
  neutral: styles.resultSummaryIconNeutral,
};

const RESULT_TITLE_ICON_CLASS_MAP: Record<ImportResultTone, string> = {
  success: styles.resultSummaryTitleIconSuccess,
  warning: styles.resultSummaryTitleIconWarning,
  error: styles.resultSummaryTitleIconError,
  neutral: styles.resultSummaryTitleIconNeutral,
};

const getImportResultTone = (result: AssetImportResult): ImportResultTone => {
  if (result.success > 0 && result.failed === 0) {
    return 'success';
  }
  if (result.success > 0 && result.failed > 0) {
    return 'warning';
  }
  if (result.failed > 0) {
    return 'error';
  }
  return 'neutral';
};

const OptimizedAssetImport: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState<AssetImportResult | null>(null);
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
      await assetImportService.downloadTemplate('land_property_asset_template.xlsx');
      MessageManager.success('模板下载成功');
    } catch {
      MessageManager.error('模板下载失败');
    }
  };

  // 文件上传配置
  const uploadProps: UploadProps = {
    fileList,
    beforeUpload: file => {
      const isExcel =
        file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
        file.type === 'application/vnd.ms-excel';

      if (!isExcel) {
        MessageManager.error('只能上传Excel文件(.xlsx, .xls)');
        return false;
      }

      const isLt50M = file.size / 1024 / 1024 < 50;
      if (!isLt50M) {
        MessageManager.error('文件大小不能超过50MB');
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
      setProgress(prev => {
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
      MessageManager.error('请先选择要导入的文件');
      return;
    }

    setUploading(true);
    const progressInterval = simulateProgress();

    try {
      const file = fileList[0]?.originFileObj;
      if (file == null) {
        clearInterval(progressInterval);
        setUploading(false);
        MessageManager.error('未检测到可导入文件');
        return;
      }

      const result = await assetImportService.importAssets(file, {
        sheetName: STANDARD_SHEET_NAME,
        skipErrors: config.skipErrors,
        useOptimized: config.useOptimized,
        timeoutSeconds: config.timeout,
      });

      clearInterval(progressInterval);
      setProgress(100);

      setImportResult(result);
      setCurrentStep(2);

      // 显示性能信息
      if (result.processing_time !== undefined && result.processing_time !== null) {
        MessageManager.success(`导入完成，用时 ${result.processing_time} 秒`);
      } else {
        MessageManager.success(`导入完成，成功导入 ${result.success} 条记录`);
      }
    } catch (err: unknown) {
      clearInterval(progressInterval);
      importLogger.error('导入错误', err instanceof Error ? err : new Error(String(err)));

      const errorMessage = err instanceof Error ? err.message : '网络错误';

      const errorResult: AssetImportResult = {
        success: 0,
        failed: 0,
        total: 0,
        errors: [errorMessage],
        message: '导入失败',
        processing_time: 0,
        filename: fileList[0]?.name,
      };

      setImportResult(errorResult);
      setCurrentStep(2);
      MessageManager.error(`导入失败: ${errorResult.errors[0] ?? '未知错误'}`);
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
      title: '序号',
      dataIndex: 'index',
      key: 'index',
      width: 80,
      render: (_: unknown, __: unknown, index: number) => index + 1,
    },
    {
      title: '错误信息',
      dataIndex: 'error',
      key: 'error',
      ellipsis: true,
    },
  ];

  const errorData = useMemo(
    () =>
      importResult?.errors?.map(error => ({
        key: error,
        error,
      })) ?? [],
    [importResult]
  );

  const {
    data: pagedErrorData,
    pagination: errorPagination,
    loadList: loadErrorList,
    updatePagination: updateErrorPagination,
  } = useArrayListData<Record<string, unknown>, Record<string, never>>({
    items: errorData,
    initialFilters: {},
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadErrorList({ page: 1 });
  }, [errorData, loadErrorList]);

  const importResultTone = importResult != null ? getImportResultTone(importResult) : 'neutral';

  return (
    <div className={styles.importPage}>
      <div className={styles.pageHeader}>
        <Title level={2} className={styles.pageTitle}>
          <FileExcelOutlined className={styles.pageTitleIcon} aria-hidden /> 数据导入
        </Title>
        <Button type="dashed" icon={<SettingOutlined />} onClick={() => setShowConfig(!showConfig)}>
          {showConfig ? '隐藏配置' : '显示配置'}
        </Button>
      </div>

      {/* 配置面板 */}
      {showConfig && (
        <Card title="导入配置" size="small" className={styles.configCard}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="使用优化导入">
                <Switch
                  checked={config.useOptimized}
                  onChange={checked => setConfig(prev => ({ ...prev, useOptimized: checked }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="超时时间(秒)">
                <InputNumber
                  min={60}
                  max={1800}
                  value={config.timeout}
                  onChange={value => setConfig(prev => ({ ...prev, timeout: value ?? 600 }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="跳过错误">
                <Switch
                  checked={config.skipErrors}
                  onChange={checked => setConfig(prev => ({ ...prev, skipErrors: checked }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="批量大小">
                <Select
                  value={config.batchSize}
                  onChange={value => setConfig(prev => ({ ...prev, batchSize: value || 100 }))}
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
        <Steps
          current={currentStep}
          className={styles.stepper}
          items={[
            { title: '选择文件', content: '上传Excel文件' },
            { title: '执行导入', content: '处理数据' },
            { title: '查看结果', content: '导入完成' },
          ]}
        />

        {/* 步骤0: 选择文件 */}
        {currentStep === 0 && (
          <div>
            <Alert
              title="导入说明"
              description={
                <div className={styles.instructionsDescription}>
                  <p>• 支持Excel文件批量导入资产数据</p>
                  <p>• 智能数据验证和错误处理</p>
                  <p>• 实时导入进度反馈</p>
                  <p>• 支持大文件导入 (最大50MB)</p>
                  {IMPORT_INSTRUCTIONS.map((instruction, index) => (
                    <p key={instruction}>
                      {index + 1}. {instruction}
                    </p>
                  ))}
                </div>
              }
              type="info"
              showIcon
              className={styles.instructionsAlert}
            />

            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12}>
                <Card size="small" title="第一步：下载模板">
                  <Space orientation="vertical" className={styles.fullWidthStack}>
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
                  <Space orientation="vertical" className={styles.fullWidthStack}>
                    <Text>选择填写好的Excel文件</Text>
                    <Upload.Dragger {...uploadProps} className={styles.uploadDragger}>
                      <p className="ant-upload-drag-icon">
                        <FileExcelOutlined className={styles.uploadIcon} />
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
          <div className={styles.importExecution}>
            <FileExcelOutlined className={styles.executionIcon} />
            <Title level={4}>文件已选择</Title>
            <Text className={styles.executionFileMeta}>文件名：{fileList[0]?.name}</Text>
            <br />
            <Text type="secondary">
              文件大小：{((fileList[0]?.size ?? 0) / 1024 / 1024).toFixed(2)} MB
            </Text>

            {uploading && (
              <div className={styles.progressBlock}>
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
                {uploading ? '导入中…' : '开始导入'}
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
              className={`${styles.resultSummaryCard} ${RESULT_CARD_CLASS_MAP[importResultTone]}`}
            >
              <div className={styles.resultSummaryBody}>
                {importResult.success > 0 && importResult.failed === 0 ? (
                  <CheckCircleOutlined
                    className={`${styles.resultSummaryIcon} ${RESULT_ICON_CLASS_MAP[importResultTone]}`}
                  />
                ) : importResult.success > 0 && importResult.failed > 0 ? (
                  <ExclamationCircleOutlined
                    className={`${styles.resultSummaryIcon} ${RESULT_ICON_CLASS_MAP[importResultTone]}`}
                  />
                ) : (
                  <ExclamationCircleOutlined
                    className={`${styles.resultSummaryIcon} ${RESULT_ICON_CLASS_MAP[importResultTone]}`}
                  />
                )}

                <Title level={3} className={styles.resultSummaryTitle}>
                  {importResult.success > 0 && importResult.failed === 0 ? (
                    <Space>
                      <CheckCircleFilled className={RESULT_TITLE_ICON_CLASS_MAP[importResultTone]} />
                      导入成功！
                    </Space>
                  ) : importResult.success > 0 && importResult.failed > 0 ? (
                    <Space>
                      <ExclamationCircleFilled className={RESULT_TITLE_ICON_CLASS_MAP[importResultTone]} />
                      部分成功
                    </Space>
                  ) : importResult.failed > 0 ? (
                    <Space>
                      <CloseCircleFilled className={RESULT_TITLE_ICON_CLASS_MAP[importResultTone]} />
                      导入失败
                    </Space>
                  ) : (
                    <Space>
                      <FileTextFilled className={RESULT_TITLE_ICON_CLASS_MAP[importResultTone]} />
                      导入完成
                    </Space>
                  )}
                </Title>

                <Text type="secondary" className={styles.resultSummaryText}>
                  {importResult.processing_time !== undefined &&
                    importResult.processing_time !== null && (
                      <span>处理时间: {importResult.processing_time}秒 | </span>
                    )}
                  {importResult.success > 0 && importResult.failed === 0
                    ? `成功导入 ${importResult.success} 条资产记录`
                    : importResult.success > 0 && importResult.failed > 0
                      ? `成功 ${importResult.success} 条，失败 ${importResult.failed} 条，总计 ${importResult.total} 条`
                      : importResult.failed > 0
                        ? `${importResult.failed} 条记录导入失败`
                        : '没有数据被导入，请检查文件格式和内容'}
                </Text>

                {/* 性能指标 */}
                {importResult.performance_metrics && (
                  <div className={styles.resultSummaryMetrics}>
                    <Text type="secondary">
                      性能指标: {importResult.performance_metrics.records_per_second} 记录/秒
                      {importResult.performance_metrics.estimated_time_for_1000 > 0 && (
                        <span>
                          {' '}
                          | 预估1000条记录需{' '}
                          {importResult.performance_metrics.estimated_time_for_1000} 秒
                        </span>
                      )}
                    </Text>
                  </div>
                )}
              </div>
            </Card>

            {/* 详细统计 */}
            <Row gutter={[16, 16]} className={styles.statsRow}>
              <Col xs={24} sm={8}>
                <Card size="small" variant="borderless" className={styles.statCard}>
                  <Statistic title="成功记录" value={importResult.success} className={styles.statisticSuccess} />
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card size="small" variant="borderless" className={styles.statCard}>
                  <Statistic
                    title="失败记录"
                    value={importResult.failed}
                    className={importResult.failed > 0 ? styles.statisticError : styles.statisticMuted}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card size="small" variant="borderless" className={styles.statCard}>
                  <Statistic title="总计" value={importResult.total} className={styles.statisticPrimary} />
                </Card>
              </Col>
            </Row>

            {/* 错误详情 */}
            {importResult.failed > 0 && importResult.errors.length > 0 && (
              <Card
                title={`错误详情 (${importResult.errors.length} 条)`}
                size="small"
                className={styles.errorCard}
                extra={
                  <Button
                    type="link"
                    onClick={() => {
                      const errorText = importResult.errors.join('\\n');
                      navigator.clipboard.writeText(errorText);
                      MessageManager.success('错误信息已复制到剪贴板');
                    }}
                  >
                    复制错误信息
                  </Button>
                }
              >
                <TableWithPagination
                  columns={errorColumns}
                  dataSource={pagedErrorData}
                  paginationState={errorPagination}
                  onPageChange={updateErrorPagination}
                  paginationProps={{
                    showSizeChanger: true,
                    showTotal: (total: number) => `共 ${total} 条`,
                  }}
                  size="small"
                  scroll={{ y: 300 }}
                />
              </Card>
            )}

            <div className={styles.resultActions}>
              <Space size="large">
                <Button onClick={handleReset}>重新导入</Button>
                <Button type="primary" onClick={() => (window.location.href = '/assets')}>
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
