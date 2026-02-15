import React, { useEffect, useState, type ReactNode } from 'react';
import { Button, Card, Col, Modal, Row, Space, Statistic, Tag, Tooltip, Typography } from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  FileExcelOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { MessageManager } from '@/utils/messageManager';
import { assetService } from '@/services/assetService';
import { rentContractExcelService } from '@/services/rentContractExcelService';
import type { ColumnsType } from 'antd/es/table';
import { createLogger } from '@/utils/logger';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { useArrayListData } from '@/hooks/useArrayListData';
import PageContainer from '@/components/Common/PageContainer';
import styles from './TemplateManagementPage.module.css';

const _pageLogger = createLogger('TemplateManagement');

const { Text } = Typography;

interface TemplateInfo {
  key: string;
  name: string;
  description: string;
  type: 'asset' | 'rent-contract';
  version: string;
  updateDate: string;
  fileSize: string;
  fields: string[];
  status: 'active' | 'draft' | 'deprecated';
}

interface TemplateFilters {
  placeholder: string;
}

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';

// 模板数据
const templates: TemplateInfo[] = [
  {
    key: 'asset-import',
    name: '资产导入模板',
    description: '用于批量导入资产数据的Excel模板，包含所有必要字段',
    type: 'asset',
    version: 'v2.0',
    updateDate: '2025-09-24',
    fileSize: '25KB',
    fields: [
      '权属方',
      '权属类别',
      '项目名称',
      '物业名称',
      '物业地址',
      '土地面积',
      '实际房产面积',
      '非经营物业面积',
      '可出租面积',
      '已出租面积',
      '确权状态',
      '证载用途',
      '实际用途',
      '业态类别',
      '使用状态',
      '是否涉诉',
      '物业性质',
      '是否计入出租率',
      '接收模式',
      '接收协议开始日期',
      '接收协议结束日期',
    ],
    status: 'active',
  },
  {
    key: 'rent-contract-import',
    name: '租赁合同导入模板',
    description: '用于批量导入租赁合同信息的Excel模板',
    type: 'rent-contract',
    version: 'v1.0',
    updateDate: '2025-09-20',
    fileSize: '18KB',
    fields: [
      '合同编号',
      '资产名称',
      '承租方',
      '合同开始日期',
      '合同结束日期',
      '月租金',
      '押金',
      '付款方式',
      '合同状态',
    ],
    status: 'active',
  },
];

const TYPE_META_MAP: Record<
  TemplateInfo['type'],
  {
    label: string;
    tone: Tone;
  }
> = {
  asset: { label: '资产导入', tone: 'primary' },
  'rent-contract': { label: '租赁合同', tone: 'warning' },
};

const STATUS_META_MAP: Record<
  TemplateInfo['status'],
  {
    label: string;
    hint: string;
    tone: Tone;
    icon: ReactNode;
  }
> = {
  active: { label: '使用中', hint: '已发布', tone: 'success', icon: <CheckCircleOutlined /> },
  draft: { label: '草稿', hint: '待发布', tone: 'warning', icon: <ClockCircleOutlined /> },
  deprecated: { label: '已废弃', hint: '停止维护', tone: 'error', icon: <CloseCircleOutlined /> },
};

