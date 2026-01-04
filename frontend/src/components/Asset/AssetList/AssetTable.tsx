import React from "react";
import { Table, Tag, Button, Space, Popconfirm, Tooltip } from "antd";
import { EditOutlined, DeleteOutlined, EyeOutlined, HistoryOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type {
  TableRowSelection,
  TablePaginationConfig,
  SorterResult,
  TableCurrentDataSource,
} from "antd/es/table/interface";
import type { FilterValue } from "antd/es/table/interface";
import VirtualTable from "./VirtualTable";
import type { Asset, AssetListResponse } from "@/types/asset";
import { formatArea, formatPercentage, formatDate, getStatusColor } from "@/utils/format";

/**
 * AssetTable组件属性接口
 */
interface AssetTableProps {
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
  onTableChange: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Asset> | SorterResult<Asset>[],
    extra: TableCurrentDataSource<Asset>,
  ) => void;
  /** 选中的行键值 */
  selectedRowKeys?: React.Key[];
  /** 行选择变化回调函数 */
  onSelectChange?: (
    selectedRowKeys: React.Key[],
    selectedRows: Asset[],
    info: { type: "all" | "none" | "invert" | "single" | "multiple" },
  ) => void;
  /** 汇总行渲染函数 */
  summary?: () => React.ReactNode;
}

/**
 * 获取表格列定义
 * @param onView 查看资产详情回调函数
 * @param onEdit 编辑资产回调函数
 * @param onDelete 删除资产回调函数
 * @param onViewHistory 查看资产历史回调函数
 * @returns 表格列配置数组
 */
