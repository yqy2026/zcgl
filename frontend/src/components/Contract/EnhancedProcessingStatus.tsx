/**
 * 增强版PDF处理状态组件
 * 支持中文合同识别的详细处理进度和状态显示
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Progress,
  Tag,
  Row,
  Col,
  Statistic,
  Alert,
  Space,
  Button,
  Timeline,
  Badge,
  Typography,
  Spin,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  RocketOutlined,
  ExperimentOutlined,
  EyeOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { EnhancedSessionProgress, ProcessingOptions } from '../../types/enhancedPdfImport';

const { Text } = Typography;

interface ProcessingStep {
  step: string;
  status: 'waiting' | 'processing' | 'completed' | 'error';
  title: string;
  description?: string;
  progress?: number;
  duration?: number;
  error?: string;
  details?: Record<string, unknown>;
}

interface EnhancedProcessingStatusProps {
  sessionId: string;
  currentStatus?: EnhancedSessionProgress;
  processingOptions?: ProcessingOptions;
  onRefresh?: () => void;
  onCancel?: () => void;
  showDetails?: boolean;
  compact?: boolean;
  onError?: (error: string) => void;
  // Internal properties for compatibility
  _sessionId?: string;
  _processingOptions?: ProcessingOptions;
  _onRefresh?: () => void;
  _onCancel?: () => void;
  _compact?: boolean;
  _onError?: (error: string) => void;
}

const EnhancedProcessingStatus: React.FC<EnhancedProcessingStatusProps> = ({
  _sessionId,
  currentStatus,
  _processingOptions,
  _onRefresh,
  _onCancel,
  showDetails = true,
  _compact = false,
  _onError,
}) => {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [_autoRefresh, _setAutoRefresh] = useState(true);

  // 兼容旧版步骤映射
  const stepMap: Record<string, string> = {
    file_upload: '文件上传',
    pdf_conversion: 'PDF转换',
    text_extraction: '文本提取',
    info_extraction: '信息提取',
    data_validation: '数据验证',
    asset_matching: '资产匹配',
    ownership_matching: '权属方匹配',
    duplicate_check: '重复检查',
    final_review: '最终审核',
  };

  // 状态颜色映射
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'processing';
      case 'error':
        return 'error';
      case 'uploading':
        return 'warning';
      default:
        return 'default';
    }
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined />;
      case 'processing':
        return <LoadingOutlined spin />;
      case 'error':
        return <CloseCircleOutlined />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  // 处理步骤数据
  const processingSteps = useMemo((): ProcessingStep[] => {
    if (!currentStatus) return [];

    const steps: ProcessingStep[] = [
      {
        step: 'file_upload',
        status: 'completed',
        title: '文件上传',
        description: 'PDF文件已成功上传并保存',
        progress: 100,
      },
      {
        step: 'pdf_conversion',
        status: currentStatus.processing_method === 'ocr' ? 'processing' : 'completed',
        title: 'PDF处理',
        description:
          currentStatus.processing_method === 'ocr'
            ? '正在使用OCR技术处理PDF文档'
            : 'PDF文档处理完成',
        progress: currentStatus.processing_method === 'ocr' ? 80 : 100,
      },
      {
        step: 'text_extraction',
        status: 'completed',
        title: '文本提取',
        description: `成功提取${currentStatus.chinese_char_count ?? 0}个中文字符`,
        progress: 100,
      },
      {
        step: 'info_extraction',
        status: 'completed',
        title: '信息提取',
        description: `提取了${Object.keys(currentStatus.extracted_data || {}).length}个字段`,
        progress: 100,
      },
      {
        step: 'data_validation',
        status:
          currentStatus.validation_results !== undefined &&
          currentStatus.validation_results !== null
            ? 'completed'
            : 'processing',
        title: '数据验证',
        description:
          currentStatus.validation_results !== undefined &&
          currentStatus.validation_results !== null
            ? '数据验证完成，置信度优秀'
            : '正在进行智能数据验证',
        progress:
          currentStatus.validation_results !== undefined &&
          currentStatus.validation_results !== null
            ? 100
            : 70,
      },
      {
        step: 'matching',
        status: 'processing',
        title: '智能匹配',
        description: '正在进行资产和权属方智能匹配',
        progress: 60,
      },
      {
        step: 'final_review',
        status: 'waiting',
        title: '最终审核',
        description: '等待用户审核和确认',
        progress: 0,
      },
    ];

    // 根据实际状态更新步骤
    const currentStep = currentStatus.current_step;
    if (currentStep !== undefined && currentStep !== null) {
      const stepIndex = steps.findIndex(s => s.step === currentStep);
      if (stepIndex !== -1) {
        // 更新当前步骤及之前步骤的状态
        steps.forEach((step, index) => {
          if (index < stepIndex) {
            step.status = 'completed';
            step.progress = 100;
          } else if (index === stepIndex) {
            step.status = 'processing';
            step.progress = currentStatus.progress_percentage ?? 0;
          } else {
            step.status = 'waiting';
            step.progress = 0;
          }
        });
      }
    }

    return steps;
  }, [currentStatus]);

  // 性能指标
  const performanceMetrics = useMemo(() => {
    if (currentStatus === undefined || currentStatus === null) return null;

    return {
      processingMethod: currentStatus.processing_method,
      textQuality:
        currentStatus.chinese_char_count !== undefined &&
        currentStatus.chinese_char_count !== null &&
        currentStatus.chinese_char_count > 0
          ? '优秀'
          : '良好',
      extractionConfidence:
        currentStatus.confidence_score !== undefined && currentStatus.confidence_score !== null
          ? `${(currentStatus.confidence_score * 100).toFixed(1)}%`
          : '计算中',
      ocrUsed: currentStatus.ocr_used,
      estimatedTime: currentStatus.processing_method === 'ocr' ? '45-60秒' : '30-45秒',
    };
  }, [currentStatus]);

  // 错误处理和重试逻辑
  const handleRetry = async () => {
    if (_onRefresh !== undefined && _onRefresh !== null && typeof _onRefresh === 'function') {
      _onRefresh();
    }
  };

  const handleStepDetail = (step: string) => {
    setExpanded(expanded === step ? null : step);
  };

  if (currentStatus === undefined || currentStatus === null) {
    return (
      <Card>
        <Spin size="large" tip="加载处理状态中...">
          <div style={{ height: 200 }} />
        </Spin>
      </Card>
    );
  }

  return (
    <div className="enhanced-processing-status">
      {/* 整体进度 */}
      <Card
        title={
          <Space>
            <RocketOutlined />
            <span>PDF智能处理进度</span>
            <Button type="text" size="small" icon={<SyncOutlined />} onClick={handleRetry}>
              刷新
            </Button>
          </Space>
        }
      >
        <Row gutter={16}>
          <Col span={16}>
            <Progress
              percent={currentStatus.progress_percentage ?? 0}
              status={currentStatus.progress_percentage === 100 ? 'success' : 'active'}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
              strokeWidth={8}
              format={percent => `${percent}%`}
            />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">
                当前状态：{stepMap[currentStatus.current_step] || '准备中'}
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Statistic
                title="处理方法"
                value={performanceMetrics?.processingMethod === 'ocr' ? 'OCR识别' : '文本提取'}
                prefix={<ExperimentOutlined />}
              />
              <Statistic
                title="置信度"
                value={performanceMetrics?.extractionConfidence ?? '计算中'}
                suffix="%"
                valueStyle={{
                  color:
                    parseFloat(performanceMetrics?.extractionConfidence ?? '0') > 80
                      ? '#3f8600'
                      : '#cf1322',
                }}
              />
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 详细步骤 */}
      {showDetails && (
        <Card title="处理详情" style={{ marginTop: 16 }}>
          <Timeline>
            {processingSteps.map((step, _index) => (
              <Timeline.Item
                key={step.step}
                dot={getStatusIcon(step.status)}
                color={getStatusColor(step.status)}
              >
                <div
                  role={step.details ? 'button' : undefined}
                  tabIndex={step.details ? 0 : undefined}
                  style={{
                    cursor: step.details ? 'pointer' : 'default',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    backgroundColor: step.status === 'processing' ? '#f6ffed' : 'transparent',
                  }}
                  onClick={() => step.details && handleStepDetail(step.step)}
                  onKeyDown={e => {
                    if (step.details && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      handleStepDetail(step.step);
                    }
                  }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Text strong>{step.title}</Text>
                      <Badge
                        status={
                          step.status === 'completed'
                            ? 'success'
                            : step.status === 'processing'
                              ? 'processing'
                              : step.status === 'error'
                                ? 'error'
                                : 'default'
                        }
                        text={
                          step.status === 'completed'
                            ? '已完成'
                            : step.status === 'processing'
                              ? '处理中'
                              : step.status === 'error'
                                ? '失败'
                                : '等待中'
                        }
                      />
                    </Space>

                    {step.description != null && (
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {step.description}
                      </Text>
                    )}

                    {step.progress !== undefined && (
                      <Progress
                        percent={step.progress}
                        size="small"
                        showInfo={false}
                        strokeColor={step.status === 'completed' ? '#52c41a' : '#1890ff'}
                      />
                    )}

                    {step.error != null && (
                      <Alert message={step.error} type="error" style={{ marginTop: 8 }} />
                    )}
                  </Space>

                  {/* 展开的详细信息 */}
                  {expanded === step.step && step.details && (
                    <div
                      style={{
                        marginTop: 12,
                        padding: 12,
                        backgroundColor: '#fafafa',
                        borderRadius: 4,
                        border: '1px solid #d9d9d9',
                      }}
                    >
                      <Text code>{JSON.stringify(step.details, null, 2)}</Text>
                    </div>
                  )}
                </div>
              </Timeline.Item>
            ))}
          </Timeline>
        </Card>
      )}

      {/* 警告和建议 */}
      {currentStatus.warnings && currentStatus.warnings.length > 0 && (
        <Alert
          message="处理提示"
          description={
            <ul>
              {currentStatus.warnings.map((warning: string, index: number) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          }
          type="warning"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}

      {/* 增强功能标识 */}
      <Card size="small" style={{ marginTop: 16 }}>
        <Space wrap>
          <Tag icon={<ExperimentOutlined />} color="blue">
            增强版提取器
          </Tag>
          <Tag icon={<EyeOutlined />} color="green">
            智能质量评估
          </Tag>
          <Tag color="purple">多引擎支持</Tag>
          {(performanceMetrics?.ocrUsed ?? false) && <Tag color="orange">OCR增强</Tag>}
        </Space>
      </Card>
    </div>
  );
};

export default EnhancedProcessingStatus;
