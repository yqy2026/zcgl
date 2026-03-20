import React from 'react';
import { Badge, Button, Popconfirm, Select, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';

import type { EnumFieldType, EnumFieldValue } from '@/services/dictionary';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import styles from './EnumFieldPage.module.css';

const { Option } = Select;

interface EnumFieldValueManagerProps {
  enumTypes: EnumFieldType[];
  enumValues: EnumFieldValue[];
  selectedTypeId: string | null;
  loading: boolean;
  pagination: PaginationState;
  onSelectType: (value?: string) => void;
  onCreateValue: () => void;
  onPageChange: (pagination: { current?: number; pageSize?: number }) => void;
  onEditValue: (value: EnumFieldValue) => void;
  onDeleteValue: (id: string) => void;
}

const buildColorPreviewStyle = (color: string): React.CSSProperties =>
  ({ ['--preview-color' as string]: color }) as React.CSSProperties;

const EnumFieldValueManager: React.FC<EnumFieldValueManagerProps> = ({
  enumTypes,
  enumValues,
  selectedTypeId,
  loading,
  pagination,
  onSelectType,
  onCreateValue,
  onPageChange,
  onEditValue,
  onDeleteValue,
}) => {
  const columns: ColumnsType<EnumFieldValue> = [
    {
      title: '标签',
      dataIndex: 'label',
      key: 'label',
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
      render: text => <code className={styles.codeValue}>{text}</code>,
    },
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      render: text => (text != null ? <code className={styles.codeValue}>{text}</code> : '-'),
    },
    {
      title: '颜色',
      dataIndex: 'color',
      key: 'color',
      render: color =>
        color != null ? (
          <Space className={styles.colorCell}>
            <span className={styles.colorPreview} style={buildColorPreviewStyle(color)} />
            <span className={styles.colorValue}>{color}</span>
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => (
        <Space className={styles.configTagGroup}>
          <Space size={6} className={styles.statusGroup}>
            <Badge status={record.is_active ? 'success' : 'default'} />
            <span className={record.is_active ? styles.toneSuccess : styles.toneWarning}>
              {record.is_active ? '启用' : '禁用'}
            </span>
          </Space>
          {record.is_default === true && (
            <Tag className={[styles.statusTag, styles.toneWarning].join(' ')}>默认</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space className={styles.actionGroup}>
          <Button
            type="text"
            icon={<EditOutlined />}
            className={styles.tableActionButton}
            onClick={() => onEditValue(record)}
            aria-label={`编辑枚举值 ${record.label}`}
          />
          <Popconfirm title="确定删除此枚举值吗？" onConfirm={() => onDeleteValue(record.id)}>
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              className={styles.tableActionButton}
              aria-label={`删除枚举值 ${record.label}`}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className={styles.toolbarSection}>
        <Space className={styles.valueToolbar} wrap>
          <Select
            placeholder="选择枚举类型"
            className={styles.typeSelect}
            value={selectedTypeId ?? undefined}
            onChange={onSelectType}
            allowClear
          >
            {enumTypes.map(type => (
              <Option key={type.id} value={type.id}>
                {type.name}
              </Option>
            ))}
          </Select>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            className={styles.actionButton}
            onClick={onCreateValue}
            disabled={selectedTypeId == null}
          >
            新建枚举值
          </Button>
        </Space>
      </div>
      <TableWithPagination
        columns={columns}
        dataSource={enumValues}
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

export default EnumFieldValueManager;
