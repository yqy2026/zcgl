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
import { UploadOutlined, DeleteOutlined, EyeOutlined, InfoCircleOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import { DictionarySelect } from '@/components/Dictionary';
import { useAssetFormContext } from './AssetFormContext';
import { generateFormFieldIds } from '@/utils/accessibility';
import styles from './AssetDetailedSection.module.css';

const { Option } = Select;
const { TextArea } = Input;
const { Title } = Typography;

/**
 * AssetForm - Detailed Information Section
 * Fields: tenant info, contract info, terminal contracts
 */
const AssetDetailedSection: React.FC = () => {
  const { showAdvanced, setShowAdvanced, terminalContractFileList, setTerminalContractFileList } =
    useAssetFormContext();

  // 为字段生成可访问性 ID
  const tenantNameIds = generateFormFieldIds('tenant-name');
  const tenantContactIds = generateFormFieldIds('tenant-contact');
  const contractNumberIds = generateFormFieldIds('contract-number');
  const contractStartDateIds = generateFormFieldIds('contract-start-date');
  const contractEndDateIds = generateFormFieldIds('contract-end-date');
  const monthlyRentIds = generateFormFieldIds('monthly-rent');
  const depositIds = generateFormFieldIds('deposit');
  const isSubleaseIds = generateFormFieldIds('is-sublease');
  const subleaseNotesIds = generateFormFieldIds('sublease-notes');
  const terminalContractIds = generateFormFieldIds('terminal-contract');

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
          <Switch
            checked={showAdvanced}
            onChange={setShowAdvanced}
            size="small"
            aria-label="显示高级选项"
          />
        </Space>
      }
      className={styles.sectionCard}
    >
      {showAdvanced && (
        <>
          {/* Lessee Info */}
          <Title level={5}>
            承租方信息
            <Tooltip title="承租方信息来自合同管理模块，只能查看不能编辑">
              <InfoCircleOutlined className={styles.infoIcon} />
            </Tooltip>
          </Title>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="承租方名称" name="tenant_name" htmlFor={tenantNameIds.inputId}>
                <Input
                  id={tenantNameIds.inputId}
                  placeholder="自动从合同获取"
                  readOnly
                  aria-label={tenantNameIds.labelId}
                  aria-readonly="true"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="租户联系方式"
                name="tenant_contact"
                htmlFor={tenantContactIds.inputId}
              >
                <Input
                  id={tenantContactIds.inputId}
                  placeholder="自动从合同获取"
                  readOnly
                  aria-label={tenantContactIds.labelId}
                  aria-readonly="true"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="承租方类型" name="tenant_type">
                <DictionarySelect dictType="tenant_type" placeholder="自动从合同获取" disabled />
              </Form.Item>
            </Col>
          </Row>

          {/* Contract Info */}
          <Title level={5}>
            合同信息
            <Tooltip title="合同信息来自合同管理模块，只能查看不能编辑">
              <InfoCircleOutlined className={styles.infoIcon} />
            </Tooltip>
          </Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="租赁合同编号"
                name="lease_contract_number"
                htmlFor={contractNumberIds.inputId}
              >
                <Input
                  id={contractNumberIds.inputId}
                  placeholder="自动从合同获取"
                  readOnly
                  aria-label={contractNumberIds.labelId}
                  aria-readonly="true"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="合同开始日期"
                name="contract_start_date"
                htmlFor={contractStartDateIds.inputId}
              >
                <DatePicker
                  className={styles.fullWidthControl}
                  disabled
                  id={contractStartDateIds.inputId}
                  aria-label={contractStartDateIds.labelId}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="合同结束日期"
                name="contract_end_date"
                htmlFor={contractEndDateIds.inputId}
              >
                <DatePicker
                  className={styles.fullWidthControl}
                  disabled
                  id={contractEndDateIds.inputId}
                  aria-label={contractEndDateIds.labelId}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="月租金(元)" name="monthly_rent" htmlFor={monthlyRentIds.inputId}>
                <InputNumber
                  id={monthlyRentIds.inputId}
                  placeholder="自动从合同获取"
                  className={styles.fullWidthControl}
                  min={0}
                  precision={2}
                  disabled
                  aria-label={monthlyRentIds.labelId}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="押金(元)" name="deposit" htmlFor={depositIds.inputId}>
                <InputNumber
                  id={depositIds.inputId}
                  placeholder="自动从合同获取"
                  className={styles.fullWidthControl}
                  min={0}
                  precision={2}
                  disabled
                  aria-label={depositIds.labelId}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="是否分租/转租" name="is_sublease" htmlFor={isSubleaseIds.inputId}>
                <Select
                  id={isSubleaseIds.inputId}
                  placeholder="请选择"
                  disabled
                  aria-label={isSubleaseIds.labelId}
                >
                  <Option value={false}>否</Option>
                  <Option value={true}>是</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="分租/转租备注"
                name="sublease_notes"
                htmlFor={subleaseNotesIds.inputId}
              >
                <TextArea
                  id={subleaseNotesIds.inputId}
                  rows={2}
                  placeholder="请输入分租/转租备注"
                  aria-label={subleaseNotesIds.labelId}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* Terminal Contract Files */}
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="终端合同文件"
                name="terminal_contract_files"
                htmlFor={terminalContractIds.inputId}
              >
                <div>
                  <Upload {...terminalContractUploadProps}>
                    <Button icon={<UploadOutlined />} aria-label="上传PDF终端合同文件">
                      上传PDF终端合同文件
                    </Button>
                  </Upload>
                  <div className={styles.uploadHintText} role="note" aria-label="文件上传说明">
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
                              aria-label={`查看终端合同文件: ${file.name}`}
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
                              aria-label={`删除终端合同文件: ${file.name}`}
                            >
                              删除
                            </Button>,
                          ]}
                        >
                          <List.Item.Meta
                            avatar={<Tag color="green">PDF</Tag>}
                            title={<span aria-label={`文件名: ${file.name}`}>{file.name}</span>}
                            description={`文件大小: ${file.size != null ? (file.size / 1024 / 1024).toFixed(2) + 'MB' : '未知'}`}
                          />
                        </List.Item>
                      )}
                      className={styles.terminalContractList}
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

export default AssetDetailedSection;
