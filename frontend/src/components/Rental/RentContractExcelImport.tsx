/**
 * 租金合同Excel导入导出组件
 */

import React, { useState } from 'react';
import {
  Button,
  Upload,
  Modal,
  Form,
  Switch,
  Checkbox,
  DatePicker,
  Space,
  Alert,
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  Divider,
  List,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  DownloadOutlined,
  ExportOutlined,
  FileExcelOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { rentContractExcelService, ExcelImportResult } from '../../services/rentContractExcelService';

const { Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;

import { createLogger } from '../../utils/logger';
const componentLogger = createLogger('RentContractExcelImport');

interface RentContractExcelImportProps {
  onImportSuccess?: () => void;
  className?: string;
}

const RentContractExcelImport: React.FC<RentContractExcelImportProps> = ({
  onImportSuccess,
  className,
}) => {
  const [form] = Form.useForm();
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResult, setImportResult] = useState<ExcelImportResult | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [importOptions, setImportOptions] = useState({
    import_terms: true,
    import_ledger: false,
    overwrite_existing: false,
  });

  // 处理文件上传
  const handleFileUpload = async (file: File) => {
    try {
      setImporting(true);
      setImportResult(null);

      const result = await rentContractExcelService.handleFileUpload(file, {
        ...importOptions,
        onSuccess: (result) => {
          setImportResult(result);
          if (result.success) {
            MessageManager.success(rentContractExcelService.getImportSuccessSummary(result));
            if (onImportSuccess !== undefined && onImportSuccess !== null) {
              onImportSuccess();
            }
          } else {
            MessageManager.error(result.message);
          }
        },
        onError: (error) => {
          MessageManager.error(error.message);
        },
      });

      return result;
    } catch (error) {
      componentLogger.error('导入失败:', error as Error);
      MessageManager.error('导入失败，请重试');
      return null;
    } finally {
      setImporting(false);
      setFileList([]);
    }
  };

  // 处理导出
  const handleExport = async () => {
    try {
      const values = await form.validateFields();
      setExporting(true);

      await rentContractExcelService.exportAndDownload({
        start_date: values.date_range?.[0]?.format('YYYY-MM-DD'),
        end_date: values.date_range?.[1]?.format('YYYY-MM-DD'),
        include_terms: values.include_terms,
        include_ledger: values.include_ledger,
      });

      MessageManager.success('导出成功');
      setExportModalVisible(false);
      form.resetFields();
    } catch (error) {
      componentLogger.error('导出失败:', error as Error);
      MessageManager.error('导出失败，请重试');
    } finally {
      setExporting(false);
    }
  };

  // 下载模板
  const handleDownloadTemplate = async () => {
    try {
      await rentContractExcelService.downloadTemplateFile();
      MessageManager.success('模板下载成功');
    } catch {
      MessageManager.error('模板下载失败，请重试');
    }
  };

  // 上传组件配置
  const uploadProps = {
    accept: '.xlsx,.xls',
    beforeUpload: (file: File) => {
      const validation = rentContractExcelService.validateExcelFile(file);
      if (!validation.isValid) {
        MessageManager.error(validation.error ?? '文件验证失败');
        return Upload.LIST_IGNORE;
      }

      // 开始上传
      handleFileUpload(file);
      return Upload.LIST_IGNORE; // 阻止自动上传
    },
    fileList,
    showUploadList: false,
    disabled: importing,
  };

  return (
    <div className={className}>
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card
            title="导入数据"
            extra={<FileExcelOutlined style={{ color: '#52c41a' }} />}
            actions={[
              <Button
                key="template"
                type="link"
                icon={<DownloadOutlined />}
                onClick={handleDownloadTemplate}
              >
                下载模板
              </Button>,
              <Button
                key="import"
                type="primary"
                icon={<UploadOutlined />}
                onClick={() => setImportModalVisible(true)}
              >
                导入Excel
              </Button>,
            ]}
          >
            <Paragraph type="secondary">
              从Excel文件批量导入租金合同数据，支持合同信息、租金条款和台账记录的导入。
            </Paragraph>

            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Alert
                message="导入说明"
                description={
                  <ul style={{ margin: 0, paddingLeft: 16 }}>
                    <li>请先下载模板，按照模板格式填写数据</li>
                    <li>支持.xlsx和.xls格式，文件大小不超过10MB</li>
                    <li>导入前请确保资产和权属方信息已存在</li>
                  </ul>
                }
                type="info"
                showIcon
              />
            </Space>
          </Card>
        </Col>

        <Col span={12}>
          <Card
            title="导出数据"
            extra={<ExportOutlined style={{ color: '#1890ff' }} />}
            actions={[
              <Button
                key="export"
                type="primary"
                icon={<ExportOutlined />}
                onClick={() => setExportModalVisible(true)}
              >
                导出Excel
              </Button>,
            ]}
          >
            <Paragraph type="secondary">
              将租金合同数据导出为Excel文件，支持按时间范围筛选和选择导出内容。
            </Paragraph>

            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Alert
                message="导出说明"
                description={
                  <ul style={{ margin: 0, paddingLeft: 16 }}>
                    <li>可选择导出合同信息、租金条款和台账记录</li>
                    <li>支持按时间范围筛选数据</li>
                    <li>导出的Excel文件包含多个工作表</li>
                  </ul>
                }
                type="info"
                showIcon
              />
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 导入模态框 */}
      <Modal
        title="导入Excel文件"
        open={importModalVisible}
        onCancel={() => {
          setImportModalVisible(false);
          setImportResult(null);
          setFileList([]);
        }}
        footer={null}
        width={600}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 导入选项 */}
          <Card title="导入选项" size="small">
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Checkbox
                checked={importOptions.import_terms}
                onChange={(e) =>
                  setImportOptions({
                    ...importOptions,
                    import_terms: e.target.checked,
                  })
                }
              >
                导入租金条款
              </Checkbox>
              <Checkbox
                checked={importOptions.import_ledger}
                onChange={(e) =>
                  setImportOptions({
                    ...importOptions,
                    import_ledger: e.target.checked,
                  })
                }
              >
                导入台账记录
              </Checkbox>
              <Checkbox
                checked={importOptions.overwrite_existing}
                onChange={(e) =>
                  setImportOptions({
                    ...importOptions,
                    overwrite_existing: e.target.checked,
                  })
                }
              >
                覆盖已存在的数据
              </Checkbox>
            </Space>
          </Card>

          {/* 文件上传 */}
          <Upload {...uploadProps}>
            <Button
              icon={<UploadOutlined />}
              loading={importing}
              disabled={importing}
              block
            >
              {importing ? '正在导入...' : '选择Excel文件'}
            </Button>
          </Upload>

          {/* 导入结果 */}
          {importResult && (
            <Card
              title={
                <Space>
                  {importResult.success ? (
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  ) : (
                    <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                  )}
                  <Text>导入结果</Text>
                </Space>
              }
              size="small"
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="合同"
                      value={importResult.imported_contracts}
                      suffix="个"
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="条款"
                      value={importResult.imported_terms}
                      suffix="个"
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="台账"
                      value={importResult.imported_ledgers}
                      suffix="个"
                    />
                  </Col>
                </Row>

                {importResult.warnings.length > 0 && (
                  <>
                    <Divider titlePlacement="start">警告</Divider>
                    <List
                      size="small"
                      dataSource={importResult.warnings.slice(0, 3)}
                      renderItem={(item) => (
                        <List.Item>
                          <Text type="warning">{item}</Text>
                        </List.Item>
                      )}
                    />
                    {importResult.warnings.length > 3 && (
                      <Text type="secondary">
                        还有 {importResult.warnings.length - 3} 个警告...
                      </Text>
                    )}
                  </>
                )}

                {importResult.errors.length > 0 && (
                  <>
                    <Divider titlePlacement="start">错误</Divider>
                    <List
                      size="small"
                      dataSource={importResult.errors.slice(0, 3)}
                      renderItem={(item) => (
                        <List.Item>
                          <Text type="danger">{item}</Text>
                        </List.Item>
                      )}
                    />
                    {importResult.errors.length > 3 && (
                      <Text type="secondary">
                        还有 {importResult.errors.length - 3} 个错误...
                      </Text>
                    )}
                  </>
                )}
              </Space>
            </Card>
          )}
        </Space>
      </Modal>

      {/* 导出模态框 */}
      <Modal
        title="导出Excel文件"
        open={exportModalVisible}
        onOk={handleExport}
        onCancel={() => {
          setExportModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={exporting}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="include_terms"
            label="包含租金条款"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="include_ledger"
            label="包含台账记录"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>

          <Form.Item name="date_range" label="时间范围">
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RentContractExcelImport;
