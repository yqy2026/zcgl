import React, { useMemo } from 'react';
import { Card, Form, Select, Checkbox, Button, Space, Alert, Divider, Row, Col, Tag, Typography } from 'antd';
import { DownloadOutlined, FileExcelOutlined, HistoryOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd/es/form';

import type { AssetSearchParams } from '@/types/asset';
import type { ExportFieldOption } from './assetExportConfig';

const { Option } = Select;
const { Text } = Typography;

interface AssetExportFormProps {
  form: FormInstance;
  availableFields: ExportFieldOption[];
  selectedAssetIds?: string[];
  searchParams?: AssetSearchParams;
  isExporting: boolean;
  onExport: () => void;
  onShowHistory: () => void;
  children?: React.ReactNode;
}

const AssetExportForm: React.FC<AssetExportFormProps> = ({
  form,
  availableFields,
  selectedAssetIds,
  searchParams,
  isExporting,
  onExport,
  onShowHistory,
  children,
}) => {
  const defaultSelectedFields = useMemo(
    () => availableFields.filter(field => field.required === true).map(field => field.key),
    [availableFields]
  );

  return (
    <Card
      title={
        <Space>
          <FileExcelOutlined />
          数据导出
          {selectedAssetIds !== undefined &&
            selectedAssetIds !== null &&
            selectedAssetIds.length > 0 && (
              <Tag color="blue">已选择 {selectedAssetIds.length} 条记录</Tag>
            )}
        </Space>
      }
      extra={
        <Button icon={<HistoryOutlined />} onClick={onShowHistory}>
          导出历史
        </Button>
      }
      style={{ marginBottom: 16 }}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          format: 'xlsx',
          includeHeaders: true,
          selectedFields: defaultSelectedFields,
        }}
      >
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8}>
            <Form.Item name="format" label="导出格式">
              <Select>
                <Option value="xlsx">Excel (.xlsx)</Option>
                <Option value="csv">CSV (.csv)</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8}>
            <Form.Item name="includeHeaders" valuePropName="checked">
              <Checkbox>包含表头</Checkbox>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="selectedFields" label="选择导出字段">
          <Checkbox.Group style={{ width: '100%' }}>
            <Row gutter={[16, 8]}>
              {availableFields.map(field => (
                <Col xs={24} sm={12} md={8} lg={6} key={field.key}>
                  <Checkbox value={field.key} disabled={field.required}>
                    {field.label}
                    {field.required === true && <Text type="secondary"> *</Text>}
                  </Checkbox>
                </Col>
              ))}
            </Row>
          </Checkbox.Group>
        </Form.Item>

        {/* 筛选条件预览 */}
        {(searchParams !== undefined ||
          (selectedAssetIds !== undefined &&
            selectedAssetIds !== null &&
            selectedAssetIds.length > 0)) && (
          <div>
            <Divider titlePlacement="start">导出范围</Divider>

            {selectedAssetIds !== undefined &&
            selectedAssetIds !== null &&
            selectedAssetIds.length > 0 ? (
              <Alert
                message={`将导出已选择的 ${selectedAssetIds.length} 条资产记录`}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            ) : (
              searchParams && (
                <Alert
                  message="将根据当前搜索条件导出匹配的资产记录"
                  description={
                    <div style={{ marginTop: 8 }}>
                      <Space wrap>
                        {Object.entries(searchParams).map(([key, value]) => {
                          if (value === undefined || value === null || value === '') {
                            return null;
                          }

                          const fieldNames: Record<string, string> = {
                            search: '关键词',
                            ownership_status: '确权状态',
                            property_nature: '物业性质',
                            usage_status: '使用状态',
                            ownership_entity: '权属方',
                            management_entity: '管理方',
                            business_category: '业态类别',
                          };

                          const displayKey = fieldNames[key] || key;
                          const displayValue =
                            typeof value === 'boolean' ? (value ? '是' : '否') : String(value);

                          return (
                            <Tag key={key}>
                              {displayKey}: {displayValue}
                            </Tag>
                          );
                        })}
                      </Space>
                    </div>
                  }
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )
            )}
          </div>
        )}

        <Form.Item>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={onExport}
            loading={isExporting}
            size="large"
          >
            开始导出
          </Button>
        </Form.Item>
      </Form>

      {children}
    </Card>
  );
};

export default React.memo(AssetExportForm);
