/**
 * PDF导入状态页面
 * 显示实时处理进度、结果和错误信息
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Progress,
  Steps,
  Button,
  Space,
  Alert,
  Typography,
  Row,
  Col,
  Tag,
  Timeline,
  Statistic,
  Modal,
  Descriptions,
  Divider
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  RobotOutlined,
  DatabaseOutlined,
  EyeOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons';

import {
  pdfImportService,
  type SessionProgress,
  type CompleteResult,
  type FileInfo
} from '../../services/pdfImportService';
import { COLORS } from '@/styles/colorMap';

const { Title, Text } = Typography;

interface ContractImportStatusProps {
  sessionId: string;
  fileInfo: FileInfo;
  onComplete: (result: CompleteResult) => void;
  onError: (error: string) => void;
  onCancel: () => void;
}

interface ProcessingStep {
  title: string;
  description: string;
  icon: React.ReactNode;
  status: 'wait' | 'process' | 'finish' | 'error';
  details?: string;
}

const ContractImportStatus: React.FC<ContractImportStatusProps> = ({
  sessionId,
  fileInfo,
  onComplete,
  onError,
  onCancel
}) => {
  const [currentProgress, setCurrentProgress] = useState<SessionProgress | null>(null);
  const [steps, setSteps] = useState<ProcessingStep[]>([]);
  const [result, setResult] = useState<CompleteResult | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 初始化步骤
  useEffect(() => {
    // Component initialized

    const initialSteps: ProcessingStep[] = [
      {
        title: '文件上传',
        description: '上传PDF文件到服务器',
        icon: <FileTextOutlined />,
        status: 'finish',
        details: `文件: ${fileInfo?.filename} (${pdfImportService.formatFileSize(fileInfo?.size || 0)})`
      },
      {
        title: '文档解析',
        description: '解析文档结构与内容',
        icon: <RobotOutlined />,
        status: 'process',
        details: '智能识别文档布局'
      },
      {
        title: '智能识别',
        description: '识别合同条款与关键要素',
        icon: <DatabaseOutlined />,
        status: 'wait',
        details: '提取合同编号、金额等关键信息'
      },
      {
        title: '数据校验',
        description: '校验数据完整性与合规性',
        icon: <CheckCircleOutlined />,
        status: 'wait',
        details: '自动检查必填项'
      },
      {
        title: '关联分析',
        description: '匹配系统内资产与权属方',
        icon: <EyeOutlined />,
        status: 'wait',
        details: '自动关联业务数据'
      }
    ];
    setSteps(initialSteps);
  }, [fileInfo, sessionId]);

  // 轮询进度
  const pollProgress = useCallback(async () => {
    try {
      const response = await pdfImportService.getProgress(sessionId);

      if (response.success && response.session_status) {
        setCurrentProgress(response.session_status);

        // 更新步骤状态
        updateStepsStatus(response.session_status);

        // 检查是否完成
        if (response.session_status.status === 'ready_for_review') {
          // 停止自动刷新
          setAutoRefresh(false);

          // 获取完整结果
          const resultResponse = await pdfImportService.getResult(sessionId);
          if (resultResponse.success && resultResponse.result) {
            setResult(resultResponse.result);
            onComplete(resultResponse.result);
          }
        } else if (response.session_status.status === 'failed') {
          // 停止自动刷新
          setAutoRefresh(false);
          onError(response.session_status.error_message ?? '处理失败');
        } else if (response.session_status.status === 'cancelled') {
          // 停止自动刷新
          setAutoRefresh(false);
          onError('处理已取消');
        }
      }
    } catch (error: unknown) {
      console.error('获取进度失败:', error);
      // 不立即调用onError，让轮询继续
      // 只有在连续多次失败时才停止
    }
  }, [sessionId, onComplete, onError]);

  // 自动轮询
  useEffect(() => {
    if (!autoRefresh) return;

    // 立即执行一次轮询
    pollProgress();

    // 然后每1.5秒轮询一次
    const interval = setInterval(() => {
      pollProgress();
    }, 1500);

    return () => clearInterval(interval);
  }, [autoRefresh, pollProgress]);

  // 更新步骤状态
  const updateStepsStatus = (progress: SessionProgress) => {
    setSteps(prevSteps => {
      const newSteps = [...prevSteps];
      const stepMapping: Record<string, number> = {
        'created': 0,
        'converting_pdf': 1,
        'extracting_info': 2,
        'validating_data': 3,
        'matching_data': 4,
        'ready_for_review': 5,
        'completed': 5,
        'failed': 5
      };

      const currentStep = stepMapping[progress.current_step] || 0;

      newSteps.forEach((step, index) => {
        if (index < currentStep) {
          step.status = 'finish';
        } else if (index === currentStep) {
          step.status = progress.status === 'failed' ? 'error' : 'process';
          step.details = progress.error_message ?? step.description;
        } else {
          step.status = 'wait';
        }
      });

      return newSteps;
    });
  };

  // 手动刷新
  const handleRefresh = () => {
    pollProgress();
  };

  // 下载原始文件
  const handleDownload = () => {
    MessageManager.info('下载功能待实现');
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready_for_review': return COLORS.success;
      case 'failed':
      case 'cancelled': return COLORS.error;
      case 'completed': return COLORS.primary;
      default: return COLORS.warning;
    }
  };

  // 获取状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'created': return '已创建';
      case 'converting': return '转换中';
      case 'extracting': return '提取中';
      case 'validating': return '验证中';
      case 'matching': return '匹配中';
      case 'ready_for_review': return '待确认';
      case 'failed': return '处理失败';
      case 'cancelled': return '已取消';
      case 'imported': return '已导入';
      default: return '处理中';
    }
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready_for_review': return <CheckCircleOutlined />;
      case 'failed':
      case 'cancelled': return <CloseCircleOutlined />;
      case 'completed': return <CheckCircleOutlined />;
      default: return <LoadingOutlined />;
    }
  };

  return (
    <div className="contract-import-status">
      {/* 头部信息 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="large">
              <div>
                <Title level={4} style={{ margin: 0 }}>
                  PDF合同处理状态
                </Title>
                <Text type="secondary">
                  会话ID: {sessionId}
                </Text>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={!currentProgress}
              >
                刷新
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                disabled={fileInfo == null}
              >
                下载
              </Button>
              <Button onClick={onCancel}>
                取消
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 当前状态 */}
      {currentProgress && (
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Space>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  backgroundColor: getStatusColor(currentProgress.status),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white'
                }}>
                  {getStatusIcon(currentProgress.status)}
                </div>
                <div>
                  <Title level={5} style={{ margin: 0, color: getStatusColor(currentProgress.status) }}>
                    {getStatusText(currentProgress.status)}
                  </Title>
                  <Text type="secondary">
                    {currentProgress.current_step}
                  </Text>
                </div>
              </Space>
            </Col>
            <Col>
              <Statistic
                title="处理进度"
                value={currentProgress.progress}
                precision={0}
                suffix="%"
                valueStyle={{
                  color: getStatusColor(currentProgress.status)
                }}
              />
            </Col>
          </Row>

          {(currentProgress.error_message?.length ?? 0) > 0 && (
            <Alert
              message="处理错误"
              description={currentProgress.error_message}
              type="error"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Card>
      )}

      {/* 处理步骤 */}
      <Card title="处理步骤" style={{ marginBottom: 16 }}>
        <Steps
          current={steps.findIndex(step => step.status === 'process')}
          status={steps.some(step => step.status === 'error') ? 'error' : 'process'}
          items={steps.map((step, index) => ({
            key: index,
            title: step.title,
            description: (
              <div>
                <div>{step.description}</div>
                {(step.details != null) && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {step.details}
                  </Text>
                )}
              </div>
            ),
            icon: step.icon,
            status: step.status,
          }))}
        />
      </Card>

      {/* 详细信息 */}
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Title level={5}>处理详情</Title>
          </Col>
          <Col>
            <Button
              type="text"
              onClick={() => setShowDetailsModal(true)}
            >
              查看详细信息
            </Button>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="文件名">
                {fileInfo?.filename}
              </Descriptions.Item>
              <Descriptions.Item label="文件大小">
                {pdfImportService.formatFileSize(fileInfo?.size || 0)}
              </Descriptions.Item>
              <Descriptions.Item label="文件类型">
                {fileInfo?.content_type}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {currentProgress?.created_at}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {currentProgress?.updated_at}
              </Descriptions.Item>
            </Descriptions>
          </Col>
          <Col span={12}>
            {currentProgress && (
              <div>
                <Title level={5}>处理时间线</Title>
                <Timeline>
                  <Timeline.Item color="blue" dot>
                    <Text strong>会话创建</Text>
                    <br />
                    <Text type="secondary">{currentProgress.created_at}</Text>
                  </Timeline.Item>
                  <Timeline.Item color="green" dot>
                    <Text strong>开始处理</Text>
                    <br />
                    <Text type="secondary">{currentProgress.created_at}</Text>
                  </Timeline.Item>
                  {(currentProgress.error_message?.length ?? 0) > 0 && (
                    <Timeline.Item color="red" dot>
                      <Text strong>处理失败</Text>
                      <br />
                      <Text type="secondary">{currentProgress.updated_at}</Text>
                    </Timeline.Item>
                  )}
                  {currentProgress.status === 'ready_for_review' && (
                    <Timeline.Item color="green" dot>
                      <Text strong>处理完成</Text>
                      <br />
                      <Text type="secondary">{currentProgress.updated_at}</Text>
                    </Timeline.Item>
                  )}
                </Timeline>
              </div>
            )}
          </Col>
        </Row>
      </Card>

      {/* 结果统计 */}
      {result && (
        <Card title="处理结果统计" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="提取字段数"
                value={result.extraction_result.processed_fields}
                suffix={`/ ${result.extraction_result.total_fields}`}
                valueStyle={{ color: COLORS.success }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="验证评分"
                value={result.validation_result.validation_score}
                precision={2}
                suffix="%"
                valueStyle={{ color: COLORS.success }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="匹配置信度"
                value={result.matching_result.match_confidence}
                precision={2}
                suffix="%"
                valueStyle={{ color: COLORS.success }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总体评分"
                value={result.summary.total_confidence}
                precision={2}
                suffix="%"
                valueStyle={{ color: COLORS.success }}
              />
            </Col>
          </Row>

          {/* 处理摘要 */}
          <Divider />
          <Descriptions column={3} size="small">
            <Descriptions.Item label="提取方法">
              {result.extraction_result.extraction_method}
            </Descriptions.Item>
            <Descriptions.Item label="提取可信度">
              <Tag color={result.summary.extraction_confidence >= 0.8 ? 'green' : 'orange'}>
                {(result.summary.extraction_confidence * 100).toFixed(1)}%
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="验证字段数">
              {result.validation_result.processed_fields}
            </Descriptions.Item>
            <Descriptions.Item label="错误数量">
              <Tag color={result.validation_result.errors.length > 0 ? 'red' : 'green'}>
                {result.validation_result.errors.length}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="警告数量">
              <Tag color={result.validation_result.warnings.length > 0 ? 'orange' : 'green'}>
                {result.validation_result.warnings.length}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="匹配资产数">
              {result.matching_result.matched_assets.length}
            </Descriptions.Item>
            <Descriptions.Item label="匹配权属方数">
              {result.matching_result.matched_ownerships.length}
            </Descriptions.Item>
            <Descriptions.Item label="重复合同数">
              <Tag color={result.matching_result.duplicate_contracts.length > 0 ? 'red' : 'green'}>
                {result.matching_result.duplicate_contracts.length}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* 详细信息模态框 */}
      <Modal
        title="处理详细信息"
        open={showDetailsModal}
        onCancel={() => setShowDetailsModal(false)}
        footer={[
          <Button key="close" onClick={() => setShowDetailsModal(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {currentProgress && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="会话ID">
              <Text code>{sessionId}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="当前状态">
              <Tag color={getStatusColor(currentProgress.status)}>
                {getStatusText(currentProgress.status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="当前步骤">
              {currentProgress.current_step}
            </Descriptions.Item>
            <Descriptions.Item label="进度">
              <Progress percent={currentProgress.progress} />
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {currentProgress.created_at}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {currentProgress.updated_at}
            </Descriptions.Item>
            <Descriptions.Item label="错误信息" span={2}>
              {currentProgress.error_message ?? '无'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default ContractImportStatus;
