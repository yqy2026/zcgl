import React from 'react';
import { Card, Tag, Space, Button, Typography, Progress, Tooltip } from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  EnvironmentOutlined,
  BuildOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { Asset } from '@/types/asset';
import { PropertyNature } from '@/types/asset';
import { COLORS } from '@/styles/colorMap';
import styles from './AssetCard.module.css';

const { Text, Title } = Typography;
const { Meta } = Card;

interface AssetCardProps {
  asset: Asset;
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

const AssetCard: React.FC<AssetCardProps> = ({ asset, onView, onEdit, onDelete }) => {
  const occupancyRate = asset.occupancy_rate ?? 0;

  const getOccupancyColor = (rate: number) => {
    if (rate > 80) {
      return COLORS.success;
    }
    if (rate > 50) {
      return COLORS.warning;
    }
    return COLORS.error;
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      出租: 'success',
      闲置: 'warning',
      自用: 'processing',
      公房: 'default',
      其他: 'default',
    };
    return colorMap[status] || 'default';
  };

  const getOwnershipColor = (status: string) => {
    const colorMap: Record<string, string> = {
      已确权: 'success',
      未确权: 'error',
      部分确权: 'warning',
    };
    return colorMap[status] || 'default';
  };

  return (
    <Card
      hoverable
      actions={[
        <Tooltip title="查看详情" key="view">
          <Button type="text" icon={<EyeOutlined />} onClick={onView} />
        </Tooltip>,
        <Tooltip title="编辑" key="edit">
          <Button type="text" icon={<EditOutlined />} onClick={onEdit} />
        </Tooltip>,
        <Tooltip title="删除" key="delete">
          <Button type="text" danger icon={<DeleteOutlined />} onClick={onDelete} />
        </Tooltip>,
      ]}
    >
      <Meta
        title={
          <div>
            <Title level={5} className={styles.cardTitle}>
              {asset.property_name}
            </Title>
            <Space wrap>
              <Tag color={asset.property_nature === PropertyNature.COMMERCIAL ? 'green' : 'blue'}>
                {String(asset.property_nature)}
              </Tag>
              <Tag color={getStatusColor(asset.usage_status)}>{asset.usage_status}</Tag>
              <Tag color={getOwnershipColor(asset.ownership_status)}>{asset.ownership_status}</Tag>
            </Space>
          </div>
        }
        description={
          <div className={styles.cardDescription}>
            {/* 地址信息 */}
            <div className={styles.addressRow}>
              <Space>
                <EnvironmentOutlined className={styles.detailIcon} />
                <Text type="secondary" className={styles.detailText}>
                  {asset.address}
                </Text>
              </Space>
            </div>

            {/* 权属方 */}
            <div className={styles.ownershipRow}>
              <Space>
                <UserOutlined className={styles.detailIcon} />
                <Text type="secondary" className={styles.detailText}>
                  {asset.ownership_entity}
                </Text>
              </Space>
            </div>

            {/* 面积信息 */}
            <div className={styles.areaRow}>
              <Space>
                <BuildOutlined className={styles.detailIcon} />
                <Text type="secondary" className={styles.detailText}>
                  总面积: {asset.actual_property_area}㎡ | 可租: {asset.rentable_area}㎡ | 已租:{' '}
                  {asset.rented_area}㎡
                </Text>
              </Space>
            </div>

            {/* 出租率 */}
            <div>
              <div className={styles.occupancyHeader}>
                <div className={styles.occupancyHeaderRow}>
                  <Text className={styles.occupancyLabel}>出租率</Text>
                  <Text
                    strong
                    className={styles.occupancyValue}
                    style={{
                      color: getOccupancyColor(occupancyRate),
                    }}
                  >
                    {occupancyRate.toFixed(1)}%
                  </Text>
                </div>
              </div>
              <Progress
                percent={occupancyRate}
                strokeColor={getOccupancyColor(occupancyRate)}
                size="small"
                showInfo={false}
              />
            </div>
          </div>
        }
      />
    </Card>
  );
};

export default AssetCard;
