import React from 'react';
import { Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ServiceFeeLedger } from '@/types/rentContract';
import dayjs from 'dayjs';

const { Text } = Typography;

interface ServiceFeeLedgerTableProps {
    ledgers: ServiceFeeLedger[];
    loading?: boolean;
}

const ServiceFeeLedgerTable: React.FC<ServiceFeeLedgerTableProps> = ({ ledgers, loading = false }) => {
    const columns: ColumnsType<ServiceFeeLedger> = [
        {
            title: '所属月份',
            dataIndex: 'year_month',
            key: 'year_month',
            width: 100,
            render: (text) => <Text strong>{text}</Text>,
        },
        {
            title: '实收租金',
            dataIndex: 'paid_rent_amount',
            key: 'paid_rent_amount',
            width: 120,
            align: 'right',
            render: (val) => `¥${Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`,
        },
        {
            title: '服务费率',
            dataIndex: 'fee_rate',
            key: 'fee_rate',
            width: 100,
            align: 'right',
            render: (val) => `${(Number(val) * 100).toFixed(2)}%`,
        },
        {
            title: '服务费金额',
            dataIndex: 'fee_amount',
            key: 'fee_amount',
            width: 120,
            align: 'right',
            render: (val) => (
                <Text type="danger">¥{Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</Text>
            ),
        },
        {
            title: '结算状态',
            dataIndex: 'settlement_status',
            key: 'settlement_status',
            width: 100,
            render: (status) => {
                let color = 'default';
                if (status === '已结算') color = 'success';
                if (status === '待结算') color = 'warning';
                return <Tag color={color}>{status}</Tag>;
            },
        },
        {
            title: '结算日期',
            dataIndex: 'settlement_date',
            key: 'settlement_date',
            width: 120,
            render: (date) => (date ? dayjs(date).format('YYYY-MM-DD') : '-'),
        },
        {
            title: '备注',
            dataIndex: 'notes',
            key: 'notes',
            ellipsis: true,
        },
    ];

    return (
        <Table
            rowKey="id"
            columns={columns}
            dataSource={ledgers}
            pagination={false}
            loading={loading}
            size="small"
            bordered
            summary={(pageData) => {
                let totalFee = 0;
                let totalPaidRent = 0;

                pageData.forEach((record) => {
                    totalFee += Number(record.fee_amount);
                    totalPaidRent += Number(record.paid_rent_amount);
                });

                return (
                    <Table.Summary fixed>
                        <Table.Summary.Row>
                            <Table.Summary.Cell index={0}><Text strong>合计</Text></Table.Summary.Cell>
                            <Table.Summary.Cell index={1} align="right">
                                <Text>¥{totalPaidRent.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={2} />
                            <Table.Summary.Cell index={3} align="right">
                                <Text strong type="danger">¥{totalFee.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={4} colSpan={3} />
                        </Table.Summary.Row>
                    </Table.Summary>
                );
            }}
        />
    );
};

export default ServiceFeeLedgerTable;
