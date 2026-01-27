import React from 'react';
import { Row, Col, Card, Input, Select, Button } from 'antd';
import { SearchOutlined, PlusOutlined } from '@ant-design/icons';
import { ContractStatus, ContractStatusLabels } from '@/types/rentContract';
import type { Asset } from '@/types/asset';
import type { Ownership } from '@/types/ownership';

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
    <Card style={{ marginBottom: '24px' }}>
      <Row gutter={16}>
        <Col span={6}>
          <Search
            placeholder="搜索合同编号或承租方"
            onSearch={value => onSearch({ keyword: value })}
            enterButton={<SearchOutlined />}
          />
        </Col>
        <Col span={4}>
          <Select
            placeholder="选择物业"
            style={{ width: '100%' }}
            allowClear
            onChange={value => onSearch({ asset_id: value })}
          >
            {assets.map(asset => (
              <Option key={asset.id} value={asset.id}>
                {asset.property_name}
              </Option>
            ))}
          </Select>
        </Col>
        <Col span={4}>
          <Select
            placeholder="选择权属方"
            style={{ width: '100%' }}
            allowClear
            onChange={value => onSearch({ ownership_id: value })}
          >
            {ownerships.map(ownership => (
              <Option key={ownership.id} value={ownership.id}>
                {ownership.name}
              </Option>
            ))}
          </Select>
        </Col>
        <Col span={4}>
          <Select
            placeholder="合同状态"
            style={{ width: '100%' }}
            allowClear
            onChange={value => onSearch({ contract_status: value })}
          >
            {Object.values(ContractStatus).map(status => (
              <Option key={status} value={status}>
                {ContractStatusLabels[status]}
              </Option>
            ))}
          </Select>
        </Col>
        <Col span={4}>
          <Button onClick={onReset}>重置</Button>
        </Col>
        <Col span={2}>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>
            新建合同
          </Button>
        </Col>
      </Row>
    </Card>
  );
};

export default ContractFilterBar;
