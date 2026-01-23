/**
 * 虚拟滚动表格组件
 * 使用@tanstack/react-virtual实现高性能表格
 */

import React, { useRef } from 'react';
import { Tag, Button, Space, Popconfirm, Tooltip, Pagination } from 'antd';
import { EditOutlined, DeleteOutlined, EyeOutlined, HistoryOutlined } from '@ant-design/icons';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ColumnsType, ColumnType as AntColumnType } from 'antd/es/table';
import type { ColumnGroupType } from 'antd/es/table';
import type {
  TableRowSelection,
  TablePaginationConfig,
  SorterResult,
  TableCurrentDataSource,
} from 'antd/es/table/interface';
import type { FilterValue } from 'antd/es/table/interface';

import type { Asset, AssetListResponse } from '@/types/asset';
import { formatArea, formatPercentage, formatDate, getStatusColor } from '@/utils/format';

// Type guard for ColumnType
function isColumnType<T>(
  column: ColumnGroupType<T> | AntColumnType<T>
): column is AntColumnType<T> {
  return 'dataIndex' in column;
}

/**
 * 虚拟滚动表格属性接口
 */
interface VirtualTableProps {
  /** 资产列表数据 */
  data?: AssetListResponse;
  /** 加载状态 */
  loading?: boolean;
  /** 编辑资产回调函数 */
  onEdit: (asset: Asset) => void;
  /** 删除资产回调函数 */
  onDelete: (id: string) => void;
  /** 查看资产详情回调函数 */
  onView: (asset: Asset) => void;
  /** 查看资产历史回调函数 */
  onViewHistory: (asset: Asset) => void;
  /** 表格变化回调函数 */
  onTableChange?: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Asset> | SorterResult<Asset>[],
    extra: TableCurrentDataSource<Asset>
  ) => void;
  /** 选中的行键值 */
  selectedRowKeys?: React.Key[];
  /** 行选择变化回调函数 */
  onSelectChange?: (
    selectedRowKeys: React.Key[],
    selectedRows: Asset[],
    info: { type: 'all' | 'none' | 'invert' | 'single' | 'multiple' }
  ) => void;
  /** 汇总行渲染函数 */
  summary?: () => React.ReactNode;
  /** 行高 */
  rowHeight?: number;
  /** 表格高度 */
  height?: number;
  /** 内部使用的加载状态（用于兼容） */
  _loading?: boolean;
  /** 内部使用的表格变化回调（用于兼容） */
  _onTableChange?: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Asset> | SorterResult<Asset>[],
    extra: TableCurrentDataSource<Asset>
  ) => void;
}

/**
 * 获取表格列定义
 */
