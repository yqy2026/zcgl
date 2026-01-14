/**
 * 押金台账历史组件
 *
 * @description 展示合同的押金变动记录（收取、退还、抵扣、转移）
 * @module components/Rental
 */

import React from 'react';
import { Card, Table, Tag, Empty } from 'antd';
import { WalletOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { DepositLedger, DepositTransactionType } from '@/types/rentContract';

interface DepositLedgerHistoryProps {
    depositLedgers?: DepositLedger[];
    loading?: boolean;
}

/**
 * 交易类型映射
 */
const TRANSACTION_TYPE_MAP: Record<DepositTransactionType, { label: string; color: string }> = {
    receipt: { label: '收取押金', color: 'green' },
    refund: { label: '退还押金', color: 'blue' },
    deduction: { label: '抵扣欠款', color: 'orange' },
    transfer_out: { label: '转出（续签）', color: 'purple' },
    transfer_in: { label: '转入（续签）', color: 'cyan' },
};

/**
 * DepositLedgerHistory - 押金台账历史组件
 */
const DepositLedgerHistory: React.FC<DepositLedgerHistoryProps> = ({
    depositLedgers = [],
    loading = false,
}) => {
    // 表格列定义
    const columns: ColumnsType<DepositLedger> = [
        {
            title: '交易日期',
            dataIndex: 'transaction_date',
            key: 'transaction_date',
            width: 120,
            render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
        },
        {
            title: '交易类型',
            dataIndex: 'transaction_type',
            key: 'transaction_type',
            width: 120,
            render: (type: DepositTransactionType) => {
                const info = TRANSACTION_TYPE_MAP[type] ?? { label: type, color: 'default' };
                return <Tag color={info.color}>{info.label}</Tag>;
            },
        },
        {
            title: '金额',
            dataIndex: 'amount',
            key: 'amount',
            width: 120,
            align: 'right',
            render: (amount: number) => {
                // 后端已使用有符号金额（正=收入，负=支出）
                return (
                    <span style={{ color: amount >= 0 ? '#52c41a' : '#ff4d4f' }}>
                        {amount >= 0 ? '+' : ''}¥{Math.abs(amount).toLocaleString()}
                    </span>
                );
            },
        },
        {
            title: '操作人',
            dataIndex: 'operator',
            key: 'operator',
            width: 100,
            render: (op: string) => op || '-',
        },
        {
            title: '备注',
            dataIndex: 'notes',
            key: 'notes',
            ellipsis: true,
            render: (notes: string) => notes || '-',
        },
    ];

    return (
        <Card
            title={
                <span>
                    <WalletOutlined style={{ marginRight: 8 }} />
                    押金变动记录 ({depositLedgers.length})
                </span>
            }
            style={{ marginBottom: 16 }}
        >
            {depositLedgers.length > 0 ? (
                <Table
                    dataSource={depositLedgers}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                    pagination={false}
                    size="small"
                    bordered
                />
            ) : (
                <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无押金变动记录"
                />
            )}
        </Card>
    );
};

export default DepositLedgerHistory;
