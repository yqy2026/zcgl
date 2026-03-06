/**
 * 租金台账页面
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Input,
  Select,
  DatePicker,
  Modal,
  Tooltip,
  Row,
  Col,
  Statistic,
  Typography,
  Form,
  Alert,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { ListToolbar } from '@/components/Common/ListToolbar';
import PartySelector from '@/components/Common/PartySelector';
import PageContainer from '@/components/Common/PageContainer';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  SearchOutlined,
  EditOutlined,
  CheckOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  DollarOutlined,
  FileExcelOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { TableRowSelection } from 'antd/es/table/interface';
import dayjs from 'dayjs';

import {
  RentLedger,
  RentLedgerListResponse,
  RentLedgerQueryParams,
  RentLedgerUpdate,
  RentStatisticsOverview,
} from '@/types/rentContract';
import { Asset, AssetListResponse } from '@/types/asset';
import { rentContractService } from '@/services/rentContractService';
import { assetService } from '@/services/assetService';
import { RENTAL_QUERY_KEYS } from '@/constants/queryKeys';
import { useFormat } from '@/utils/format';
import { createLogger } from '@/utils/logger';
import styles from './RentLedgerPage.module.css';

const pageLogger = createLogger('RentLedger');

const { Text } = Typography;
const { Search } = Input;
const { Option } = Select;

interface BatchUpdateValues {
  payment_status: '未支付' | '部分支付' | '已支付' | '逾期';
  payment_date?: dayjs.Dayjs;
  payment_method?: string;
  notes?: string;
}

type RentLedgerFilters = Omit<RentLedgerQueryParams, 'page' | 'pageSize' | 'page_size'>;
type LedgerPaymentStatus = RentLedger['payment_status'];
type Tone = 'primary' | 'success' | 'warning' | 'error';

const resolveDisplayText = (value: string | null | undefined): string => {
  if (value == null) {
    return '未知';
  }
  const normalizedValue = value.trim();
  return normalizedValue !== '' ? normalizedValue : '未知';
};

const normalizePercentage = (value: number): number => Math.min(100, Math.max(0, value));

const resolvePaymentRateTone = (rate: number): Tone => {
  if (rate >= 90) {
    return 'success';
  }
  if (rate >= 70) {
    return 'warning';
  }
  return 'error';
};

const resolvePaymentRateLabel = (rate: number): string => {
  if (rate >= 90) {
    return '优';
  }
  if (rate >= 70) {
    return '中';
  }
  return '低';
};

const RentLedgerPage: React.FC = () => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  const [uiState, setUiState] = useState({
    selectedLedgers: [] as RentLedger[],
    showBatchModal: false,
  });
  const [filters, setFilters] = useState<RentLedgerFilters>({});
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });

  const format = useFormat();
  const paymentStatusConfig: Record<
    LedgerPaymentStatus,
    {
      icon: React.ReactNode;
      tone: Tone;
      assistiveText: string;
    }
  > = {
    未支付: {
      icon: <ClockCircleOutlined />,
      tone: 'warning',
      assistiveText: '待处理',
    },
    部分支付: {
      icon: <ExclamationCircleOutlined />,
      tone: 'warning',
      assistiveText: '未结清',
    },
    已支付: {
      icon: <CheckOutlined />,
      tone: 'success',
      assistiveText: '已结清',
    },
    逾期: {
      icon: <ExclamationCircleOutlined />,
      tone: 'error',
      assistiveText: '需催缴',
    },
  };

  const {
    data: ledgersResponse,
    error: ledgersError,
    isLoading: isLedgersLoading,
    isFetching: isLedgersFetching,
  } = useQuery<RentLedgerListResponse>({
    queryKey: RENTAL_QUERY_KEYS.ledgerList(
      paginationState.current,
      paginationState.pageSize,
      filters as Record<string, unknown>
    ),
    queryFn: () =>
      rentContractService.getRentLedgers({
        page: paginationState.current,
        pageSize: paginationState.pageSize,
        ...filters,
      }),
    retry: 1,
  });

  const { data: statistics, error: statisticsError } = useQuery<RentStatisticsOverview>({
    queryKey: RENTAL_QUERY_KEYS.ledgerStatistics,
    queryFn: () => rentContractService.getRentStatistics(),
    staleTime: 60 * 1000,
    retry: 1,
  });

  const { data: assetsResponse, error: assetsError } = useQuery<AssetListResponse>({
    queryKey: RENTAL_QUERY_KEYS.ledgerReferenceAssets,
    queryFn: () => assetService.getAssets({ page_size: 100 }),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (ledgersError != null) {
      pageLogger.error('加载台账列表失败:', ledgersError);
      const errorMessage = ledgersError instanceof Error ? ledgersError.message : '未知错误';
      MessageManager.error(`加载台账列表失败: ${errorMessage}`);
    }
  }, [ledgersError]);

  useEffect(() => {
    if (statisticsError != null) {
      pageLogger.error('加载统计数据失败:', statisticsError);
    }
  }, [statisticsError]);

  useEffect(() => {
    if (assetsError != null) {
      pageLogger.error('加载资产参考数据失败:', assetsError);
      MessageManager.error('加载参考数据失败');
    }
  }, [assetsError]);

  const ledgers = ledgersResponse?.items ?? [];
  const assets: Asset[] = assetsResponse?.items ?? [];
  const statisticsData = statistics ?? null;
  const loading = isLedgersLoading || isLedgersFetching;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: ledgersResponse?.total ?? 0,
    }),
    [ledgersResponse?.total, paginationState.current, paginationState.pageSize]
  );

  const refreshLedgersAndStatistics = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.ledgerListRoot });
    void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.ledgerStatistics });
  }, [queryClient]);

  // 处理分页变化
  const handleTableChange = (pagination: { current?: number; pageSize?: number }): void => {
    setPaginationState(prev => ({
      current: pagination.current ?? prev.current,
      pageSize: pagination.pageSize ?? prev.pageSize,
    }));
  };

  // 处理搜索
  const handleSearch = (values: Record<string, unknown>) => {
    setFilters(values as RentLedgerFilters);
    setPaginationState(prev => ({ ...prev, current: 1 }));
  };

  // 重置搜索
  const handleReset = () => {
    setFilters({});
    setPaginationState(prev => ({ ...prev, current: 1 }));
  };

  // 更新台账支付状态
  const handleUpdateLedger = async (id: string, data: RentLedgerUpdate) => {
    try {
      await rentContractService.updateRentLedger(id, data);
      MessageManager.success('更新成功');
      refreshLedgersAndStatistics();
    } catch (error: unknown) {
      pageLogger.error('更新台账支付状态失败:', error);
      MessageManager.error('更新失败');
    }
  };

  // 批量更新支付状态
  const handleBatchUpdate = async (values: BatchUpdateValues) => {
    if (uiState.selectedLedgers.length === 0) {
      MessageManager.warning('请先选择要更新的台账记录');
      return;
    }

    try {
      await rentContractService.batchUpdateRentLedger({
        ledger_ids: uiState.selectedLedgers.map(ledger => ledger.id),
        payment_status: values.payment_status,
        payment_date: values.payment_date?.format('YYYY-MM-DD'),
        payment_method: values.payment_method ?? '',
        notes: values.notes ?? '',
      });
      MessageManager.success('批量更新成功');
      setUiState(prev => ({ ...prev, showBatchModal: false, selectedLedgers: [] }));
      refreshLedgersAndStatistics();
    } catch (error: unknown) {
      pageLogger.error('批量更新台账支付状态失败:', error);
      MessageManager.error('批量更新失败');
    }
  };

  // 导出Excel
  const handleExport = async () => {
    try {
      const blob = await rentContractService.exportLedgersToExcel(
        filters as Record<string, unknown>
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `租金台账_${dayjs().format('YYYY-MM-DD')}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      MessageManager.success('导出成功');
    } catch (error: unknown) {
      pageLogger.error('导出台账失败:', error);
      MessageManager.error('导出失败');
    }
  };

  // 选择行变化
  const rowSelection: TableRowSelection<RentLedger> = {
    selectedRowKeys: uiState.selectedLedgers.map(ledger => ledger.id),
    onChange: (_selectedRowKeys: React.Key[], selectedRows: RentLedger[]) => {
      setUiState(prev => ({ ...prev, selectedLedgers: selectedRows }));
    },
  };

  // 快速支付
  const handleQuickPayment = (ledger: RentLedger) => {
    Modal.confirm({
      title: '确认支付',
      content: `确认将台账 ${ledger.year_month} 标记为已支付？`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        await handleUpdateLedger(ledger.id, {
          payment_status: '已支付',
          paid_amount: ledger.due_amount,
          payment_date: dayjs().format('YYYY-MM-DD'),
        });
      },
    });
  };

  // 表格列定义
  const columns: ColumnsType<RentLedger> = [
    {
      title: '年月',
      dataIndex: 'year_month',
      key: 'year_month',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '合同编号',
      dataIndex: ['contract', 'contract_number'],
      key: 'contract_number',
      render: (text: string) => resolveDisplayText(text),
    },
    {
      title: '承租方',
      dataIndex: ['contract', 'tenant_name'],
      key: 'tenant_name',
      render: (text: string) => resolveDisplayText(text),
    },
    {
      title: '物业名称',
      dataIndex: ['asset', 'asset_name'],
      key: 'asset_name',
      render: (text: string) => resolveDisplayText(text),
    },
    {
      title: '产权方主体',
      key: 'owner_party_name',
      render: (_value: unknown, record: RentLedger) =>
        resolveDisplayText(record.contract?.owner_party_name ?? record.ownership?.name),
    },
    {
      title: '应缴日期',
      dataIndex: 'due_date',
      key: 'due_date',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '应收金额',
      dataIndex: 'due_amount',
      key: 'due_amount',
      render: (amount: number) => format.currency(amount),
      align: 'right' as const,
    },
    {
      title: '实收金额',
      dataIndex: 'paid_amount',
      key: 'paid_amount',
      render: (amount: number, record: RentLedger) => {
        const tone: Tone = amount < record.due_amount ? 'error' : 'success';
        return (
          <Space size={6} className={styles.inlineStatus} wrap>
            <Text className={[styles.valueText, toneClassMap[tone]].join(' ')}>
              {format.currency(amount)}
            </Text>
            <Tag className={[styles.statusTag, toneClassMap[tone]].join(' ')}>
              {tone === 'error' ? '不足额' : '足额'}
            </Tag>
          </Space>
        );
      },
      align: 'right' as const,
    },
    {
      title: '欠款金额',
      dataIndex: 'overdue_amount',
      key: 'overdue_amount',
      render: (amount: number) => {
        if (amount > 0) {
          return (
            <Space size={6} className={styles.inlineStatus} wrap>
              <Text className={[styles.valueText, styles.toneError].join(' ')}>
                {format.currency(amount)}
              </Text>
              <Tag className={[styles.statusTag, styles.toneError].join(' ')}>欠款</Tag>
            </Space>
          );
        }
        return <Tag className={[styles.statusTag, styles.toneSuccess].join(' ')}>无欠款</Tag>;
      },
      align: 'right' as const,
    },
    {
      title: '支付状态',
      dataIndex: 'payment_status',
      key: 'payment_status',
      render: (status: string) => {
        const config =
          paymentStatusConfig[status as LedgerPaymentStatus] ?? paymentStatusConfig['未支付'];
        return (
          <Space size={6} className={styles.inlineStatus} wrap>
            <Tag
              icon={config.icon}
              className={[styles.statusTag, toneClassMap[config.tone]].join(' ')}
            >
              {status}
            </Tag>
            <Text type="secondary" className={styles.statusAssistText}>
              {config.assistiveText}
            </Text>
          </Space>
        );
      },
    },
    {
      title: '支付日期',
      dataIndex: 'payment_date',
      key: 'payment_date',
      render: (date: string) => (date != null ? dayjs(date).format('YYYY-MM-DD') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record: RentLedger) => (
        <Space size="small" className={styles.tableActionGroup}>
          {record.payment_status !== '已支付' && (
            <Tooltip title="快速支付">
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleQuickPayment(record)}
                aria-label={`快速支付 ${record.year_month}`}
                className={styles.tableActionButton}
              />
            </Tooltip>
          )}
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              aria-label={`编辑 ${record.year_month}`}
              className={styles.tableActionButton}
              onClick={() => {
                form.setFieldsValue({
                  payment_status: record.payment_status,
                  paid_amount: record.paid_amount,
                  payment_date: record.payment_date != null ? dayjs(record.payment_date) : null,
                  payment_method: record.payment_method,
                  notes: record.notes,
                });
                setUiState(prev => ({ ...prev, selectedLedgers: [record] }));
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const paymentRateTone = resolvePaymentRateTone(Number(statisticsData?.payment_rate ?? 0));
  const paymentRateLabel = resolvePaymentRateLabel(Number(statisticsData?.payment_rate ?? 0));
  const overdueTone: Tone = Number(statisticsData?.total_overdue ?? 0) > 0 ? 'error' : 'success';

  return (
    <PageContainer
      title="租金台账管理"
      subTitle="管理物业租金台账，支持支付状态更新和统计分析"
      className={styles.ledgerPage}
    >
      {/* 统计卡片 */}
      {statisticsData != null && (
        <Row gutter={[16, 16]} className={styles.overviewRow}>
          <Col xs={24} sm={12} lg={6}>
            <Card className={[styles.metricCard, styles.tonePrimary].join(' ')}>
              <Statistic
                title="应收总额"
                value={statisticsData.total_due}
                precision={2}
                prefix={<DollarOutlined />}
                suffix="元"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card className={[styles.metricCard, styles.toneSuccess].join(' ')}>
              <Statistic
                title="已收总额"
                value={statisticsData.total_paid}
                precision={2}
                prefix={<DollarOutlined />}
                suffix="元"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card className={[styles.metricCard, toneClassMap[overdueTone]].join(' ')}>
              <Statistic
                title="欠款总额"
                value={statisticsData.total_overdue}
                precision={2}
                prefix={<DollarOutlined />}
                suffix="元"
              />
              <Tag
                className={[styles.statusTag, toneClassMap[overdueTone], styles.metricTag].join(
                  ' '
                )}
              >
                {overdueTone === 'error' ? '需催缴' : '正常'}
              </Tag>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card className={[styles.metricCard, toneClassMap[paymentRateTone]].join(' ')}>
              <Statistic
                title="收缴率"
                value={normalizePercentage(Number(statisticsData.payment_rate))}
                precision={2}
                suffix="%"
              />
              <Tag
                className={[styles.statusTag, toneClassMap[paymentRateTone], styles.metricTag].join(
                  ' '
                )}
              >
                {paymentRateLabel}
              </Tag>
            </Card>
          </Col>
        </Row>
      )}

      {/* 搜索区域 */}
      <Card className={styles.filterCard}>
        <ListToolbar
          variant="plain"
          gutter={[16, 16]}
          items={[
            {
              key: 'search',
              col: { xs: 24, sm: 12, lg: 4 },
              content: (
                <Search
                  placeholder="搜索合同或承租方"
                  onSearch={value => handleSearch({ keyword: value })}
                  enterButton={<SearchOutlined />}
                  className={styles.filterControl}
                />
              ),
            },
            {
              key: 'asset',
              col: { xs: 24, sm: 12, lg: 4 },
              content: (
                <Select
                  placeholder="选择物业"
                  allowClear
                  onChange={value => handleSearch({ asset_id: value })}
                  className={styles.filterControl}
                >
                  {assets.map(asset => (
                    <Option key={asset.id} value={asset.id}>
                      {asset.asset_name}
                    </Option>
                  ))}
                </Select>
              ),
            },
            {
              key: 'owner-party',
              col: { xs: 24, sm: 12, lg: 4 },
              content: (
                <PartySelector
                  placeholder="选择产权方主体"
                  filterMode="owner"
                  onChange={value => handleSearch({ owner_party_id: value })}
                  style={{ width: '100%' }}
                />
              ),
            },
            {
              key: 'status',
              col: { xs: 24, sm: 12, lg: 4 },
              content: (
                <Select
                  placeholder="支付状态"
                  allowClear
                  onChange={value => handleSearch({ payment_status: value })}
                  className={styles.filterControl}
                >
                  <Option value="未支付">未支付</Option>
                  <Option value="部分支付">部分支付</Option>
                  <Option value="已支付">已支付</Option>
                  <Option value="逾期">逾期</Option>
                </Select>
              ),
            },
            {
              key: 'month',
              col: { xs: 24, sm: 12, lg: 4 },
              content: (
                <DatePicker
                  picker="month"
                  placeholder="选择月份"
                  className={styles.filterControl}
                  onChange={(_date, dateString) => {
                    if (typeof dateString === 'string') {
                      handleSearch({ year_month: dateString });
                    }
                  }}
                />
              ),
            },
            {
              key: 'actions',
              col: { xs: 24, sm: 12, lg: 4 },
              content: (
                <Space className={styles.toolbarActions} size={8} wrap>
                  <Button onClick={handleReset}>重置</Button>
                  <Button type="primary" icon={<FileExcelOutlined />} onClick={handleExport}>
                    导出
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* 操作区域 */}
      {uiState.selectedLedgers.length > 0 && (
        <Alert
          title={`已选择 ${uiState.selectedLedgers.length} 条记录`}
          type="info"
          showIcon
          className={styles.selectionAlert}
          action={
            <Space size={8} wrap>
              <Button
                type="primary"
                size="small"
                onClick={() => setUiState(prev => ({ ...prev, showBatchModal: true }))}
              >
                批量更新
              </Button>
              <Button
                size="small"
                onClick={() => setUiState(prev => ({ ...prev, selectedLedgers: [] }))}
              >
                取消选择
              </Button>
            </Space>
          }
        />
      )}

      {/* 台账列表 */}
      <Card className={styles.tableCard}>
        <TableWithPagination
          columns={columns}
          dataSource={ledgers}
          rowKey="id"
          rowSelection={rowSelection}
          loading={loading}
          paginationState={pagination}
          onPageChange={handleTableChange}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* 批量更新弹窗 */}
      <Modal
        title="批量更新支付状态"
        open={uiState.showBatchModal}
        onCancel={() => setUiState(prev => ({ ...prev, showBatchModal: false }))}
        footer={null}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleBatchUpdate}>
          <Form.Item
            name="payment_status"
            label="支付状态"
            rules={[{ required: true, message: '请选择支付状态' }]}
          >
            <Select>
              <Option value="未支付">未支付</Option>
              <Option value="部分支付">部分支付</Option>
              <Option value="已支付">已支付</Option>
              <Option value="逾期">逾期</Option>
            </Select>
          </Form.Item>

          <Form.Item name="payment_date" label="支付日期">
            <DatePicker className={styles.fullWidthInput} />
          </Form.Item>

          <Form.Item name="payment_method" label="支付方式">
            <Select placeholder="请选择支付方式">
              <Option value="现金">现金</Option>
              <Option value="银行转账">银行转账</Option>
              <Option value="支票">支票</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Form.Item>

          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="请输入备注信息" />
          </Form.Item>

          <Form.Item>
            <Space className={styles.modalFooterActions}>
              <Button onClick={() => setUiState(prev => ({ ...prev, showBatchModal: false }))}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                确认更新
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default RentLedgerPage;
