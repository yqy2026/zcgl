import React, { useMemo, useState } from 'react';
import {
  Alert,
  App,
  Button,
  Card,
  DatePicker,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Segmented,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { useMutation, useQuery } from '@tanstack/react-query';
import dayjs, { type Dayjs } from 'dayjs';
import { Link, useSearchParams } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import {
  ASSET_ROUTES,
  CONTRACT_CENTER_ROUTES,
  PROJECT_ROUTES,
  SYSTEM_ROUTES,
} from '@/constants/routes';
import { ledgerService } from '@/services/ledgerService';
import type {
  LedgerEntry,
  LedgerFollowUpStatus,
  LedgerListParams,
  LedgerPaymentStatus,
  OperationsLedgerView,
  PaymentAllocationTargetType,
  ServiceFeeLedger,
} from '@/types/ledger';
import { buildQueryScopeKey } from '@/utils/queryScope';
import styles from './OperationsLedgerPage.module.css';

const PAGE_SIZE = 20;

const CONTRACT_LEDGER_VIEWS = new Set<OperationsLedgerView>([
  'terminal_collection',
  'operator_income',
  'operator_cost',
]);

const VIEW_OPTIONS: Array<{ label: string; value: OperationsLedgerView }> = [
  { label: '终端租户收缴', value: 'terminal_collection' },
  { label: '运营方收入', value: 'operator_income' },
  { label: '运营方成本', value: 'operator_cost' },
  { label: '服务费结算', value: 'service_fee_settlement' },
];

const PAYMENT_STATUS_LABELS: Record<
  Exclude<OperationsLedgerView, 'service_fee_settlement'>,
  Record<string, { label: string; color: string }>
> = {
  terminal_collection: {
    unpaid: { label: '未收', color: 'default' },
    paid: { label: '已收', color: 'green' },
    partial: { label: '部分收款', color: 'orange' },
    voided: { label: '已作废', color: 'gray' },
  },
  operator_income: {
    unpaid: { label: '未收', color: 'default' },
    paid: { label: '已收', color: 'green' },
    partial: { label: '部分收款', color: 'orange' },
    voided: { label: '已作废', color: 'gray' },
  },
  operator_cost: {
    unpaid: { label: '未付', color: 'default' },
    paid: { label: '已付', color: 'green' },
    partial: { label: '部分付款', color: 'orange' },
    voided: { label: '已作废', color: 'gray' },
  },
};

const PAYMENT_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '未收/未付', value: 'unpaid' },
  { label: '已收/已付', value: 'paid' },
  { label: '部分收付', value: 'partial' },
  { label: '已作废', value: 'voided' },
];

const FOLLOW_UP_OPTIONS: Array<{ label: string; value: LedgerFollowUpStatus }> = [
  { label: '待跟进', value: 'pending_follow_up' },
  { label: '已联系', value: 'contacted' },
  { label: '承诺付款', value: 'promised_payment' },
  { label: '存在争议', value: 'disputed' },
  { label: '线下已收待登记', value: 'offline_received_pending_entry' },
  { label: '暂缓', value: 'deferred' },
];

const FOLLOW_UP_META: Record<LedgerFollowUpStatus, { label: string; color: string }> = {
  pending_follow_up: { label: '待跟进', color: 'orange' },
  contacted: { label: '已联系', color: 'blue' },
  promised_payment: { label: '承诺付款', color: 'cyan' },
  disputed: { label: '存在争议', color: 'red' },
  offline_received_pending_entry: { label: '线下已收待登记', color: 'purple' },
  deferred: { label: '暂缓', color: 'default' },
};

const SERVICE_FEE_STATUS_META: Record<string, { label: string; color: string }> = {
  unpaid: { label: '未收', color: 'default' },
  paid: { label: '已收', color: 'green' },
  partial: { label: '部分收款', color: 'orange' },
  voided: { label: '已作废', color: 'gray' },
};

interface CashFlowFormValues {
  occurred_on?: Dayjs;
  amount?: number | null;
  counterparty_id?: string;
  target_id?: string;
  year_month?: string;
  notes?: string;
}

interface FollowUpFormValues {
  follow_up_status?: LedgerFollowUpStatus;
  next_follow_up_date?: Dayjs | null;
  follow_up_note?: string;
}

interface ServiceFeeGenerateFormValues {
  contract_group_id?: string;
}

interface ServiceFeeReconcileFormValues {
  reason?: string;
}

const resolveCurrentYearMonth = () => dayjs().format('YYYY-MM');

const normalizeText = (value: string | undefined): string | undefined => {
  const normalized = value?.trim();
  return normalized == null || normalized === '' ? undefined : normalized;
};

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

