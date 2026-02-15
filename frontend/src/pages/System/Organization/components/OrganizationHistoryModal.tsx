import React, { useMemo } from 'react';
import { Modal, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import type { OrganizationHistory } from '@/types/organization';
import { historyActionMetaMap } from '../constants';
import { resolveHistoryActionMeta } from '../utils';
import type { Tone } from '../types';
import styles from '../../OrganizationPage.module.css';

interface HistoryPaginationState {
  current: number;
  pageSize: number;
  total: number;
  pages?: number;
}

interface OrganizationHistoryModalProps {
  open: boolean;
  selectedOrganizationName?: string;
  historyItems: OrganizationHistory[];
  paginationState: HistoryPaginationState;
  getToneClassName: (tone: Tone) => string;
  onClose: () => void;
  onPageChange: (next: { current?: number; pageSize?: number }) => void;
}

const OrganizationHistoryModal: React.FC<OrganizationHistoryModalProps> = ({
  open,
  selectedOrganizationName,
  historyItems,
  paginationState,
  getToneClassName,
  onClose,
  onPageChange,
}) => {
  const columns = useMemo<ColumnsType<OrganizationHistory>>(
    () => [
      {
        title: '操作类型',
        dataIndex: 'action',
        key: 'action',
        render: action => {
          const config = resolveHistoryActionMeta(action ?? '', historyActionMetaMap);
          return (
            <Tag
              className={`${styles.statusTag} ${styles.historyActionTag} ${getToneClassName(config.tone)}`}
            >
              {config.label}
            </Tag>
          );
        },
      },
      {
        title: '字段名称',
        dataIndex: 'field_name',
        key: 'field_name',
        render: field => field ?? '-',
      },
      {
        title: '原值',
        dataIndex: 'old_value',
        key: 'old_value',
        render: value => value ?? '-',
      },
      {
        title: '新值',
        dataIndex: 'new_value',
        key: 'new_value',
        render: value => value ?? '-',
      },
      {
        title: '操作人',
        dataIndex: 'created_by',
        key: 'created_by',
        render: user => user ?? '系统',
      },
      {
        title: '操作时间',
        dataIndex: 'created_at',
        key: 'created_at',
        render: date => new Date(date).toLocaleString(),
      },
    ],
    [getToneClassName]
  );

  return (
    <Modal
      title={`组织历史记录 - ${selectedOrganizationName ?? ''}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={1000}
    >
      <TableWithPagination
        columns={columns}
        dataSource={historyItems}
        rowKey="id"
        paginationState={paginationState}
        onPageChange={onPageChange}
        paginationProps={{
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条记录`,
        }}
      />
    </Modal>
  );
};

export default OrganizationHistoryModal;
