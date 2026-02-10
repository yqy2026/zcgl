import React from 'react';
import { Card, Input, Select, Button, Space } from 'antd';
import { SearchOutlined, PlusOutlined } from '@ant-design/icons';
import { ContractStatus, ContractStatusLabels } from '@/types/rentContract';
import type { Asset } from '@/types/asset';
import type { Ownership } from '@/types/ownership';
import { ListToolbar } from '@/components/Common/ListToolbar';
import styles from './ContractFilterBar.module.css';

const { Search } = Input;
const { Option } = Select;

interface ContractFilterBarProps {
  assets: Asset[];
  ownerships: Ownership[];
  onSearch: (values: Record<string, unknown>) => void;
  onReset: () => void;
  onCreate: () => void;
}

const ContractFilterBar: React.FC<ContractFilterBarProps> = ({
  assets,
  ownerships,
  onSearch,
  onReset,
  onCreate,
}) => {
  return (
    <Card className={styles.filterCard}>
      <ListToolbar
        variant="plain"
        gutter={[16, 16]}
        items={[
          {
            key: 'search',
            col: { xs: 24, sm: 12, lg: 6 },
            content: (
              <Search
                placeholder="搜索合同编号或承租方"
                onSearch={value => onSearch({ keyword: value })}
                enterButton={<SearchOutlined />}
                className={styles.filterControl}
              />
            ),
          },
          {
            key: 'asset',
            col: { xs: 24, sm: 12, lg: 4 },
            content: (
              <Select
                placeholder="选择物业"
                allowClear
                onChange={value => onSearch({ asset_id: value })}
                className={styles.filterControl}
              >
                {assets.map(asset => (
                  <Option key={asset.id} value={asset.id}>
                    {asset.property_name}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'ownership',
            col: { xs: 24, sm: 12, lg: 4 },
            content: (
              <Select
                placeholder="选择权属方"
                allowClear
                onChange={value => onSearch({ ownership_id: value })}
                className={styles.filterControl}
              >
                {ownerships.map(ownership => (
                  <Option key={ownership.id} value={ownership.id}>
                    {ownership.name}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'status',
            col: { xs: 24, sm: 12, lg: 4 },
            content: (
              <Select
                placeholder="合同状态"
                allowClear
                onChange={value => onSearch({ contract_status: value })}
                className={styles.filterControl}
              >
                {Object.values(ContractStatus).map(status => (
                  <Option key={status} value={status}>
                    {ContractStatusLabels[status]}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'actions',
            col: { xs: 24, sm: 12, lg: 6 },
            content: (
              <Space size={8} wrap className={styles.toolbarActions}>
                <Button onClick={onReset} className={styles.actionButton}>
                  重置
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={onCreate}
                  className={styles.actionButton}
                >
                  新建合同
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
};

export default ContractFilterBar;
