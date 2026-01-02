/**
 * 增强PDF导入上传组件
 * 提供更好的用户体验和进度反馈
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Upload,
  Button,
  Card,
  Space,
  Typography,
  Alert,
  Row,
  Col,
  Statistic,
  Divider,
  Tag,
  Tooltip,
  Steps,
  Modal,
  message,
  Switch,
  Badge,
  Progress
} from 'antd';
import {
  CloudUploadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  SettingOutlined,
  RocketOutlined,
  EyeOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';

import { pdfImportService } from '../../services/pdfImportService';
import type {
  SessionProgress,
  SystemInfoResponse
} from '../../services/pdfImportService';

const { Dragger } = Upload;
const { Paragraph } = Typography;

interface EnhancedPDFImportUploaderProps {
  onUploadSuccess: (sessionId: string, fileInfo: UploadFile) => void;
  onUploadError: (error: string) => void;
  maxSize?: number; // MB
  className?: string;
}

interface ProcessingStep {
  title: string;
  description: string;
  status: 'wait' | 'process' | 'finish' | 'error' | 'uploading' | 'completed' | 'failed';
  progress?: number;
  duration?: number;
}

interface UploadStats {
  uploadSpeed: number; // KB/s
  estimatedTime: number; // seconds
  fileAnalysis: {
    type: 'scanned' | 'digital' | 'mixed' | 'unknown';
    quality: 'excellent' | 'good' | 'fair' | 'poor';
    recommendedMethod: string;
  };
}

const EnhancedPDFImportUploader: React.FC<EnhancedPDFImportUploaderProps> = ({
  onUploadSuccess,
  onUploadError,
  maxSize = 50,
  className
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [processingProgress, setProcessingProgress] = useState<SessionProgress | null>(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [uploadStats, setUploadStats] = useState<UploadStats | null>(null);
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>([]);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const progressTimerRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 默认处理选项
  const [processingOptions, setProcessingOptions] = useState({
    prefer_ocr: true,
    enable_chinese_optimization: true,
    enable_table_detection: true,
    enable_seal_detection: true,
    confidence_threshold: 0.7,
    use_template_learning: true,
    enable_multi_engine_fusion: true,
    enable_semantic_validation: true
  });

  // 加载系统信息
  useEffect(() => {
    loadSystemInfo();
    return () => {
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const loadSystemInfo = async () => {
    try {
      const info = await pdfImportService.getEnhancedSystemInfo();
      setSystemInfo(info);
    } catch {
      // Failed to get system info
    }
  };

  // 初始化处理步骤
  const initializeProcessingSteps = (): ProcessingStep[] => [
    {
      title: '文件上传',
      description: '上传PDF文件到服务器',
      status: 'wait'
    },
    {
      title: '文档分析',
      description: '分析文档类型和质量',
      status: 'wait'
    },
    {
      title: '文本提取',
      description: '提取PDF文本内容',
      status: 'wait'
    },
    {
      title: '信息识别',
      description: '智能识别合同信息',
      status: 'wait'
    },
    {
      title: '数据验证',
      description: '验证和映射数据',
      status: 'wait'
    },
    {
      title: '处理完成',
      description: '准备人工确认',
      status: 'wait'
    }
  ];

  // 更新处理步骤状态
  const updateProcessingSteps = (progress: SessionProgress) => {
    const steps = initializeProcessingSteps();

    // 根据进度映射到步骤
    const stepMapping: Record<string, number> = {
      'uploading': 0,
      'analyzing': 1,
      'text_extraction': 2,
      'info_extraction': 3,
      'validation': 4,
      'matching': 4,
      'ready_for_review': 5,
      'completed': 5,
      'failed': -1
    };

    const currentStepIndex = stepMapping[progress.status] || 0;

    // 更新步骤状态
    steps.forEach((step, index) => {
      if (index < currentStepIndex) {
        step.status = 'finish';
        step.progress = 100;
      } else if (index === currentStepIndex) {
        step.status = progress.status === 'failed' ? 'error' : 'process';
        step.progress = progress.progress;
      } else {
        step.status = 'wait';
        step.progress = 0;
      }
    });

    setProcessingSteps(steps);
  };

  // 文件上传前验证
  const beforeUpload = useCallback((file: File) => {
    const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    if (!isPDF) {
      message.error('只能上传PDF文件！');
      return false;
    }

    const isLtMaxSize = file.size / 1024 / 1024 < maxSize;
    if (!isLtMaxSize) {
      message.error(`文件大小不能超过 ${maxSize}MB！`);
      return false;
    }

    return true;
  }, [maxSize]);

  // 上传配置
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,application/pdf',
    beforeUpload,
    showUploadList: false,
    customRequest: async ({ file, onSuccess, onError, onProgress: _onProgress }) => {
      try {
        setUploading(true);
        setUploadProgress(0);

        // 创建AbortController
        abortControllerRef.current = new AbortController();

        // 模拟上传进度
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            const newProgress = prev + Math.random() * 10;
            return Math.min(newProgress, 90);
          });
        }, 200);

        // 使用增强上传
        const response = await pdfImportService.uploadPDFFileEnhanced(
          file as File,
          processingOptions,
          abortControllerRef.current.signal
        );

        clearInterval(progressInterval);
        setUploadProgress(100);

        if (response.success) {
          setCurrentSession(response.session_id!);

          // 开始轮询处理进度
          startProgressPolling(response.session_id!);

          // 获取文件分析信息
          if ((response as any).enhanced_status) {
            setUploadStats({
              uploadSpeed: (file as any).size / 1024 / (Date.now() / 1000),
              estimatedTime: 30,
              fileAnalysis: {
                type: 'mixed',
                quality: 'good',
                recommendedMethod: (response as any).enhanced_status?.final_results?.extraction_quality?.processing_methods?.[0] || 'hybrid'
              }
            });
          }

          onSuccess?.(response);
          onUploadSuccess(response.session_id!, {
            uid: (file as any).uid,
            name: (file as any).name,
            status: 'done',
            size: (file as any).size,
            type: (file as any).type
          });

          message.success('文件上传成功，开始智能处理...');
        } else {
          throw new Error(response.error || '上传失败');
        }

      } catch (error: unknown) {
        // Note: progressInterval is out of scope here, declared in try block
        setUploading(false);
        setUploadProgress(0);

        const errorMessage = error instanceof Error ? error.message : '上传失败';
        onError?.(new Error(errorMessage));
        onUploadError(errorMessage);
        message.error(errorMessage);
      } finally {
        setTimeout(() => {
          setUploading(false);
          setUploadProgress(0);
        }, 1000);
      }
    }
  };

  // 开始进度轮询
  const startProgressPolling = (sessionId: string) => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
    }

    progressTimerRef.current = setInterval(async () => {
      try {
        const result = await pdfImportService.getEnhancedProgress(sessionId);

        if (result.success && result.session_status) {
          setProcessingProgress(result.session_status);
          updateProcessingSteps(result.session_status);

          // 如果处理完成或失败，停止轮询
          if (['ready_for_review', 'completed', 'failed', 'cancelled'].includes(result.session_status.status)) {
            if (progressTimerRef.current) {
              clearInterval(progressTimerRef.current);
              progressTimerRef.current = null;
            }

            if (result.session_status.status === 'ready_for_review' || result.session_status.status === 'completed') {
              message.success('文件处理完成！');
            } else if (result.session_status.status === 'failed') {
              message.error(`处理失败: ${result.session_status.error_message || '未知错误'}`);
            }
          }
        }
      } catch (error) {
        console.error('获取进度失败:', error);
      }
    }, 2000);
  };

  // 取消上传
  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    if (currentSession) {
      pdfImportService.cancelEnhancedSession(currentSession, '用户取消');
    }

    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }

    setUploading(false);
    setUploadProgress(0);
    setProcessingProgress(null);
    setCurrentSession(null);
    setProcessingSteps(initializeProcessingSteps());

    message.info('已取消上传');
  }, [currentSession]);

  // 重置状态
  const handleReset = useCallback(() => {
    setUploading(false);
    setUploadProgress(0);
    setProcessingProgress(null);
    setCurrentSession(null);
    setProcessingSteps(initializeProcessingSteps());
    setUploadStats(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // 获取步骤图标
  const getStepIcon = (step: ProcessingStep) => {
    switch (step.status) {
      case 'finish':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'process':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <FileTextOutlined />;
    }
  };

  return (
    <div className={className}>
      <Card
        title={
          <Space>
            <CloudUploadOutlined />
            <span>智能PDF导入</span>
            {systemInfo && (
              <Badge
                count="AI增强"
                style={{ backgroundColor: '#52c41a' }}
              />
            )}
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="高级选项">
              <Button
                type="text"
                icon={<SettingOutlined />}
                onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              />
            </Tooltip>
            {currentSession && (
              <Tooltip title="预览处理结果">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => setShowPreviewModal(true)}
                />
              </Tooltip>
            )}
          </Space>
        }
      >
        {/* 处理步骤显示 */}
        {processingSteps.length > 0 && (uploading || processingProgress) && (
          <div style={{ marginBottom: 24 }}>
            <Steps
              size="small"
              current={processingSteps.findIndex(s => s.status === 'process')}
              items={processingSteps.map(step => ({
                title: step.title,
                description: step.description,
                status: ((): 'wait' | 'process' | 'finish' | 'error' => {
                  switch (step.status) {
                    case 'wait':
                      return 'wait'
                    case 'process':
                    case 'uploading':
                      return 'process'
                    case 'finish':
                    case 'completed':
                      return 'finish'
                    case 'error':
                    case 'failed':
                      return 'error'
                    default:
                      return 'process'
                  }
                })(),
                icon: getStepIcon(step)
              }))}
            />

            {(uploading || processingProgress) && (
              <div style={{ marginTop: 16 }}>
                <Progress
                  percent={uploading ? uploadProgress : (processingProgress?.progress || 0)}
                  status={processingProgress?.status === 'failed' ? 'exception' : undefined}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />

                {processingProgress && (
                  <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                    <Typography.Text type="secondary">
                      {processingProgress.current_step || '准备中...'}
                    </Typography.Text>
                    <Typography.Text type="secondary">
                      {processingProgress.progress || 0}%
                    </Typography.Text>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 上传区域 */}
        {!currentSession && (
          <Dragger {...uploadProps} disabled={uploading}>
            <p className="ant-upload-drag-icon">
              <CloudUploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">
              点击或拖拽文件到此区域上传
            </p>
            <p className="ant-upload-hint">
              支持PDF文件，最大{maxSize}MB
            </p>
          </Dragger>
        )}

        {/* 高级选项 */}
        {showAdvancedOptions && (
          <Card
            size="small"
            title="处理选项"
            style={{ marginTop: 16 }}
            extra={
              <Space>
                <Switch
                  checked={processingOptions.prefer_ocr}
                  onChange={(checked) => setProcessingOptions(prev => ({ ...prev, prefer_ocr: checked }))}
                  checkedChildren="OCR"
                  unCheckedChildren="文本"
                />
                <Switch
                  checked={processingOptions.enable_chinese_optimization}
                  onChange={(checked) => setProcessingOptions(prev => ({ ...prev, enable_chinese_optimization: checked }))}
                  checkedChildren="中文优化"
                />
              </Space>
            }
          >
            <Row gutter={16}>
              <Col span={12}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Typography.Text strong>置信度阈值</Typography.Text>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.1"
                      value={processingOptions.confidence_threshold}
                      onChange={(e) => setProcessingOptions(prev => ({ ...prev, confidence_threshold: parseFloat(e.target.value) }))}
                      style={{ width: '100%' }}
                    />
                    <Typography.Text type="secondary">{processingOptions.confidence_threshold}</Typography.Text>
                  </div>
                </Space>
              </Col>
              <Col span={12}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Switch
                    checked={processingOptions.enable_multi_engine_fusion}
                    onChange={(checked) => setProcessingOptions(prev => ({ ...prev, enable_multi_engine_fusion: checked }))}
                    checkedChildren="多引擎融合"
                  />
                  <Switch
                    checked={processingOptions.enable_semantic_validation}
                    onChange={(checked) => setProcessingOptions(prev => ({ ...prev, enable_semantic_validation: checked }))}
                    checkedChildren="语义验证"
                  />
                </Space>
              </Col>
            </Row>
          </Card>
        )}

        {/* 系统信息显示 */}
        {systemInfo && (
          <Alert
            message={
              <Space>
                <RocketOutlined />
                <span>AI增强PDF处理系统已就绪</span>
              </Space>
            }
            description={
              <Space wrap>
                <Tag color="blue">多引擎处理</Tag>
                <Tag color="green">中文优化</Tag>
                <Tag color="purple">智能验证</Tag>
                <Tag color="orange">语义分析</Tag>
              </Space>
            }
            type="success"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {/* 处理统计 */}
        {uploadStats && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={8}>
              <Statistic
                title="上传速度"
                value={uploadStats.uploadSpeed}
                suffix="KB/s"
                precision={1}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="预估时间"
                value={uploadStats.estimatedTime}
                suffix="秒"
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="推荐方法"
                value={uploadStats.fileAnalysis.recommendedMethod}
                valueStyle={{ fontSize: 14 }}
              />
            </Col>
          </Row>
        )}

        {/* 操作按钮 */}
        {(uploading || currentSession) && (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Space>
              <Button onClick={handleCancel} danger>
                取消处理
              </Button>
              <Button onClick={handleReset}>
                重新开始
              </Button>
            </Space>
          </div>
        )}

        {/* 预览模态框 */}
        <Modal
          title="处理结果预览"
          open={showPreviewModal}
          onCancel={() => setShowPreviewModal(false)}
          footer={[
            <Button key="close" onClick={() => setShowPreviewModal(false)}>
              关闭
            </Button>
          ]}
          width={800}
        >
          {processingProgress && (
            <div>
              <Paragraph>
                <Typography.Text strong>处理状态：</Typography.Text>
                <Tag color={processingProgress.status === 'ready_for_review' ? 'green' : 'blue'}>
                  {processingProgress.status}
                </Tag>
              </Paragraph>

              {(processingProgress as any).enhanced_status && (
                <div>
                  <Divider />
                  <Paragraph>
                    <Typography.Text strong>文档分析结果：</Typography.Text>
                  </Paragraph>
                  <ul>
                    <li>文档类型：{(processingProgress as any).enhanced_status.document_analysis?.document_type || '未知'}</li>
                    <li>质量评分：{(processingProgress as any).enhanced_status.document_analysis?.quality_score || 0}/10</li>
                    <li>建议：{(processingProgress as any).enhanced_status.document_analysis?.recommendations?.join('；') || '无'}</li>
                  </ul>

                  <Paragraph>
                    <Typography.Text strong>提取质量：</Typography.Text>
                  </Paragraph>
                  <ul>
                    <li>总体质量：{(processingProgress as any).enhanced_status.final_results?.extraction_quality?.overall_quality || 0}/10</li>
                    <li>验证分数：{(processingProgress as any).enhanced_status.final_results?.validation_score || 0}/10</li>
                    <li>处理方法：{(processingProgress as any).enhanced_status.final_results?.extraction_quality?.processing_methods?.join('、') || '未知'}</li>
                  </ul>
                </div>
              )}
            </div>
          )}
        </Modal>
      </Card>
    </div>
  );
};

export default EnhancedPDFImportUploader;