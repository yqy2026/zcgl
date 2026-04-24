import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Form, Input, Modal, Select, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import PageContainer from '@/components/Common/PageContainer';
import { SYSTEM_ROUTES } from '@/constants/routes';
import {
  partyService,
  type PartyImportPayload,
  type PartyCreatePayload,
  type PartyListResult,
} from '@/services/partyService';
import type { Party, PartyReviewStatus, PartyType } from '@/types/party';
import { MessageManager } from '@/utils/messageManager';
import { parsePartyImportWorkbook } from './partyImport';

interface PartyFilters {
  search: string;
  partyType: PartyType | 'all';
  status: string | 'all';
  reviewStatus: PartyReviewStatus | 'all';
}

const PARTY_TYPE_OPTIONS: Array<{ label: string; value: PartyType }> = [
  { label: '组织', value: 'organization' },
  { label: '法人主体', value: 'legal_entity' },
  { label: '自然人', value: 'individual' },
];

const REVIEW_STATUS_OPTIONS: Array<{ label: string; value: PartyReviewStatus | 'all' }> = [
  { label: '全部审核状态', value: 'all' },
  { label: '草稿', value: 'draft' },
  { label: '待审核', value: 'pending' },
  { label: '已审核', value: 'approved' },
  { label: '已反审核', value: 'reversed' },
];

const PARTY_TYPE_LABELS: Record<PartyType, string> = {
  organization: '组织',
  legal_entity: '法人主体',
  individual: '自然人',
};

const REVIEW_STATUS_META: Record<PartyReviewStatus, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  pending: { color: 'processing', label: '待审核' },
  approved: { color: 'success', label: '已审核' },
  reversed: { color: 'warning', label: '已反审核' },
};

const renderReviewStatus = (
  reviewStatus: PartyReviewStatus | null | undefined
): React.ReactNode => {
  const resolvedStatus = reviewStatus ?? 'draft';
  const meta = REVIEW_STATUS_META[resolvedStatus];
  return <Tag color={meta.color}>{meta.label}</Tag>;
};

const PartyListPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [createForm] = Form.useForm<PartyCreatePayload>();
  const [filters, setFilters] = useState<PartyFilters>({
    search: '',
    partyType: 'all',
    status: 'all',
    reviewStatus: 'all',
  });
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importPreviewCount, setImportPreviewCount] = useState(0);
  const [importPayload, setImportPayload] = useState<PartyImportPayload | null>(null);

  const queryFilters = useMemo(
    () => ({
      search: filters.search.trim() !== '' ? filters.search.trim() : undefined,
      party_type: filters.partyType !== 'all' ? filters.partyType : undefined,
      status: filters.status !== 'all' ? filters.status : undefined,
      limit: 200,
    }),
    [filters.partyType, filters.search, filters.status]
  );

  const partyListQuery = useQuery<PartyListResult>({
    queryKey: [
      'system-party-list',
      queryFilters.search ?? '',
      queryFilters.party_type ?? '',
      queryFilters.status ?? '',
    ],
    queryFn: async () => {
      return await partyService.getParties(queryFilters);
    },
    staleTime: 60 * 1000,
  });

  const createPartyMutation = useMutation({
    mutationFn: async (payload: PartyCreatePayload) => {
      return await partyService.createParty(payload);
    },
    onSuccess: async party => {
      MessageManager.success(`主体 ${party.name} 已创建`);
      setCreateModalOpen(false);
      createForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['system-party-list'] });
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '创建主体失败');
    },
  });

  const importPartyMutation = useMutation({
    mutationFn: async (payload: PartyImportPayload) => {
      return await partyService.importParties(payload);
    },
    onSuccess: async result => {
      MessageManager.success(`主体导入完成：成功 ${result.created_count} 条`);
      setImportModalOpen(false);
      setImportFile(null);
      setImportPreviewCount(0);
      setImportPayload(null);
      await queryClient.invalidateQueries({ queryKey: ['system-party-list'] });
    },
    onError: error => {
      MessageManager.error(error instanceof Error ? error.message : '主体导入失败');
    },
  });

  const parties = useMemo(() => {
    const sourceItems = partyListQuery.data?.items ?? [];
    if (filters.reviewStatus === 'all') {
      return sourceItems;
    }
    return sourceItems.filter(party => (party.review_status ?? 'draft') === filters.reviewStatus);
  }, [filters.reviewStatus, partyListQuery.data?.items]);

  const columns = useMemo<ColumnsType<Party>>(
    () => [
      {
        title: '主体名称',
        dataIndex: 'name',
        key: 'name',
      },
      {
        title: '主体编码',
        dataIndex: 'code',
        key: 'code',
      },
      {
        title: '主体类型',
        dataIndex: 'party_type',
        key: 'party_type',
        render: (value: PartyType) => PARTY_TYPE_LABELS[value],
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (value: string) => (
          <Tag color={value === 'active' ? 'success' : 'default'}>{value}</Tag>
        ),
      },
      {
        title: '审核状态',
        dataIndex: 'review_status',
        key: 'review_status',
        render: (value: PartyReviewStatus | null | undefined) => renderReviewStatus(value),
      },
      {
        title: '操作',
        key: 'actions',
        render: (_, record) => (
          <Button
            type="link"
            aria-label={`查看主体${record.name}详情`}
            onClick={() => {
              navigate(SYSTEM_ROUTES.PARTY_DETAIL(record.id));
            }}
          >
            查看详情
          </Button>
        ),
      },
    ],
    [navigate]
  );

  const handleCreateSubmit = async (): Promise<void> => {
    const values = await createForm.validateFields();
    createPartyMutation.mutate(values);
  };

  const handleImportFile = async (file: File): Promise<void> => {
    const items = await parsePartyImportWorkbook(file);
    setImportFile(file);
    setImportPreviewCount(items.length);
    setImportPayload({ items });
  };

  return (
    <PageContainer title="主体主档管理" subTitle="维护主体台账、审核状态与基础信息主档">
      <Space orientation="vertical" size="large" style={{ width: '100%' }}>
        <Space wrap>
          <Input.Search
            allowClear
            placeholder="按主体名称或编码搜索"
            value={filters.search}
            onChange={event => {
              setFilters(currentFilters => ({
                ...currentFilters,
                search: event.target.value,
              }));
            }}
            onSearch={value => {
              setFilters(currentFilters => ({
                ...currentFilters,
                search: value,
              }));
            }}
            style={{ width: 280 }}
          />
          <Select
            value={filters.partyType}
            style={{ width: 160 }}
            options={[{ label: '全部主体类型', value: 'all' }, ...PARTY_TYPE_OPTIONS]}
            onChange={value => {
              setFilters(currentFilters => ({
                ...currentFilters,
                partyType: value,
              }));
            }}
          />
          <Select
            value={filters.status}
            style={{ width: 140 }}
            options={[
              { label: '全部状态', value: 'all' },
              { label: 'active', value: 'active' },
              { label: 'inactive', value: 'inactive' },
            ]}
            onChange={value => {
              setFilters(currentFilters => ({
                ...currentFilters,
                status: value,
              }));
            }}
          />
          <Select
            value={filters.reviewStatus}
            style={{ width: 160 }}
            options={REVIEW_STATUS_OPTIONS}
            onChange={value => {
              setFilters(currentFilters => ({
                ...currentFilters,
                reviewStatus: value,
              }));
            }}
          />
          <Button
            onClick={() => {
              void partyListQuery.refetch();
            }}
          >
            刷新列表
          </Button>
          <Button
            type="primary"
            onClick={() => {
              setCreateModalOpen(true);
            }}
          >
            新建主体
          </Button>
          <Button
            onClick={() => {
              setImportModalOpen(true);
            }}
          >
            批量导入
          </Button>
        </Space>

        <Typography.Text type="secondary">
          共 {parties.length} 条主体记录
          {partyListQuery.data?.total != null ? ` / 后端总数 ${partyListQuery.data.total}` : ''}
        </Typography.Text>

        <Table<Party>
          rowKey="id"
          loading={partyListQuery.isLoading || partyListQuery.isFetching}
          columns={columns}
          dataSource={parties}
          pagination={false}
          locale={{
            emptyText: partyListQuery.isError ? '主体列表加载失败' : '暂无主体数据',
          }}
        />
      </Space>

      <Modal
        title="新建主体"
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        onOk={() => {
          void handleCreateSubmit();
        }}
        okText="保存主体"
        cancelText="取消"
        confirmLoading={createPartyMutation.isPending}
        destroyOnHidden
      >
        <Form<PartyCreatePayload>
          form={createForm}
          layout="vertical"
          initialValues={{
            party_type: 'organization',
            status: 'active',
          }}
        >
          <Form.Item
            label="主体名称"
            name="name"
            rules={[{ required: true, message: '请输入主体名称' }]}
          >
            <Input aria-label="主体名称" />
          </Form.Item>
          <Form.Item
            label="主体编码"
            name="code"
            rules={[{ required: true, message: '请输入主体编码' }]}
          >
            <Input aria-label="主体编码" />
          </Form.Item>
          <Form.Item
            label="主体类型"
            name="party_type"
            rules={[{ required: true, message: '请选择主体类型' }]}
          >
            <Select aria-label="主体类型" options={PARTY_TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              aria-label="状态"
              options={[
                { label: 'active', value: 'active' },
                { label: 'inactive', value: 'inactive' },
              ]}
            />
          </Form.Item>
          <Form.Item label="外部引用" name="external_ref">
            <Input aria-label="外部引用" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="主体批量导入"
        open={importModalOpen}
        onCancel={() => {
          setImportModalOpen(false);
          setImportFile(null);
          setImportPreviewCount(0);
          setImportPayload(null);
        }}
        onOk={() => {
          if (importPayload != null) {
            importPartyMutation.mutate(importPayload);
          }
        }}
        okText="开始导入"
        cancelText="取消"
        okButtonProps={{ disabled: importPayload == null }}
        confirmLoading={importPartyMutation.isPending}
        destroyOnHidden
      >
        <input
          aria-label="主体导入文件"
          type="file"
          accept=".xlsx,.xls"
          onChange={event => {
            const nextFile = event.target.files?.[0];
            if (nextFile != null) {
              void handleImportFile(nextFile);
            }
          }}
        />
        <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
          {importFile != null
            ? `已选择文件：${importFile.name}`
            : '支持 .xlsx / .xls，读取首个工作表'}
          {importPreviewCount > 0 ? `，已识别 ${importPreviewCount} 条主体数据` : ''}
        </Typography.Paragraph>
      </Modal>
    </PageContainer>
  );
};

export default PartyListPage;
