import React, { useCallback, useMemo } from 'react';
import { List, Typography, Tag, Space, Button, Tooltip } from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  EnvironmentOutlined,
  UserOutlined,
  HomeOutlined,
} from '@ant-design/icons';

import type { Asset, AssetSearchParams } from '@/types/asset';
import { highlightText, extractSearchTerms } from '@/utils/highlight';
import { formatArea, getStatusColor } from '@/utils/format';
import { getIconButtonProps } from '@/utils/accessibility';
import styles from './AssetSearchResult.module.css';

const { Text, Paragraph } = Typography;

interface AssetSearchResultProps {
  assets: Asset[];
  searchParams: AssetSearchParams;
  loading?: boolean;
  onViewDetail: (asset: Asset) => void;
  onEdit: (asset: Asset) => void;
}

const AssetSearchResult: React.FC<AssetSearchResultProps> = ({
  assets,
  searchParams,
  loading = false,
  onViewDetail,
  onEdit,
}) => {
  // 提取搜索关键词
  const searchTermInput = searchParams.search ?? '';
  const searchTerms = useMemo(() => extractSearchTerms(searchTermInput), [searchTermInput]);

  // 高亮文本的辅助函数
  const highlightSearchText = useCallback(
    (text: string) => {
      if (searchTerms.length === 0) return text;
      return highlightText(text, searchTermInput);
    },
    [searchTermInput, searchTerms]
  );

  return (
    <List
      loading={loading}
      dataSource={assets}
      renderItem={asset => {
        const projectName = asset.project_name;
        const notes = asset.notes;
        const hasProjectName = projectName != null && projectName.trim() !== '';
        const hasNotes = notes != null && notes.trim() !== '';

        return (
          <List.Item
            key={asset.id}
            actions={[
              <Tooltip key="view" title="查看详情">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => onViewDetail(asset)}
                  {...getIconButtonProps('view', '资产')}
                />
              </Tooltip>,
              <Tooltip key="edit" title="编辑">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => onEdit(asset)}
                  {...getIconButtonProps('edit', '资产')}
                />
              </Tooltip>,
            ]}
          >
            <List.Item.Meta
              title={
                <Space>
                  <HomeOutlined className={styles.titleIcon} />
                  <Text strong className={styles.propertyTitle}>
                    {highlightSearchText(asset.property_name)}
                  </Text>
                  <Tag color={getStatusColor(asset.ownership_status, 'ownership')}>
                    {asset.ownership_status}
                  </Tag>
                  <Tag color={getStatusColor(asset.property_nature, 'property')}>
                    {asset.property_nature}
                  </Tag>
                  <Tag color={getStatusColor(asset.usage_status, 'usage')}>
                    {asset.usage_status}
                  </Tag>
                </Space>
              }
              description={
                <div>
                  {/* 地址信息 */}
                  <div className={styles.infoBlock}>
                    <Space>
                      <EnvironmentOutlined className={styles.mutedIcon} />
                      <Text type="secondary">{highlightSearchText(asset.address)}</Text>
                    </Space>
                  </div>

                  {/* 权属信息 */}
                  <div className={styles.infoBlock}>
                    <Space>
                      <UserOutlined className={styles.mutedIcon} />
                      <Text type="secondary">
                        权属方: {highlightSearchText(asset.ownership_entity ?? '')}
                      </Text>
                      {asset.management_entity != null && (
                        <>
                          <Text type="secondary">|</Text>
                          <Text type="secondary">
                            管理方: {highlightSearchText(asset.management_entity)}
                          </Text>
                        </>
                      )}
                    </Space>
                  </div>

                  {/* 面积信息 */}
                  <div className={styles.infoBlock}>
                    <Space wrap>
                      {asset.actual_property_area != null && (
                        <Text type="secondary">
                          实际面积: {formatArea(asset.actual_property_area)}
                        </Text>
                      )}
                      {asset.rentable_area != null && (
                        <Text type="secondary">可租面积: {formatArea(asset.rentable_area)}</Text>
                      )}
                      {asset.rented_area != null && (
                        <Text type="secondary">已租面积: {formatArea(asset.rented_area)}</Text>
                      )}
                      {asset.occupancy_rate != null && (
                        <Text type="secondary">出租率: {asset.occupancy_rate}</Text>
                      )}
                    </Space>
                  </div>

                  {/* 用途信息 */}
                  {(asset.certificated_usage != null ||
                    asset.actual_usage != null ||
                    asset.business_category != null) && (
                    <div className={styles.infoBlock}>
                      <Space wrap>
                        {asset.certificated_usage != null && (
                          <Text type="secondary">
                            证载用途: {highlightSearchText(asset.certificated_usage)}
                          </Text>
                        )}
                        {asset.actual_usage != null && (
                          <Text type="secondary">
                            实际用途: {highlightSearchText(asset.actual_usage)}
                          </Text>
                        )}
                        {asset.business_category != null && (
                          <Text type="secondary">
                            业态: {highlightSearchText(asset.business_category)}
                          </Text>
                        )}
                      </Space>
                    </div>
                  )}

                  {/* 承租方信息 */}
                  {asset.tenant_name != null && (
                    <div className={styles.infoBlock}>
                      <Text type="secondary">承租方: {highlightSearchText(asset.tenant_name)}</Text>
                    </div>
                  )}

                  {/* 特殊标记 */}
                  <div>
                    <Space>
                      {asset.is_litigated != null && <Tag color="red">涉诉</Tag>}
                      {asset.include_in_occupancy_rate != null && (
                        <Tag color="green">计入出租率</Tag>
                      )}
                      {hasProjectName && <Tag color="blue">{highlightSearchText(projectName)}</Tag>}
                    </Space>
                  </div>

                  {/* 描述信息 */}
                  {hasNotes && (
                    <div className={styles.notesBlock}>
                      <Paragraph
                        ellipsis={{ rows: 2, expandable: true, symbol: '展开' }}
                        className={styles.notesParagraph}
                      >
                        {highlightSearchText(notes)}
                      </Paragraph>
                    </div>
                  )}
                </div>
              }
            />
          </List.Item>
        );
      }}
    />
  );
};

export default React.memo(AssetSearchResult);