const getColumns = (
  onView: (asset: Asset) => void,
  onEdit: (asset: Asset) => void,
  onDelete: (id: string) => void,
  onViewHistory: (asset: Asset) => void
): ColumnsType<Asset> => [
  {
    title: '所属项目',
    dataIndex: 'project_name',
    key: 'project_name',
    width: 150,
    fixed: 'left',
    sorter: true,
    ellipsis: {
      showTitle: false,
    },
    render: (text: string | undefined, record: Asset) => {
      const projectName = record.project_name ?? text;
      const isId = typeof projectName === 'string' && projectName.length === 36;

      let displayText: string = projectName ?? '未配置项目';
      if (isId) {
        displayText = '未配置项目';
      }

      return <Tooltip title={displayText ?? '未设置'}>{displayText ?? '-'}</Tooltip>;
    },
  },
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
        <Tooltip title="点击查看详情">{text}</Tooltip>
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
    render: (text: string) => <Tooltip title={text}>{text}</Tooltip>,
  },
  {
    title: '所在地址',
    dataIndex: 'address',
    key: 'address',
    width: 200,
    ellipsis: {
      showTitle: false,
    },
    render: (text: string) => <Tooltip title={text}>{text}</Tooltip>,
  },
  {
    title: '土地面积',
    dataIndex: 'land_area',
    key: 'land_area',
    width: 120,
    align: 'right',
    sorter: true,
    render: value => formatArea(value),
  },
  {
    title: '实际面积',
    dataIndex: 'actual_property_area',
    key: 'actual_property_area',
    width: 120,
    align: 'right',
    sorter: true,
    render: value => formatArea(value),
  },
  {
    title: '可出租面积',
    dataIndex: 'rentable_area',
    key: 'rentable_area',
    width: 130,
    align: 'right',
    sorter: true,
    render: value => formatArea(value),
  },
  {
    title: '已出租面积',
    dataIndex: 'rented_area',
    key: 'rented_area',
    width: 130,
    align: 'right',
    sorter: true,
    render: value => formatArea(value),
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
    render: status => <Tag color={getStatusColor(status, 'ownership')}>{status}</Tag>,
  },
  {
    title: '物业性质',
    dataIndex: 'property_nature',
    key: 'property_nature',
    width: 100,
    filters: [
      { text: '经营性', value: '经营性' },
      { text: '非经营性', value: '非经营性' },
    ],
    render: nature => <Tag color={getStatusColor(nature, 'property')}>{nature}</Tag>,
  },
  {
    title: '使用状态',
    dataIndex: 'usage_status',
    key: 'usage_status',
    width: 100,
    filters: [
      { text: '出租', value: '出租' },
      { text: '空置', value: '空置' },
      { text: '自用', value: '自用' },
      { text: '公房', value: '公房' },
      { text: '待移交', value: '待移交' },
      { text: '待处置', value: '待处置' },
      { text: '其他', value: '其他' },
    ],
    render: status => <Tag color={getStatusColor(status, 'usage')}>{status}</Tag>,
  },
  {
    title: '出租率',
    dataIndex: 'occupancy_rate',
    key: 'occupancy_rate',
    width: 100,
    align: 'right',
    sorter: true,
    render: (rate, record) => {
      if (rate != null) {
        return formatPercentage(rate);
      }

      if (record.rentable_area != null && record.rented_area != null) {
        const calculatedRate = (record.rented_area / record.rentable_area) * 100;
        return (
          <span
            style={{
              color:
                calculatedRate >= 80 ? '#52c41a' : calculatedRate >= 60 ? '#faad14' : '#ff4d4f',
            }}
          >
            {formatPercentage(calculatedRate)}
          </span>
        );
      }

      return '-';
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
    render: isLitigated => (
      <Tag color={isLitigated === true ? 'red' : 'green'}>{isLitigated === true ? '是' : '否'}</Tag>
    ),
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 120,
    sorter: true,
    render: date => formatDate(date),
  },
  {
    title: '更新时间',
    dataIndex: 'updated_at',
    key: 'updated_at',
    width: 120,
    sorter: true,
    render: date => formatDate(date),
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render: (_, record) => (
      <Space size="small">
        <Tooltip title="查看详情">
          <Button type="text" icon={<EyeOutlined />} onClick={() => onView(record)} size="small" />
        </Tooltip>

        <Tooltip title="编辑">
          <Button type="text" icon={<EditOutlined />} onClick={() => onEdit(record)} size="small" />
        </Tooltip>

        <Tooltip title="查看历史">
          <Button
            type="text"
            icon={<HistoryOutlined />}
            onClick={() => onViewHistory(record)}
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
            <Button type="text" danger icon={<DeleteOutlined />} size="small" />
          </Tooltip>
        </Popconfirm>
      </Space>
    ),
  },
];

/**
 * 虚拟滚动表格组件
 * 支持大数据量的高性能表格渲染
 */
