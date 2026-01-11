/**
 * 增强版PDF导入页面
 * 专门针对中文租赁合同识别的智能处理界面
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Upload,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Progress,
  Tag,
  Alert,
  Badge,
  Statistic,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  InboxOutlined,
  SettingOutlined,
  FileTextOutlined,
  RobotOutlined,
  FireOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons';
import type { UploadProps } from 'antd/es/upload';
import type { RcFile } from 'antd/es/upload/interface';
import { pdfImportService } from '../../services/pdfImportService';
import EnhancedProcessingStatus from '../../components/Contract/EnhancedProcessingStatus';
import EnhancedContractReview from '../../components/Contract/EnhancedContractReview';
import type {
  ProcessingOptions,
  EnhancedSessionProgress,
  EnhancedSystemCapabilities
} from '../../types/enhancedPdfImport';
import { createLogger } from '../../utils/logger';
import { COLORS } from '@/styles/colorMap';

const _pageLogger = createLogger('EnhancedPDFImport');

const { Title, Text } = Typography;
const { Dragger } = Upload;

const EnhancedPDFImportPage: React.FC = () => {
  // 状态管理
  const [processing, setProcessing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStatus, _setCurrentStatus] = useState<EnhancedSessionProgress | null>(null);
  const [systemCapabilities, setSystemCapabilities] = useState<EnhancedSystemCapabilities | null>(null);
  const [fileList, _setFileList] = useState<RcFile[]>([]);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [processingOptions, _setProcessingOptions] = useState<ProcessingOptions>({
    prefer_ocr: true,
    enable_chinese_optimization: true,
    enable_table_detection: true,
    enable_seal_detection: true,
    confidence_threshold: 0.7,
    use_template_learning: true,
    enable_multi_engine_fusion: true,
    enable_semantic_validation: true
  });
  const [showResults, setShowResults] = useState(false);
  const [uploadProgress, _setUploadProgress] = useState(0);

  // 组件挂载时检查系统能力
  useEffect(() => {
    checkSystemCapabilities();
  }, []);

  // 检查系统能力 (占位符实现 - 页面已废弃)
  const checkSystemCapabilities = async () => {
    try {
      // 占位符 - 页面已废弃，直接设置默认值
      setSystemCapabilities({
        pdfplumber_available: true,
        pymupdf_available: true,
        spacy_available: true,
        ocr_available: true,
        enhanced_extraction: true,
        intelligent_matching: true,
        multi_engine_support: true,
        chinese_optimized: true,
        real_time_validation: true,
        table_detection: true,
        seal_detection: true,
        template_learning: true,
        semantic_validation: true,
        supported_formats: ['pdf'],
        max_file_size_mb: 50,
        estimated_processing_time: '2-5秒',
      });
    } catch {
      // 忽略错误，页面已废弃
    }
  };

  // 渲染功能标签 (占位符实现 - 页面已废弃)
  const renderFeatureTag = (enabled: boolean, text: string, color: string) => {
    return enabled ? <Tag color={color}>{text}</Tag> : null;
  };

  // 上传配置 (占位符实现 - 页面已废弃)
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    fileList: fileList as unknown as any[],
    beforeUpload: () => false,
    onChange: () => {
      // 占位符 - 页面已废弃
    },
  };

  // 重试处理 (占位符实现 - 页面已废弃)
  const handleRetry = () => {
    // 占位符 - 页面已废弃
  };

  // 取消处理 (占位符实现 - 页面已废弃)
  const handleCancel = () => {
    setProcessing(false);
    setShowResults(false);
    setSessionId(null);
  };

  // 渲染处理选项 (占位符实现 - 页面已废弃)
  const renderProcessingOptions = () => {
    if (!showAdvancedSettings) return null;
    return (
      <Card title="高级处理选项" style={{ marginTop: 16 }} size="small">
        <Text>此页面已废弃，请使用标准的PDF导入页面</Text>
      </Card>
    );
  };

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      <Alert
        message="页面已迁移"
        description={
          <div>
            此页面（实验版）已废弃，所有增强功能已集成至标准的
            <Button type="link" href="/contract/import">PDF合同导入</Button>
            页面。
            <br />
            This page is deprecated. Please use the standard PDF Import page which now supports Smart Mode.
          </div>
        }
        type="warning"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <div style={{ opacity: 0.5, pointerEvents: 'none', filter: 'grayscale(100%)' }}>
        {/* Deprecated Content Below */}
        <Title level={2} style={{ textAlign: 'center', marginBottom: 32 }}>
          <FireOutlined style={{ color: COLORS.error, marginRight: 8 }} />
          增强版PDF智能导入
          <Tag color="blue" style={{ marginLeft: 8 }}>中文合同专用</Tag>
        </Title>

        {/* 系统能力状态 */}
        {systemCapabilities && (
          <Alert
            message={
              <Space>
                <Text>增强功能状态: </Text>
                <Badge
                  status={systemCapabilities.enhanced_extraction ? 'success' : 'warning'}
                  text={
                    systemCapabilities.enhanced_extraction
                      ? '完全可用'
                      : '部分功能受限'
                  }
                />
                <Text style={{ marginLeft: 8 }}>
                  共7个优化模块可用
                </Text>
              </Space>
            }
            type={systemCapabilities.enhanced_extraction ? 'success' : 'warning'}
            showIcon
            style={{ marginBottom: 24 }}
          />
        )}

        {/* 功能展示 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={24}>
            <Card title="增强功能特性" size="small">
              <Row gutter={[16, 16]}>
                <Col span={6}>
                  <Space direction="vertical" size="small">
                    {renderFeatureTag(!!systemCapabilities?.chinese_optimized, '中文OCR优化', 'blue')}
                    {renderFeatureTag(!!systemCapabilities?.table_detection, '表格分析', 'green')}
                    {renderFeatureTag(!!systemCapabilities?.seal_detection, '印章检测', 'purple')}
                  </Space>
                </Col>
                <Col span={6}>
                  <Space direction="vertical" size="small">
                    {renderFeatureTag(!!systemCapabilities?.multi_engine_support, '多引擎融合', 'orange')}
                    {renderFeatureTag(!!systemCapabilities?.semantic_validation, '语义验证', 'red')}
                    {renderFeatureTag(!!systemCapabilities?.template_learning, '模板学习', 'cyan')}
                  </Space>
                </Col>
                <Col span={6}>
                  <Space direction="vertical" size="small">
                    {renderFeatureTag(!!systemCapabilities?.real_time_validation, '实时验证', 'magenta')}
                    {renderFeatureTag(true, '智能匹配', 'default')}
                    {renderFeatureTag(true, '质量评估', 'default')}
                  </Space>
                </Col>
                <Col span={6}>
                  <Space direction="vertical" size="small">
                    {renderFeatureTag(!!systemCapabilities?.chinese_optimized, '深度学习', 'geekblue')}
                    {renderFeatureTag(true, '自适应算法', 'purple')}
                    {renderFeatureTag(true, '用户体验优化', 'gold')}
                  </Space>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        {/* 上传和处理选项 */}
        <Row gutter={16}>
          <Col span={16}>
            <Card title="文件上传" style={{ minHeight: 300 }}>
              <Dragger {...uploadProps} style={{ padding: 24 }}>
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽PDF文件到此处上传</p>
                <p className="ant-upload-hint">
                  支持中文合同扫描件，推荐使用高质量扫描
                </p>
              </Dragger>

              {fileList.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Text>文件: {fileList[0].name}</Text>
                  <Progress
                    percent={uploadProgress}
                    status={uploadProgress === 100 ? 'success' : 'active'}
                    style={{ marginTop: 8 }}
                  />
                </div>
              )}
            </Card>
          </Col>

          <Col span={8}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Card title="处理选项" size="small" style={{ flex: 1 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button
                    type="default"
                    icon={<SettingOutlined />}
                    onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                  >
                    {showAdvancedSettings ? '隐藏设置' : '高级设置'}
                  </Button>

                  <div style={{ marginTop: 16 }}>
                    <Text strong>当前配置:</Text>
                    <div style={{ marginTop: 8 }}>
                      <div>中文优化: {processingOptions.enable_chinese_optimization ? '启用' : '禁用'}</div>
                      <div>多引擎: {processingOptions.enable_multi_engine_fusion ? '启用' : '禁用'}</div>
                      <div>语义验证: {processingOptions.enable_semantic_validation ? '启用' : '禁用'}</div>
                    </div>
                  </div>
                </Space>
              </Card>

              <Space style={{ marginTop: 16 }}>
                <Button
                  type="primary"
                  icon={<RobotOutlined />}
                  onClick={() => pdfImportService.testEnhancedFeatures()}
                >
                  测试增强功能
                </Button>
              </Space>
            </Space>
          </Col>
        </Row>

        {/* 高级设置 */}
        {renderProcessingOptions()}

        {/* 处理状态 */}
        {processing && sessionId && (
          <Card title="处理状态" style={{ marginTop: 24 }}>
            <EnhancedProcessingStatus
              sessionId={sessionId}
              currentStatus={currentStatus || undefined}
              onError={(error) => MessageManager.error('处理状态错误: ' + error)}
              showDetails={true}
            />
          </Card>
        )}

        {/* 处理结果 */}
        {showResults && currentStatus && (
          <Card title="智能处理结果" style={{ marginTop: 24 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ marginBottom: 16 }}>
                <Title level={4}>
                  <FileTextOutlined style={{ marginRight: 8 }} />
                  处理摘要
                </Title>

                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="识别字段数"
                      value={Object.keys(currentStatus.enhanced_status?.final_fields || {}).length}
                      suffix="/58"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="总体置信度"
                      value={currentStatus.enhanced_status?.semantic_validation?.overall_confidence ?
                        (currentStatus.enhanced_status.semantic_validation.overall_confidence * 100).toFixed(1) : 0}
                      suffix="%"
                      precision={1}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="处理时间"
                      value={'60-90秒'}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="状态"
                      value={currentStatus.status === 'ready_for_review' ? '完成' : '处理中'}
                      valueStyle={{
                        color: currentStatus.status === 'ready_for_review' ? COLORS.success : COLORS.primary
                      }}
                    />
                  </Col>
                </Row>
              </div>

              <EnhancedContractReview
                sessionData={currentStatus as unknown as Record<string, unknown>}
                onConfirm={(_confirmedData: Record<string, unknown>) => {
                  // Confirm import data
                  MessageManager.success('功能开发中，数据提交功能将在下个版本实现');
                }}
                onCancel={handleCancel}
              />
            </Space>
          </Card>
        )}

        {/* 底部操作按钮 */}
        {processing && (
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Space>
              <Button onClick={handleRetry} disabled={!sessionId}>
                <RobotOutlined />
                刷新状态
              </Button>
              <Button onClick={handleCancel} danger>
                取消处理
              </Button>
            </Space>
          </div>
        )}

        {/* 帮助提示 */}
        <Alert
          message={
            <Space>
              <QuestionCircleOutlined />
              <Text style={{ marginLeft: 8 }}>
                提示：增强版PDF导入专门针对中文租赁合同进行了优化，相比标准版本识别准确率提升25-35%
              </Text>
            </Space>
          }
          type="info"
          style={{ marginTop: 24 }}
          showIcon
        />
      </div>
      </div>
      );
};

      export default EnhancedPDFImportPage;
