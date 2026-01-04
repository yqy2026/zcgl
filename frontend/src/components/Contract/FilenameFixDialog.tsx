import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Space,
  Typography,
  Alert,
  Steps,
  Card,
  Row,
  Col,
  Table,
  Tag,
  message,
  Spin
} from 'antd';
import {
  InfoCircleOutlined,
  ReloadOutlined,
  CopyOutlined
} from '@ant-design/icons';
import { createLogger } from '../../utils/logger';

const componentLogger = createLogger('FilenameFixDialog');
const { Title, Text, Paragraph } = Typography;

interface FilenameFixDialogProps {
  visible: boolean;
  onCancel: () => void;
  originalFilename: string;
  onFilenameFixed: (fixedFilename: string) => void;
}

interface ValidationResult {
  valid: boolean;
  issues: string[];
  suggestions: string[];
  severity: 'low' | 'medium' | 'high';
}

interface FixStep {
  title: string;
  description: string;
  status: 'wait' | 'process' | 'finish' | 'error';
  content?: React.ReactNode;
}

interface FilenameChange {
  original: string;
  fixed: string;
  reason: string;
  type: 'replacement' | 'removal' | 'truncation' | 'addition';
}

export const FilenameFixDialog: React.FC<FilenameFixDialogProps> = ({
  visible,
  onCancel,
  originalFilename,
  onFilenameFixed
}) => {
  const [loading, setLoading] = useState(false);
  const [_validationResult, _setValidationResult] = useState<ValidationResult | null>(null);
  const [suggestedFilename, setSuggestedFilename] = useState<string>('');
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [_filenameChanges, _setFilenameChanges] = useState<FilenameChange[]>([]);
  const [customFilename, setCustomFilename] = useState<string>('');
  const [copySuccess, setCopySuccess] = useState<boolean>(false);

  // 步骤定义
  const [steps, setSteps] = useState<FixStep[]>([]);

  // 中文特殊字符映射
  const charMappings: { [key: string]: string } = {
    '【': '[',
    '】': ']',
    '（': '(',
    '）': ')',
    '《': '<',
    '》': '>',
    '\u201C': '"',  // Left double quotation mark
    '\u201D': '"',  // Right double quotation mark
    '\u2018': "'",  // Left single quotation mark
    '\u2019': "'",  // Right single quotation mark
    '：': ':',
    '，': ',',
    '。': '.',
    '；': ';',
    '！': '!',
    '？': '?',
    '…': '...',
    '—': '-',
    '–': '-'
  };

  const analyzeAndFixFilename = (filename: string): { fixed: string; changes: FilenameChange[] } => {
    const changes: FilenameChange[] = [];
    let fixed = filename;

    // 步骤1: 分离文件名和扩展名
    const nameWithoutExt = fixed.replace(/\.pdf$/i, '');
    const ext = fixed.endsWith('.pdf') ? '.pdf' : '';

    // 步骤2: 替换中文特殊字符
    let tempFixed = nameWithoutExt;
    Object.entries(charMappings).forEach(([chinese, standard]) => {
      if (tempFixed.includes(chinese)) {
        const before = tempFixed;
        tempFixed = tempFixed.replace(new RegExp(chinese, 'g'), standard);
        if (before !== tempFixed) {
          changes.push({
            original: chinese,
            fixed: standard,
            reason: '中文特殊字符替换为标准字符',
            type: 'replacement'
          });
        }
      }
    });

    // 步骤3: 移除危险字符
    const dangerousChars = /[<>:"/\\|?*]/g;
    const beforeDangerous = tempFixed;
    tempFixed = tempFixed.replace(dangerousChars, '_');
    if (beforeDangerous !== tempFixed) {
      const dangerousMatches = beforeDangerous.match(/[<>:"/\\|?*]/g) || [];
      dangerousMatches.forEach(char => {
        changes.push({
          original: char,
          fixed: '_',
          reason: '移除系统不兼容字符',
          type: 'removal'
        });
      });
    }

    // 步骤4: 合并连续的特殊字符
    const beforeConsecutive = tempFixed;
    tempFixed = tempFixed.replace(/_{2,}/g, '_');
    if (beforeConsecutive !== tempFixed) {
      changes.push({
        original: '__',
        fixed: '_',
        reason: '合并连续的特殊字符',
        type: 'removal'
      });
    }

    // 步骤5: 移除开头和结尾的特殊字符
    const beforeTrim = tempFixed;
    tempFixed = tempFixed.replace(/^[._-]+|[._-]+$/g, '');
    if (beforeTrim !== tempFixed) {
      changes.push({
        original: beforeTrim + (beforeTrim !== tempFixed ? '...' : ''),
        fixed: tempFixed,
        reason: '移除开头/结尾的特殊字符',
        type: 'removal'
      });
    }

    // 步骤6: 长度检查和截断
    const maxLength = 200;
    if (tempFixed.length > maxLength - ext.length) {
      const originalLength = tempFixed.length;
      const keepLength = maxLength - ext.length - 15;
      const tempFixed2 = tempFixed.substring(0, keepLength) + '...' + tempFixed.substring(-12);
      changes.push({
        original: tempFixed,
        fixed: tempFixed2,
        reason: `文件名截断 (${originalLength} → ${tempFixed2.length})`,
        type: 'truncation'
      });
      tempFixed = tempFixed2;
    }

    // 步骤7: 确保有PDF扩展名
    if (!ext || !ext.toLowerCase().includes('.pdf')) {
      const beforeExt = tempFixed;
      tempFixed += '.pdf';
      if (beforeExt !== tempFixed) {
        changes.push({
          original: beforeExt,
          fixed: tempFixed,
          reason: '添加PDF扩展名',
          type: 'addition'
        });
      }
    }

    fixed = tempFixed;
    return { fixed, changes };
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (visible && originalFilename) {
      validateAndSuggest();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, originalFilename]);

  const validateAndSuggest = async () => {
    setLoading(true);
    setCurrentStep(0);

    try {
      // 本地分析和修复
      const { fixed, changes } = analyzeAndFixFilename(originalFilename);
      setSuggestedFilename(fixed);
      _setFilenameChanges(changes);
      setCustomFilename(fixed);

      // 构建步骤信息
      const newSteps: FixStep[] = [
        {
          title: '文件名分析',
          description: '分析原始文件名中的问题',
          status: 'finish',
          content: (
            <div>
              <Text strong>原始文件名:</Text>
              <div style={{
                padding: '8px 12px',
                backgroundColor: '#fff1f0',
                borderRadius: '6px',
                marginTop: '8px',
                wordBreak: 'break-all'
              }}>
                <Text code>{originalFilename}</Text>
              </div>
            </div>
          )
        }
      ];

      if (changes.length > 0) {
        newSteps.push({
          title: '自动修复',
          description: `执行 ${changes.length} 项修复操作`,
          status: 'finish',
          content: (
            <Table
              size="small"
              dataSource={changes}
              pagination={false}
              columns={[
                {
                  title: '原字符',
                  dataIndex: 'original',
                  key: 'original',
                  render: (text: string) => (
                    <Tag color="red">{text}</Tag>
                  )
                },
                {
                  title: '修复为',
                  dataIndex: 'fixed',
                  key: 'fixed',
                  render: (text: string) => (
                    <Tag color="green">{text}</Tag>
                  )
                },
                {
                  title: '原因',
                  dataIndex: 'reason',
                  key: 'reason',
                  ellipsis: true
                }
              ]}
            />
          )
        });
      }

      newSteps.push({
        title: '完成检查',
        description: '验证修复结果',
        status: 'finish',
        content: (
          <div>
            <Space direction="vertical">
              <div>
                <Text strong>建议文件名:</Text>
                <div style={{
                  padding: '8px 12px',
                  backgroundColor: '#f6ffed',
                  borderRadius: '6px',
                  marginTop: '8px',
                  wordBreak: 'break-all'
                }}>
                  <Text code style={{ color: '#389e0d' }}>{fixed}</Text>
                </div>
              </div>
              <Button
                size="small"
                icon={<CopyOutlined />}
                onClick={() => {
                  navigator.clipboard.writeText(fixed);
                  setCopySuccess(true);
                  setTimeout(() => setCopySuccess(false), 2000);
                  message.success('文件名已复制到剪贴板');
                }}
              >
                {copySuccess ? '已复制' : '复制文件名'}
              </Button>
            </Space>
          </div>
        )
      });

      setSteps(newSteps);
      setCurrentStep(newSteps.length - 1);

    } catch (error) {
      componentLogger.error('文件名修复失败:', error as Error);
      setSteps([
        {
          title: '修复失败',
          description: '文件名修复过程中发生错误',
          status: 'error',
          content: (
            <Alert
              type="error"
              message="文件名修复失败"
              description="请检查文件名格式或手动重命名"
            />
          )
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomFilenameChange = (value: string) => {
    setCustomFilename(value);
    const { fixed, changes } = analyzeAndFixFilename(value);
    setSuggestedFilename(fixed);
    _setFilenameChanges(changes);
  };

  const handleConfirm = () => {
    onFilenameFixed(suggestedFilename);
    onCancel();
    message.success('文件名已更新');
  };

  const renderStepContent = () => {
    const currentStepData = steps[currentStep];
    if ((currentStepData === null || currentStepData === undefined)) return null;

    return (
      <div style={{ padding: '20px 0' }}>
        {currentStepData.content}
      </div>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <InfoCircleOutlined />
          <span>文件名优化助手</span>
        </Space>
      }
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="retry"
          icon={<ReloadOutlined />}
          onClick={validateAndSuggest}
          loading={loading}
        >
          重新分析
        </Button>,
        <Button
          key="confirm"
          type="primary"
          onClick={handleConfirm}
          disabled={!suggestedFilename}
        >
          确认使用
        </Button>
      ]}
      destroyOnHidden
    >
      <Spin spinning={loading}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>文件名智能修复</Title>
            <Paragraph type="secondary">
              系统将自动检测并修复文件名中的问题，确保文件名在所有操作系统上都能正常工作。
            </Paragraph>
          </div>

          <Card>
            <Steps current={currentStep} items={steps} />
            {renderStepContent()}
          </Card>

          {/* 手动编辑选项 */}
          <Card title="手动调整（可选）" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>自定义文件名:</Text>
                <div style={{ marginTop: 8 }}>
                  <input
                    type="text"
                    value={customFilename}
                    onChange={(e) => handleCustomFilenameChange(e.target.value)}
                    placeholder="输入自定义文件名"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      border: '1px solid #d9d9d9',
                      borderRadius: '6px'
                    }}
                  />
                </div>
              </div>
              <Alert
                message="提示"
                description="您可以直接编辑文件名，系统会实时验证并提供修复建议。"
                type="info"
                showIcon
                style={{ fontSize: '12px' }}
              />
            </Space>
          </Card>

          {/* 预览结果 */}
          {suggestedFilename && (
            <Card title="修复结果预览" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Row gutter={16}>
                  <Col span={4}>
                    <Text strong>修复前:</Text>
                  </Col>
                  <Col span={20}>
                    <Text code style={{ wordBreak: 'break-all', fontSize: '12px' }}>
                      {originalFilename}
                    </Text>
                  </Col>
                </Row>
                <Row gutter={16}>
                  <Col span={4}>
                    <Text strong>修复后:</Text>
                  </Col>
                  <Col span={20}>
                    <Text code style={{ wordBreak: 'break-all', fontSize: '12px', color: '#389e0d' }}>
                      {suggestedFilename}
                    </Text>
                  </Col>
                </Row>
              </Space>
            </Card>
          )}

          {/* 修复说明 */}
          <Alert
            message="关于文件名修复"
            description={
              <div style={{ fontSize: '12px' }}>
                <p>• <strong>中文特殊字符</strong>：【】（）等会被替换为标准字符 []()</p>
                <p>• <strong>危险字符</strong>：&lt;&gt;:"/\\|?* 等会被移除或替换</p>
                <p>• <strong>长度限制</strong>：超过200字符的文件名会被智能截断</p>
                <p>• <strong>扩展名</strong>：确保文件以.pdf结尾</p>
              </div>
            }
            type="info"
            showIcon
          />
        </Space>
      </Spin>
    </Modal>
  );
};

export default FilenameFixDialog;