const VirtualTable: React.FC<VirtualTableProps> = ({
  data,
  _loading = false,
  onEdit,
  onDelete,
  onView,
  onViewHistory,
  _onTableChange,
  selectedRowKeys = [],
  onSelectChange,
  summary,
  rowHeight = 55,
  height = 600,
}) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const columns = getColumns(onView, onEdit, onDelete, onViewHistory);
  const items = data?.items ?? [];

  // 虚拟滚动配置
  const rowVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 5,
  });

  // 行选择配置
  const rowSelection: TableRowSelection<Asset> | undefined = onSelectChange
    ? {
        selectedRowKeys,
        onChange: onSelectChange,
        getCheckboxProps: (record: Asset) => ({
          name: record.property_name,
        }),
      }
    : undefined;

  // 渲染虚拟行
  const renderVirtualRow = (index: number) => {
    const item = items[index];
    const style = {
      position: 'absolute' as const,
      top: 0,
      left: 0,
      width: '100%',
      height: `${rowHeight}px`,
      display: 'flex',
      alignItems: 'center',
      borderBottom: '1px solid #f0f0f0',
      backgroundColor: index % 2 === 0 ? '#fafafa' : '#ffffff',
    };

    return (
      <div key={item.id} style={style}>
        <div style={{ display: 'flex', width: '100%', padding: '0 16px' }}>
          {columns.map((column, colIndex) => {
            // Type guard to ensure column has dataIndex
            if (!isColumnType(column)) {
              return null;
            }

            const dataIndex = column.dataIndex as keyof Asset;
            const value = item[dataIndex];

            // Type-safe render function call
            const renderValue = column.render
              ? (
                  column.render as (value: unknown, record: Asset, index: number) => React.ReactNode
                )(value, item, index)
              : (value as React.ReactNode);

            return (
              <div
                key={column.key ?? colIndex}
                style={{
                  flex: column.width != null ? `0 0 ${column.width}px` : '1',
                  minWidth: column.width ?? 100,
                  padding: '0 8px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  textAlign: column.align ?? 'left',
                }}
              >
                {renderValue}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // 计算表头宽度
  const totalWidth = columns.reduce(
    (sum: number, col) => sum + (typeof col.width === 'number' ? col.width : 150),
    0
  );

  return (
    <div>
      {/* 表头 */}
      <div
        style={{
          display: 'flex',
          width: '100%',
          backgroundColor: '#fafafa',
          borderBottom: '2px solid #f0f0f0',
          fontWeight: 'bold',
          padding: '12px 16px',
          minWidth: `${totalWidth}px`,
        }}
      >
        {rowSelection && (
          <div style={{ width: 50, textAlign: 'center' }}>
            <input type="checkbox" />
          </div>
        )}
        {columns.map((column, index) => {
          // Type-safe title access
          const title = isColumnType(column) ? column.title : undefined;
          return (
            <div
              key={column.key ?? index}
              style={{
                flex: column.width != null ? `0 0 ${column.width}px` : '1',
                minWidth: column.width ?? 100,
                padding: '0 8px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {title as React.ReactNode}
            </div>
          );
        })}
      </div>

      {/* 虚拟滚动内容 */}
      <div
        ref={parentRef}
        style={{
          height: `${height}px`,
          overflow: 'auto',
          border: '1px solid #f0f0f0',
          position: 'relative',
        }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {rowVirtualizer.getVirtualItems().map(virtualItem => (
            <div
              key={virtualItem.index}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {renderVirtualRow(virtualItem.index)}
            </div>
          ))}
        </div>
      </div>

      {/* 分页 */}
      <div style={{ padding: '16px 0', textAlign: 'right' }}>
        <Pagination
          current={data?.page ?? 1}
          pageSize={data?.pageSize ?? 20}
          total={data?.total ?? 0}
          showSizeChanger={true}
          showQuickJumper={true}
          showTotal={(total: number, range: [number, number]) =>
            `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
          }
          pageSizeOptions={['10', '20', '50', '100']}
          size="middle"
        />
      </div>

      {/* 汇总行 */}
      {summary && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#fafafa',
            borderTop: '1px solid #f0f0f0',
          }}
        >
          {summary()}
        </div>
      )}
    </div>
  );
};

export default React.memo(VirtualTable);