const getColumns = (
  onView: (asset: Asset) => void,
  onEdit: (asset: Asset) => void,
  onDelete: (id: string) => void,
  onViewHistory: (asset: Asset) => void,
): ColumnsType<Asset> => [
  {
    title: "所属项目",
    dataIndex: "project_name",
    key: "project_name",
    width: 150,
    fixed: "left",
    sorter: true,
    ellipsis: {
      showTitle: false,
    },
    render: (text: string, record: Asset) => {
      // 如果是项目ID格式，尝试显示关联的项目名称
      const projectName = (record.project_name !== null && record.project_name !== undefined && record.project_name !== '') ? record.project_name : text;
      const isId = typeof projectName === "string" && projectName.length === 36; // UUID格式

      let displayText: string = projectName;
      if (isId) {
        // 如果是ID格式，显示"未配置项目"
        displayText = "未配置项目";
      }

      return <Tooltip title={(displayText !== null && displayText !== undefined && displayText !== '') ? displayText : "未设置"}>{(displayText !== null && displayText !== undefined && displayText !== '') ? displayText : "-"}</Tooltip>;
    },
  },
  {
    title: "物业名称",
    dataIndex: "property_name",
    key: "property_name",
    width: 200,
    fixed: "left",
    sorter: true,
    render: (text: string, record: Asset) => (
      <Button
        type="link"
        onClick={() => onView(record)}
        style={{ padding: 0, height: "auto", textAlign: "left" }}
      >
        <Tooltip title="点击查看详情">{text}</Tooltip>
      </Button>
    ),
  },
  {
    title: "权属方",
    dataIndex: "ownership_entity",
    key: "ownership_entity",
    width: 150,
    sorter: true,
    ellipsis: {
      showTitle: false,
    },
    render: (text: string) => <Tooltip title={text}>{text}</Tooltip>,
  },
  {
    title: "权属类别",
    dataIndex: "ownership_category",
    key: "ownership_category",
    width: 150,
    sorter: true,
    ellipsis: {
      showTitle: false,
    },
    filters: [
      { text: "国资管理集团合并口径", value: "1" },
      { text: "民政托管企业", value: "2" },
      { text: "其他", value: "3" },
    ],
    render: (text: string, _record: Asset) => {
      // 权属类别映射
      let displayText: string = text;
      if (typeof text === "string") {
        // 权属类别字典映射
        const categoryMap: Record<string, string> = {
          "1": "国资管理集团合并口径",
          "2": "民政托管企业",
          "3": "其他",
        };
        // 如果是数字ID，转换为对应文字
        if (/^\d+$/.test(text) && categoryMap[text]) {
          displayText = categoryMap[text];
        }
      }

      return <Tooltip title={(displayText !== null && displayText !== undefined && displayText !== '') ? displayText : "未设置"}>{(displayText !== null && displayText !== undefined && displayText !== '') ? displayText : "-"}</Tooltip>;
    },
  },
  {
    title: "所在地址",
    dataIndex: "address",
    key: "address",
    width: 200,
    ellipsis: {
      showTitle: false,
    },
    render: (text: string) => <Tooltip title={text}>{text}</Tooltip>,
  },
  {
    title: "土地面积",
    dataIndex: "land_area",
    key: "land_area",
    width: 120,
    align: "right",
    sorter: true,
    render: (value: number) => formatArea(value),
  },
  {
    title: "实际面积",
    dataIndex: "actual_property_area",
    key: "actual_property_area",
    width: 120,
    align: "right",
    sorter: true,
    render: (value: number) => formatArea(value),
  },
  {
    title: "可出租面积",
    dataIndex: "rentable_area",
    key: "rentable_area",
    width: 130,
    align: "right",
    sorter: true,
    render: (value: number) => formatArea(value),
  },
  {
    title: "已出租面积",
    dataIndex: "rented_area",
    key: "rented_area",
    width: 130,
    align: "right",
    sorter: true,
    render: (value: number) => formatArea(value),
  },
  {
    title: "确权状态",
    dataIndex: "ownership_status",
    key: "ownership_status",
    width: 100,
    filters: [
      { text: "已确权", value: "已确权" },
      { text: "未确权", value: "未确权" },
      { text: "部分确权", value: "部分确权" },
    ],
    render: (status: string) => <Tag color={getStatusColor(status, "ownership")}>{status}</Tag>,
  },
  {
    title: "物业性质",
    dataIndex: "property_nature",
    key: "property_nature",
    width: 100,
    filters: [
      { text: "经营性", value: "经营性" },
      { text: "非经营性", value: "非经营性" },
    ],
    render: (nature: string) => <Tag color={getStatusColor(nature, "property")}>{nature}</Tag>,
  },
  {
    title: "使用状态",
    dataIndex: "usage_status",
    key: "usage_status",
    width: 100,
    filters: [
      { text: "出租", value: "出租" },
      { text: "空置", value: "空置" },
      { text: "自用", value: "自用" },
      { text: "公房", value: "公房" },
      { text: "待移交", value: "待移交" },
      { text: "待处置", value: "待处置" },
      { text: "其他", value: "其他" },
    ],
    render: (status: string) => <Tag color={getStatusColor(status, "usage")}>{status}</Tag>,
  },
  {
    title: "出租率",
    dataIndex: "occupancy_rate",
    key: "occupancy_rate",
    width: 100,
    align: "right",
    sorter: true,
    render: (rate: number, record: Asset) => {
      // 如果有出租率字段直接显示，否则计算
      if (rate !== null && rate !== undefined) {
        return formatPercentage(rate);
      }

      // 计算出租率
      if ((record.rentable_area !== null && record.rentable_area !== undefined) && (record.rented_area !== null && record.rented_area !== undefined)) {
        const calculatedRate = (record.rented_area / record.rentable_area) * 100;
        return (
          <span
            style={{
              color:
                calculatedRate >= 80 ? "#52c41a" : calculatedRate >= 60 ? "#faad14" : "#ff4d4f",
            }}
          >
            {formatPercentage(calculatedRate)}
          </span>
        );
      }

      return "-";
    },
  },
  {
    title: "是否涉诉",
    dataIndex: "is_litigated",
    key: "is_litigated",
    width: 100,
    filters: [
      { text: "是", value: true },
      { text: "否", value: false },
    ],
    render: (isLitigated: boolean) => (
      <Tag color={isLitigated === true ? "red" : "green"}>{isLitigated === true ? "是" : "否"}</Tag>
    ),
  },
  {
    title: "创建时间",
    dataIndex: "created_at",
    key: "created_at",
    width: 120,
    sorter: true,
    render: (date: string) => formatDate(date),
  },
  {
    title: "更新时间",
    dataIndex: "updated_at",
    key: "updated_at",
    width: 120,
    sorter: true,
    render: (date: string) => formatDate(date),
  },
  {
    title: "操作",
    key: "actions",
    width: 150,
    fixed: "right",
    render: (_: unknown, record: Asset) => (
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
 * 资产表格组件
 * 用于展示资产列表数据，支持排序、筛选、分页、虚拟滚动等功能
 */
const AssetTable: React.FC<AssetTableProps> = ({
  data,
  loading = false,
  onEdit,
  onDelete,
  onView,
  onViewHistory,
  onTableChange,
  selectedRowKeys = [],
  onSelectChange,
  summary,
}) => {
  const columns = getColumns(onView, onEdit, onDelete, onViewHistory);

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

  // 移除虚拟滚动组件（antd-virtualized-table已移除）
  // 如需要虚拟滚动，可使用Antd内置的scroll属性或考虑其他方案

  // 根据数据量选择是否使用虚拟滚动
  const itemsLength = data?.items?.length;
  const itemCount = (itemsLength !== null && itemsLength !== undefined) ? itemsLength : 0;
  const shouldUseVirtualScroll = itemCount > 100; // 超过100条记录时使用虚拟滚动

  if (shouldUseVirtualScroll) {
    return (
      <VirtualTable
        data={data}
        loading={loading}
        onEdit={onEdit}
        onDelete={onDelete}
        onView={onView}
        onViewHistory={onViewHistory}
        onTableChange={onTableChange}
        selectedRowKeys={selectedRowKeys}
        onSelectChange={onSelectChange}
        summary={summary}
        height={600}
      />
    );
  }

  // 少量数据时使用标准表格
  return (
    <Table
      columns={columns}
      dataSource={data?.items || []}
      rowKey="id"
      loading={loading}
      scroll={{ x: 1800, y: 600 }}
      rowSelection={rowSelection}
      pagination={{
        current: (data?.page !== null && data?.page !== undefined) ? data.page : 1,
        pageSize: (data?.limit !== null && data?.limit !== undefined) ? data.limit : 20,
        total: (data?.total !== null && data?.total !== undefined) ? data.total : 0,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
        pageSizeOptions: ["10", "20", "50", "100"],
        size: "default",
      }}
      onChange={onTableChange}
      size="middle"
      bordered
      sticky={{ offsetHeader: 64 }}
      summary={summary}
    />
  );
};

export default React.memo(AssetTable);
