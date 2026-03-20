/**
 * LLM Prompt 管理列表页面
 * 提供 Prompt 模板的列表展示、筛选、激活、版本管理等功能
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  Empty,
  Table,
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
  PromptVersion,
  PromptStatus,
  DocType,
  LLMProvider,
  PromptTemplateListResponse,
  PromptQueryParams,
  PromptStatistics,
} from '@/types/llmPrompt';
import { llmPromptService } from '@/services/llmPromptService';
import { createLogger } from '@/utils/logger';
import PromptEditor from '@/components/System/PromptEditor';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import PageContainer from '@/components/Common/PageContainer';
import { useQuery } from '@tanstack/react-query';
import {
  DOC_TYPE_META_MAP,
  PROVIDER_META_MAP,
  STATUS_META_MAP,
  VERSION_SOURCE_META,
  getAccuracyTone,
  getConfidenceTone,
  getToneClassName,
  normalizeVersion,
  type PromptFilters,
} from './promptListConstants';
import styles from './PromptListPage.module.css';

const logger = createLogger('PromptListPage');
const { Option } = Select;

const PromptListPage: React.FC = () => {
  const [filters, setFilters] = useState<PromptFilters>({
    doc_type: undefined,
    status: undefined,
    provider: undefined,
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });
  const [editorVisible, setEditorVisible] = useState(false);
  const [editorMode, setEditorMode] = useState<'create' | 'edit'>('create');
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(null);

  const fetchPromptList = useCallback(async (): Promise<PromptTemplateListResponse> => {
    const params: PromptQueryParams = {
      page: paginationState.current,
      pageSize: paginationState.pageSize,
      doc_type: filters.doc_type,
      status: filters.status,
      provider: filters.provider,
    };

    return await llmPromptService.getPrompts(params);
  }, [
    filters.doc_type,
    filters.provider,
    filters.status,
    paginationState.current,
    paginationState.pageSize,
  ]);

  const {
    data: promptsResponse,
    error: promptsError,
    isLoading: isPromptsLoading,
    isFetching: isPromptsFetching,
    refetch: refetchPrompts,
  } = useQuery<PromptTemplateListResponse>({
    queryKey: ['prompt-list', paginationState.current, paginationState.pageSize, filters],
    queryFn: fetchPromptList,
    retry: false,
  });

  const {
    data: statistics = null,
    error: statisticsError,
    refetch: refetchStatistics,
  } = useQuery<PromptStatistics>({
    queryKey: ['prompt-statistics'],
    queryFn: () => llmPromptService.getStatistics(),
    staleTime: 60 * 1000,
    retry: false,
  });

  useEffect(() => {
    if (promptsError != null) {
      logger.error('加载 Prompt 列表失败', promptsError);
      message.error('加载 Prompt 列表失败');
    }
  }, [promptsError]);

  useEffect(() => {
    if (statisticsError != null) {
      logger.error('加载统计数据失败', statisticsError);
    }
  }, [statisticsError]);

  const prompts = promptsResponse?.items ?? [];
  const loading = isPromptsLoading || isPromptsFetching;
  const isRefreshing = isPromptsFetching === true;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: promptsResponse?.total ?? 0,
    }),
    [paginationState.current, paginationState.pageSize, promptsResponse?.total]
  );
  const enabledFilterCount = [filters.doc_type, filters.provider, filters.status].filter(
    item => item != null
  ).length;
  const activePromptCount =
    statistics?.status_distribution.find(item => item.status === PromptStatus.ACTIVE)?.count ?? 0;

  const refreshPromptsAndStatistics = useCallback(() => {
    void refetchPrompts();
    void refetchStatistics();
  }, [refetchPrompts, refetchStatistics]);

  const handleRefresh = useCallback(() => {
    refreshPromptsAndStatistics();
  }, [refreshPromptsAndStatistics]);

  const updateFilters = useCallback((nextFilters: Partial<PromptFilters>) => {
    setFilters(prev => ({ ...prev, ...nextFilters }));
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

  // 激活 Prompt
  const handleActivate = async (id: string, name: string) => {
    try {
      await llmPromptService.activatePrompt(id);
      message.success(`Prompt "${name}" 已激活`);
      refreshPromptsAndStatistics();
    } catch (error) {
      logger.error(`激活 Prompt 失败: ${id}`, error);
      message.error('激活失败');
    }
  };

  // 查看版本历史
  const handleViewVersions = async (prompt: PromptTemplate) => {
    try {
      const versions = await llmPromptService.getPromptVersions(prompt.id);
      const versionColumns: ColumnsType<PromptVersion> = [
        {
          title: '版本',
          dataIndex: 'version',
          key: 'version',
          width: 120,
          render: (version: string) => (
            <Tag className={`${styles.semanticTag} ${styles.versionTag} ${styles.tonePrimary}`}>
              {normalizeVersion(version)}
            </Tag>
          ),
        },
        {
          title: '变更说明',
          dataIndex: 'change_description',
          key: 'change_description',
          render: (description?: string) => description ?? '-',
        },
        {
          title: '创建时间',
          dataIndex: 'created_at',
          key: 'created_at',
          width: 180,
          render: (createdAt: string) => dayjs(createdAt).format('YYYY-MM-DD HH:mm'),
        },
        {
          title: '自动生成',
          dataIndex: 'auto_generated',
          key: 'auto_generated',
          width: 120,
          render: (autoGenerated?: boolean) => {
            const sourceMeta =
              autoGenerated === true ? VERSION_SOURCE_META.auto : VERSION_SOURCE_META.manual;
            return (
              <Tag
                className={`${styles.semanticTag} ${styles.sourceTag} ${getToneClassName(
                  sourceMeta.tone
                )}`}
              >
                {sourceMeta.label}
                <span className={styles.statusHint}>{sourceMeta.hint}</span>
              </Tag>
            );
          },
        },
      ];

      Modal.info({
        title: `版本历史 - ${prompt.name}`,
        width: 880,
        content: (
          <div className={styles.versionModalContent}>
            {versions.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="暂无版本记录"
                className={styles.versionEmpty}
              />
            ) : (
              <Table<PromptVersion>
                rowKey="id"
                className={styles.versionTable}
                columns={versionColumns}
                dataSource={versions}
                size="small"
                pagination={false}
                scroll={{ x: 720 }}
              />
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
    refreshPromptsAndStatistics();
  };

  // 表格列定义
  const columns: ColumnsType<PromptTemplate> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: PromptTemplate) => (
        <div className={styles.nameCell}>
          <span className={styles.nameText}>{text}</span>
          <span className={styles.versionText}>{normalizeVersion(record.version)}</span>
        </div>
      ),
    },
    {
      title: '文档类型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 120,
      render: (docType: DocType) => {
        const meta = DOC_TYPE_META_MAP[docType];
        return (
          <Tag className={`${styles.semanticTag} ${styles.typeTag} ${getToneClassName(meta.tone)}`}>
            {meta.label}
          </Tag>
        );
      },
    },
    {
      title: '提供商',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      render: (provider: LLMProvider) => {
        const meta = PROVIDER_META_MAP[provider];
        return (
          <Tag
            className={`${styles.semanticTag} ${styles.providerTag} ${getToneClassName(meta.tone)}`}
          >
            {meta.label}
          </Tag>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: PromptStatus) => {
        const meta = STATUS_META_MAP[status];
        return (
          <Tag
            icon={meta.icon}
            className={`${styles.semanticTag} ${styles.statusTag} ${getToneClassName(meta.tone)}`}
          >
            {meta.label}
            <span className={styles.statusHint}>{meta.hint}</span>
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
        <span className={`${styles.metricText} ${getToneClassName(getAccuracyTone(value))}`}>
          {(value * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      title: '平均置信度',
      dataIndex: 'avg_confidence',
      key: 'avg_confidence',
      width: 120,
      render: (value: number) => (
        <span className={`${styles.metricText} ${getToneClassName(getConfidenceTone(value))}`}>
          {(value * 100).toFixed(1)}%
        </span>
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
        <Space size={4} className={styles.actionGroup}>
          {record.status !== PromptStatus.ACTIVE && (
            <Tooltip title="激活">
              <Button
                type="text"
                icon={<RocketOutlined />}
                onClick={() => handleActivate(record.id, record.name)}
                aria-label="激活"
                className={styles.tableActionButton}
              />
            </Tooltip>
          )}
          <Tooltip title="版本历史">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => handleViewVersions(record)}
              aria-label="版本历史"
              className={styles.tableActionButton}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              aria-label="编辑"
              className={styles.tableActionButton}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleDocTypeChange = useCallback(
    (value?: DocType) => {
      updateFilters({ doc_type: value });
    },
    [updateFilters]
  );

  const handleProviderChange = useCallback(
    (value?: LLMProvider) => {
      updateFilters({ provider: value });
    },
    [updateFilters]
  );

  const handleStatusChange = useCallback(
    (value?: PromptStatus) => {
      updateFilters({ status: value });
    },
    [updateFilters]
  );

  return (
    <PageContainer
      className={styles.pageShell}
      title="LLM Prompt 管理"
      subTitle="统一管理模板版本、状态与性能指标"
    >
      {/* 统计卡片 */}
      {statistics != null && (
        <Row gutter={[16, 16]} className={styles.summaryRow}>
          <Col xs={24} sm={12} xl={6}>
            <Card className={`${styles.summaryCard} ${styles.statsCard}`}>
              <Statistic
                title="总 Prompt 数"
                value={statistics.total_prompts}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card className={`${styles.summaryCard} ${styles.statsCard} ${styles.toneSuccess}`}>
              <Statistic
                title="活跃 Prompt"
                value={activePromptCount}
                prefix={<CheckCircleOutlined />}
                suffix={<span className={styles.totalSuffix}>/ {statistics.total_prompts}</span>}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.summaryCard} ${styles.statsCard} ${getToneClassName(
                statistics.overall_avg_accuracy >= 0.85 ? 'success' : 'warning'
              )}`}
            >
              <Statistic
                title="平均准确率"
                value={(statistics.overall_avg_accuracy * 100).toFixed(1)}
                suffix="%"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.summaryCard} ${styles.statsCard} ${getToneClassName(
                statistics.overall_avg_confidence >= 0.8 ? 'success' : 'warning'
              )}`}
            >
              <Statistic
                title="平均置信度"
                value={(statistics.overall_avg_confidence * 100).toFixed(1)}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主卡片 */}
      <Card
        title="Prompt 模板列表"
        extra={
          <Space size={8} className={styles.headerActions} wrap>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={isRefreshing}
              aria-label="刷新 Prompt 列表"
              className={styles.actionButton}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              aria-label="新建 Prompt 模板"
              className={styles.actionButton}
            >
              新建 Prompt
            </Button>
          </Space>
        }
      >
        {/* 筛选器 */}
        <div className={styles.filtersSection}>
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
                    className={styles.fullWidthControl}
                    value={filters.doc_type}
                    onChange={handleDocTypeChange}
                    aria-label="筛选文档类型"
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
                    className={styles.fullWidthControl}
                    value={filters.provider}
                    onChange={handleProviderChange}
                    aria-label="筛选提供商"
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
                    className={styles.fullWidthControl}
                    value={filters.status}
                    onChange={handleStatusChange}
                    aria-label="筛选 Prompt 状态"
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
        <div className={styles.filterSummary}>
          <span className={styles.summaryText}>总记录：{pagination.total}</span>
          <span className={styles.summaryText}>启用筛选：{enabledFilterCount}</span>
        </div>

        {/* 表格 */}
        <TableWithPagination
          columns={columns}
          dataSource={prompts}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={handlePageChange}
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
    </PageContainer>
  );
};

export default PromptListPage;
