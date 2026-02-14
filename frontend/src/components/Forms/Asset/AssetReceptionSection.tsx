import React from 'react';
import { Form, Button, DatePicker, Upload, List, Tag, Row, Col, Card, Typography } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { UploadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import GroupedSelectSingle from '@/components/Common/GroupedSelect';
import { BusinessModelOptions } from '@/utils/enumHelpers';
import { useAssetFormContext } from './AssetFormContext';
import { generateFormFieldIds } from '@/utils/accessibility';
import styles from './AssetReceptionSection.module.css';

const { Title } = Typography;

/**
 * AssetForm - Reception Info Section
 * Fields: business model, agreement dates, agreement attachments
 */
const AssetReceptionSection: React.FC = () => {
  const { fileList, setFileList } = useAssetFormContext();

  // 为字段生成可访问性 ID
  const businessModelIds = generateFormFieldIds('business-model');
  const agreementStartDateIds = generateFormFieldIds('agreement-start-date');
  const agreementEndDateIds = generateFormFieldIds('agreement-end-date');
  const attachmentsIds = generateFormFieldIds('attachments');

  const uploadProps: UploadProps = {
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
      return false; // Prevent auto-upload
    },
    onChange: (info: { fileList: UploadFile[] }) => {
      setFileList(info.fileList);
    },
    fileList: fileList,
  };

  return (
    <Card className={styles.sectionCard}>
      <Title level={5}>接收信息</Title>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="接收模式"
            name="business_model"
            htmlFor={businessModelIds.inputId}
          >
            <GroupedSelectSingle
              groups={[{ label: '接收模式', options: BusinessModelOptions }]}
              placeholder="请选择接收模式"
              showGroupLabel={false}
              id={businessModelIds.inputId}
              aria-label={businessModelIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="(当前)接收协议开始日期"
            name="operation_agreement_start_date"
            htmlFor={agreementStartDateIds.inputId}
          >
            <DatePicker
              className={styles.datePickerFullWidth}
              id={agreementStartDateIds.inputId}
              aria-label={agreementStartDateIds.labelId}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="(当前)接收协议结束日期"
            name="operation_agreement_end_date"
            htmlFor={agreementEndDateIds.inputId}
          >
            <DatePicker
              className={styles.datePickerFullWidth}
              id={agreementEndDateIds.inputId}
              aria-label={agreementEndDateIds.labelId}
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={24}>
          <Form.Item
            label="接收协议文件"
            name="operation_agreement_attachments"
            htmlFor={attachmentsIds.inputId}
          >
            <div>
              <Upload {...uploadProps}>
                <Button
                  icon={<UploadOutlined />}
                  aria-label="上传PDF接收协议文件"
                >
                  上传PDF接收协议文件
                </Button>
              </Upload>
              <div
                className={styles.uploadHintText}
                role="note"
                aria-label="文件上传说明"
              >
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
                            if (file.url != null) {
                              window.open(file.url, '_blank');
                            }
                          }}
                          aria-label={`查看文件: ${file.name}`}
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
                          aria-label={`删除文件: ${file.name}`}
                        >
                          删除
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<Tag color="blue">PDF</Tag>}
                        title={<span aria-label={`文件名: ${file.name}`}>{file.name}</span>}
                        description={`文件大小: ${file.size != null ? (file.size / 1024 / 1024).toFixed(2) + 'MB' : '未知'}`}
                      />
                    </List.Item>
                  )}
                  className={styles.attachmentList}
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