const TemplateManagementPage: React.FC = () => {
  const [downloadingTemplateKey, setDownloadingTemplateKey] = useState<string | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<TemplateInfo | null>(null);
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
    neutral: styles.toneNeutral,
  };

  const {
    data: templateRows,
    loading,
    pagination,
    loadList,
    updatePagination,
  } = useArrayListData<TemplateInfo, TemplateFilters>({
    items: templates,
    initialFilters: {
      placeholder: '',
    },
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadList({ page: 1 });
  }, [loadList]);
  const activeTemplateCount = templates.filter(template => template.status === 'active').length;

  const getToneClassName = (tone: Tone): string => {
    return toneClassMap[tone];
  };

  const normalizeVersion = (version: string): string => {
    if (version.startsWith('v')) {
      return version;
    }
    return `v${version}`;
  };

  // 下载模板
  const handleDownloadTemplate = async (template: TemplateInfo) => {
    setDownloadingTemplateKey(template.key);
    try {
      if (template.type === 'asset') {
        await assetService.downloadImportTemplate();
        MessageManager.success('资产导入模板下载成功');
      } else if (template.type === 'rent-contract') {
        await rentContractExcelService.downloadTemplateFile();
        MessageManager.success('租赁合同导入模板下载成功');
      }
    } catch (error: unknown) {
      _pageLogger.error('下载模板失败:', error as Error);
      MessageManager.error(`下载模板失败: ${(error as Error).message || '网络错误'}`);
    } finally {
      setDownloadingTemplateKey(null);
    }
  };

  // 预览模板
  const handlePreviewTemplate = (template: TemplateInfo) => {
    setPreviewTemplate(template);
    setPreviewVisible(true);
  };

  const getTypeTag = (type: TemplateInfo['type']) => {
    const meta = TYPE_META_MAP[type];
    return (
      <Tag className={`${styles.statusTag} ${styles.typeTag} ${getToneClassName(meta.tone)}`}>
        {meta.label}
      </Tag>
    );
  };

  // 获取状态标签
  const getStatusTag = (status: TemplateInfo['status'] | string) => {
    const statusMeta = STATUS_META_MAP[status as TemplateInfo['status']];
    if (statusMeta == null) {
      return <Tag className={`${styles.statusTag} ${styles.toneNeutral}`}>未知</Tag>;
    }
    return (
      <Tag
        className={`${styles.statusTag} ${getToneClassName(statusMeta.tone)}`}
        icon={statusMeta.icon}
      >
        {statusMeta.label}
        <span className={styles.statusHint}>· {statusMeta.hint}</span>
      </Tag>
    );
  };

  // 表格列定义
  const columns: ColumnsType<TemplateInfo> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: TemplateInfo) => (
        <div className={styles.templateNameCell}>
          <FileExcelOutlined className={styles.templateIcon} />
          <span>
            <span className={styles.templateNameText}>{text}</span>
            <Text type="secondary" className={styles.templateVersion}>
              {normalizeVersion(record.version)}
            </Text>
          </span>
        </div>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: TemplateInfo['type']) => getTypeTag(type),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '更新时间',
      dataIndex: 'updateDate',
      key: 'updateDate',
    },
    {
      title: '文件大小',
      dataIndex: 'fileSize',
      key: 'fileSize',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: TemplateInfo) => (
        <Space className={styles.actionGroup}>
          <Tooltip title="下载模板">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              className={`${styles.actionButton} ${styles.tableActionButton}`}
              onClick={() => handleDownloadTemplate(record)}
              loading={downloadingTemplateKey === record.key}
              disabled={downloadingTemplateKey != null && downloadingTemplateKey !== record.key}
              aria-label={`下载模板 ${record.name}`}
            >
              下载
            </Button>
          </Tooltip>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              className={`${styles.actionButton} ${styles.tableActionButton}`}
              onClick={() => handlePreviewTemplate(record)}
              aria-label={`预览模板 ${record.name}`}
            >
              预览
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      className={styles.pageShell}
      title="数据模板管理"
      subTitle="管理和下载各种数据导入模板，确保数据导入的准确性和一致性"
    >
      {/* 统计信息 */}
      <Row gutter={[16, 16]} className={styles.statsRow}>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
            <Statistic title="可用模板" value={activeTemplateCount} suffix="个" />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.tonePrimary}`}>
            <Statistic
              title="资产模板"
              value={templates.filter(t => t.type === 'asset').length}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.toneWarning}`}>
            <Statistic
              title="合同模板"
              value={templates.filter(t => t.type === 'rent-contract').length}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className={`${styles.statsCard} ${styles.toneNeutral}`}>
            <Statistic title="总下载量" value={0} suffix="次" />
          </Card>
        </Col>
      </Row>

      {/* 使用说明 */}
      <Card
        title={
          <Space>
            <InfoCircleOutlined className={styles.sectionIcon} />
            使用说明
          </Space>
        }
        className={styles.instructionsCard}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card size="small" title="1. 下载模板" className={styles.instructionStepCard}>
              <Text className={styles.instructionText}>
                点击&quot;下载&quot;按钮获取对应的数据导入模板文件
              </Text>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title="2. 填写数据" className={styles.instructionStepCard}>
              <Text className={styles.instructionText}>按照模板格式和字段要求填写您的数据</Text>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title="3. 导入数据" className={styles.instructionStepCard}>
              <Text className={styles.instructionText}>
                在对应的导入页面上传填写完成的 Excel 文件
              </Text>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 模板列表 */}
      <Card>
        <div className={styles.tableSummary} aria-live="polite">
          <Text type="secondary">共 {pagination.total} 个模板</Text>
          <Text type="secondary">可用模板 {activeTemplateCount} 个</Text>
        </div>
        <TableWithPagination
          columns={columns}
          dataSource={templateRows}
          rowKey="key"
          loading={loading}
          paginationState={pagination}
          onPageChange={updatePagination}
          paginationProps={{
            showTotal: (total: number, range: [number, number]) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* 模板预览弹窗 */}
      <Modal
        title="模板详情"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
      >
        {previewTemplate != null && (
          <div className={styles.previewContent}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <div className={styles.detailItem}>
                  <Text strong className={styles.detailLabel}>
                    模板名称：
                  </Text>
                  <Text>{previewTemplate.name}</Text>
                </div>
              </Col>
              <Col span={12}>
                <div className={styles.detailItem}>
                  <Text strong className={styles.detailLabel}>
                    版本：
                  </Text>
                  <Text>{previewTemplate.version}</Text>
                </div>
              </Col>
              <Col span={12}>
                <div className={styles.detailItem}>
                  <Text strong className={styles.detailLabel}>
                    类型：
                  </Text>
                  {getTypeTag(previewTemplate.type)}
                </div>
              </Col>
              <Col span={12}>
                <div className={styles.detailItem}>
                  <Text strong className={styles.detailLabel}>
                    状态：
                  </Text>
                  {getStatusTag(previewTemplate.status)}
                </div>
              </Col>
              <Col span={24}>
                <div className={styles.detailItem}>
                  <Text strong className={styles.detailLabel}>
                    描述：
                  </Text>
                  <Text className={styles.descriptionText}>{previewTemplate.description}</Text>
                </div>
              </Col>
              <Col span={24}>
                <Text strong>包含字段：</Text>
                <div className={styles.fieldsContainer}>
                  {previewTemplate.fields.map(field => (
                    <Tag key={field} className={styles.fieldTag}>
                      {field}
                    </Tag>
                  ))}
                </div>
              </Col>
            </Row>
            <div className={styles.previewFooter}>
              <Space className={styles.previewFooterActions} wrap>
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  className={`${styles.actionButton} ${styles.modalActionButton}`}
                  onClick={() => {
                    handleDownloadTemplate(previewTemplate);
                    setPreviewVisible(false);
                  }}
                  loading={downloadingTemplateKey === previewTemplate.key}
                  aria-label={`下载模板 ${previewTemplate.name}`}
                >
                  下载模板
                </Button>
                <Button
                  className={`${styles.actionButton} ${styles.modalActionButton}`}
                  onClick={() => setPreviewVisible(false)}
                >
                  关闭
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default TemplateManagementPage;
