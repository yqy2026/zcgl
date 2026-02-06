import React, { useCallback, useMemo, useState } from 'react';
import { Table, Tag, Button, Space, Popconfirm, Tooltip, Modal, Input } from 'antd';
import { EditOutlined, DeleteOutlined, EyeOutlined, HistoryOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type {
  TablePaginationConfig,
  SorterResult,
  TableCurrentDataSource,
  FilterValue,
} from 'antd/es/table/interface';

import type { Asset, AssetListResponse } from '@/types/asset';
import { DataStatus } from '@/types/asset';
import { formatArea, formatPercentage, formatDate, getStatusColor } from '@/utils/format';
import { getOccupancyRateColor } from '@/styles/colorMap';
import { useSystemDictionary } from '@/hooks/useSystemDictionary';
import usePermission from '@/hooks/usePermission';
import { TableWithPagination } from '@/components/Common/TableWithPagination';

// Constants
const UUID_LENGTH = 36;

/**
 * 格式化权属类别显示文本
 * 从系统字典选项中查找对应的标签,如果找不到则返回原始值或默认值
 *
 * @param text - 权属类别值
 * @param options - 系统字典选项列表
 * @returns 格式化后的显示文本
 */
function formatOwnershipCategory(
  text: string | undefined,
  options: Array<{ label: string; value: string }>
): string {
  if (!text || options.length === 0) {
    return text ?? '其他';
  }

  const matchedOption = options.find(opt => opt.value === String(text));
  return matchedOption?.label ?? text;
}

function getDataStatusColor(status?: string): string {
  switch (status) {
    case DataStatus.NORMAL:
      return 'green';
    case DataStatus.DELETED:
      return 'red';
    case DataStatus.ARCHIVED:
      return 'orange';
    case DataStatus.ABNORMAL:
      return 'volcano';
    default:
      return 'default';
  }
}

interface AssetListProps {
  data?: AssetListResponse;
  loading?: boolean;
  onEdit: (asset: Asset) => void;
  onDelete: (id: string) => void;
  onRestore: (id: string) => void;
  onHardDelete: (id: string) => void;
  onView: (asset: Asset) => void;
  onViewHistory: (asset: Asset) => void;
  onTableChange: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Asset> | SorterResult<Asset>[],
    extra: TableCurrentDataSource<Asset>
  ) => void;
  selectedRowKeys?: React.Key[];
  onSelectChange?: (selectedRowKeys: React.Key[]) => void;
}