const getOutstandingAmount = (entry: LedgerEntry): number =>
  Math.max(Number(entry.amount_due || 0) - Number(entry.paid_amount || 0), 0);

const getServiceFeeOutstandingAmount = (entry: ServiceFeeLedger): number =>
  Math.max(Number(entry.amount_due || 0) - Number(entry.paid_amount || 0), 0);

const isDerivedOverdue = (entry: LedgerEntry, view: OperationsLedgerView): boolean => {
  if (view === 'operator_cost' || entry.payment_status === 'voided') {
    return false;
  }
  const dueDate = dayjs(entry.due_date);
  if (!dueDate.isValid() || !dueDate.isBefore(dayjs(), 'day')) {
    return false;
  }
  return Number(entry.paid_amount) < Number(entry.amount_due);
};

const isContractLedgerView = (
  value: OperationsLedgerView
): value is Exclude<OperationsLedgerView, 'service_fee_settlement'> =>
  CONTRACT_LEDGER_VIEWS.has(value);

const OperationsLedgerPage: React.FC = () => {
  const { message } = App.useApp();
  const [searchParams] = useSearchParams();
  const queryScopeKey = buildQueryScopeKey();
  const [cashFlowForm] = Form.useForm<CashFlowFormValues>();
  const [followUpForm] = Form.useForm<FollowUpFormValues>();
  const [serviceFeeGenerateForm] = Form.useForm<ServiceFeeGenerateFormValues>();
  const [serviceFeeReconcileForm] = Form.useForm<ServiceFeeReconcileFormValues>();

  const initialView = searchParams.get('ledger_view') as OperationsLedgerView | null;
  const [activeView, setActiveView] = useState<OperationsLedgerView>(
    initialView != null && VIEW_OPTIONS.some(item => item.value === initialView)
      ? initialView
      : 'terminal_collection'
  );
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [yearMonthRange, setYearMonthRange] = useState<[Dayjs | null, Dayjs | null]>([
    dayjs(resolveCurrentYearMonth()),
    dayjs(resolveCurrentYearMonth()),
  ]);
  const [flowDateRange, setFlowDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);
  const [paymentStatus, setPaymentStatus] = useState<LedgerPaymentStatus | undefined>(undefined);
  const [projectId, setProjectId] = useState(searchParams.get('project_id') ?? '');
  const [contractId, setContractId] = useState(searchParams.get('contract_id') ?? '');
  const [assetId, setAssetId] = useState(searchParams.get('asset_id') ?? '');
  const [partyId, setPartyId] = useState(searchParams.get('party_id') ?? '');
  const [exportError, setExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedEntryIds, setSelectedEntryIds] = useState<React.Key[]>([]);
  const [cashFlowModalOpen, setCashFlowModalOpen] = useState(false);
  const [followUpModalOpen, setFollowUpModalOpen] = useState(false);
  const [serviceFeeReceiptOpen, setServiceFeeReceiptOpen] = useState(false);
  const [serviceFeeReconcileEntry, setServiceFeeReconcileEntry] = useState<ServiceFeeLedger | null>(
    null
  );
  const [serviceFeeGroupId, setServiceFeeGroupId] = useState(
    searchParams.get('contract_group_id') ?? ''
  );

  const yearMonthStart = yearMonthRange[0]?.format('YYYY-MM') ?? undefined;
  const yearMonthEnd = yearMonthRange[1]?.format('YYYY-MM') ?? undefined;
  const flowOccurredOnStart = flowDateRange[0]?.format('YYYY-MM-DD') ?? undefined;
  const flowOccurredOnEnd = flowDateRange[1]?.format('YYYY-MM-DD') ?? undefined;
  const normalizedProjectId = projectId.trim();
  const normalizedContractId = contractId.trim();
  const normalizedAssetId = assetId.trim();
  const normalizedPartyId = partyId.trim();
  const normalizedServiceFeeGroupId = serviceFeeGroupId.trim();
  const isServiceFeeView = activeView === 'service_fee_settlement';
  const hasRequiredLedgerFilter =
    isContractLedgerView(activeView) &&
    (yearMonthStart != null ||
      flowOccurredOnStart != null ||
      flowOccurredOnEnd != null ||
      normalizedProjectId !== '' ||
      normalizedContractId !== '' ||
      normalizedAssetId !== '' ||
      normalizedPartyId !== '');

  const currentLedgerParams = useMemo<LedgerListParams>(
    () => ({
      offset,
      limit,
      ledger_view: isContractLedgerView(activeView) ? activeView : undefined,
      project_id: normalizedProjectId || undefined,
      year_month_start: yearMonthStart,
      year_month_end: yearMonthEnd,
      flow_occurred_on_start: flowOccurredOnStart,
      flow_occurred_on_end: flowOccurredOnEnd,
      payment_status: paymentStatus,
      contract_id: normalizedContractId || undefined,
      asset_id: normalizedAssetId || undefined,
      party_id: normalizedPartyId || undefined,
      include_voided: paymentStatus === 'voided',
    }),
    [
      activeView,
      assetId,
      contractId,
      flowOccurredOnEnd,
      flowOccurredOnStart,
      limit,
      offset,
      partyId,
      paymentStatus,
      projectId,
      yearMonthEnd,
      yearMonthStart,
    ]
  );

  const ledgerQuery = useQuery({
    queryKey: ['operations-ledger', queryScopeKey, activeView, currentLedgerParams],
    queryFn: () => ledgerService.getLedgerEntries(currentLedgerParams),
    enabled: hasRequiredLedgerFilter,
  });

  const serviceFeeQuery = useQuery({
    queryKey: [
      'operations-ledger-service-fees',
      queryScopeKey,
      normalizedServiceFeeGroupId,
      normalizedProjectId,
    ],
    queryFn: () =>
      ledgerService.listServiceFees({
        ...(normalizedServiceFeeGroupId !== ''
          ? { contract_group_id: normalizedServiceFeeGroupId }
          : {}),
        ...(normalizedProjectId !== '' ? { project_id: normalizedProjectId } : {}),
      }),
    enabled: isServiceFeeView && (normalizedServiceFeeGroupId !== '' || normalizedProjectId !== ''),
  });

  const ledgerItems = hasRequiredLedgerFilter ? (ledgerQuery.data?.items ?? []) : [];
  const serviceFeeItems = isServiceFeeView ? (serviceFeeQuery.data ?? []) : [];
  const amountDueTotal = useMemo(
    () => ledgerItems.reduce((sum, item) => sum + Number(item.amount_due || 0), 0),
    [ledgerItems]
  );
  const paidAmountTotal = useMemo(
    () => ledgerItems.reduce((sum, item) => sum + Number(item.paid_amount || 0), 0),
    [ledgerItems]
  );
  const serviceFeeAmountDueTotal = useMemo(
    () => serviceFeeItems.reduce((sum, item) => sum + Number(item.amount_due || 0), 0),
    [serviceFeeItems]
  );
  const serviceFeePaidAmountTotal = useMemo(
    () => serviceFeeItems.reduce((sum, item) => sum + Number(item.paid_amount || 0), 0),
    [serviceFeeItems]
  );
  const selectedEntries = useMemo(() => {
    const selectedIdSet = new Set(selectedEntryIds.map(String));
    return ledgerItems.filter(item => selectedIdSet.has(item.entry_id));
  }, [ledgerItems, selectedEntryIds]);
  const selectedEntry = selectedEntries[0];

  const cashFlowMutation = useMutation({
    mutationFn: async (values: CashFlowFormValues) => {
      const amount = values.amount;
      const occurredOn = values.occurred_on;
      if (amount == null || Number.isNaN(amount) || amount <= 0) {
        throw new Error('请输入有效金额');
      }
      if (occurredOn == null) {
        throw new Error('请选择发生日期');
      }
      const isServiceFeeReceipt = activeView === 'service_fee_settlement';
      const targetId = isServiceFeeReceipt
        ? normalizeText(values.target_id)
        : selectedEntry?.entry_id;
      const yearMonth = isServiceFeeReceipt
        ? normalizeText(values.year_month)
        : selectedEntry?.year_month;
      if (targetId == null || yearMonth == null) {
        throw new Error('缺少分摊目标');
      }

      const flow = await ledgerService.createPaymentFlow({
        flow_type:
          activeView === 'operator_cost'
            ? 'upstream_cost_payment'
            : isServiceFeeReceipt
              ? 'service_fee_receipt'
              : 'terminal_rent_receipt',
        occurred_on: occurredOn.format('YYYY-MM-DD'),
        amount,
        counterparty_id: normalizeText(values.counterparty_id),
        notes: normalizeText(values.notes),
      });

      const targetType: PaymentAllocationTargetType = isServiceFeeReceipt
        ? 'service_fee_ledger'
        : 'contract_ledger_entry';
      await ledgerService.savePaymentFlowAllocations(flow.flow_id, [
        {
          target_type: targetType,
          target_id: targetId,
          year_month: yearMonth,
          amount,
        },
      ]);

      return flow;
    },
    onSuccess: async () => {
      setCashFlowModalOpen(false);
      setServiceFeeReceiptOpen(false);
      setSelectedEntryIds([]);
      cashFlowForm.resetFields();
      if (
        activeView === 'service_fee_settlement' &&
        (normalizedServiceFeeGroupId !== '' || normalizedProjectId !== '')
      ) {
        await serviceFeeQuery.refetch();
      } else if (activeView !== 'service_fee_settlement') {
        await ledgerQuery.refetch();
      }
      message.success('收付流水已登记');
    },
  });

  const followUpMutation = useMutation({
    mutationFn: async (values: FollowUpFormValues) => {
      if (selectedEntry == null) {
        throw new Error('请选择一条终端收缴台账');
      }
      return ledgerService.updateLedgerEntryFollowUp(selectedEntry.entry_id, {
        follow_up_status: values.follow_up_status ?? null,
        next_follow_up_date: values.next_follow_up_date?.format('YYYY-MM-DD') ?? null,
        follow_up_note: normalizeText(values.follow_up_note) ?? null,
      });
    },
    onSuccess: async () => {
      setFollowUpModalOpen(false);
      followUpForm.resetFields();
      await ledgerQuery.refetch();
      message.success('跟进状态已更新');
    },
  });

  const serviceFeeGenerateMutation = useMutation({
    mutationFn: async (values: ServiceFeeGenerateFormValues) => {
      const contractGroupId = normalizeText(values.contract_group_id);
      if (contractGroupId == null) {
        throw new Error('请填写合同组 ID');
      }
      return ledgerService.generateServiceFees({ contract_group_id: contractGroupId });
    },
    onSuccess: (result, values) => {
      const contractGroupId = normalizeText(values.contract_group_id);
      if (contractGroupId != null) {
        setServiceFeeGroupId(contractGroupId);
        if (contractGroupId === normalizedServiceFeeGroupId) {
          void serviceFeeQuery.refetch();
        }
      }
      serviceFeeGenerateForm.resetFields();
      message.success(
        `服务费已生成：新增 ${result.created}，更新 ${result.updated}，作废 ${result.voided}`
      );
    },
  });

  const serviceFeeReconcileMutation = useMutation({
    mutationFn: async (values: ServiceFeeReconcileFormValues) => {
      if (serviceFeeReconcileEntry == null) {
        throw new Error('请选择服务费台账');
      }
      const reason = normalizeText(values.reason);
      if (reason == null) {
        throw new Error('请填写处理原因');
      }
      return ledgerService.reconcileServiceFeeSource(
        serviceFeeReconcileEntry.service_fee_entry_id,
        { reason }
      );
    },
    onSuccess: async () => {
      setServiceFeeReconcileEntry(null);
      serviceFeeReconcileForm.resetFields();
      await serviceFeeQuery.refetch();
      message.success('服务费台账来源已校准');
    },
  });

  const handleQueryServiceFees = () => {
    serviceFeeGenerateForm
      .validateFields(['contract_group_id'])
      .then(values => {
        const contractGroupId = normalizeText(values.contract_group_id);
        if (contractGroupId != null) {
          setServiceFeeGroupId(contractGroupId);
        }
      })
      .catch(() => undefined);
  };

  const resetPagination = () => {
    setOffset(0);
    setSelectedEntryIds([]);
    setExportError(null);
  };

  const handleTableChange = (pagination: TablePaginationConfig) => {
    const nextPageSize = pagination.pageSize ?? PAGE_SIZE;
    const nextCurrent = pagination.current ?? 1;
    setLimit(nextPageSize);
    setOffset((nextCurrent - 1) * nextPageSize);
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
      setExportError(error instanceof Error ? error.message : '导出经营台账失败');
    } finally {
      setIsExporting(false);
    }
  };

  const openCashFlowModal = () => {
    if (selectedEntry == null) {
      return;
    }
    cashFlowForm.setFieldsValue({
      occurred_on: dayjs(),
      amount: getOutstandingAmount(selectedEntry),
      counterparty_id:
        activeView === 'operator_cost'
          ? (selectedEntry.attributed_owner_party_id ?? undefined)
          : (selectedEntry.attributed_operator_party_id ?? undefined),
      year_month: selectedEntry.year_month,
      target_id: selectedEntry.entry_id,
    });
    setCashFlowModalOpen(true);
  };

  const openServiceFeeReceiptModal = (entry?: ServiceFeeLedger) => {
    cashFlowForm.setFieldsValue({
      occurred_on: dayjs(),
      target_id: entry?.service_fee_entry_id,
      year_month: entry?.year_month,
      amount: entry != null ? getServiceFeeOutstandingAmount(entry) : undefined,
      counterparty_id: entry?.attributed_owner_party_id ?? undefined,
    });
    setServiceFeeReceiptOpen(true);
  };

  const openServiceFeeReconcileModal = (entry: ServiceFeeLedger) => {
    serviceFeeReconcileMutation.reset();
    serviceFeeReconcileForm.resetFields();
    setServiceFeeReconcileEntry(entry);
  };

  const openFollowUpModal = () => {
    if (selectedEntry == null) {
      return;
    }
    followUpForm.setFieldsValue({
      follow_up_status: selectedEntry.follow_up_status ?? undefined,
      next_follow_up_date:
        selectedEntry.next_follow_up_date != null ? dayjs(selectedEntry.next_follow_up_date) : null,
      follow_up_note: selectedEntry.follow_up_note ?? undefined,
    });
    setFollowUpModalOpen(true);
  };

  const columns = useMemo<ColumnsType<LedgerEntry>>(() => {
    const statusMeta =
      activeView !== 'service_fee_settlement'
        ? PAYMENT_STATUS_LABELS[activeView]
        : PAYMENT_STATUS_LABELS.terminal_collection;
    const amountTitle = activeView === 'operator_cost' ? '应付' : '应收';
    const paidTitle = activeView === 'operator_cost' ? '实付' : '实收';
    const columnsForView: ColumnsType<LedgerEntry> = [
      {
        title: '账期',
        dataIndex: 'year_month',
        key: 'year_month',
        width: 110,
      },
      {
        title: '合同/协议',
        dataIndex: 'contract_id',
        key: 'contract_id',
        ellipsis: true,
        render: (value: string) => (
          <Link to={`${CONTRACT_CENTER_ROUTES.LIST}?contract_id=${value}`}>{value}</Link>
        ),
      },
      {
        title: '项目',
        dataIndex: 'attributed_project_id',
        key: 'attributed_project_id',
        ellipsis: true,
        render: (value?: string | null) =>
          value != null && value.trim() !== '' ? (
            <Link to={PROJECT_ROUTES.DETAIL(value)}>{value}</Link>
          ) : (
            '-'
          ),
      },
      {
        title: '资产',
        dataIndex: 'attributed_asset_ids',
        key: 'attributed_asset_ids',
        ellipsis: true,
        render: (value?: string[] | null) =>
          (value?.length ?? 0) > 0 ? (
            <Space size="small" wrap>
              {value?.slice(0, 2).map(assetIdValue => (
                <Link key={assetIdValue} to={ASSET_ROUTES.DETAIL(assetIdValue)}>
                  {assetIdValue}
                </Link>
              ))}
            </Space>
          ) : (
            '-'
          ),
      },
      {
        title: '主体',
        key: 'attributed_parties',
        ellipsis: true,
        render: (_, record) => {
          const partyIds = [
            record.attributed_owner_party_id,
            record.attributed_operator_party_id,
          ].filter((value): value is string => value != null && value.trim() !== '');
          return partyIds.length > 0 ? (
            <Space size="small" wrap>
              {Array.from(new Set(partyIds)).map(partyIdValue => (
                <Link key={partyIdValue} to={SYSTEM_ROUTES.PARTY_DETAIL(partyIdValue)}>
                  {partyIdValue}
                </Link>
              ))}
            </Space>
          ) : (
            '-'
          );
        },
      },
      {
        title: '到期日',
        dataIndex: 'due_date',
        key: 'due_date',
        width: 130,
      },
      {
        title: amountTitle,
        dataIndex: 'amount_due',
        key: 'amount_due',
        align: 'right',
        render: (value: string | number, record) =>
          `${formatAmount(value)} ${record.currency_code}`,
      },
      {
        title: paidTitle,
        dataIndex: 'paid_amount',
        key: 'paid_amount',
        align: 'right',
        render: (value: string | number, record) =>
          `${formatAmount(value)} ${record.currency_code}`,
      },
      {
        title: '状态',
        dataIndex: 'payment_status',
        key: 'payment_status',
        width: 120,
        render: (value: string, record) => {
          const meta = isDerivedOverdue(record, activeView)
            ? { label: '逾期', color: 'red' }
            : (statusMeta[value] ?? { label: value, color: 'default' });
          return <Tag color={meta.color}>{meta.label}</Tag>;
        },
      },
      {
        title: '流水日期',
        dataIndex: 'flow_occurred_on_dates',
        key: 'flow_occurred_on_dates',
        ellipsis: true,
        render: (value?: string[]) => ((value?.length ?? 0) > 0 ? value?.join('；') : '-'),
      },
    ];

    if (activeView === 'terminal_collection') {
      columnsForView.push(
        {
          title: '跟进',
          dataIndex: 'follow_up_status',
          key: 'follow_up_status',
          width: 130,
          render: (value?: LedgerFollowUpStatus | null) => {
            if (value == null) {
              return '-';
            }
            const meta = FOLLOW_UP_META[value];
            return <Tag color={meta.color}>{meta.label}</Tag>;
          },
        },
        {
          title: '下次跟进',
          dataIndex: 'next_follow_up_date',
          key: 'next_follow_up_date',
          width: 130,
          render: (value?: string | null) => value ?? '-',
        }
      );
    }

    return columnsForView;
  }, [activeView]);

  const serviceFeeColumns = useMemo<ColumnsType<ServiceFeeLedger>>(
    () => [
      {
        title: '账期',
        dataIndex: 'year_month',
        key: 'year_month',
        width: 110,
      },
      {
        title: '服务费台账 ID',
        dataIndex: 'service_fee_entry_id',
        key: 'service_fee_entry_id',
        ellipsis: true,
      },
      {
        title: '来源租金台账',
        dataIndex: 'source_ledger_ids',
        key: 'source_ledger_ids',
        ellipsis: true,
        render: (value?: string[]) =>
          (value?.length ?? 0) > 0 ? (
            <Space size="small" wrap>
              {value?.map(sourceLedgerId => (
                <Tag key={sourceLedgerId}>{sourceLedgerId}</Tag>
              ))}
            </Space>
          ) : (
            '-'
          ),
      },
      {
        title: '计算基数',
        dataIndex: 'calculation_base_amount',
        key: 'calculation_base_amount',
        align: 'right',
        render: (value: string | number, record) =>
          `${formatAmount(value)} ${record.currency_code}`,
      },
      {
        title: '费率',
        dataIndex: 'service_fee_ratio',
        key: 'service_fee_ratio',
        align: 'right',
        width: 100,
        render: (value: string | number) => `${(Number(value) * 100).toFixed(2)}%`,
      },
      {
        title: '应收服务费',
        dataIndex: 'amount_due',
        key: 'amount_due',
        align: 'right',
        render: (value: string | number, record) =>
          `${formatAmount(value)} ${record.currency_code}`,
      },
      {
        title: '实收服务费',
        dataIndex: 'paid_amount',
        key: 'paid_amount',
        align: 'right',
        render: (value: string | number, record) =>
          `${formatAmount(value)} ${record.currency_code}`,
      },
      {
        title: '状态',
        dataIndex: 'payment_status',
        key: 'payment_status',
        width: 120,
        render: (value: string) => {
          const meta = SERVICE_FEE_STATUS_META[value] ?? { label: value, color: 'default' };
          return <Tag color={meta.color}>{meta.label}</Tag>;
        },
      },
      {
        title: '操作',
        key: 'actions',
        width: 190,
        render: (_, record) => (
          <Space size="small">
            <Button
              type="link"
              disabled={
                record.payment_status === 'voided' || getServiceFeeOutstandingAmount(record) <= 0
              }
              onClick={() => openServiceFeeReceiptModal(record)}
            >
              登记收款
            </Button>
            <Button
              type="link"
              disabled={record.payment_status === 'voided'}
              onClick={() => openServiceFeeReconcileModal(record)}
            >
              校准来源
            </Button>
          </Space>
        ),
      },
    ],
    [openServiceFeeReceiptModal, openServiceFeeReconcileModal]
  );

  const selectedCanRegisterFlow =
    selectedEntry != null &&
    selectedEntry.payment_status !== 'voided' &&
    getOutstandingAmount(selectedEntry) > 0 &&
    (activeView === 'terminal_collection' || activeView === 'operator_cost');
  const selectedCanFollowUp =
    selectedEntry != null &&
    selectedEntry.payment_status !== 'voided' &&
    activeView === 'terminal_collection';

  return (
    <PageContainer title="经营台账" subTitle="按经营视图查询收缴、收入、成本和服务费结算。">
      <Space orientation="vertical" size="large" className={styles.pageStack}>
        <Segmented
          value={activeView}
          options={VIEW_OPTIONS}
          onChange={value => {
            setActiveView(value as OperationsLedgerView);
            resetPagination();
          }}
        />

        {ledgerQuery.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              ledgerQuery.error instanceof Error ? ledgerQuery.error.message : '经营台账加载失败'
            }
          />
        ) : null}
        {!isServiceFeeView && !hasRequiredLedgerFilter ? (
          <Alert
            type="warning"
            showIcon
            title="请至少选择账期、项目、合同、资产、主体或流水日期后查询经营台账。"
          />
        ) : null}
        {exportError != null ? <Alert type="error" showIcon title={exportError} /> : null}
        {cashFlowMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              cashFlowMutation.error instanceof Error
                ? cashFlowMutation.error.message
                : '收付流水登记失败'
            }
          />
        ) : null}
        {followUpMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              followUpMutation.error instanceof Error
                ? followUpMutation.error.message
                : '跟进状态维护失败'
            }
          />
        ) : null}
        {serviceFeeGenerateMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              serviceFeeGenerateMutation.error instanceof Error
                ? serviceFeeGenerateMutation.error.message
                : '服务费生成失败'
            }
          />
        ) : null}
        {serviceFeeQuery.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              serviceFeeQuery.error instanceof Error
                ? serviceFeeQuery.error.message
                : '服务费台账加载失败'
            }
          />
        ) : null}

        {!isServiceFeeView ? (
          <>
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
                    className={styles.fullWidthControl}
                  />
                </label>
                <label className={styles.toolbarItem}>
                  <span className={styles.toolbarLabel}>流水日期</span>
                  <DatePicker.RangePicker
                    value={flowDateRange}
                    onChange={value => {
                      setFlowDateRange(value ?? [null, null]);
                      resetPagination();
                    }}
                    className={styles.fullWidthControl}
                  />
                </label>
                <label className={styles.toolbarItem}>
                  <span className={styles.toolbarLabel}>收付状态</span>
                  <Select
                    value={paymentStatus ?? ''}
                    options={PAYMENT_STATUS_OPTIONS}
                    onChange={value => {
                      setPaymentStatus(value === '' ? undefined : (value as LedgerPaymentStatus));
                      resetPagination();
                    }}
                    className={styles.fullWidthControl}
                  />
                </label>
                <label className={styles.toolbarItem}>
                  <span className={styles.toolbarLabel}>项目 ID</span>
                  <Input
                    value={projectId}
                    onChange={event => {
                      setProjectId(event.target.value);
                      resetPagination();
                    }}
                    placeholder="按项目筛选"
                  />
                </label>
                <label className={styles.toolbarItem}>
                  <span className={styles.toolbarLabel}>合同/协议 ID</span>
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
                  <span className={styles.toolbarLabel}>资产 ID</span>
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
                  <span className={styles.toolbarLabel}>主体 ID</span>
                  <Input
                    value={partyId}
                    onChange={event => {
                      setPartyId(event.target.value);
                      resetPagination();
                    }}
                    placeholder="按主体筛选"
                  />
                </label>
                <Space className={styles.toolbarActions}>
                  <Button
                    type="primary"
                    disabled={!selectedCanRegisterFlow}
                    onClick={openCashFlowModal}
                  >
                    {activeView === 'operator_cost' ? '登记付款' : '登记收款'}
                  </Button>
                  <Button disabled={!selectedCanFollowUp} onClick={openFollowUpModal}>
                    维护跟进
                  </Button>
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
                <Statistic
                  title="本页实收/实付"
                  value={paidAmountTotal}
                  precision={2}
                  suffix="元"
                />
              </Space>
            </div>

            <Card className={styles.tableCard} title="台账明细">
              <Table<LedgerEntry>
                rowKey="entry_id"
                loading={
                  hasRequiredLedgerFilter && (ledgerQuery.isLoading || ledgerQuery.isFetching)
                }
                columns={columns}
                dataSource={ledgerItems}
                rowSelection={{
                  type: 'radio',
                  selectedRowKeys: selectedEntryIds,
                  onChange: nextSelectedEntryIds => {
                    setSelectedEntryIds(nextSelectedEntryIds);
                  },
                  getCheckboxProps: record => ({
                    disabled: record.payment_status === 'voided',
                  }),
                }}
                pagination={{
                  current: Math.floor(offset / limit) + 1,
                  pageSize: limit,
                  total: hasRequiredLedgerFilter ? (ledgerQuery.data?.total ?? 0) : 0,
                  showSizeChanger: true,
                }}
                locale={{
                  emptyText: (
                    <Empty description="暂无经营台账记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ),
                }}
                onChange={handleTableChange}
              />
            </Card>
          </>
        ) : (
          <div className={styles.serviceFeeGrid}>
            <Card title="服务费生成与查询">
              <Form form={serviceFeeGenerateForm} layout="vertical">
                <Form.Item
                  label="合同组 ID"
                  name="contract_group_id"
                  rules={[{ required: true, message: '请填写合同组 ID' }]}
                >
                  <Input placeholder="contract_group_id" />
                </Form.Item>
                <Space wrap>
                  <Button onClick={handleQueryServiceFees}>查询来源账期</Button>
                  <Button
                    type="primary"
                    loading={serviceFeeGenerateMutation.isPending}
                    onClick={() => {
                      serviceFeeGenerateForm
                        .validateFields()
                        .then(values => serviceFeeGenerateMutation.mutate(values))
                        .catch(() => undefined);
                    }}
                  >
                    生成服务费
                  </Button>
                </Space>
              </Form>
            </Card>
            <Card title="服务费收款登记">
              <Button type="primary" onClick={() => openServiceFeeReceiptModal()}>
                登记服务费收款
              </Button>
            </Card>
            <Card className={styles.serviceFeeTableCard} title="服务费来源账期">
              <Space size="large" wrap className={styles.serviceFeeSummary}>
                <Statistic title="服务费条目" value={serviceFeeItems.length} />
                <Statistic
                  title="应收服务费"
                  value={serviceFeeAmountDueTotal}
                  precision={2}
                  suffix="元"
                />
                <Statistic
                  title="实收服务费"
                  value={serviceFeePaidAmountTotal}
                  precision={2}
                  suffix="元"
                />
              </Space>
              <Table<ServiceFeeLedger>
                rowKey="service_fee_entry_id"
                loading={serviceFeeQuery.isLoading || serviceFeeQuery.isFetching}
                columns={serviceFeeColumns}
                dataSource={serviceFeeItems}
                pagination={{ pageSize: 10, showSizeChanger: true }}
                locale={{
                  emptyText: (
                    <Empty
                      description={
                        normalizedServiceFeeGroupId === ''
                          ? '请输入合同组 ID 后查询服务费台账'
                          : '暂无服务费台账'
                      }
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                  ),
                }}
              />
            </Card>
          </div>
        )}
      </Space>

      <Modal
        title={activeView === 'operator_cost' ? '登记付款流水' : '登记收款流水'}
        open={cashFlowModalOpen || serviceFeeReceiptOpen}
        okText="登记"
        cancelText="取消"
        confirmLoading={cashFlowMutation.isPending}
        onOk={() => {
          cashFlowForm
            .validateFields()
            .then(values => cashFlowMutation.mutate(values))
            .catch(() => undefined);
        }}
        onCancel={() => {
          setCashFlowModalOpen(false);
          setServiceFeeReceiptOpen(false);
          cashFlowForm.resetFields();
        }}
      >
        <Form form={cashFlowForm} layout="vertical">
          {serviceFeeReceiptOpen ? (
            <>
              <Form.Item
                label="服务费台账 ID"
                name="target_id"
                rules={[{ required: true, message: '请填写服务费台账 ID' }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="账期"
                name="year_month"
                rules={[{ required: true, message: '请填写账期' }]}
              >
                <Input placeholder="YYYY-MM" />
              </Form.Item>
            </>
          ) : null}
          <Form.Item
            label="发生日期"
            name="occurred_on"
            rules={[{ required: true, message: '请选择发生日期' }]}
          >
            <DatePicker className={styles.fullWidthControl} />
          </Form.Item>
          <Form.Item label="金额" name="amount" rules={[{ required: true, message: '请输入金额' }]}>
            <InputNumber min={0} precision={2} className={styles.fullWidthControl} />
          </Form.Item>
          <Form.Item label="对方主体 ID" name="counterparty_id">
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="notes">
            <Input.TextArea rows={3} maxLength={200} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="维护跟进状态"
        open={followUpModalOpen}
        okText="保存"
        cancelText="取消"
        confirmLoading={followUpMutation.isPending}
        onOk={() => {
          followUpForm
            .validateFields()
            .then(values => followUpMutation.mutate(values))
            .catch(() => undefined);
        }}
        onCancel={() => {
          setFollowUpModalOpen(false);
          followUpForm.resetFields();
        }}
      >
        <Form form={followUpForm} layout="vertical">
          <Form.Item label="跟进状态" name="follow_up_status">
            <Select allowClear options={FOLLOW_UP_OPTIONS} />
          </Form.Item>
          <Form.Item label="下次跟进日期" name="next_follow_up_date">
            <DatePicker className={styles.fullWidthControl} />
          </Form.Item>
          <Form.Item label="跟进备注" name="follow_up_note">
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="校准服务费台账来源"
        open={serviceFeeReconcileEntry != null}
        okText="校准"
        cancelText="取消"
        confirmLoading={serviceFeeReconcileMutation.isPending}
        onOk={() => {
          serviceFeeReconcileForm
            .validateFields()
            .then(values => serviceFeeReconcileMutation.mutate(values))
            .catch(() => undefined);
        }}
        onCancel={() => {
          setServiceFeeReconcileEntry(null);
          serviceFeeReconcileForm.resetFields();
          serviceFeeReconcileMutation.reset();
        }}
      >
        {serviceFeeReconcileMutation.isError ? (
          <Alert
            type="error"
            showIcon
            message={
              serviceFeeReconcileMutation.error instanceof Error
                ? serviceFeeReconcileMutation.error.message
                : '服务费来源校准失败'
            }
          />
        ) : null}
        <Form form={serviceFeeReconcileForm} layout="vertical">
          <Form.Item
            label="处理原因"
            name="reason"
            rules={[{ required: true, message: '请填写处理原因' }]}
          >
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default OperationsLedgerPage;
