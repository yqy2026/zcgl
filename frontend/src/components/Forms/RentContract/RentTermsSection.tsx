import React from 'react';
import { Table, Button, Space, Card, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import { useRentContractFormContext, RentTermFormData } from './RentContractFormContext';

/**
 * RentContractForm - Rent Terms Section
 * Displays table of rent terms with add/edit/delete
 */
const RentTermsSection: React.FC = () => {
    const { rentTerms, handleAddRentTerm, handleEditRentTerm, handleDeleteRentTerm } = useRentContractFormContext();

    const rentTermColumns: ColumnsType<RentTermFormData> = [
        {
            title: '开始日期',
            dataIndex: 'start_date',
            key: 'start_date',
            render: (date: Dayjs) => date.format('YYYY-MM-DD'),
            width: 120,
        },
        {
            title: '结束日期',
            dataIndex: 'end_date',
            key: 'end_date',
            render: (date: Dayjs) => date.format('YYYY-MM-DD'),
            width: 120,
        },
        {
            title: '月租金',
            dataIndex: 'monthly_rent',
            key: 'monthly_rent',
            render: (amount: number) => `¥${amount.toLocaleString()}`,
            width: 120,
        },
        {
            title: '管理费',
            dataIndex: 'management_fee',
            key: 'management_fee',
            render: (amount: number) => `¥${(amount || 0).toLocaleString()}`,
            width: 100,
        },
        {
            title: '其他费用',
            dataIndex: 'other_fees',
            key: 'other_fees',
            render: (amount: number) => `¥${(amount || 0).toLocaleString()}`,
            width: 100,
        },
        {
            title: '月应收总额',
            key: 'total_amount',
            render: (record: RentTermFormData) => {
                const total = record.monthly_rent + (record.management_fee || 0) + (record.other_fees || 0);
                return `¥${total.toLocaleString()}`;
            },
            width: 120,
        },
        {
            title: '说明',
            dataIndex: 'rent_description',
            key: 'rent_description',
            ellipsis: true,
        },
        {
            title: '操作',
            key: 'actions',
            width: 120,
            render: (record: RentTermFormData) => (
                <Space size="small">
                    <Button
                        type="text"
                        size="small"
                        onClick={() => handleEditRentTerm(record)}
                    >
                        编辑
                    </Button>
                    <Popconfirm
                        title="确认删除"
                        description="确实要删除这个租金条款吗？"
                        onConfirm={() => handleDeleteRentTerm(record.key)}
                        okText="确认"
                        cancelText="取消"
                    >
                        <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                        >
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <Card
            title="租金条款"
            size="small"
            style={{ marginBottom: 16 }}
            extra={
                <Button
                    type="primary"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={handleAddRentTerm}
                >
                    添加条款
                </Button>
            }
        >
            <Table
                columns={rentTermColumns}
                dataSource={rentTerms}
                pagination={false}
                size="small"
                locale={{ emptyText: '暂无租金条款，请点击"添加条款"按钮添加' }}
            />
        </Card>
    );
};

export default RentTermsSection;
