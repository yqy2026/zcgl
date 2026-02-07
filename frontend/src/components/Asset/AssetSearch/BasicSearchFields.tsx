import React from 'react';
import { Col, Form, Input, Select } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { DataStatus } from '@/types/asset';

const { Option } = Select;

interface BasicSearchFieldsProps {
  ownershipEntityOptions?: Array<{ value: string; label: string }>;
  businessCategoryOptions?: Array<{ value: string; label: string }>;
}

export const BasicSearchFields = React.memo(function BasicSearchFields({
  ownershipEntityOptions: _ownershipEntityOptions = [],
  businessCategoryOptions: _businessCategoryOptions = [],
}: BasicSearchFieldsProps) {
  return (
    <>
      <Col xs={24} sm={12} md={8} lg={6}>
        <Form.Item name="search" label="关键词搜索">
          <Input placeholder="输入物业名称、地址等关键词" prefix={<SearchOutlined />} allowClear />
        </Form.Item>
      </Col>

      <Col xs={24} sm={12} md={8} lg={6}>
        <Form.Item name="ownership_status" label="确权状态">
          <Select placeholder="选择确权状态" allowClear showSearch optionFilterProp="children">
            <Option value="已确权">已确权</Option>
            <Option value="未确权">未确权</Option>
            <Option value="部分确权">部分确权</Option>
            <Option value="无法确认业权">无法确认业权</Option>
          </Select>
        </Form.Item>
      </Col>

      <Col xs={24} sm={12} md={8} lg={6}>
        <Form.Item name="property_nature" label="物业性质">
          <Select placeholder="选择物业性质" allowClear showSearch optionFilterProp="children">
            <Option value="经营性">经营性</Option>
            <Option value="非经营性">非经营性</Option>
            <Option value="经营-外部">经营-外部</Option>
            <Option value="经营-内部">经营-内部</Option>
            <Option value="经营-租赁">经营-租赁</Option>
            <Option value="非经营类-公配">非经营类-公配</Option>
            <Option value="非经营类-其他">非经营类-其他</Option>
            <Option value="经营类">经营类</Option>
            <Option value="非经营类">非经营类</Option>
            <Option value="经营-配套">经营-配套</Option>
            <Option value="非经营-配套">非经营-配套</Option>
            <Option value="经营-配套镇">经营-配套镇</Option>
            <Option value="非经营-配套镇">非经营-配套镇</Option>
            <Option value="经营-处置类">经营-处置类</Option>
            <Option value="非经营-处置类">非经营-处置类</Option>
            <Option value="非经营-公配房">非经营-公配房</Option>
            <Option value="非经营类-配套">非经营类-配套</Option>
          </Select>
        </Form.Item>
      </Col>

      <Col xs={24} sm={12} md={8} lg={6}>
        <Form.Item name="usage_status" label="使用状态">
          <Select placeholder="选择使用状态" allowClear showSearch optionFilterProp="children">
            <Option value="出租">出租</Option>
            <Option value="空置">空置</Option>
            <Option value="自用">自用</Option>
            <Option value="公房">公房</Option>
            <Option value="其他">其他</Option>
            <Option value="转租">转租</Option>
            <Option value="公配">公配</Option>
            <Option value="空置规划">空置规划</Option>
            <Option value="空置预留">空置预留</Option>
            <Option value="配套">配套</Option>
            <Option value="空置配套">空置配套</Option>
            <Option value="空置配">空置配</Option>
            <Option value="待处置">待处置</Option>
            <Option value="待移交">待移交</Option>
            <Option value="闲置">闲置</Option>
          </Select>
        </Form.Item>
      </Col>

      <Col xs={24} sm={12} md={8} lg={6}>
        <Form.Item name="data_status" label="资产状态">
          <Select placeholder="选择资产状态" allowClear showSearch optionFilterProp="children">
            <Option value={DataStatus.NORMAL}>正常</Option>
            <Option value={DataStatus.DELETED}>回收站</Option>
            <Option value={DataStatus.ARCHIVED}>已归档</Option>
            <Option value={DataStatus.ABNORMAL}>异常</Option>
          </Select>
        </Form.Item>
      </Col>
    </>
  );
});
