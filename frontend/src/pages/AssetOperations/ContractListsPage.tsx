/**
 * 资产运营 · 上游/终端合同列表（共享骨架）
 *
 * 两个路由复用同一页面骨架：表格四态分离 + 常驻详情栏（条款、覆盖单元、
 * 版本链、生命周期事件）。选中行同步 URL；数据走 React Query。
 */

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Button, Segmented, Table, Tag, Input } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type {
  TerminalContractListItem,
  UpstreamContractListItem,
} from '@/services/assetOperationsService';

import styles from './ContractListsPage.module.css';
import ChangeTimelinePanel from './ChangeTimelinePanel';
import OwnerPartySelect from './OwnerPartySelect';
import ContractRentPanel from './ContractRentPanel';
import ContractDepositPanel from './ContractDepositPanel';
import ContractScanPanel from './ContractScanPanel';
import ContractSupplementsPanel from './ContractSupplementsPanel';
import HandoverDocumentsPanel from './HandoverDocumentsPanel';

const PAGE_SIZE = 20;

const UPSTREAM_STATUS_LABELS: Record<UpstreamContractListItem['status'], string> = {
  scheduled: '待生效',
  active: '履行中',
  expiring: '即将到期',
  expired_pending_action: '已到期待处理',
  exited: '已退出',
  historical: '历史版本',
};

const TERMINAL_STATUS_LABELS: Record<TerminalContractListItem['status'], string> = {
  scheduled: '待生效',
  active: '履行中',
  expiring: '即将到期',
  ended: '已结束',
  historical: '历史版本',
};

export function isScopeForbidden(error: unknown): boolean {
  return (
    error instanceof AssetOperationsError &&
    (error.code === 'PARTY_SCOPE_MISSING' || error.code === 'ASSET_OPS_PERMISSION_DENIED')
  );
}

function formatMoney(value: number): string {
  return `¥${value.toLocaleString('zh-CN')}`;
}

function ChainRow(props: {
  chain: { contractId: string; contractNumber: string; relation: string }[];
  currentId: string;
}): React.ReactElement {
  return (
    <div className={styles.chainRow}>
      {props.chain.length === 0 ? (
        <span>—</span>
      ) : (
        props.chain.map(node => (
          <span
            key={node.contractId}
            className={
              node.contractId === props.currentId
                ? `${styles.chainNode} ${styles.chainNodeCurrent}`
                : styles.chainNode
            }
          >
            {node.relation === 'predecessor' ? '← ' : node.relation === 'successor' ? '→ ' : ''}
            {node.contractNumber}
          </span>
        ))
      )}
    </div>
  );
}

function ContractDetailRows(props: {
  rows: { label: string; value: React.ReactNode }[];
}): React.ReactElement {
  return (
    <div>
      {props.rows.map(row => (
        <div className={styles.fieldRow} key={row.label}>
          <span className={styles.fieldLabel}>{row.label}</span>
          <span className={styles.fieldValue}>{row.value}</span>
        </div>
      ))}
    </div>
  );
}

export function UpstreamContractsPage(): React.ReactElement {
  return <UpstreamList title="上游合同" statusLabels={UPSTREAM_STATUS_LABELS} />;
}

export function TerminalContractsPage(): React.ReactElement {
  return <TerminalList title="终端合同" statusLabels={TERMINAL_STATUS_LABELS} />;
}

