import React from 'react';
import { Card, Tag, Button, Space, Tooltip, Row, Col, Statistic, Progress } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  HistoryOutlined,
  EnvironmentOutlined,
  UserOutlined,
} from '@ant-design/icons';

import type { Asset } from '@/types/asset';
import {
  formatPercentage,
  formatDate,
  getStatusColor,
  calculateOccupancyRate,
} from '@/utils/format';
import { getOccupancyRateColor } from '@/styles/colorMap';
import styles from './AssetCard.module.css';

interface AssetCardProps {
  asset: Asset;
  onEdit: (asset: Asset) => void;
  onDelete: (id: string) => void;
  onView: (asset: Asset) => void;
  selected?: boolean;
  onSelect?: (asset: Asset, selected: boolean) => void;
}

const AssetCard: React.FC<AssetCardProps> = ({
  asset,
  onEdit,
  onDelete,
  onView,
  selected = false,
  onSelect,
}) => {
  // 计算出租率
  const occupancyRate =
    asset.occupancy_rate ?? calculateOccupancyRate(asset.rented_area, asset.rentable_area);
  const occupancyValueStyle: React.CSSProperties = {
    color: getOccupancyRateColor(occupancyRate),
  };

  return (
    <Card
      className={`asset-card ${selected ? 'selected' : ''} ${styles.card} ${selected ? styles.cardSelected : styles.cardDefault}`}
      hoverable
      onClick={() => onSelect?.(asset, !selected)}
      actions={[
        <Tooltip title="查看详情" key="view">
          <Button
            type="text"
            icon={<EyeOutlined />}
            aria-label="查看详情"
            onClick={e => {
              e.stopPropagation();
              onView(asset);
            }}
          />
        </Tooltip>,
        <Tooltip title="编辑" key="edit">
          <Button
            type="text"
            icon={<EditOutlined />}
            aria-label="编辑"
            onClick={e => {
              e.stopPropagation();
              onEdit(asset);
            }}
          />
        </Tooltip>,
        <Tooltip title="查看历史" key="history">
          <Button
            type="text"
            icon={<HistoryOutlined />}
            aria-label="查看历史"
            onClick={e => {
              e.stopPropagation();
              // 这里可以打开历史记录
            }}
          />
        </Tooltip>,
        <Tooltip title="删除" key="delete">
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            aria-label="删除"
            onClick={e => {
              e.stopPropagation();
              onDelete(asset.id);
            }}
          />
        </Tooltip>,
      ]}
    >
      {/* 卡片头部 */}
      <Card.Meta
        title={
          <div className={styles.metaTitle}>
            <span className={styles.propertyName}>{asset.property_name}</span>
            <Space>
              <Tag color={getStatusColor(asset.ownership_status, 'ownership')}>
                {asset.ownership_status}
              </Tag>
              <Tag color={getStatusColor(asset.property_nature, 'property')}>
                {asset.property_nature}
              </Tag>
            </Space>
          </div>
        }
        description={
          <div>
            <div className={styles.metaRow}>
              <EnvironmentOutlined className={styles.metaIcon} />
              <span className={styles.metaText}>{asset.address}</span>
            </div>
            <div className={styles.metaRow}>
              <UserOutlined className={styles.metaIcon} />
              <span className={styles.metaText}>权属方：{asset.ownership_entity}</span>
            </div>
          </div>
        }
      />

      {/* 卡片内容 */}
      <div className={styles.content}>
        {/* 面积信息 */}
        <Row gutter={16} className={styles.areaRow}>
          <Col span={6}>
            <Statistic title="土地面积" value={asset.land_area ?? 0} suffix="㎡" precision={2} />
          </Col>
          <Col span={6}>
            <Statistic
              title="实际面积"
              value={asset.actual_property_area ?? 0}
              suffix="㎡"
              precision={2}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="可出租面积"
              value={asset.rentable_area ?? 0}
              suffix="㎡"
              precision={2}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已出租面积"
              value={asset.rented_area ?? 0}
              suffix="㎡"
              precision={2}
            />
          </Col>
        </Row>

        {/* 出租率进度条 */}
        {(asset.rentable_area ?? 0) > 0 && (
          <div className={styles.occupancyContainer}>
            <div className={styles.occupancyHeader}>
              <span className={styles.occupancyLabel}>出租率</span>
              <span className={styles.occupancyValue} style={occupancyValueStyle}>
                {formatPercentage(occupancyRate)}
              </span>
            </div>
            <Progress
              percent={occupancyRate}
              strokeColor={getOccupancyRateColor(occupancyRate)}
              size="small"
              showInfo={false}
            />
          </div>
        )}

        {/* 状态标签 */}
        <div className={styles.statusSection}>
          <Space wrap>
            <Tag color={getStatusColor(asset.usage_status, 'usage')}>{asset.usage_status}</Tag>
            {asset.is_litigated == true && <Tag color="red">涉诉</Tag>}
            {(asset.certificated_usage?.trim() ?? '') !== '' && (
              <Tag color="blue">证载：{asset.certificated_usage}</Tag>
            )}
            {(asset.actual_usage?.trim() ?? '') !== '' &&
              asset.actual_usage !== asset.certificated_usage && (
                <Tag color="orange">实际：{asset.actual_usage}</Tag>
              )}
          </Space>
        </div>

        {/* 时间信息 */}
        <div className={styles.timeInfo}>
          <div>创建时间：{formatDate(asset.created_at)}</div>
          <div>更新时间：{formatDate(asset.updated_at)}</div>
        </div>
      </div>
    </Card>
  );
};

export default AssetCard;
