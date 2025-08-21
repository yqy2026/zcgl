import React from 'react'
import { Table, Tag, Button, Space, Popconfirm, Tooltip } from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  HistoryOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'

import type { Asset, AssetListResponse } from '@/types/asset'
import { formatArea, formatPercentage, formatDate, getStatusColor } from '@/utils/format'

interface AssetListProps {
  data?: AssetListResponse
  loading?: boolean
  onEdit: (asset: Asset) => void
  onDelete: (id: string) => void
  onView: (asset: Asset) => void
  onTableChange: (pagination: any, filters: any, sorter: any) => void
  selectedRowKeys?: string[]
  onSelectChange?: (selectedRowKeys: string[]) => void
}

const AssetList: React.FC<AssetListProps> = ({
  data,
  loading = false,
  onEdit,
  onDelete,
  onView,
  onTableChange,
  selectedRowKeys = [],
  onSelectChange,
}) => {
  const navigate = useNavigate()

  // 表格列定义
  const columns: ColumnsType<Asset> = [
    {
      title: '物业名称',
      dataIndex: 'property_name',
      key: 'property_name',
      width: 200,
      fixed: 'left',
      sorter: true,
      render: (text, record) => (
        <Button
          type="link"
          onClick={() => onView(record)}
          style={{ padding: 0, height: 'auto', textAlign: 'left' }}
        >
          <Tooltip title="点击查看详情">
            {text}
          </Tooltip>
        </Button>
      ),
    },
    {
      title: '权属方',
      dataIndex: 'ownership_entity',
      key: 'ownership_entity',
      width: 150,
      sorter: true,
      ellipsis: {
        showTitle: false,
      },
      render: (text) => (
        <Tooltip title={text}>
          {text}
        </Tooltip>
      ),
    },
    {
      title: '经营管理方',
      dataIndex: 'management_entity',
      key: 'management_entity',
      width: 150,
      ellipsis: {
        showTitle: false,
      },
      render: (text) => (
        <Tooltip title={text || '未设置'}>
          {text || '-'}
        </Tooltip>
      ),
    },
    {
      title: '所在地址',
      dataIndex: 'address',
      key: 'address',
      width: 200,
      ellipsis: {
        showTitle: false,
      },
      render: (text) => (
        <Tooltip title={text}>
          {text}
        </Tooltip>
      ),
    },
    {
      title: '土地面积',
      dataIndex: 'land_area',
      key: 'land_area',
      width: 120,
      align: 'right',
      sorter: true,
      render: (value) => formatArea(value),
    },
    {
      title: '实际面积',
      dataIndex: 'actual_property_area',
      key: 'actual_property_area',
      width: 120,
      align: 'right',
      sorter: true,
      render: (value) => formatArea(value),
    },
    {
      title: '可出租面积',
      dataIndex: 'rentable_area',
      key: 'rentable_area',
      width: 130,
      align: 'right',
      sorter: true,
      render: (value) => formatArea(value),
    },
    {
      title: '已出租面积',
      dataIndex: 'rented_area',
      key: 'rented_area',
      width: 130,
      align: 'right',
      sorter: true,
      render: (value) => formatArea(value),
    },
    {
      title: '确权状态',
      dataIndex: 'ownership_status',
      key: 'ownership_status',
      width: 100,
      filters: [
        { text: '已确权', value: '已确权' },
        { text: '未确权', value: '未确权' },
        { text: '部分确权', value: '部分确权' },
      ],
      render: (status) => (
        <Tag color={getStatusColor(status, 'ownership')}>
          {status}
        </Tag>
      ),
    },
    {
      title: '物业性质',
      dataIndex: 'property_nature',
      key: 'property_nature',
      width: 100,
      filters: [
        { text: '经营类', value: '经营类' },
        { text: '非经营类', value: '非经营类' },
      ],
      render: (nature) => (
        <Tag color={getStatusColor(nature, 'property')}>
          {nature}
        </Tag>
      ),
    },
    {
      title: '使用状态',
      dataIndex: 'usage_status',
      key: 'usage_status',
      width: 100,
      filters: [
        { text: '出租', value: '出租' },
        { text: '闲置', value: '闲置' },
        { text: '自用', value: '自用' },
        { text: '公房', value: '公房' },
        { text: '其他', value: '其他' },
      ],
      render: (status) => (
        <Tag color={getStatusColor(status, 'usage')}>
          {status}
        </Tag>
      ),
    },
    {
      title: '出租率',
      dataIndex: 'occupancy_rate',
      key: 'occupancy_rate',
      width: 100,
      align: 'right',
      sorter: true,
      render: (rate, record) => {
        // 如果有出租率字段直接显示，否则计算
        if (rate) {
          return formatPercentage(rate)
        }
        
        // 计算出租率
        if (record.rentable_area && record.rented_area) {
          const calculatedRate = (record.rented_area / record.rentable_area) * 100
          return (
            <span style={{ 
              color: calculatedRate >= 80 ? '#52c41a' : 
                     calculatedRate >= 60 ? '#faad14' : '#ff4d4f'
            }}>
              {formatPercentage(calculatedRate)}
            </span>
          )
        }
        
        return '-'
      },
    },
    {
      title: '是否涉诉',
      dataIndex: 'is_litigated',
      key: 'is_litigated',
      width: 100,
      filters: [
        { text: '是', value: true },
        { text: '否', value: false },
      ],
      render: (isLitigated) => (
        <Tag color={isLitigated ? 'red' : 'green'}>
          {isLitigated ? '是' : '否'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      sorter: true,
      render: (date) => formatDate(date),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 120,
      sorter: true,
      render: (date) => formatDate(date),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => onView(record)}
              size="small"
            />
          </Tooltip>
          
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
              size="small"
            />
          </Tooltip>
          
          <Tooltip title="查看历史">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => navigate(`/assets/${record.id}/history`)}
              size="small"
            />
          </Tooltip>
          
          <Popconfirm
            title="确定要删除这个资产吗？"
            description="删除后无法恢复，请谨慎操作"
            onConfirm={() => onDelete(record.id)}
            okText="确定"
            cancelText="取消"
            okType="danger"
          >
            <Tooltip title="删除">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                size="small"
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 行选择配置
  const rowSelection = onSelectChange ? {
    selectedRowKeys,
    onChange: onSelectChange,
    getCheckboxProps: (record: Asset) => ({
      name: record.property_name,
    }),
  } : undefined

  return (
    <Table
      columns={columns}
      dataSource={data?.data || []}
      rowKey="id"
      loading={loading}
      scroll={{ x: 1800, y: 600 }}
      rowSelection={rowSelection}
      pagination={{
        current: data?.page || 1,
        pageSize: data?.limit || 20,
        total: data?.total || 0,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) =>
          `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
        pageSizeOptions: ['10', '20', '50', '100'],
        size: 'default',
      }}
      onChange={onTableChange}
      size="middle"
      bordered
      sticky={{ offsetHeader: 64 }}
    />
  )
}

export default AssetList