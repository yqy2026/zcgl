/**
 * LLM Prompt 编辑器组件
 * 支持创建和编辑 Prompt 模板，带实时预览功能
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Space,
  Card,
  Tag,
  message,
  Row,
  Col,
  Typography,
  Alert,
  Tabs,
} from 'antd';
import { SaveOutlined, EyeOutlined } from '@ant-design/icons';

import type { PromptTemplate, PromptTemplateCreate, PromptTemplateUpdate } from '@/types/llmPrompt';
import { DocType, LLMProvider } from '@/types/llmPrompt';
import { llmPromptService } from '@/services/llmPromptService';
import { createLogger } from '@/utils/logger';
import styles from './PromptEditor.module.css';

const logger = createLogger('PromptEditor');
const { TextArea } = Input;
const { Option } = Select;
const { Text, Paragraph } = Typography;

// Form values interface
interface PromptFormValues {
  name: string;
  doc_type?: string;
  provider?: string;
  description?: string;
  system_prompt?: string;
  user_prompt_template?: string;
  few_shot_examples?: string;
  tags?: string[];
  change_description?: string;
}

interface PromptEditorProps {
  visible: boolean;
  prompt?: PromptTemplate | null;
  mode: 'create' | 'edit';
  onSuccess: () => void;
  onCancel: () => void;
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  visible,
  prompt,
  mode,
  onSuccess,
  onCancel,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState({
    system_prompt: '',
    user_prompt_template: '',
  });
  const [activeTab, setActiveTab] = useState('edit');

  // 初始化表单数据
  useEffect(() => {
    if (visible) {
      if (mode === 'edit' && prompt != null) {
        form.setFieldsValue({
          name: prompt.name,
          doc_type: prompt.doc_type,
          provider: prompt.provider,
          description: prompt.description ?? '',
          system_prompt: prompt.system_prompt,
          user_prompt_template: prompt.user_prompt_template,
          few_shot_examples: JSON.stringify(prompt.few_shot_examples ?? {}, null, 2),
          tags: prompt.tags ?? [],
        });
        setPreviewData({
          system_prompt: prompt.system_prompt,
          user_prompt_template: prompt.user_prompt_template,
        });
      } else {
        form.resetFields();
        setPreviewData({
          system_prompt: '',
          user_prompt_template: '',
        });
      }
    }
  }, [visible, mode, prompt, form]);

  // 实时预览更新
  const handleFieldChange = (field: 'system_prompt' | 'user_prompt_template', value: string) => {
    setPreviewData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = (await form.validateFields()) as PromptFormValues;
      setLoading(true);

      // 解析 few_shot_examples
      let fewShotExamples: Record<string, unknown> = {};
      try {
        if (values.few_shot_examples && values.few_shot_examples.trim() !== '') {
          fewShotExamples = JSON.parse(values.few_shot_examples) as Record<string, unknown>;
        }
      } catch {
        message.error('Few-shot 示例 JSON 格式不正确');
        setLoading(false);
        return;
      }

      if (mode === 'create') {
        const createData: PromptTemplateCreate = {
          name: values.name,
          doc_type: (values.doc_type ?? DocType.CONTRACT) as DocType,
          provider: (values.provider ?? LLMProvider.QWEN) as LLMProvider,
          description: values.description ?? '',
          system_prompt: values.system_prompt ?? '',
          user_prompt_template: values.user_prompt_template ?? '',
          few_shot_examples: fewShotExamples,
          tags: values.tags ?? [],
        };

        await llmPromptService.createPrompt(createData);
        message.success('Prompt 创建成功');
      } else if (mode === 'edit' && prompt != null) {
        const updateData: PromptTemplateUpdate = {
          name: values.name,
          description: values.description,
          system_prompt: values.system_prompt,
          user_prompt_template: values.user_prompt_template,
          few_shot_examples: fewShotExamples,
          tags: values.tags ?? [],
          change_description: values.change_description,
        };

        await llmPromptService.updatePrompt(prompt.id, updateData);
        message.success('Prompt 更新成功');
      }

      onSuccess();
    } catch (error) {
      logger.error('提交失败', error);
      message.error('操作失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 预览变量替换
  const renderPreview = (template: string) => {
    // 简单的变量替换预览
    const preview = template
      .replace('{pages_hint}', '\\n\\n注意:这是一份多页文档')
      .replace(/\{\{/g, '【')
      .replace(/\}\}/g, '】');

    return preview;
  };

  const tabItems = [
    {
      key: 'edit',
      label: '编辑',
      children: (
        <div>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Prompt 名称"
                name="name"
                rules={[
                  { required: true, message: '请输入名称' },
                  { max: 100, message: '名称不能超过100个字符' },
                ]}
              >
                <Input placeholder="例如: 租赁合同提取-Qwen" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="文档类型"
                name="doc_type"
                rules={[{ required: true, message: '请选择文档类型' }]}
              >
                <Select placeholder="选择文档类型">
                  <Option value={DocType.CONTRACT}>租赁合同</Option>
                  <Option value={DocType.PROPERTY_CERT}>产权证</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="LLM 提供商"
                name="provider"
                rules={[{ required: true, message: '请选择提供商' }]}
              >
                <Select placeholder="选择提供商">
                  <Option value={LLMProvider.QWEN}>Qwen (阿里)</Option>
                  <Option value={LLMProvider.HUNYUAN}>Hunyuan (腾讯)</Option>
                  <Option value={LLMProvider.DEEPSEEK}>DeepSeek</Option>
                  <Option value={LLMProvider.GLM}>GLM (智谱)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="标签" name="tags">
                <Select mode="tags" placeholder="输入标签，回车添加">
                  <Option value="提取">提取</Option>
                  <Option value="合同">合同</Option>
                  <Option value="产权证">产权证</Option>
                  <Option value="优化">优化</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="简要描述此 Prompt 的用途" maxLength={500} showCount />
          </Form.Item>

          <Form.Item
            label="系统 Prompt (System Prompt)"
            name="system_prompt"
            rules={[{ required: true, message: '请输入系统 Prompt' }]}
            extra="定义 AI 助手的角色和基本规则"
          >
            <TextArea
              rows={6}
              placeholder="例如: 你是一位专业的合同信息提取专家..."
              onChange={e => handleFieldChange('system_prompt', e.target.value)}
            />
          </Form.Item>

          <Form.Item
            label="用户 Prompt 模板 (User Prompt Template)"
            name="user_prompt_template"
            rules={[{ required: true, message: '请输入用户 Prompt 模板' }]}
            extra="具体的任务指令，可使用变量如 {pages_hint}"
          >
            <TextArea
              rows={10}
              placeholder="例如: 请分析这份合同图片，提取以下信息..."
              onChange={e => handleFieldChange('user_prompt_template', e.target.value)}
            />
          </Form.Item>

          <Form.Item
            label="Few-shot 示例 (JSON)"
            name="few_shot_examples"
            extra="可选：提供示例帮助 AI 理解任务格式"
          >
            <TextArea
              rows={6}
              placeholder='{"example1": {"input": "...", "output": "..."}}'
              className={styles.monospaceTextarea}
            />
          </Form.Item>

          {mode === 'edit' && (
            <Form.Item
              label="变更说明"
              name="change_description"
              rules={[{ required: true, message: '请说明此次变更的内容' }]}
            >
              <Input placeholder="例如: 优化了日期识别的准确性" />
            </Form.Item>
          )}
        </div>
      ),
    },
    {
      key: 'preview',
      label: '预览',
      children: (
        <div>
          <Card title="系统 Prompt" size="small" className={styles.cardSpacing}>
            <Paragraph className={styles.promptPreview}>
              {previewData.system_prompt || '暂无内容'}
            </Paragraph>
          </Card>

          <Card title="用户 Prompt 模板" size="small">
            <Paragraph className={styles.promptPreview}>
              {renderPreview(previewData.user_prompt_template) || '暂无内容'}
            </Paragraph>
          </Card>

          <Alert
            title="提示"
            description="预览中的 {pages_hint} 等变量将在实际使用时被替换为具体内容"
            type="info"
            showIcon
            className={styles.previewTip}
          />
        </div>
      ),
    },
    {
      key: 'help',
      label: '帮助',
      children: (
        <div>
          <Card title="什么是 System Prompt?" size="small" className={styles.cardSpacing}>
            <Paragraph>
              System Prompt 定义了 AI 助手的<strong>角色</strong>和<strong>基本行为规则</strong>。
              它会应用到所有对话中，设定 AI 的&quot;人格&quot;和&quot;工作方式&quot;。
            </Paragraph>
            <Paragraph>
              <Text strong>示例：</Text>
              <br />
              <Text code>
                你是一位专业的合同信息提取专家，擅长从中国房地产租赁合同中准确提取结构化信息。
              </Text>
            </Paragraph>
          </Card>

          <Card title="什么是 User Prompt Template?" size="small" className={styles.cardSpacing}>
            <Paragraph>
              User Prompt Template 是<strong>具体的任务指令</strong>，描述了需要完成的具体工作。
              可以使用变量模板，如 <Text code>&#123;pages_hint&#125;</Text> 会在运行时被替换。
            </Paragraph>
            <Paragraph>
              <Text strong>示例：</Text>
              <br />
              <Text code>请分析这份合同图片，提取以下信息并返回JSON格式...</Text>
            </Paragraph>
          </Card>

          <Card title="什么是 Few-shot 示例?" size="small" className={styles.cardSpacing}>
            <Paragraph>
              Few-shot 示例通过提供<strong>输入-输出示例</strong>，帮助 AI
              理解期望的格式和质量标准。 这对于复杂的提取任务特别有效。
            </Paragraph>
            <Paragraph>
              <Text strong>示例：</Text>
              <br />
              <Text>示例输入包含合同图片，示例输出包含提取到的合同号 HT-2024-001</Text>
            </Paragraph>
          </Card>

          <Alert
            title="最佳实践"
            description={
              <ul>
                <li>System Prompt 要简洁明了，定义清楚角色和规则</li>
                <li>User Prompt 要具体详细，明确输出格式和字段要求</li>
                <li>Few-shot 示例要覆盖常见的边界情况</li>
                <li>使用 JSON 格式输出时，要给出完整的结构示例</li>
                <li>测试和迭代是提高 Prompt 质量的关键</li>
              </ul>
            }
            type="success"
            showIcon
          />
        </div>
      ),
    },
  ];

  return (
    <Modal
      title={
        <Space>
          {mode === 'create' ? '新建 Prompt' : '编辑 Prompt'}
          {mode === 'edit' && prompt && <Tag color="blue">v{prompt.version}</Tag>}
        </Space>
      }
      open={visible}
      onCancel={onCancel}
      width={900}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="preview" icon={<EyeOutlined />} onClick={() => setActiveTab('preview')}>
          预览
        </Button>,
        <Button
          key="submit"
          type="primary"
          icon={<SaveOutlined />}
          loading={loading}
          onClick={handleSubmit}
        >
          {mode === 'create' ? '创建' : '保存'}
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical">
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Form>
    </Modal>
  );
};

export default PromptEditor;
