import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Popconfirm, Space, Table, Upload, message } from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileSearchOutlined,
  SwapOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { UploadProps } from 'antd';

import {
  propertyCertificateAttachmentService,
  type PropertyCertificateAttachment,
} from '@/services/propertyCertificateAttachmentService';

interface PropertyCertificateAttachmentsPanelProps {
  certificateId: string;
}

const validateFile = (file: File): boolean => {
  const allowed = ['application/pdf', 'image/jpeg', 'image/png'];
  if (!allowed.includes(file.type) || file.size > 20 * 1024 * 1024) {
    message.error('仅支持 20 MiB 以内的 PDF、JPEG 或 PNG');
    return false;
  }
  return true;
};

export const PropertyCertificateAttachmentsPanel: React.FC<
  PropertyCertificateAttachmentsPanelProps
> = ({ certificateId }) => {
  const navigate = useNavigate();
  const [busyId, setBusyId] = useState<string | null>(null);
  const {
    data: attachments = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['property-certificate-attachments', certificateId],
    queryFn: () => propertyCertificateAttachmentService.list(certificateId),
  });

  const append: UploadProps['customRequest'] = async options => {
    const file = options.file as File;
    if (!validateFile(file)) {
      options.onError?.(new Error('Invalid attachment'));
      return;
    }
    setBusyId('append');
    try {
      await propertyCertificateAttachmentService.append(certificateId, file);
      await refetch();
      options.onSuccess?.({});
    } catch (error) {
      options.onError?.(error as Error);
      message.error('附件追加失败');
    } finally {
      setBusyId(null);
    }
  };

  const replace =
    (attachmentId: string): UploadProps['customRequest'] =>
    async options => {
      const file = options.file as File;
      if (!validateFile(file)) {
        options.onError?.(new Error('Invalid attachment'));
        return;
      }
      setBusyId(attachmentId);
      try {
        await propertyCertificateAttachmentService.replace(certificateId, attachmentId, file);
        await refetch();
        options.onSuccess?.({});
      } catch (error) {
        options.onError?.(error as Error);
        message.error('附件替换失败');
      } finally {
        setBusyId(null);
      }
    };

  const remove = async (attachmentId: string) => {
    setBusyId(attachmentId);
    try {
      await propertyCertificateAttachmentService.remove(certificateId, attachmentId);
      await refetch();
    } catch {
      message.error('附件删除失败，最后一件附件不能删除');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Card
      title="附件"
      extra={
        <Upload
          multiple
          showUploadList={false}
          customRequest={append}
          accept=".pdf,.jpg,.jpeg,.png"
        >
          <Button icon={<UploadOutlined />} loading={busyId === 'append'}>
            追加
          </Button>
        </Upload>
      }
    >
      <Table<PropertyCertificateAttachment>
        loading={isLoading}
        rowKey="id"
        pagination={false}
        dataSource={attachments}
        columns={[
          { title: '文件名', dataIndex: 'file_name' },
          { title: '类型', dataIndex: 'file_type', width: 90 },
          {
            title: '大小',
            dataIndex: 'file_size',
            width: 110,
            render: (value: number) => `${(value / 1024 / 1024).toFixed(2)} MiB`,
          },
          {
            title: '操作',
            width: 220,
            render: (_value, record) => (
              <Space>
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  title="预览"
                  onClick={() =>
                    window.open(
                      propertyCertificateAttachmentService.previewUrl(certificateId, record.id),
                      '_blank',
                      'noopener,noreferrer'
                    )
                  }
                />{' '}
                <Button
                  type="text"
                  icon={<FileSearchOutlined />}
                  title="复核"
                  onClick={() =>
                    navigate(
                      `/property-certificates/import?certificate_id=${certificateId}&attachment_id=${record.id}`
                    )
                  }
                />
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  title="下载"
                  onClick={() =>
                    window.open(
                      propertyCertificateAttachmentService.downloadUrl(certificateId, record.id),
                      '_blank',
                      'noopener,noreferrer'
                    )
                  }
                />
                <Upload
                  showUploadList={false}
                  customRequest={replace(record.id)}
                  accept=".pdf,.jpg,.jpeg,.png"
                >
                  <Button
                    type="text"
                    icon={<SwapOutlined />}
                    title="替换"
                    loading={busyId === record.id}
                  />
                </Upload>
                <Popconfirm
                  title="删除附件？"
                  disabled={attachments.length <= 1}
                  onConfirm={() => void remove(record.id)}
                >
                  <Button
                    danger
                    type="text"
                    icon={<DeleteOutlined />}
                    title="删除"
                    disabled={attachments.length <= 1 || busyId === record.id}
                  />
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
};
