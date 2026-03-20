import React, { useMemo } from 'react';
import {
  Badge,
  Button,
  Card,
  Col,
  Input,
  Row,
  Select,
  Space,
  Tag,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { EnumFieldType, EnumFieldValue } from '@/services/dictionary';
import EnumValuePreview from '@/components/Dictionary/EnumValuePreview';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import styles from './DictionaryPage.module.css';

const { Option } = Select;
const { Search } = Input;

export interface EnumFieldWithType {
  type: EnumFieldType;
  values: EnumFieldValue[];
}

export interface OverviewFilters {
  keyword: string;
  category: string;
}

const resolveText = (value: string | null | undefined, fallback: string): string => {
  if (value == null) {
    return fallback;
  }
  const normalizedValue = value.trim();
  return normalizedValue !== '' ? normalizedValue : fallback;
};

interface DictionaryListProps {
  enumTypes: EnumFieldType[];
  overviewData: EnumFieldWithType[];
  overviewLoading: boolean;
  overviewPagination: PaginationState;
  overviewFilters: OverviewFilters;
  categories: string[];
  activeType: string | undefined;
  onActiveTypeChange: (value?: string) => void;
  onApplyOverviewFilters: (filters: OverviewFilters) => void;
  onUpdateOverviewPagination: (pagination: { current?: number; pageSize?: number }) => void;
  onViewDetail: (typeCode: string) => void;
  onRefresh: () => void;
}

const DictionaryList: React.FC<DictionaryListProps> = ({
  enumTypes,
  overviewData,
  overviewLoading,
  overviewPagination,
  overviewFilters,
  categories,
  activeType,
  onActiveTypeChange,
  onApplyOverviewFilters,
  onUpdateOverviewPagination,
  onViewDetail,
  onRefresh,
}) => {
  const overviewColumns: ColumnsType<EnumFieldWithType> = useMemo(
    () => [
      {
        title: '类型名称',
        dataIndex: ['type', 'name'],
        width: 200,
        render: (name: string, record) => (
          <div className={styles.typeNameCell}>
            <div className={styles.typeName}>{name}</div>
            <div className={styles.typeCode}>
              <Tag className={[styles.codeTag, styles.tonePrimary].join(' ')}>
                {record.type.code}
              </Tag>
            </div>
          </div>
        ),
      },
      {
        title: '分类',
        dataIndex: ['type', 'category'],
        width: 120,
        render: (category: string) => resolveText(category, '未分类'),
      },
      {
        title: '描述',
        dataIndex: ['type', 'description'],
        width: 200,
        ellipsis: true,
        render: (desc: string) => resolveText(desc, '-'),
      },
      {
        title: '枚举值预览',
        width: 300,
        render: (_, record) => (
          <EnumValuePreview
            values={record.values}
            maxDisplay={3}
            size="small"
            showInactiveCount={true}
          />
        ),
      },
      {
        title: '操作',
        key: 'action',
        width: 100,
        render: (_, record) => (
          <Button
            type="text"
            size="small"
            className={styles.viewDetailButton}
            onClick={() => onViewDetail(record.type.code)}
            aria-label={`查看类型 ${record.type.name}`}
          >
            查看详情
          </Button>
        ),
      },
    ],
    [onViewDetail]
  );

  return (
    <Card
      title={
        <Space>
          <span>枚举值字段管理</span>
          <Badge count={enumTypes.length} showZero />
        </Space>
      }
      extra={
        <Space>
          <Button className={styles.refreshButton} onClick={onRefresh}>
            刷新
          </Button>
        </Space>
      }
    >
      {/* 搜索和筛选区域 */}
      <Row gutter={[16, 16]} className={styles.filtersRow}>
        <Col xs={24} md={10} xl={8}>
          <Search
            placeholder="搜索枚举类型或值"
            value={overviewFilters.keyword}
            onChange={e =>
              onApplyOverviewFilters({ ...overviewFilters, keyword: e.target.value })
            }
            prefix={<SearchOutlined />}
            allowClear
          />
        </Col>
        <Col xs={24} md={7} xl={6}>
          <Select
            placeholder="选择分类"
            value={overviewFilters.category}
            onChange={value =>
              onApplyOverviewFilters({ ...overviewFilters, category: value })
            }
            className={styles.fullWidthControl}
          >
            {categories.map(cat => (
              <Option key={cat} value={cat}>
                {cat === 'all' ? '全部分类' : cat}
              </Option>
            ))}
          </Select>
        </Col>
        <Col xs={24} md={7} xl={6}>
          <Select
            placeholder="选择字典类型"
            value={activeType}
            onChange={onActiveTypeChange}
            className={styles.fullWidthControl}
            allowClear
          >
            {enumTypes.map(t => (
              <Option key={t.code} value={t.code}>
                {t.name} ({t.code})
              </Option>
            ))}
          </Select>
        </Col>
        <Col xs={24} xl={4}>
          <div className={styles.typeTotal}>
            <span className={styles.typeTotalText}>
              共 {overviewPagination.total} 个类型
            </span>
          </div>
        </Col>
      </Row>

      {/* 列表视图 */}
      <TableWithPagination
        rowKey={record => record.type.id}
        loading={overviewLoading}
        columns={overviewColumns}
        dataSource={overviewData}
        paginationState={overviewPagination}
        onPageChange={onUpdateOverviewPagination}
        paginationProps={{
          showSizeChanger: false,
          showQuickJumper: false,
          showTotal: (total: number, range: [number, number]) =>
            `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        }}
        scroll={{ x: 1200 }}
        size="middle"
      />
    </Card>
  );
};

export default DictionaryList;
