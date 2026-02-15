import React, { useMemo } from 'react';
import { Button, Space, Tooltip } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { TableWithPagination, type PaginationState } from '@/components/Common/TableWithPagination';
import type { OperationLog } from '@/services/systemService';
import type { Tone } from '../types';
import {
  OperationActionTag,
  OperationModuleTag,
  OperationResponseTimeText,
  OperationStatusTag,
} from './OperationLogTags';
import styles from '../../OperationLogPage.module.css';

interface OperationLogTableProps {
  logs: OperationLog[];
  loading: boolean;
  paginationState: PaginationState;
  resolveToneClassName: (tone: Tone) => string;
  onPageChange: (next: { current?: number; pageSize?: number }) => void;
  onViewDetail: (log: OperationLog) => void;
}

const OperationLogTable: React.FC<OperationLogTableProps> = ({
  logs,
  loading,
  paginationState,
  resolveToneClassName,
  onPageChange,
  onViewDetail,
}) => {
  const columns = useMemo<ColumnsType<OperationLog>>(
    () => [
      {
        title: '操作时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 180,
        render: date => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
      },
      {
        title: '用户信息',
        key: 'user_info',
        width: 150,
        render: (_, record) => {
          const accountName =
            record.username != null && record.username.trim() !== '' ? record.username : '-';
          const displayName =
            record.user_name != null && record.user_name.trim() !== ''
              ? record.user_name
              : accountName;
          return (
            <Space orientation="vertical" size={2} className={styles.userCell}>
              <div className={styles.primaryText}>{displayName}</div>
              <div className={styles.secondaryText}>
                {accountName === '-' ? '-' : `账号 @${accountName}`}
              </div>
            </Space>
          );
        },
      },
      {
        title: '操作',
        dataIndex: 'action',
        key: 'action',
        width: 100,
        render: action => (
          <OperationActionTag
            action={typeof action === 'string' ? action : ''}
            resolveToneClassName={resolveToneClassName}
          />
        ),
      },
      {
        title: '模块',
        key: 'module',
        width: 120,
        render: (_, record) => (
          <OperationModuleTag
            module={record.module}
            moduleName={record.module_name}
            resolveToneClassName={resolveToneClassName}
          />
        ),
      },
      {
        title: '资源',
        key: 'resource',
        width: 150,
        render: (_, record) => (
          <div className={styles.resourceCell}>
            <div className={styles.primaryText}>{record.resource_name ?? '-'}</div>
            <div className={styles.secondaryText}>
              {record.resource_type != null && record.resource_type.trim() !== ''
                ? record.resource_type
                : '-'}
            </div>
          </div>
        ),
      },
      {
        title: 'IP地址',
        dataIndex: 'ip_address',
        key: 'ip_address',
        width: 120,
        render: ip => {
          const ipAddress = typeof ip === 'string' && ip.trim() !== '' ? ip : '-';
          return (
            <Tooltip title={ipAddress}>
              <span className={styles.ipValue}>{ipAddress}</span>
            </Tooltip>
          );
        },
      },
      {
        title: '响应状态',
        dataIndex: 'response_status',
        key: 'response_status',
        width: 132,
        render: status => (
          <OperationStatusTag
            status={typeof status === 'number' ? status : null}
            resolveToneClassName={resolveToneClassName}
          />
        ),
      },
      {
        title: '响应时间',
        dataIndex: 'response_time',
        key: 'response_time',
        width: 112,
        render: time => (
          <OperationResponseTimeText
            time={typeof time === 'number' ? time : null}
            resolveToneClassName={resolveToneClassName}
          />
        ),
      },
      {
        title: '操作',
        key: 'actions',
        fixed: 'right',
        width: 88,
        render: (_, record) => (
          <Tooltip title="查看详情">
            <Button
              type="text"
              className={styles.rowActionButton}
              icon={<EyeOutlined />}
              onClick={() => onViewDetail(record)}
              aria-label={`查看操作日志 ${record.id} 详情`}
            />
          </Tooltip>
        ),
      },
    ],
    [onViewDetail, resolveToneClassName]
  );

  return (
    <TableWithPagination
      columns={columns}
      dataSource={logs}
      rowKey="id"
      loading={loading}
      paginationState={paginationState}
      onPageChange={onPageChange}
      paginationProps={{
        showTotal: (total: number, range: [number, number]) =>
          `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
      }}
      scroll={{ x: 1200 }}
    />
  );
};

export default OperationLogTable;
