import React from 'react';
import { Badge, Button, Input, Popconfirm, Space, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DeleteOutlined, EditOutlined, EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';

import type { EnumFieldType } from '@/services/dictionary';
import EnumValuePreview from '@/components/Dictionary/EnumValuePreview';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import styles from './EnumFieldPage.module.css';

const { Search } = Input;

interface EnumFieldListProps {
  enumTypes: EnumFieldType[];
  loading: boolean;
  pagination: PaginationState;
  keyword: string;
  onKeywordChange: (keyword: string) => void;
  onCreateType: () => void;
  onPageChange: (pagination: { current?: number; pageSize?: number }) => void;
  onViewValues: (typeId: string) => void;
  onEditType: (type: EnumFieldType) => void;
  onDeleteType: (id: string) => void;
}

type Tone = 'success' | 'warning';

const resolveText = (value: string | null | undefined, fallback: string): string => {
  if (value == null) {
    return fallback;
  }
  const normalizedValue = value.trim();
  return normalizedValue !== '' ? normalizedValue : fallback;
};

const getTypeStatusTone = (status: EnumFieldType['status']): Tone =>
  status === 'active' ? 'success' : 'warning';

const EnumFieldList: React.FC<EnumFieldListProps> = ({
  enumTypes,
  loading,
  pagination,
  keyword,
  onKeywordChange,
  onCreateType,
  onPageChange,
  onViewValues,
  onEditType,
  onDeleteType,
}) => {
  const toneClassMap: Record<Tone, string> = {
    success: styles.toneSuccess,
    warning: styles.toneWarning,
  };

  const columns: ColumnsType<EnumFieldType> = [
    {
      title: '类型名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space className={styles.typeNameCell}>
          <span className={styles.typeNameText}>{text}</span>
          {record.is_system && (
            <Tag className={[styles.statusTag, styles.tonePrimary].join(' ')}>系统</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      render: text => <code className={styles.codeValue}>{text}</code>,
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      render: text => resolveText(text, '-'),
    },
    {
      title: '配置',
      key: 'config',
      render: (_, record) => (
        <Space className={styles.configTagGroup}>
          {record.is_multiple && (
            <Tag className={[styles.statusTag, styles.toneSuccess].join(' ')}>多选</Tag>
          )}
          {record.is_hierarchical && (
            <Tag className={[styles.statusTag, styles.toneWarning].join(' ')}>层级</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: status => {
        const tone = getTypeStatusTone(status);
        return (
          <Space size={6} className={styles.statusGroup}>
            <Badge status={status === 'active' ? 'success' : 'default'} />
            <span className={[styles.statusText, toneClassMap[tone]].join(' ')}>
              {status === 'active' ? '启用' : '禁用'}
            </span>
          </Space>
        );
      },
    },
    {
      title: '枚举值预览',
      key: 'enum_values_preview',
      render: (_, record) => (
        <EnumValuePreview
          values={record.enum_values ?? []}
          maxDisplay={5}
          size="small"
          showInactiveCount={false}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space className={styles.actionGroup}>
          <Tooltip title="查看枚举值">
            <Button
              type="text"
              icon={<EyeOutlined />}
              className={styles.tableActionButton}
              onClick={() => onViewValues(record.id)}
              aria-label={`查看类型 ${record.name} 的枚举值`}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              className={styles.tableActionButton}
              onClick={() => onEditType(record)}
              aria-label={`编辑类型 ${record.name}`}
            />
          </Tooltip>
          {!record.is_system && (
            <Popconfirm title="确定删除此枚举类型吗？" onConfirm={() => onDeleteType(record.id)}>
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                className={styles.tableActionButton}
                aria-label={`删除类型 ${record.name}`}
              />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className={styles.toolbarSection}>
        <Space className={styles.typeToolbar} size={12} wrap>
          <Search
            placeholder="搜索类型名称、编码或类别"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={event => onKeywordChange(event.target.value)}
            allowClear
            className={styles.typeSearch}
          />
          <div className={styles.typeSummaryText}>共 {pagination.total} 个类型</div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            className={styles.actionButton}
            onClick={onCreateType}
          >
            新建枚举类型
          </Button>
        </Space>
      </div>
      <TableWithPagination
        columns={columns}
        dataSource={enumTypes}
        rowKey="id"
        loading={loading}
        paginationState={pagination}
        onPageChange={onPageChange}
        paginationProps={{
          showTotal: (total: number) => `共 ${total} 条记录`,
        }}
      />
    </>
  );
};

export default EnumFieldList;
