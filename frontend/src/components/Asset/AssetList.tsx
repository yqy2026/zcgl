import React from "react";
import { Table, Tag, Button, Space, Popconfirm, Tooltip } from "antd";
import { EditOutlined, DeleteOutlined, EyeOutlined, HistoryOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";

import type { Asset, AssetListResponse } from "@/types/asset";
import { formatArea, formatPercentage, formatDate, getStatusColor } from "@/utils/format";
import type { PaginationConfig, FilterConfig, SorterConfig } from "@/types/common";

interface AssetListProps {
  data?: AssetListResponse;
  loading?: boolean;
  onEdit: (asset: Asset) => void;
  onDelete: (id: string) => void;
  onView: (asset: Asset) => void;
  onViewHistory: (asset: Asset) => void;
  onTableChange: (
    pagination: PaginationConfig,
    filters: FilterConfig,
    sorter: SorterConfig,
  ) => void;
  selectedRowKeys?: React.Key[];
  onSelectChange?: (selectedRowKeys: React.Key[]) => void;
}

const AssetList: React.FC<AssetListProps> = ({
  data,
  loading = false,
  onEdit,
  onDelete,
  onView,
  onViewHistory,
  onTableChange,
  selectedRowKeys = [],
  onSelectChange,
}) => {
  // 表格列定义
  const columns: ColumnsType<Asset> = [
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
      render: (text, record) => {
        // 如果是项目ID格式，尝试显示关联的项目名称
        const projectName = record.project_name || text;
        const isId = typeof projectName === "string" && projectName.length === 36; // UUID格式

        let displayText = projectName;
        if (isId) {
          // 如果是ID格式，显示"未配置项目"
          displayText = "未配置项目";
        }

        return <Tooltip title={displayText || "未设置"}>{displayText || "-"}</Tooltip>;
      },
    },
    {
      title: "物业名称",
      dataIndex: "property_name",
      key: "property_name",
      width: 200,
      fixed: "left",
      sorter: true,
      render: (text, record) => (
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
      render: (text) => <Tooltip title={text}>{text}</Tooltip>,
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
      render: (text, _record) => {
        // 权属类别映射
        let displayText = text;
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

        return <Tooltip title={displayText || "未设置"}>{displayText || "-"}</Tooltip>;
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
      render: (text) => <Tooltip title={text}>{text}</Tooltip>,
    },
    {
      title: "土地面积",
      dataIndex: "land_area",
      key: "land_area",
      width: 120,
      align: "right",
      sorter: true,
      render: (value) => formatArea(value),
    },
    {
      title: "实际面积",
      dataIndex: "actual_property_area",
      key: "actual_property_area",
      width: 120,
      align: "right",
      sorter: true,
      render: (value) => formatArea(value),
    },
    {
      title: "可出租面积",
      dataIndex: "rentable_area",
      key: "rentable_area",
      width: 130,
      align: "right",
      sorter: true,
      render: (value) => formatArea(value),
    },
    {
      title: "已出租面积",
      dataIndex: "rented_area",
      key: "rented_area",
      width: 130,
      align: "right",
      sorter: true,
      render: (value) => formatArea(value),
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
      render: (status) => <Tag color={getStatusColor(status, "ownership")}>{status}</Tag>,
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
      render: (nature) => <Tag color={getStatusColor(nature, "property")}>{nature}</Tag>,
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
      render: (status) => <Tag color={getStatusColor(status, "usage")}>{status}</Tag>,
    },
    {
      title: "出租率",
      dataIndex: "occupancy_rate",
      key: "occupancy_rate",
      width: 100,
      align: "right",
      sorter: true,
      render: (rate, record) => {
        // 如果有出租率字段直接显示，否则计算
        if (rate) {
          return formatPercentage(rate);
        }

        // 计算出租率
        if (record.rentable_area && record.rented_area) {
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
      render: (isLitigated) => (
        <Tag color={isLitigated ? "red" : "green"}>{isLitigated ? "是" : "否"}</Tag>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 120,
      sorter: true,
      render: (date) => formatDate(date),
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      key: "updated_at",
      width: 120,
      sorter: true,
      render: (date) => formatDate(date),
    },
    {
      title: "操作",
      key: "actions",
      width: 150,
      fixed: "right",
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

  // 计算当前页汇总数据
  const calculateSummary = () => {
    const items = data?.items || [];
    if (items.length === 0) return null;

    const summary = items.reduce(
      (acc, item) => {
        return {
          landArea: acc.landArea + (Number(item.land_area) || 0),
          actualArea: acc.actualArea + (Number(item.actual_property_area) || 0),
          rentableArea: acc.rentableArea + (Number(item.rentable_area) || 0),
          rentedArea: acc.rentedArea + (Number(item.rented_area) || 0),
        };
      },
      {
        landArea: 0,
        actualArea: 0,
        rentableArea: 0,
        rentedArea: 0,
      },
    );

    // 正确计算未出租面积和出租率
    const unrentedArea = summary.rentableArea - summary.rentedArea;
    const occupancyRate =
      summary.rentableArea > 0 ? (summary.rentedArea / summary.rentableArea) * 100 : 0;

    return {
      ...summary,
      unrentedArea,
      occupancyRate,
    };
  };

  const summary = calculateSummary();

  // 汇总行渲染函数
  const renderSummary = (_pageData: readonly Asset[]) => {
    if (!summary) return null;

    return (
      <Table.Summary fixed>
        <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={6} align="right">
            <strong>当前页合计：</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={6} align="right">
            <strong>{formatArea(summary.landArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={7} align="right">
            <strong>{formatArea(summary.actualArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={8} align="right">
            <strong>{formatArea(summary.rentableArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={9} align="right">
            <strong>{formatArea(summary.rentedArea)}</strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={10} colSpan={5} />
          <Table.Summary.Cell index={15} align="right">
            <strong
              style={{
                color:
                  summary.occupancyRate >= 80
                    ? "#52c41a"
                    : summary.occupancyRate >= 60
                      ? "#faad14"
                      : "#ff4d4f",
              }}
            >
              {formatPercentage(summary.occupancyRate)}
            </strong>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={16} colSpan={3} />
        </Table.Summary.Row>
      </Table.Summary>
    );
  };

  // 行选择配置
  const rowSelection = onSelectChange
    ? {
        selectedRowKeys,
        onChange: onSelectChange,
        getCheckboxProps: (record: Asset) => ({
          name: record.property_name,
        }),
      }
    : undefined;

  return (
    <Table
      columns={columns}
      dataSource={data?.items || []}
      rowKey="id"
      loading={loading}
      scroll={{ x: 1800, y: 600 }}
      rowSelection={rowSelection}
      summary={renderSummary}
      pagination={{
        current: data?.page || 1,
        pageSize: data?.limit || 20,
        total: data?.total || 0,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
        pageSizeOptions: ["10", "20", "50", "100"],
        size: "default",
      }}
      onChange={onTableChange as any}
      size="middle"
      bordered
      sticky={{ offsetHeader: 64 }}
    />
  );
};

export default AssetList;
