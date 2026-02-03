/**
 * LLM Prompt 管理列表页面
 * 提供 Prompt 模板的列表展示、筛选、激活、版本管理等功能
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Select,
  Modal,
  Tooltip,
  Row,
  Col,
  Statistic,
  Typography,
  message,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  RocketOutlined,
  HistoryOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import {
  PromptTemplate,
  PromptStatus,
  DocType,
  LLMProvider,
  PromptQueryParams,
  PromptStatistics,
} from '@/types/llmPrompt';
import { llmPromptService } from '@/services/llmPromptService';
import { createLogger } from '@/utils/logger';
import { COLORS } from '@/styles/colorMap';
import PromptEditor from '@/components/System/PromptEditor';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import { useListData } from '@/hooks/useListData';

const logger = createLogger('PromptListPage');
const { Title } = Typography;
const { Option } = Select;

interface PromptFilters {
  doc_type?: DocType;
  status?: PromptStatus;
  provider?: LLMProvider;
}

const PromptListPage: React.FC = () => {
  const [statistics, setStatistics] = useState<PromptStatistics | null>(null);
  const [editorVisible, setEditorVisible] = useState(false);
  const [editorMode, setEditorMode] = useState<'create' | 'edit'>('create');
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(null);

  const fetchPromptList = useCallback(
    async ({
      page,
      pageSize,
      doc_type,
      status,
      provider,
    }: {
      page: number;
      pageSize: number;
    } & PromptFilters) => {
      const params: PromptQueryParams = {
        page,
        pageSize,
      };

      if (doc_type != null) {
        params.doc_type = doc_type;
      }
      if (status != null) {
        params.status = status;
      }
      if (provider != null) {
        params.provider = provider;
      }

      return await llmPromptService.getPrompts(params);
    },
    []
  );

  const handleLoadError = useCallback((error: unknown) => {
    logger.error('加载 Prompt 列表失败', error);
    message.error('加载 Prompt 列表失败');
  }, []);

  const {
    data: prompts,
    loading,
    pagination,
    filters,
    loadList,
    applyFilters,
    updatePagination,
  } = useListData<PromptTemplate, PromptFilters>({
    fetcher: fetchPromptList,
    initialFilters: {
      doc_type: undefined,
      status: undefined,
      provider: undefined,
    },
    initialPageSize: 10,
    onError: handleLoadError,
  });

  // 加载统计数据
  const loadStatistics = useCallback(async () => {
    try {
      const stats = await llmPromptService.getStatistics();
      setStatistics(stats);
    } catch (error) {
      logger.error('加载统计数据失败', error);
    }
  }, []);

  useEffect(() => {
    void loadList();
    void loadStatistics();
  }, [loadList, loadStatistics]);

  const handleRefresh = useCallback(() => {
    void loadList();
    void loadStatistics();
  }, [loadList, loadStatistics]);

  // 激活 Prompt
  const handleActivate = async (id: string, name: string) => {
    try {
      await llmPromptService.activatePrompt(id);
      message.success(`Prompt "${name}" 已激活`);
      void loadList();
    } catch (error) {
      logger.error(`激活 Prompt 失败: ${id}`, error);
      message.error('激活失败');
    }
  };

  // 查看版本历史
  const handleViewVersions = async (prompt: PromptTemplate) => {
    try {
      const versions = await llmPromptService.getPromptVersions(prompt.id);

      Modal.info({
        title: `版本历史 - ${prompt.name}`,
        width: 800,
        content: (
          <div style={{ marginTop: 16 }}>
            {versions.length === 0 ? (
              <p>暂无版本记录</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <th style={{ padding: '8px', textAlign: 'left' }}>版本</th>
                    <th style={{ padding: '8px', textAlign: 'left' }}>变更说明</th>
                    <th style={{ padding: '8px', textAlign: 'left' }}>创建时间</th>
                    <th style={{ padding: '8px', textAlign: 'left' }}>自动生成</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map(version => (
                    <tr key={version.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '8px' }}>
                        <Tag color="blue">{version.version}</Tag>
                      </td>
                      <td style={{ padding: '8px' }}>{version.change_description || '-'}</td>
                      <td style={{ padding: '8px' }}>
                        {dayjs(version.created_at).format('YYYY-MM-DD HH:mm')}
                      </td>
                      <td style={{ padding: '8px' }}>
                        {version.auto_generated ? <Tag color="purple">自动</Tag> : <Tag>手动</Tag>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ),
      });
    } catch (error) {
      logger.error(`获取版本历史失败: ${prompt.id}`, error);
      message.error('获取版本历史失败');
    }
  };

  // 打开新建编辑器
  const handleCreate = () => {
    setEditorVisible(true);
    setEditorMode('create');
    setSelectedPrompt(null);
  };

  // 打开编辑编辑器
  const handleEdit = (prompt: PromptTemplate) => {
    setEditorVisible(true);
    setEditorMode('edit');
    setSelectedPrompt(prompt);
  };

  // 关闭编辑器
  const handleEditorCancel = () => {
    setEditorVisible(false);
    setSelectedPrompt(null);
  };

  // 编辑器成功回调
  const handleEditorSuccess = () => {
    setEditorVisible(false);
    setSelectedPrompt(null);
    void loadList();
    void loadStatistics();
  };

  // 表格列定义
  const columns: ColumnsType<PromptTemplate> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: PromptTemplate) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>v{record.version}</div>
        </div>
      ),
    },
    {
      title: '文档类型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 120,
      render: (docType: DocType) => {
        const config: Record<DocType, { text: string; color: string }> = {
          [DocType.CONTRACT]: { text: '租赁合同', color: 'blue' },
          [DocType.PROPERTY_CERT]: { text: '产权证', color: 'green' },
        };
        const { text, color } = config[docType] ?? { text: docType, color: 'default' };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '提供商',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      render: (provider: LLMProvider) => {
        const config: Record<LLMProvider, { text: string; color: string }> = {
          [LLMProvider.QWEN]: { text: 'Qwen', color: 'cyan' },
          [LLMProvider.HUNYUAN]: { text: '混元', color: 'purple' },
          [LLMProvider.DEEPSEEK]: { text: 'DeepSeek', color: 'orange' },
          [LLMProvider.GLM]: { text: '智谱', color: 'geekblue' },
        };
        const { text, color } = config[provider] ?? { text: provider, color: 'default' };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: PromptStatus) => {
        const config: Record<PromptStatus, { text: string; color: string; icon: React.ReactNode }> =
          {
            [PromptStatus.ACTIVE]: {
              text: '活跃',
              color: 'success',
              icon: <CheckCircleOutlined />,
            },
            [PromptStatus.DRAFT]: { text: '草稿', color: 'default', icon: null },
            [PromptStatus.ARCHIVED]: { text: '已归档', color: 'default', icon: null },
          };
        const { text, color, icon } = config[status] ?? {
          text: status,
          color: 'default',
          icon: null,
        };
        return (
          <Tag icon={icon} color={color}>
            {text}
          </Tag>
        );
      },
    },
    {
      title: '平均准确率',
      dataIndex: 'avg_accuracy',
      key: 'avg_accuracy',
      width: 120,
      render: (value: number) => (
        <div>
          <div
            style={{
              fontWeight: value >= 90 ? 'bold' : 'normal',
              color: value >= 90 ? COLORS.success : value >= 70 ? COLORS.warning : COLORS.error,
            }}
          >
            {(value * 100).toFixed(1)}%
          </div>
        </div>
      ),
    },
    {
      title: '平均置信度',
      dataIndex: 'avg_confidence',
      key: 'avg_confidence',
      width: 120,
      render: (value: number) => (
        <div>
          <div
            style={{
              color: value >= 0.8 ? COLORS.success : value >= 0.6 ? COLORS.warning : COLORS.error,
            }}
          >
            {(value * 100).toFixed(1)}%
          </div>
        </div>
      ),
    },
    {
      title: '使用次数',
      dataIndex: 'total_usage',
      key: 'total_usage',
      width: 100,
      render: (value: number) => <span>{value}</span>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 120,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right' as const,
      render: (_: unknown, record: PromptTemplate) => (
        <Space size="small">
          {record.status !== PromptStatus.ACTIVE && (
            <Tooltip title="激活">
              <Button
                type="text"
                icon={<RocketOutlined />}
                onClick={() => handleActivate(record.id, record.name)}
              />
            </Tooltip>
          )}
          <Tooltip title="版本历史">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => handleViewVersions(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleDocTypeChange = useCallback(
    (value?: DocType) => {
      applyFilters({
        ...filters,
        doc_type: value,
      });
    },
    [applyFilters, filters]
  );

  const handleProviderChange = useCallback(
    (value?: LLMProvider) => {
      applyFilters({
        ...filters,
        provider: value,
      });
    },
    [applyFilters, filters]
  );

  const handleStatusChange = useCallback(
    (value?: PromptStatus) => {
      applyFilters({
        ...filters,
        status: value,
      });
    },
    [applyFilters, filters]
  );

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 统计卡片 */}
      {statistics != null && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总 Prompt 数"
                value={statistics.total_prompts}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃 Prompt"
                value={
                  statistics.status_distribution.find(
                    (s: { status: PromptStatus; count: number }) => s.status === PromptStatus.ACTIVE
                  )?.count ?? 0
                }
                prefix={<CheckCircleOutlined />}
                styles={{ content: { color: COLORS.success } }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均准确率"
                value={(statistics.overall_avg_accuracy * 100).toFixed(1)}
                suffix="%"
                styles={{ content: {
                  color: statistics.overall_avg_accuracy >= 0.85 ? COLORS.success : COLORS.warning,
                } }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均置信度"
                value={(statistics.overall_avg_confidence * 100).toFixed(1)}
                suffix="%"
                styles={{ content: {
                  color:
                    statistics.overall_avg_confidence >= 0.8 ? COLORS.success : COLORS.warning,
                } }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主卡片 */}
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              LLM Prompt 管理
            </Title>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
          </Space>
        }
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建 Prompt
            </Button>
          </Space>
        }
      >
        {/* 筛选器 */}
        <div style={{ marginBottom: 16 }}>
          <ListToolbar
            variant="plain"
            items={[
              {
                key: 'doc-type',
                col: { xs: 24, sm: 12, md: 6, lg: 4 },
                content: (
                  <Select
                    placeholder="文档类型"
                    allowClear
                    style={{ width: '100%' }}
                    value={filters.doc_type}
                    onChange={handleDocTypeChange}
                  >
                    <Option value={DocType.CONTRACT}>租赁合同</Option>
                    <Option value={DocType.PROPERTY_CERT}>产权证</Option>
                  </Select>
                ),
              },
              {
                key: 'provider',
                col: { xs: 24, sm: 12, md: 6, lg: 4 },
                content: (
                  <Select
                    placeholder="提供商"
                    allowClear
                    style={{ width: '100%' }}
                    value={filters.provider}
                    onChange={handleProviderChange}
                  >
                    <Option value={LLMProvider.QWEN}>Qwen</Option>
                    <Option value={LLMProvider.HUNYUAN}>混元</Option>
                    <Option value={LLMProvider.DEEPSEEK}>DeepSeek</Option>
                    <Option value={LLMProvider.GLM}>智谱</Option>
                  </Select>
                ),
              },
              {
                key: 'status',
                col: { xs: 24, sm: 12, md: 6, lg: 4 },
                content: (
                  <Select
                    placeholder="状态"
                    allowClear
                    style={{ width: '100%' }}
                    value={filters.status}
                    onChange={handleStatusChange}
                  >
                    <Option value={PromptStatus.ACTIVE}>活跃</Option>
                    <Option value={PromptStatus.DRAFT}>草稿</Option>
                    <Option value={PromptStatus.ARCHIVED}>已归档</Option>
                  </Select>
                ),
              },
            ]}
          />
        </div>

        {/* 表格 */}
        <TableWithPagination
          columns={columns}
          dataSource={prompts}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={updatePagination}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Prompt 编辑器 */}
      <PromptEditor
        visible={editorVisible}
        prompt={selectedPrompt}
        mode={editorMode}
        onSuccess={handleEditorSuccess}
        onCancel={handleEditorCancel}
      />
    </div>
  );
};

export default PromptListPage;