function UpstreamList(props: {
  title: string;
  statusLabels: Record<UpstreamContractListItem['status'], string>;
}): React.ReactElement {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [ownerPartyId, setOwnerPartyId] = useState<string | undefined>();
  const [pagination, setPagination] = useState({ current: 1, pageSize: PAGE_SIZE });

  const listQuery = useQuery({
    queryKey: [
      'asset-operations-upstream-contracts',
      appliedSearch,
      ownerPartyId ?? '',
      pagination.current,
    ],
    queryFn: () =>
      assetOperationsService.listUpstreamContracts({
        q: appliedSearch.trim() === '' ? undefined : appliedSearch.trim(),
        ownerPartyId,
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });
  const selectedId = searchParams.get('contract_id') ?? '';
  const detailQuery = useQuery({
    queryKey: ['asset-operations-upstream-contract', selectedId],
    queryFn: () => assetOperationsService.getUpstreamContract(selectedId),
    enabled: selectedId !== '',
  });

  const columns: ColumnsType<UpstreamContractListItem> = useMemo(
    () => [
      { title: '合同编号', dataIndex: 'contractNumber', key: 'contractNumber' },
      {
        title: '类型',
        dataIndex: 'contractType',
        key: 'contractType',
        render: (_: unknown, record) =>
          record.contractType === 'lease' ? '承租合同' : '委托管理协议',
      },
      { title: '名称', dataIndex: 'name', key: 'name' },
      {
        title: '状态',
        key: 'status',
        render: (_: unknown, record) => (
          <Tag color={record.status === 'active' ? 'blue' : 'default'}>
            {props.statusLabels[record.status]}
          </Tag>
        ),
      },
      {
        title: '期限',
        key: 'term',
        render: (_: unknown, record) => `${record.startDate} ~ ${record.endDate}`,
      },
    ],
    [props.statusLabels]
  );

  const items = listQuery.data?.items ?? [];
  const detail = detailQuery.data ?? null;

  return (
    <ContractPageShell
      title={props.title}
      extra={
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <OwnerPartySelect
            value={ownerPartyId}
            onChange={value => {
              setOwnerPartyId(value);
              setPagination(previous => ({ ...previous, current: 1 }));
            }}
          />
          <Button
            type="primary"
            onClick={() => {
              navigate('/asset-operations/contracts/intake?contract_type=upstream_lease');
            }}
          >
            ＋ 录入已签合同
          </Button>
        </div>
      }
      searchProps={{
        searchText,
        setSearchText,
        appliedSearch,
        setAppliedSearch,
        setPagination,
      }}
      listQueryState={{
        isLoading: listQuery.isLoading,
        isError: listQuery.isError,
        error: listQuery.error,
        emptyText: '暂无上游合同，请先经录入会话登记已签合同。',
      }}
      columns={columns}
      items={items}
      total={listQuery.data?.total ?? 0}
      pagination={pagination}
      setPagination={setPagination}
      selectedId={selectedId}
      onSelect={contractId => {
        const next = new URLSearchParams(searchParams);
        next.set('contract_id', contractId);
        setSearchParams(next, { replace: true });
      }}
      detailState={{
        isLoading: detailQuery.isLoading,
        isError: detailQuery.isError,
        error: detailQuery.error,
      }}
      detail={
        detail == null ? null : (
          <div>
            <h2 style={{ fontSize: 16, marginTop: 0 }}>
              {detail.contractNumber} · {detail.name}
            </h2>
            <ContractDetailRows
              rows={[
                {
                  label: '类型',
                  value: detail.contractType === 'lease' ? '承租合同' : '委托管理协议',
                },
                { label: '押金', value: formatMoney(detail.depositAmount) },
                ...(detail.contractType === 'lease'
                  ? [
                      { label: '付款周期（只读）', value: detail.paymentCycle ?? '—' },
                      {
                        label: '付款日（只读）',
                        value: detail.paymentDay == null ? '—' : `${detail.paymentDay} 日`,
                      },
                      { label: '付款方式', value: '以租金阶段为准' },
                    ]
                  : []),
                {
                  label: '覆盖单元',
                  value: `${detail.coverages.length} 个`,
                },
                {
                  label: '关联终端',
                  value:
                    detail.terminalContractIds.length === 0
                      ? '暂无'
                      : `${detail.terminalContractIds.length} 份`,
                },
                {
                  label: '生命周期事件',
                  value: `${detail.lifecycleEvents.length} 条`,
                },
              ]}
            />
            <ExpiryBox endDate={detail.endDate} daysToExpiry={detail.daysToExpiry} />
            <ChainRow chain={detail.renewalChain} currentId={detail.id} />
            {detail.contractType === 'lease' && detail.paymentPlan.length > 0 ? (
              <PaymentPlanTable plan={detail.paymentPlan} />
            ) : null}
            {detail.unitsMatrix.length > 0 ? (
              <UnitsMatrixTable rows={detail.unitsMatrix} />
            ) : null}
            <ChangeTimelinePanel targetType="upstream_contract" targetId={detail.id} />
            <ContractScanPanel kind="upstream" contractId={detail.id} />
            <ContractSupplementsPanel kind="upstream" contractId={detail.id} />
            <HandoverDocumentsPanel kind="upstream" contractId={detail.id} />
            <ContractDepositPanel
              kind="upstream"
              contractId={detail.id}
              contractType={detail.contractType}
            />
            {detail.contractType === 'lease' ? (
              <ContractRentPanel
                key={`${detail.id}-${detail.version}`}
                kind="upstream"
                contractId={detail.id}
                startDate={detail.startDate}
                endDate={detail.endDate}
                schedules={detail.rentSchedules}
                summary={detail.rentSummary}
                canCorrect={detail.status !== 'exited' && detail.status !== 'historical'}
              />
            ) : null}
            <p style={{ marginTop: 8 }}>
              <Link to={`/asset-operations/contracts/upstream/${detail.id}/actions`}>
                退出 / 撤销 / 续签操作
              </Link>
            </p>
          </div>
        )
      }
    />
  );
}

type TerminalViewFilter =
  | 'active'
  | 'expiring_180'
  | 'rent_unpaid'
  | 'deposit_unsettled'
  | 'missing_scan'
  | 'ended';

const TERMINAL_FILTER_LABELS: { value: TerminalViewFilter; label: string }[] = [
  { value: 'active', label: '生效中' },
  { value: 'expiring_180', label: '180 天内到期' },
  { value: 'rent_unpaid', label: '租金未到账' },
  { value: 'deposit_unsettled', label: '押金未结清' },
  { value: 'missing_scan', label: '缺扫描件' },
  { value: 'ended', label: '已结束' },
];

function daysUntil(dateText: string): number {
  const target = new Date(dateText).getTime();
  if (Number.isNaN(target)) {
    return Number.POSITIVE_INFINITY;
  }
  return Math.ceil((target - Date.now()) / 86400000);
}

function TerminalList(props: {
  title: string;
  statusLabels: Record<TerminalContractListItem['status'], string>;
}): React.ReactElement {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [viewFilter, setViewFilter] = useState<TerminalViewFilter>('active');
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [ownerPartyId, setOwnerPartyId] = useState<string | undefined>();
  const [pagination, setPagination] = useState({ current: 1, pageSize: PAGE_SIZE });

  const listQuery = useQuery({
    queryKey: [
      'asset-operations-terminal-contracts',
      appliedSearch,
      ownerPartyId ?? '',
      viewFilter,
      pagination.current,
    ],
    queryFn: () =>
      assetOperationsService.listTerminalContracts({
        filter: viewFilter,
        q: appliedSearch.trim() === '' ? undefined : appliedSearch.trim(),
        ownerPartyId,
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });
  const selectedId = searchParams.get('contract_id') ?? '';
  const detailQuery = useQuery({
    queryKey: ['asset-operations-terminal-contract', selectedId],
    queryFn: () => assetOperationsService.getTerminalContract(selectedId),
    enabled: selectedId !== '',
  });

  const columns: ColumnsType<TerminalContractListItem> = useMemo(
    () => [
      {
        title: '终端租户 · 合同号',
        key: 'tenant',
        render: (_: unknown, record: TerminalContractListItem) => (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
            <span style={{ fontWeight: 500 }}>
              {record.tenantPartyName !== '' ? record.tenantPartyName : record.tenantPartyId}
            </span>
            <span
              style={{
                fontSize: 12,
                color: 'var(--color-text-secondary)',
                fontFamily: 'ui-monospace, Menlo, monospace',
              }}
            >
              {record.contractNumber}
            </span>
          </div>
        ),
      },
      {
        title: '资产单元',
        key: 'units',
        render: (_: unknown, record: TerminalContractListItem) =>
          record.unitLabels.length === 0
            ? '—'
            : record.unitLabels.length === 1
              ? record.unitLabels[0]
              : `${record.unitLabels[0]} 等（合并 ${record.unitLabels.length}）`,
      },
      {
        title: '模式',
        dataIndex: 'contractMode',
        key: 'contractMode',
        width: 100,
        render: (_: unknown, record) =>
          record.contractMode === 'sublease' ? '转租' : '产权方直签',
      },
      {
        title: '上游合同',
        key: 'upstream',
        render: (_: unknown, record: TerminalContractListItem) =>
          record.upstreamContractId == null ? (
            <span style={{ color: 'var(--color-warning, #874d00)' }}>未录入</span>
          ) : (
            (record.upstreamContractNumber ?? record.upstreamContractId)
          ),
      },
      {
        title: '租期至',
        key: 'endDate',
        width: 130,
        render: (_: unknown, record: TerminalContractListItem) => {
          const overrun = record.warnings.some(
            warning => warning.code === 'TERMINAL_TERM_EXCEEDS_UPSTREAM'
          );
          const left = daysUntil(record.endDate);
          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <span
                style={
                  overrun
                    ? { color: 'var(--color-error, #cf1322)', fontWeight: 600 }
                    : left <= 90
                      ? { color: 'var(--color-warning, #874d00)' }
                      : undefined
                }
              >
                {record.endDate}
              </span>
              {overrun ? (
                <span style={{ fontSize: 12, color: 'var(--color-error, #cf1322)' }}>
                  租期越界
                </span>
              ) : null}
            </div>
          );
        },
      },
      {
        title: '月租金',
        key: 'rent',
        align: 'right',
        width: 120,
        render: (_: unknown, record: TerminalContractListItem) => (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1, alignItems: 'flex-end' }}>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>
              {record.currentMonthlyRent != null ? formatMoney(record.currentMonthlyRent) : '—'}
            </span>
            {record.currentMonthCollectionStatus === 'unpaid' ? (
              <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>本月未到账</span>
            ) : record.currentMonthCollectionStatus === 'partial' ? (
              <span style={{ fontSize: 12, color: 'var(--color-warning, #874d00)' }}>
                部分到账 · 欠 {formatMoney(record.currentMonthRemaining ?? 0)}
              </span>
            ) : record.currentMonthCollectionStatus === 'paid' ? (
              <span style={{ fontSize: 12, color: 'var(--color-success, #237804)' }}>本月已到账</span>
            ) : null}
          </div>
        ),
      },
      {
        title: '押金 / 保证金',
        key: 'deposit',
        align: 'right',
        width: 130,
        render: (_: unknown, record: TerminalContractListItem) => (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1, alignItems: 'flex-end' }}>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>
              {record.depositAmount > 0 ? formatMoney(record.depositAmount) : '—'}
            </span>
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              {record.rentCollector === 'operator' ? '本公司收取' : '产权方收取'}
            </span>
          </div>
        ),
      },
      {
        title: '状态',
        key: 'status',
        width: 90,
        render: (_: unknown, record) => (
          <div>
            <Tag color={record.status === 'active' ? 'blue' : 'default'}>
              {props.statusLabels[record.status]}
            </Tag>
          </div>
        ),
      },
      {
        title: '扫描件',
        key: 'scan',
        width: 70,
        align: 'center',
        render: (_: unknown, record: TerminalContractListItem) =>
          record.hasScan ? (
            '有'
          ) : (
            <span style={{ color: 'var(--color-error, #cf1322)' }}>缺</span>
          ),
      },
    ],
    [props.statusLabels]
  );

  const items = listQuery.data?.items ?? [];
  const detail = detailQuery.data ?? null;

  const counts = listQuery.data?.counts ?? null;
  const countFor = (value: TerminalViewFilter): number | null => {
    if (counts == null) {
      return null;
    }
    if (value === 'active') {
      return counts.active;
    }
    if (value === 'expiring_180') {
      return counts.expiring180;
    }
    if (value === 'rent_unpaid') {
      return counts.rentUnpaid;
    }
    if (value === 'deposit_unsettled') {
      return counts.depositUnsettled;
    }
    if (value === 'missing_scan') {
      return counts.missingScan;
    }
    return counts.ended;
  };

  return (
    <ContractPageShell
      title={props.title}
      filterBar={
        <Segmented
          aria-label="终端合同视图筛选"
          value={viewFilter}
          onChange={value => {
            setViewFilter(value as TerminalViewFilter);
            setPagination(previous => ({ ...previous, current: 1 }));
          }}
          options={TERMINAL_FILTER_LABELS.map(option => ({
            value: option.value,
            label: `${option.label}${countFor(option.value) != null ? ` ${countFor(option.value)}` : ''}`,
          }))}
        />
      }
      extra={
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <OwnerPartySelect
            value={ownerPartyId}
            onChange={value => {
              setOwnerPartyId(value);
              setPagination(previous => ({ ...previous, current: 1 }));
            }}
          />
          <Button
            type="primary"
            onClick={() => {
              navigate('/asset-operations/contracts/intake?contract_type=terminal');
            }}
          >
            ＋ 录入已签合同
          </Button>
        </div>
      }
      searchPlaceholder="搜租户、单元、合同号（含已结束）"
      searchProps={{
        searchText,
        setSearchText,
        appliedSearch,
        setAppliedSearch,
        setPagination,
      }}
      listQueryState={{
        isLoading: listQuery.isLoading,
        isError: listQuery.isError,
        error: listQuery.error,
        emptyText: '暂无终端合同，请先经录入会话登记已签合同。',
      }}
      columns={columns}
      items={items}
      total={listQuery.data?.total ?? 0}
      pagination={pagination}
      setPagination={setPagination}
      selectedId={selectedId}
      onSelect={contractId => {
        const next = new URLSearchParams(searchParams);
        next.set('contract_id', contractId);
        setSearchParams(next, { replace: true });
      }}
      detailState={{
        isLoading: detailQuery.isLoading,
        isError: detailQuery.isError,
        error: detailQuery.error,
      }}
      detail={
        detail == null ? null : (
          <div>
            <h2 style={{ fontSize: 16, marginTop: 0 }}>{detail.contractNumber}</h2>
            <ContractDetailRows
              rows={[
                {
                  label: '模式',
                  value: detail.contractMode === 'sublease' ? '转租' : '产权方直签',
                },
                { label: '押金', value: formatMoney(detail.depositAmount) },
                {
                  label: '上游合同',
                  value: detail.upstreamContractId ?? '暂无（风险提示）',
                },
                {
                  label: '覆盖单元',
                  value:
                    detail.coverages.length === 0
                      ? '暂无'
                      : detail.coverages.map(coverage => coverage.assetUnitId).join('、'),
                },
                {
                  label: '生命周期事件',
                  value: `${detail.lifecycleEvents.length} 条`,
                },
              ]}
            />
            <ChainRow chain={detail.renewalChain} currentId={detail.id} />
            <ChangeTimelinePanel targetType="terminal_contract" targetId={detail.id} />
            <p style={{ marginTop: 8 }}>
              <Link to={`/asset-operations/contracts/terminal/${detail.id}/actions`}>
                终止 / 撤销 / 续签操作
              </Link>
            </p>
            <ContractRentPanel
              key={`${detail.id}-${detail.version}`}
              kind="terminal"
              contractId={detail.id}
              startDate={detail.startDate}
              endDate={detail.endDate}
              schedules={detail.rentSchedules}
              summary={detail.rentSummary}
              canCorrect={detail.status !== 'ended' && detail.status !== 'historical'}
            />
            <ContractScanPanel kind="terminal" contractId={detail.id} />
            <ContractSupplementsPanel kind="terminal" contractId={detail.id} />
            <HandoverDocumentsPanel kind="terminal" contractId={detail.id} />
            <ContractDepositPanel kind="terminal" contractId={detail.id} />
          </div>
        )
      }
    />
  );
}

