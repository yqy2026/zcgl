import React, { useMemo, useState } from 'react';
import { Alert, Button, Card, DatePicker, Input, Select, Space, Statistic, Table, Tag } from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import dayjs, { type Dayjs } from 'dayjs';
import { PageContainer } from '@/components/Common';
import { ledgerService } from '@/services/ledgerService';
import type { LedgerEntry, LedgerPaymentStatus } from '@/types/ledger';
import { buildQueryScopeKey } from '@/utils/queryScope';
import styles from './FinancialLedgerPage.module.css';

const PAGE_SIZE = 20;

const PAYMENT_STATUS_META: Record<string, { label: string; color: string }> = {
  unpaid: { label: '未收/未付', color: 'default' },
  paid: { label: '已收/已付', color: 'green' },
  overdue: { label: '逾期', color: 'red' },
  partial: { label: '部分收付', color: 'orange' },
  voided: { label: '已作废', color: 'gray' },
};

const PAYMENT_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '未收/未付', value: 'unpaid' },
  { label: '已收/已付', value: 'paid' },
  { label: '逾期', value: 'overdue' },
  { label: '部分收付', value: 'partial' },
  { label: '已作废', value: 'voided' },
];

const formatAmount = (value: string | number): string => {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return String(value);
  }
  return numericValue.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

const resolveCurrentYearMonth = () => dayjs().format('YYYY-MM');

