import React from 'react';
import {
  Form,
  Button,
  DatePicker,
  Upload,
  List,
  Tag,
  Row,
  Col,
  Card,
  Typography,
  message,
} from 'antd';
import { UploadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import GroupedSelectSingle from '../../Common/GroupedSelect';
import { BusinessModelOptions } from '../../../utils/enumHelpers';
import { useAssetFormContext } from './AssetFormContext';

const { Title } = Typography;

/**
 * AssetForm - Reception Info Section
 * Fields: business model, agreement dates, agreement attachments
 */
const AssetReceptionSection: React.FC = () => {
  const { fileList, setFileList } = useAssetFormContext();

  const uploadProps: UploadProps = {
    multiple: true,
    accept: '.pdf',
    beforeUpload: (file: File) => {
      const isPDF = file.type === 'application/pdf';
      if (!isPDF) {
        message.error('只能上传PDF文件');
        return false;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('文件大小不能超过10MB');
        return false;
      }
      return false; // Prevent auto-upload
    },
    onChange: (info: { fileList: UploadFile[] }) => {
      setFileList(info.fileList);
    },
    fileList: fileList,
  };

  return (
    <Card style={{ marginBottom: '16px' }}>
      <Title level={5}>接收信息</Title>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="接收模式" name="business_model">
            <GroupedSelectSingle
              groups={[{ label: '接收模式', options: BusinessModelOptions }]}
              placeholder="请选择接收模式"
              showGroupLabel={false}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="(当前)接收协议开始日期" name="operation_agreement_start_date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="(当前)接收协议结束日期" name="operation_agreement_end_date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={24}>
          <Form.Item label="接收协议文件" name="operation_agreement_attachments">
            <div>
              <Upload {...uploadProps}>
                <Button icon={<UploadOutlined />}>上传PDF接收协议文件</Button>
              </Upload>
              <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                支持多文件上传，每个文件不超过10MB，仅支持PDF格式
              </div>
              {fileList.length > 0 && (
                <List
                  size="small"
                  header={<div>已选择的附件</div>}
                  bordered
                  dataSource={fileList}
                  renderItem={(file: UploadFile) => (
                    <List.Item
                      actions={[
                        <Button
                          key="view"
                          type="link"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => {
                            if (file.url !== null && file.url !== undefined) {
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
                            setFileList(fileList.filter(f => f.uid !== file.uid));
                          }}
                        >
                          删除
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<Tag color="blue">PDF</Tag>}
                        title={file.name}
                        description={`文件大小: ${file.size !== null && file.size !== undefined ? (file.size / 1024 / 1024).toFixed(2) + 'MB' : '未知'}`}
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
    </Card>
  );
};

export default AssetReceptionSection;