interface SearchState {
  searchText: string;
  setSearchText: (value: string) => void;
  appliedSearch: string;
  setAppliedSearch: (value: string) => void;
  setPagination: React.Dispatch<React.SetStateAction<{ current: number; pageSize: number }>>;
}

interface ListQueryState {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  emptyText: string;
}

function ExpiryBox(props: {
  endDate: string;
  daysToExpiry: number | null;
}): React.ReactElement {
  const days = props.daysToExpiry ?? daysUntil(props.endDate);
  if (!Number.isFinite(days)) {
    return <></>;
  }
  const tone =
    days < 0
      ? { background: '#fff1f0', color: '#cf1322', label: `已过 ${-days} 天` }
      : days <= 90
        ? { background: '#fff1f0', color: '#cf1322', label: `剩 ${days} 天` }
        : days <= 180
          ? { background: '#fffbe6', color: '#874d00', label: `剩 ${days} 天` }
          : { background: '#f5f5f5', color: '#595959', label: `剩 ${days} 天` };
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 8,
        padding: '6px 12px',
        borderRadius: 8,
        ...tone,
      }}
      aria-label="到期剩余"
    >
      <span style={{ fontSize: 12 }}>到期</span>
      <b style={{ fontSize: 16, fontVariantNumeric: 'tabular-nums' }}>{tone.label}</b>
      <span style={{ fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>
        {props.endDate}
      </span>
    </div>
  );
}

