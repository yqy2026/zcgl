import React from 'react';
import { Table } from 'antd';
import type { Asset, AssetListResponse } from '@/types/asset';
import { formatArea, formatPercentage } from '@/utils/format';

/**
 * AssetSummary组件属性接口
 */
interface AssetSummaryProps {
  /** 资产列表数据 */
  data?: AssetListResponse;
}

/**
 * 计算当前页汇总数据
 * @param items 资产列表数据
 * @returns 汇总数据对象
 */
const calculateSummary = (items: Asset[] = []) => {
  if (items.length === 0) {
    return null;
  }

  const summary = items.reduce(
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
  const unrentedArea = summary.rentableArea - summary.rentedArea;
  const occupancyRate =
    summary.rentableArea > 0 ? (summary.rentedArea / summary.rentableArea) * 100 : 0;

  return {
    ...summary,
    unrentedArea,
    occupancyRate,
  };
};

/**
 * 资产汇总组件
 * 用于显示当前页资产数据的汇总信息
 */
const AssetSummary: React.FC<AssetSummaryProps> = ({ data }) => {
  const summary = calculateSummary(data?.items);

  if (!summary) {
    return null;
  }

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
                  ? '#52c41a'
                  : summary.occupancyRate >= 60
                    ? '#faad14'
                    : '#ff4d4f',
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

export default React.memo(AssetSummary);