const FinancialLedgerPage: React.FC = () => {
  const queryScopeKey = buildQueryScopeKey();
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [yearMonthRange, setYearMonthRange] = useState<[Dayjs | null, Dayjs | null]>([
    dayjs(resolveCurrentYearMonth()),
    dayjs(resolveCurrentYearMonth()),
  ]);
  const [paymentStatus, setPaymentStatus] = useState<LedgerPaymentStatus | undefined>(undefined);
  const [contractId, setContractId] = useState('');
  const [assetId, setAssetId] = useState('');
  const [partyId, setPartyId] = useState('');
  const [exportError, setExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const yearMonthStart = yearMonthRange[0]?.format('YYYY-MM') ?? undefined;
  const yearMonthEnd = yearMonthRange[1]?.format('YYYY-MM') ?? undefined;
  const normalizedContractId = contractId.trim();
  const normalizedAssetId = assetId.trim();
  const normalizedPartyId = partyId.trim();
  const hasRequiredLedgerFilter =
    yearMonthStart != null ||
    normalizedContractId !== '' ||
    normalizedAssetId !== '' ||
    normalizedPartyId !== '';

  const ledgerQuery = useQuery({
    queryKey: [
      'financial-ledger',
      queryScopeKey,
      offset,
      limit,
      yearMonthStart,
      yearMonthEnd,
      paymentStatus,
      contractId,
      assetId,
      partyId,
    ],
    queryFn: () =>
      ledgerService.getLedgerEntries({
        offset,
        limit,
        year_month_start: yearMonthStart,
        year_month_end: yearMonthEnd,
        payment_status: paymentStatus,
        contract_id: normalizedContractId || undefined,
        asset_id: normalizedAssetId || undefined,
        party_id: normalizedPartyId || undefined,
        include_voided: paymentStatus === 'voided',
      }),
    enabled: hasRequiredLedgerFilter,
  });

  const currentLedgerParams = {
    offset,
    limit,
    year_month_start: yearMonthStart,
    year_month_end: yearMonthEnd,
    payment_status: paymentStatus,
    contract_id: normalizedContractId || undefined,
    asset_id: normalizedAssetId || undefined,
    party_id: normalizedPartyId || undefined,
    include_voided: paymentStatus === 'voided',
  };

  const ledgerItems = hasRequiredLedgerFilter ? (ledgerQuery.data?.items ?? []) : [];
  const amountDueTotal = useMemo(
    () => ledgerItems.reduce((sum, item) => sum + Number(item.amount_due || 0), 0),
    [ledgerItems]
  );
  const paidAmountTotal = useMemo(
    () => ledgerItems.reduce((sum, item) => sum + Number(item.paid_amount || 0), 0),
    [ledgerItems]
  );

  const columns = useMemo<ColumnsType<LedgerEntry>>(
    () => [
      {
        title: '账期',
        dataIndex: 'year_month',
        key: 'year_month',
        width: 110,
      },
      {
        title: '合同',
        dataIndex: 'contract_id',
        key: 'contract_id',
        ellipsis: true,
      },
      {
        title: '到期日',
        dataIndex: 'due_date',
        key: 'due_date',
        width: 130,
      },
      {
        title: '应收/应付',
        dataIndex: 'amount_due',
        key: 'amount_due',
        align: 'right',
        render: (value: string | number, record) => `${formatAmount(value)} ${record.currency_code}`,
      },
      {
        title: '实收/实付',
        dataIndex: 'paid_amount',
        key: 'paid_amount',
        align: 'right',
        render: (value: string | number, record) => `${formatAmount(value)} ${record.currency_code}`,
      },
      {
        title: '状态',
        dataIndex: 'payment_status',
        key: 'payment_status',
        width: 120,
        render: (value: string) => {
          const meta = PAYMENT_STATUS_META[value] ?? { label: value, color: 'default' };
          return <Tag color={meta.color}>{meta.label}</Tag>;
        },
      },
      {
        title: '备注',
        dataIndex: 'notes',
        key: 'notes',
        ellipsis: true,
        render: (value?: string | null) => value ?? '-',
      },
    ],
    []
  );

  const handleTableChange = (pagination: TablePaginationConfig) => {
    const nextPageSize = pagination.pageSize ?? PAGE_SIZE;
    const nextCurrent = pagination.current ?? 1;
    setLimit(nextPageSize);
    setOffset((nextCurrent - 1) * nextPageSize);
  };

  const resetPagination = () => {
    setOffset(0);
    setExportError(null);
  };

  const handleExport = async () => {
    if (!hasRequiredLedgerFilter || isExporting) {
      return;
    }
    setExportError(null);
    setIsExporting(true);
    try {
      const blob = await ledgerService.exportLedgerEntries(currentLedgerParams);
      ledgerService.triggerLedgerDownload(blob);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : '导出财务台账失败');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <PageContainer
      title="财务台账"
      subTitle="跨项目查询合同应收、应付、实收、实付和逾期记录。"
    >
      <Space orientation="vertical" size="large" style={{ width: '100%' }}>
        {ledgerQuery.isError ? (
          <Alert
            type="error"
            showIcon
            title={ledgerQuery.error instanceof Error ? ledgerQuery.error.message : '财务台账加载失败'}
          />
        ) : null}
        {!hasRequiredLedgerFilter ? (
          <Alert
            type="warning"
            showIcon
            title="请至少选择账期、合同、资产或主体后查询财务台账。"
          />
        ) : null}
        {exportError != null ? <Alert type="error" showIcon title={exportError} /> : null}

        <Card className={styles.filterCard}>
          <div className={styles.toolbar}>
            <label className={styles.toolbarItem}>
              <span className={styles.toolbarLabel}>账期范围</span>
              <DatePicker.RangePicker
                picker="month"
                value={yearMonthRange}
                onChange={value => {
                  setYearMonthRange(value ?? [null, null]);
                  resetPagination();
                }}
                style={{ width: '100%' }}
              />
            </label>
            <label className={styles.toolbarItem}>
              <span className={styles.toolbarLabel}>支付状态</span>
              <Select
                value={paymentStatus ?? ''}
                options={PAYMENT_STATUS_OPTIONS}
                onChange={value => {
                  setPaymentStatus(value === '' ? undefined : (value as LedgerPaymentStatus));
                  resetPagination();
                }}
                style={{ width: '100%' }}
              />
            </label>
            <label className={styles.toolbarItem}>
              <span className={styles.toolbarLabel}>合同标识</span>
              <Input
                value={contractId}
                onChange={event => {
                  setContractId(event.target.value);
                  resetPagination();
                }}
                placeholder="按合同筛选"
              />
            </label>
            <label className={styles.toolbarItem}>
              <span className={styles.toolbarLabel}>资产标识</span>
              <Input
                value={assetId}
                onChange={event => {
                  setAssetId(event.target.value);
                  resetPagination();
                }}
                placeholder="按资产筛选"
              />
            </label>
            <label className={styles.toolbarItem}>
              <span className={styles.toolbarLabel}>主体标识</span>
              <Input
                value={partyId}
                onChange={event => {
                  setPartyId(event.target.value);
                  resetPagination();
                }}
                placeholder="按主体筛选"
              />
            </label>
            <Space>
              <Button
                disabled={!hasRequiredLedgerFilter}
                onClick={() => void ledgerQuery.refetch()}
              >
                刷新
              </Button>
              <Button
                disabled={!hasRequiredLedgerFilter}
                loading={isExporting}
                onClick={() => void handleExport()}
              >
                导出
              </Button>
            </Space>
          </div>
        </Card>

        <div className={styles.summaryRow}>
          <Space size="large" wrap>
            <Statistic
              title="当前结果数"
              value={hasRequiredLedgerFilter ? (ledgerQuery.data?.total ?? 0) : 0}
            />
            <Statistic title="本页应收/应付" value={amountDueTotal} precision={2} suffix="元" />
            <Statistic title="本页实收/实付" value={paidAmountTotal} precision={2} suffix="元" />
          </Space>
        </div>

        <Card className={styles.tableCard} title="台账明细">
          <Table<LedgerEntry>
            rowKey="entry_id"
            loading={hasRequiredLedgerFilter && (ledgerQuery.isLoading || ledgerQuery.isFetching)}
            columns={columns}
            dataSource={ledgerItems}
            pagination={{
              current: Math.floor(offset / limit) + 1,
              pageSize: limit,
              total: hasRequiredLedgerFilter ? (ledgerQuery.data?.total ?? 0) : 0,
              showSizeChanger: true,
            }}
            onChange={handleTableChange}
          />
        </Card>
      </Space>
    </PageContainer>
  );
};

export default FinancialLedgerPage;
