import React from 'react';
import { Button, Space, Tag, Tooltip, Card, Typography } from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  FileTextOutlined,
  SyncOutlined,
  StopOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useFormat } from '@/utils/format';
import { RentContract, ContractStatus, ContractStatusLabels } from '@/types/rentContract';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import styles from './ContractTable.module.css';

interface ContractTableProps {
  loading: boolean;
  contracts: RentContract[];
  pagination: {
    current: number;
    pageSize: number;
    total: number;
  };
  onTableChange: (pagination: { current?: number; pageSize?: number }) => void;
  onView: (contract: RentContract) => void;
  onEdit: (contract: RentContract) => void;
  onGenerateLedger: (id: string) => void;
  onRenew: (contract: RentContract) => void;
  onTerminate: (contract: RentContract) => void;
  onDelete: (id: string) => void;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const STATUS_TONE_MAP: Record<ContractStatus, Tone> = {
  [ContractStatus.DRAFT]: 'primary',
  [ContractStatus.PENDING]: 'warning',
  [ContractStatus.ACTIVE]: 'success',
  [ContractStatus.EXPIRING]: 'warning',
  [ContractStatus.EXPIRED]: 'error',
  [ContractStatus.TERMINATED]: 'error',
  [ContractStatus.RENEWED]: 'primary',
};

const STATUS_ASSIST_TEXT_MAP: Record<ContractStatus, string> = {
  [ContractStatus.DRAFT]: '待完善',
  [ContractStatus.PENDING]: '待审核',
  [ContractStatus.ACTIVE]: '履约中',
  [ContractStatus.EXPIRING]: '需续签',
  [ContractStatus.EXPIRED]: '已结束',
  [ContractStatus.TERMINATED]: '已结束',
  [ContractStatus.RENEWED]: '已续约',
};

const ContractTable: React.FC<ContractTableProps> = ({
  loading,
  contracts,
  pagination,
  onTableChange,
  onView,
  onEdit,
  onGenerateLedger,
  onRenew,
  onTerminate,
  onDelete,
}) => {
  const format = useFormat();
  const { Text } = Typography;
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  const columns: ColumnsType<RentContract> = [
    {
      title: '合同编号',
      dataIndex: 'contract_number',
      key: 'contract_number',
      render: (text: string, record: RentContract) => (
        <Tooltip title={text}>
          <Button
            type="link"
            size="small"
            onClick={() => onView(record)}
            className={styles.contractNumberButton}
          >
            {text}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: '承租方',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
      render: (text: string) => <span>{text}</span>,
    },
    {
      title: '物业名称',
      key: 'assets',
      render: (_: unknown, record: RentContract) => {
        const assetList = record.assets ?? [];
        if (assetList.length === 0) return '未关联';
        if (assetList.length === 1) {
          return <Tooltip title={assetList[0].address ?? ''}>{assetList[0].property_name}</Tooltip>;
        }
        return (
          <Tooltip title={assetList.map(a => a.property_name).join(', ')}>
            <Tag className={styles.assetCountTag}>{assetList.length}个资产</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '权属方',
      dataIndex: ['ownership', 'name'],
      key: 'ownership_name',
      render: (text: string | undefined) => text ?? '未知',
    },
    {
      title: '租期',
      key: 'lease_period',
      render: (_: unknown, record: RentContract) => (
        <Space orientation="vertical" size={2} className={styles.leasePeriod}>
          <span>{dayjs(record.start_date).format('YYYY-MM-DD')}</span>
          <span className={styles.leaseSeparator}>至</span>
          <span>{dayjs(record.end_date).format('YYYY-MM-DD')}</span>
        </Space>
      ),
    },
    {
      title: '月租金',
      dataIndex: 'monthly_rent_base',
      key: 'monthly_rent_base',
      render: (amount: number) => format.currency(amount),
      align: 'right',
    },
    {
      title: '合同状态',
      dataIndex: 'contract_status',
      key: 'contract_status',
      render: (status: ContractStatus) => {
        const tone = STATUS_TONE_MAP[status] ?? 'primary';
        return (
          <Space size={6} className={styles.inlineStatus} wrap>
            <Tag className={[styles.statusTag, toneClassMap[tone]].join(' ')}>
              {ContractStatusLabels[status] ?? status}
            </Tag>
            <Text type="secondary" className={styles.statusAssistText}>
              {STATUS_ASSIST_TEXT_MAP[status] ?? '状态跟进'}
            </Text>
          </Space>
        );
      },
    },
    {
      title: '签订日期',
      dataIndex: 'sign_date',
      key: 'sign_date',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_: unknown, record: RentContract) => (
        <Space size={6} className={styles.actionGroup} wrap>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => onView(record)}
              className={styles.actionButton}
              aria-label={`查看合同 ${record.contract_number}`}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
              className={styles.actionButton}
              aria-label={`编辑合同 ${record.contract_number}`}
            />
          </Tooltip>
          <Tooltip title="生成台账">
            <Button
              type="text"
              icon={<FileTextOutlined />}
              onClick={() => onGenerateLedger(record.id)}
              className={styles.actionButton}
              aria-label={`生成台账 ${record.contract_number}`}
            />
          </Tooltip>
          {record.contract_status === ContractStatus.ACTIVE && (
            <>
              <Tooltip title="续签">
                <Button
                  type="text"
                  icon={<SyncOutlined />}
                  onClick={() => onRenew(record)}
                  className={styles.actionButton}
                  aria-label={`续签合同 ${record.contract_number}`}
                />
              </Tooltip>
              <Tooltip title="终止">
                <Button
                  type="text"
                  danger
                  icon={<StopOutlined />}
                  onClick={() => onTerminate(record)}
                  className={styles.actionButton}
                  aria-label={`终止合同 ${record.contract_number}`}
                />
              </Tooltip>
            </>
          )}
          <Tooltip title="删除">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record.id)}
              className={styles.actionButton}
              aria-label={`删除合同 ${record.contract_number}`}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <Card className={styles.tableCard}>
      <TableWithPagination
        columns={columns}
        dataSource={contracts}
        rowKey="id"
        loading={loading}
        paginationState={pagination}
        onPageChange={onTableChange}
        paginationProps={{
          showTotal: (total: number, range: [number, number]) =>
            `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        }}
        scroll={{ x: 1200 }}
      />
    </Card>
  );
};

export default ContractTable;
