import React from 'react';
import { Row, Col, Typography, Select, Input } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { ownershipService } from '@/services/ownershipService';
import { useAnalyticsFiltersContext } from './FiltersContext';
import styles from './Filters.module.css';

const { Text } = Typography;
const { Option } = Select;

/**
 * Filter controls: area range, rent range, operation status, business category, etc.
 */
const FiltersSection: React.FC = () => {
  const { localFilters, handleFilterChange, loading, showAdvanced } = useAnalyticsFiltersContext();
  const { data: ownershipOptions = [], isLoading: ownershipLoading } = useQuery({
    queryKey: ['ownership-select-options'],
    queryFn: () => ownershipService.getOwnershipSelectOptions(),
    staleTime: 30 * 60 * 1000,
  });

  if (!showAdvanced) {
    return null;
  }

  return (
    <Row gutter={[16, 16]} className={styles.advancedFiltersRow}>
      <Col xs={24} md={8}>
        <Text strong className={styles.fieldLabel}>
          面积范围 (㎡):
        </Text>
        <Input.Group compact className={styles.rangeGroup}>
          <Input
            className={styles.halfWidthInput}
            placeholder="最小面积"
            type="number"
            value={localFilters.min_area}
            onChange={e =>
              handleFilterChange('min_area', e.target.value ? Number(e.target.value) : undefined)
            }
          />
          <Input
            className={styles.halfWidthInput}
            placeholder="最大面积"
            type="number"
            value={localFilters.max_area}
            onChange={e =>
              handleFilterChange('max_area', e.target.value ? Number(e.target.value) : undefined)
            }
          />
        </Input.Group>
      </Col>

      <Col xs={24} md={8}>
        <Text strong className={styles.fieldLabel}>
          租金范围 (元):
        </Text>
        <Input.Group compact className={styles.rangeGroup}>
          <Input
            className={styles.halfWidthInput}
            placeholder="最小租金"
            type="number"
            value={localFilters.min_rent}
            onChange={e =>
              handleFilterChange('min_rent', e.target.value ? Number(e.target.value) : undefined)
            }
          />
          <Input
            className={styles.halfWidthInput}
            placeholder="最大租金"
            type="number"
            value={localFilters.max_rent}
            onChange={e =>
              handleFilterChange('max_rent', e.target.value ? Number(e.target.value) : undefined)
            }
          />
        </Input.Group>
      </Col>

      <Col xs={24} md={8}>
        <Text strong className={styles.fieldLabel}>
          管理状态:
        </Text>
        <Select
          className={styles.fieldControl}
          placeholder="请选择管理状态"
          allowClear
          value={localFilters.operation_status}
          onChange={value => handleFilterChange('operation_status', value)}
          loading={loading}
        >
          <Option value="正常运营">正常运营</Option>
          <Option value="维护中">维护中</Option>
          <Option value="整改中">整改中</Option>
          <Option value="暂停运营">暂停运营</Option>
        </Select>
      </Col>

      <Col xs={24} md={8}>
        <Text strong className={styles.fieldLabel}>
          业态类别:
        </Text>
        <Select
          className={styles.fieldControl}
          placeholder="请选择业态类别"
          allowClear
          value={localFilters.business_category}
          onChange={value => handleFilterChange('business_category', value)}
          loading={loading}
        >
          <Option value="零售">零售</Option>
          <Option value="餐饮">餐饮</Option>
          <Option value="办公">办公</Option>
          <Option value="仓储">仓储</Option>
          <Option value="工业">工业</Option>
          <Option value="其他">其他</Option>
        </Select>
      </Col>

      <Col xs={24} md={8}>
        <Text strong className={styles.fieldLabel}>
          承租方类型:
        </Text>
        <Select
          className={styles.fieldControl}
          placeholder="请选择承租方类型"
          allowClear
          value={localFilters.tenant_type}
          onChange={value => handleFilterChange('tenant_type', value)}
          loading={loading}
        >
          <Option value="企业">企业</Option>
          <Option value="个人">个人</Option>
          <Option value="政府">政府</Option>
          <Option value="事业单位">事业单位</Option>
          <Option value="其他">其他</Option>
        </Select>
      </Col>

      <Col xs={24} md={8}>
        <Text strong className={styles.fieldLabel}>
          权属主体:
        </Text>
        <Select
          className={styles.fieldControl}
          placeholder="请选择权属主体"
          allowClear
          value={localFilters.owner_party_id}
          onChange={value => handleFilterChange('owner_party_id', value)}
          loading={loading || ownershipLoading}
          options={ownershipOptions}
        ></Select>
      </Col>
    </Row>
  );
};

export default FiltersSection;
