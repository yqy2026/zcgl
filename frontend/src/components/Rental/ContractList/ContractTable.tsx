import React from 'react';
import { Button, Space, Tag, Tooltip, Card } from 'antd';
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
import {
  RentContract,
  ContractStatus,
  ContractStatusLabels,
  ContractStatusColors,
} from '@/types/rentContract';
import { TableWithPagination } from '@/components/Common/TableWithPagination';

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

  const columns: ColumnsType<RentContract> = [
    {
      title: '合同编号',
      dataIndex: 'contract_number',
      key: 'contract_number',
      render: (text: string) => (
        <Tooltip title={text}>
          <Button type="link" size="small">
            {text}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: '承租方',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
      render: (text: string) => (
        <Space>
          <span>{text}</span>
        </Space>
      ),
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
            <Tag>{assetList.length}个资产</Tag>
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
      render: (record: RentContract) => (
        <Space orientation="vertical" size="small">
          <div>{dayjs(record.start_date).format('YYYY-MM-DD')}</div>
          <div>至</div>
          <div>{dayjs(record.end_date).format('YYYY-MM-DD')}</div>
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
        return (
          <Tag color={ContractStatusColors[status] || 'default'}>
            {ContractStatusLabels[status] || status}
          </Tag>
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
        <Space size="small">
          <Tooltip title="查看详情">
            <Button type="text" icon={<EyeOutlined />} onClick={() => onView(record)} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => onEdit(record)} />
          </Tooltip>
          <Tooltip title="生成台账">
            <Button
              type="text"
              icon={<FileTextOutlined />}
              onClick={() => onGenerateLedger(record.id)}
            />
          </Tooltip>
          {record.contract_status === ContractStatus.ACTIVE && (
            <>
              <Tooltip title="续签">
                <Button type="text" icon={<SyncOutlined />} onClick={() => onRenew(record)} />
              </Tooltip>
              <Tooltip title="终止">
                <Button
                  type="text"
                  danger
                  icon={<StopOutlined />}
                  onClick={() => onTerminate(record)}
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
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <Card>
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
