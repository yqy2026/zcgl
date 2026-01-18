import React from 'react';
import {
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  Button,
  Upload,
  List,
  Tag,
  Row,
  Col,
  Card,
  Typography,
  Tooltip,
  Space,
  Switch,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { COLORS } from '@/styles/colorMap';
import { UploadOutlined, DeleteOutlined, EyeOutlined, InfoCircleOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import GroupedSelectSingle from '../../Common/GroupedSelect';
import { TenantTypeOptions } from '../../../utils/enumHelpers';
import { useAssetFormContext } from './AssetFormContext';

const { Option } = Select;
const { TextArea } = Input;
const { Title } = Typography;

/**
 * AssetForm - Advanced Options Section
 * Fields: tenant info, contract info, terminal contracts
 */
const AssetAdvancedSection: React.FC = () => {
  const {
    showAdvanced,
    setShowAdvanced,
    terminalContractFileList,
    setTerminalContractFileList,
    rentContracts,
    loadingContracts,
    handleContractChange,
  } = useAssetFormContext();

  const terminalContractUploadProps: UploadProps = {
    multiple: true,
    accept: '.pdf',
    beforeUpload: (file: File) => {
      const isPDF = file.type === 'application/pdf';
      if (!isPDF) {
        MessageManager.error('只能上传PDF文件');
        return false;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        MessageManager.error('文件大小不能超过10MB');
        return false;
      }
      return false;
    },
    onChange: (info: { fileList: UploadFile[] }) => {
      setTerminalContractFileList(info.fileList);
    },
    fileList: terminalContractFileList,
  };

  return (
    <Card
      title={
        <Space>
          <span>高级选项</span>
          <Switch checked={showAdvanced} onChange={setShowAdvanced} size="small" />
        </Space>
      }
      style={{ marginBottom: '16px' }}
    >
      {showAdvanced && (
        <>
          {/* Tenant Info */}
          <Title level={5}>
            租户信息
            <Tooltip title="租户信息来自合同管理模块，只能查看不能编辑">
              <InfoCircleOutlined style={{ marginLeft: 8, color: COLORS.textSecondary }} />
            </Tooltip>
          </Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="选择租赁合同" name="selected_contract_id">
                <Select
                  placeholder="请选择租赁合同"
                  allowClear
                  loading={loadingContracts}
                  onChange={handleContractChange}
                  optionFilterProp="children"
                  showSearch
                  filterOption={(input, option) =>
                    (option?.children as unknown as string)
                      ?.toLowerCase()
                      .includes(input.toLowerCase())
                  }
                >
                  {rentContracts.map(contract => (
                    <Option key={contract.id} value={contract.id}>
                      {contract.contract_number} - {contract.tenant_name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="租户名称" name="tenant_name">
                <Input placeholder="自动从合同获取" readOnly />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="租户联系方式" name="tenant_contact">
                <Input placeholder="自动从合同获取" readOnly />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="租户类型" name="tenant_type">
                <GroupedSelectSingle
                  groups={[{ label: '租户类型', options: TenantTypeOptions }]}
                  placeholder="自动从合同获取"
                  disabled
                  showGroupLabel={false}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* Contract Info */}
          <Title level={5}>
            合同信息
            <Tooltip title="合同信息来自合同管理模块，只能查看不能编辑">
              <InfoCircleOutlined style={{ marginLeft: 8, color: COLORS.textSecondary }} />
            </Tooltip>
          </Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="租赁合同编号" name="lease_contract_number">
                <Input placeholder="自动从合同获取" readOnly />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="合同开始日期" name="contract_start_date">
                <DatePicker style={{ width: '100%' }} disabled />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="合同结束日期" name="contract_end_date">
                <DatePicker style={{ width: '100%' }} disabled />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="月租金(元)" name="monthly_rent">
                <InputNumber
                  placeholder="自动从合同获取"
                  style={{ width: '100%' }}
                  min={0}
                  precision={2}
                  disabled
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="押金(元)" name="deposit">
                <InputNumber
                  placeholder="自动从合同获取"
                  style={{ width: '100%' }}
                  min={0}
                  precision={2}
                  disabled
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="是否分租/转租" name="is_sublease">
                <Select placeholder="请选择" disabled>
                  <Option value={false}>否</Option>
                  <Option value={true}>是</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item label="分租/转租备注" name="sublease_notes">
                <TextArea rows={2} placeholder="请输入分租/转租备注" />
              </Form.Item>
            </Col>
          </Row>

          {/* Terminal Contract Files */}
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item label="终端合同文件" name="terminal_contract_files">
                <div>
                  <Upload {...terminalContractUploadProps}>
                    <Button icon={<UploadOutlined />}>上传PDF终端合同文件</Button>
                  </Upload>
                  <div style={{ marginTop: 8, fontSize: 12, color: COLORS.textSecondary }}>
                    支持多文件上传，每个文件不超过10MB，仅支持PDF格式
                  </div>
                  {terminalContractFileList.length > 0 && (
                    <List
                      size="small"
                      header={<div>已选择的终端合同文件</div>}
                      bordered
                      dataSource={terminalContractFileList}
                      renderItem={(file: UploadFile) => (
                        <List.Item
                          actions={[
                            <Button
                              key="view"
                              type="link"
                              size="small"
                              icon={<EyeOutlined />}
                              onClick={() => {
                                if (file.url != null) {
                                  window.open(file.url, '_blank');
                                }
                              }}
                            >
                              查看
                            </Button>,
                            <Button
                              key="delete"
                              type="link"
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => {
                                setTerminalContractFileList(
                                  terminalContractFileList.filter(f => f.uid !== file.uid)
                                );
                              }}
                            >
                              删除
                            </Button>,
                          ]}
                        >
                          <List.Item.Meta
                            avatar={<Tag color="green">PDF</Tag>}
                            title={file.name}
                            description={`文件大小: ${file.size != null ? (file.size / 1024 / 1024).toFixed(2) + 'MB' : '未知'}`}
                          />
                        </List.Item>
                      )}
                      style={{ marginTop: 16 }}
                    />
                  )}
                </div>
              </Form.Item>
            </Col>
          </Row>
        </>
      )}
    </Card>
  );
};

export default AssetAdvancedSection;