function PaymentPlanTable(props: {
  plan: UpstreamContractListItem['paymentPlan'];
}): React.ReactElement {
  return (
    <section aria-label="付款计划">
      <b style={{ fontSize: 13 }}>付款计划</b>
      <p
        style={{
          margin: '4px 0 8px',
          fontSize: 12,
          color: 'var(--color-text-secondary)',
        }}
      >
        按合同条款生成 · 递增自动叠加 · 付款在系统外完成，这里只记一笔
      </p>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ color: 'var(--color-text-secondary)' }}>
            <th style={{ textAlign: 'left', padding: '4px 6px' }}>期间</th>
            <th style={{ textAlign: 'right', padding: '4px 6px' }}>月租金</th>
            <th style={{ textAlign: 'right', padding: '4px 6px' }}>期数</th>
            <th style={{ textAlign: 'left', padding: '4px 6px' }}>进度</th>
            <th style={{ textAlign: 'right', padding: '4px 6px' }}>合计</th>
          </tr>
        </thead>
        <tbody>
          {props.plan.map(stage => {
            const percent =
              stage.periodCount > 0
                ? Math.round((stage.paidCount / stage.periodCount) * 100)
                : 0;
            return (
              <tr key={`${stage.stageStart}-${stage.stageEnd}`}>
                <td style={{ padding: '4px 6px' }}>
                  {stage.stageStart.slice(0, 7)} ~ {stage.stageEnd.slice(0, 7)}
                  {stage.note !== '' ? (
                    <span style={{ color: 'var(--color-text-tertiary)' }}>
                      {' '}
                      · {stage.note}
                    </span>
                  ) : null}
                </td>
                <td
                  style={{
                    padding: '4px 6px',
                    textAlign: 'right',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {formatMoney(stage.monthlyRent)}
                </td>
                <td
                  style={{
                    padding: '4px 6px',
                    textAlign: 'right',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {stage.periodCount}
                </td>
                <td style={{ padding: '4px 6px' }}>
                  <div
                    style={{
                      height: 6,
                      borderRadius: 3,
                      background: '#eef0f2',
                      overflow: 'hidden',
                      marginBottom: 2,
                    }}
                  >
                    <div
                      style={{
                        width: `${percent}%`,
                        height: '100%',
                        background: 'var(--ant-color-primary, #0e63e5)',
                      }}
                    />
                  </div>
                  <span
                    style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}
                  >
                    已付 {stage.paidCount}/{stage.periodCount}
                    {stage.nextDueDate != null
                      ? ` · 下期 ${stage.nextDueDate.slice(0, 7)}`
                      : ''}
                  </span>
                </td>
                <td
                  style={{
                    padding: '4px 6px',
                    textAlign: 'right',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {formatMoney(stage.totalAmount)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function UnitsMatrixTable(props: {
  rows: UpstreamContractListItem['unitsMatrix'];
}): React.ReactElement {
  return (
    <section aria-label="资产单元与终端合同">
      <b style={{ fontSize: 13 }}>资产单元与终端合同</b>
      <p
        style={{
          margin: '4px 0 8px',
          fontSize: 12,
          color: 'var(--color-text-secondary)',
        }}
      >
        出租方由上游模式决定：承租→本公司转租；委托→产权方直签
      </p>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ color: 'var(--color-text-secondary)' }}>
            <th style={{ textAlign: 'left', padding: '4px 6px' }}>单元</th>
            <th style={{ textAlign: 'right', padding: '4px 6px' }}>面积㎡</th>
            <th style={{ textAlign: 'left', padding: '4px 6px' }}>终端租户</th>
            <th style={{ textAlign: 'left', padding: '4px 6px' }}>终端合同</th>
            <th style={{ textAlign: 'left', padding: '4px 6px' }}>租期至</th>
            <th style={{ textAlign: 'right', padding: '4px 6px' }}>月租金</th>
            <th style={{ textAlign: 'center', padding: '4px 6px' }}>扫描件</th>
          </tr>
        </thead>
        <tbody>
          {props.rows.map(row => (
            <tr key={row.assetUnitId}>
              <td style={{ padding: '4px 6px' }}>
                {row.unitName}
                <span style={{ color: 'var(--color-text-tertiary)' }}>
                  （{row.unitCode}）
                </span>
              </td>
              <td
                style={{
                  padding: '4px 6px',
                  textAlign: 'right',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {row.rentableArea.toLocaleString('zh-CN', {
                  maximumFractionDigits: 2,
                })}
              </td>
              <td style={{ padding: '4px 6px' }}>
                {row.tenantPartyName != null ? (
                  row.tenantPartyName
                ) : (
                  <span style={{ color: 'var(--color-success, #237804)' }}>
                    空置 · 可租
                  </span>
                )}
              </td>
              <td style={{ padding: '4px 6px' }}>
                {row.terminalContractNumber ?? '—'}
              </td>
              <td style={{ padding: '4px 6px' }}>{row.terminalEndDate ?? '—'}</td>
              <td
                style={{
                  padding: '4px 6px',
                  textAlign: 'right',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {row.monthlyRent != null ? formatMoney(row.monthlyRent) : '—'}
              </td>
              <td style={{ padding: '4px 6px', textAlign: 'center' }}>
                {row.hasScan == null ? (
                  '—'
                ) : row.hasScan ? (
                  '有'
                ) : (
                  <span style={{ color: 'var(--color-error, #cf1322)' }}>缺</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ContractPageShell<T extends { id: string }>(props: {
  extra?: React.ReactNode;
  filterBar?: React.ReactNode;
  title: string;
  searchPlaceholder?: string;
  searchProps: SearchState;
  listQueryState: ListQueryState;
  columns: ColumnsType<T>;
  items: T[];
  total: number;
  pagination: { current: number; pageSize: number };
  setPagination: React.Dispatch<React.SetStateAction<{ current: number; pageSize: number }>>;
  selectedId: string;
  onSelect: (id: string) => void;
  detailState: { isLoading: boolean; isError: boolean; error: unknown };
  detail: React.ReactNode;
}): React.ReactElement {
  const listForbidden = isScopeForbidden(props.listQueryState.error);
  const detailForbidden = isScopeForbidden(props.detailState.error);

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>{props.title}</h1>
      {props.extra}
      {props.filterBar != null ? <div>{props.filterBar}</div> : null}

      {props.listQueryState.isError ? (
        <Alert
          type={listForbidden ? 'warning' : 'error'}
          showIcon
          title={
            listForbidden
              ? '没有可访问的资产范围，请联系管理员配置数据范围。'
              : props.listQueryState.error instanceof Error
                ? props.listQueryState.error.message
                : '合同列表加载失败'
          }
        />
      ) : null}

      <Input.Search
        aria-label={props.searchPlaceholder ?? '搜索合同编号'}
        placeholder={props.searchPlaceholder ?? '搜索合同编号'}
        value={props.searchProps.searchText}
        onChange={event => props.searchProps.setSearchText(event.target.value)}
        onSearch={value => {
          props.searchProps.setAppliedSearch(value);
          props.searchProps.setPagination(previous => ({
            ...previous,
            current: 1,
          }));
        }}
        allowClear
        style={{ maxWidth: 360 }}
      />

      <div className={styles.layout}>
        <Table<T>
          rowKey="id"
          columns={props.columns}
          scroll={{ x: 640 }}
          dataSource={props.items}
          loading={props.listQueryState.isLoading}
          rowClassName={record => (record.id === props.selectedId ? 'ant-table-row-selected' : '')}
          onRow={record => ({ onClick: () => props.onSelect(record.id) })}
          pagination={{
            current: props.pagination.current,
            pageSize: props.pagination.pageSize,
            total: props.total,
            showSizeChanger: false,
            onChange: (page, pageSize) => props.setPagination({ current: page, pageSize }),
          }}
          locale={{
            emptyText: props.listQueryState.isError ? ' ' : props.listQueryState.emptyText,
          }}
        />

        <aside className={styles.detailCard} aria-label="合同详情">
          {props.detailState.isError ? (
            <Alert
              type={detailForbidden ? 'warning' : 'error'}
              showIcon
              title={
                detailForbidden
                  ? '当前合同不在你的数据范围内。'
                  : props.detailState.error instanceof Error
                    ? props.detailState.error.message
                    : '详情加载失败'
              }
            />
          ) : props.detailState.isLoading ? (
            <p>详情加载中…</p>
          ) : (
            (props.detail ?? <p>在左侧选择一份合同查看详情。</p>)
          )}
        </aside>
      </div>
    </div>
  );
}

export default UpstreamContractsPage;