const AssetList: React.FC<AssetListProps> = ({
  data,
  loading = false,
  onEdit,
  onDelete,
  onRestore,
  onHardDelete,
  onView,
  onViewHistory,
  onTableChange,
  selectedRowKeys = [],
  onSelectChange,
}) => {
  // 使用系统字典获取权属类别
  const { options: ownershipCategoryOptions } = useSystemDictionary('ownership_category');
  const { isAdmin } = usePermission();
  const isAdminUser = isAdmin();

  const [hardDeleteTarget, setHardDeleteTarget] = useState<Asset | null>(null);
  const [hardDeleteInput, setHardDeleteInput] = useState('');

  const handleOpenHardDelete = useCallback((asset: Asset) => {
    setHardDeleteTarget(asset);
    setHardDeleteInput('');
  }, []);

  const handleCloseHardDelete = useCallback(() => {
    setHardDeleteTarget(null);
    setHardDeleteInput('');
  }, []);

  const hardDeleteMatch = useMemo(() => {
    if (hardDeleteTarget == null) {
      return false;
    }
    const input = hardDeleteInput.trim();
    if (input === '') {
      return false;
    }
    return input === hardDeleteTarget.property_name || input === hardDeleteTarget.id;
  }, [hardDeleteInput, hardDeleteTarget]);

  const handleConfirmHardDelete = useCallback(async () => {
    if (hardDeleteTarget == null) {
      return;
    }
    await onHardDelete(hardDeleteTarget.id);
    handleCloseHardDelete();
  }, [handleCloseHardDelete, hardDeleteTarget, onHardDelete]);

  // 表格列定义
  const columns = useMemo<ColumnsType<Asset>>(
    () => [
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
          // 如果是项目ID格式，尝试显示关联的项目名称
          const projectName = record.project_name ?? text;
          const isId = typeof projectName === 'string' && projectName.length === UUID_LENGTH;

          let displayText: string = projectName ?? '未配置项目';
          if (isId) {
            // 如果是ID格式，显示"未配置项目"
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
        title: '权属类别',
        dataIndex: 'ownership_category',
        key: 'ownership_category',
        width: 150,
        sorter: true,
        ellipsis: {
          showTitle: false,
        },
        filters: ownershipCategoryOptions.map(opt => ({
          text: opt.label,
          value: opt.value,
        })),
        render: (text: string | undefined, _record: Asset) => {
          const displayText = formatOwnershipCategory(text, ownershipCategoryOptions);
          return <Tooltip title={displayText ?? '未设置'}>{displayText ?? '-'}</Tooltip>;
        },
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
        title: '数据状态',
        dataIndex: 'data_status',
        key: 'data_status',
        width: 100,
        render: status => (
          <Tag color={getDataStatusColor(status)}>{status ?? '未知'}</Tag>
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
          if (rate !== undefined && rate !== null) {
            return formatPercentage(rate);
          }

          // 计算出租率
          if (
            record.rentable_area !== undefined &&
            record.rentable_area !== null &&
            record.rented_area !== undefined &&
            record.rented_area !== null
          ) {
            const calculatedRate = (record.rented_area / record.rentable_area) * 100;
            return (
              <span
                style={{
                  color: getOccupancyRateColor(calculatedRate),
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
          <Tag color={isLitigated === true ? 'red' : 'green'}>
            {isLitigated === true ? '是' : '否'}
          </Tag>
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
        width: 240,
        fixed: 'right',
        render: (_, record) => {
          const isDeleted = record.data_status === DataStatus.DELETED;
          const showAdminActions = isAdminUser && isDeleted;

          return (
            <Space size="small">
              <Tooltip title="查看详情">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => onView(record)}
                  size="small"
                />
              </Tooltip>

              {!isDeleted && (
                <Tooltip title="编辑">
                  <Button
                    type="text"
                    icon={<EditOutlined />}
                    onClick={() => onEdit(record)}
                    size="small"
                  />
                </Tooltip>
              )}

              <Tooltip title="查看历史">
                <Button
                  type="text"
                  icon={<HistoryOutlined />}
                  onClick={() => onViewHistory(record)}
                  size="small"
                />
              </Tooltip>

              {!isDeleted && (
                <Popconfirm
                  title="确定要删除这个资产吗？"
                  description="删除后可在回收站恢复"
                  onConfirm={() => onDelete(record.id)}
                  okText="确定"
                  cancelText="取消"
                  okType="danger"
                >
                  <Tooltip title="删除">
                    <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                  </Tooltip>
                </Popconfirm>
              )}

              {showAdminActions && (
                <Popconfirm
                  title="确定要恢复这个资产吗？"
                  description="恢复后将回到资产列表"
                  onConfirm={() => onRestore(record.id)}
                  okText="恢复"
                  cancelText="取消"
                >
                  <Button type="link" size="small">
                    恢复
                  </Button>
                </Popconfirm>
              )}

              {showAdminActions && (
                <Tooltip title="彻底删除">
                  <Button
                    type="text"
                    danger
                    size="small"
                    onClick={() => handleOpenHardDelete(record)}
                  >
                    彻底删除
                  </Button>
                </Tooltip>
              )}
            </Space>
          );
        },
      },
    ],
    [
      handleOpenHardDelete,
      isAdminUser,
      onDelete,
      onEdit,
      onRestore,
      onView,
      onViewHistory,
      ownershipCategoryOptions,
    ]
  );

  // 计算当前页汇总数据
  const items = data?.items ?? [];

  const summary = useMemo(() => {
    if (items.length === 0) return null;

    const totals = items.reduce(
      (acc, item) => {
        return {
          landArea: acc.landArea + (Number(item.land_area) ?? 0),
          actualArea: acc.actualArea + (Number(item.actual_property_area) ?? 0),
          rentableArea: acc.rentableArea + (Number(item.rentable_area) ?? 0),
          rentedArea: acc.rentedArea + (Number(item.rented_area) ?? 0),
        };
      },
      {
        landArea: 0,
        actualArea: 0,
        rentableArea: 0,
        rentedArea: 0,
      }
    );

    // 正确计算未出租面积和出租率
    const unrentedArea = totals.rentableArea - totals.rentedArea;
    const occupancyRate =
      totals.rentableArea > 0 ? (totals.rentedArea / totals.rentableArea) * 100 : 0;

    return {
      ...totals,
      unrentedArea,
      occupancyRate,
    };
  }, [items]);

  // 汇总行渲染函数
  const renderSummary = useCallback((_pageData: readonly Asset[]) => {
    if (!summary) return null;

    const selectionOffset = onSelectChange ? 1 : 0;
    const leadingSpan = 5 + selectionOffset;
    const landIndex = leadingSpan;
    const actualIndex = landIndex + 1;
    const rentableIndex = actualIndex + 1;
    const rentedIndex = rentableIndex + 1;
    const statusSpan = 4;
    const occupancyIndex = rentedIndex + 1 + statusSpan;
    const trailingSpan = 4;

    return (
      <Table.Summary fixed>
        <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={leadingSpan} align="right">
            <strong>当前页合计：</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={landIndex} align="right">
            <strong>{formatArea(summary.landArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={actualIndex} align="right">
            <strong>{formatArea(summary.actualArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={rentableIndex} align="right">
            <strong>{formatArea(summary.rentableArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={rentedIndex} align="right">
            <strong>{formatArea(summary.rentedArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={rentedIndex + 1} colSpan={statusSpan} />
          <Table.Summary.Cell index={occupancyIndex} align="right">
            <strong
              style={{
                color: getOccupancyRateColor(summary.occupancyRate),
              }}
            >
              {formatPercentage(summary.occupancyRate)}
            </strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={occupancyIndex + 1} colSpan={trailingSpan} />
        </Table.Summary.Row>
      </Table.Summary>
    );
  }, [onSelectChange, summary]);

  // 行选择配置
  const rowSelection = useMemo(() => {
    if (!onSelectChange) {
      return undefined;
    }

    return {
      selectedRowKeys,
      onChange: onSelectChange,
      hideSelectAll: true,
      getCheckboxProps: (record: Asset) => ({
        name: record.property_name,
      }),
    };
  }, [onSelectChange, selectedRowKeys]);

  const paginationState = {
    current: data?.page ?? 1,
    pageSize: data?.page_size ?? 20,
    total: data?.total ?? 0,
  };

  const handlePageChange = useCallback(
    (_pagination: { current?: number; pageSize?: number }) => {
      void _pagination;
    },
    []
  );

  return (
    <>
      <TableWithPagination
        columns={columns}
        dataSource={data?.items ?? []}
        rowKey="id"
        loading={loading}
        scroll={{ x: 2000, y: 600 }}
        rowSelection={rowSelection}
        summary={renderSummary}
        paginationState={paginationState}
        onPageChange={handlePageChange}
        paginationProps={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total: number, range: [number, number]) =>
            `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
          pageSizeOptions: ['10', '20', '50', '100'],
        }}
        onChange={onTableChange}
        size="middle"
        bordered
        sticky={{ offsetHeader: 64 }}
      />

      <Modal
        title="确认彻底删除"
        open={hardDeleteTarget != null}
        onCancel={handleCloseHardDelete}
        onOk={handleConfirmHardDelete}
        okText="彻底删除"
        okType="danger"
        cancelText="取消"
        okButtonProps={{ disabled: !hardDeleteMatch }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            此操作不可恢复。请输入物业名称或资产 ID 以确认删除：
            <strong>
              {hardDeleteTarget != null
                ? ` ${hardDeleteTarget.property_name} / ${hardDeleteTarget.id}`
                : ''}
            </strong>
          </div>
          <Input
            placeholder="输入物业名称或资产ID"
            value={hardDeleteInput}
            onChange={event => setHardDeleteInput(event.target.value)}
          />
        </Space>
      </Modal>
    </>
  );
};

export default React.memo(AssetList);
