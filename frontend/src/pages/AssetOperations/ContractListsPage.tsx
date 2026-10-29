/**
 * 资产运营 · 上游/终端合同列表（共享骨架）
 *
 * 两个路由复用同一页面骨架：表格四态分离 + 常驻详情栏（条款、覆盖单元、
 * 版本链、生命周期事件）。选中行同步 URL；数据走 React Query。
 */

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { Alert, Table, Tag, Input } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type {
  TerminalContractListItem,
  UpstreamContractListItem,
} from '@/services/assetOperationsService';

import styles from './ContractListsPage.module.css';
import ContractRentPanel from './ContractRentPanel';
import ContractDepositPanel from './ContractDepositPanel';

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

const WARNING_LABELS: Record<string, string> = {
  UPSTREAM_CONTRACT_MISSING: '暂无上游',
  TERMINAL_TERM_EXCEEDS_UPSTREAM: '租期越界',
  ARCHIVE_DOCUMENT_MISSING: '缺扫描件',
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
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [pagination, setPagination] = useState({ current: 1, pageSize: PAGE_SIZE });

  const listQuery = useQuery({
    queryKey: ['asset-operations-upstream-contracts', appliedSearch, pagination.current],
    queryFn: () =>
      assetOperationsService.listUpstreamContracts({
        q: appliedSearch.trim() === '' ? undefined : appliedSearch.trim(),
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });
  const selectedId = searchParams.get('contract_id') ?? listQuery.data?.items[0]?.id ?? '';
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
            <ChainRow chain={detail.renewalChain} currentId={detail.id} />
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

function TerminalList(props: {
  title: string;
  statusLabels: Record<TerminalContractListItem['status'], string>;
}): React.ReactElement {
  const [searchParams, setSearchParams] = useSearchParams();
  const [rentUnpaid, setRentUnpaid] = useState(false);
  const [depositUnsettled, setDepositUnsettled] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [pagination, setPagination] = useState({ current: 1, pageSize: PAGE_SIZE });

  const listQuery = useQuery({
    queryKey: [
      'asset-operations-terminal-contracts',
      appliedSearch,
      pagination.current,
      rentUnpaid,
      depositUnsettled,
    ],
    queryFn: () =>
      assetOperationsService.listTerminalContracts({
        ...(depositUnsettled
          ? { filter: 'deposit_unsettled' }
          : rentUnpaid
            ? { filter: 'rent_unpaid' }
            : {}),
        q: appliedSearch.trim() === '' ? undefined : appliedSearch.trim(),
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });
  const selectedId = searchParams.get('contract_id') ?? listQuery.data?.items[0]?.id ?? '';
  const detailQuery = useQuery({
    queryKey: ['asset-operations-terminal-contract', selectedId],
    queryFn: () => assetOperationsService.getTerminalContract(selectedId),
    enabled: selectedId !== '',
  });

  const columns: ColumnsType<TerminalContractListItem> = useMemo(
    () => [
      { title: '合同编号', dataIndex: 'contractNumber', key: 'contractNumber' },
      {
        title: '模式',
        dataIndex: 'contractMode',
        key: 'contractMode',
        render: (_: unknown, record) =>
          record.contractMode === 'sublease' ? '转租' : '产权方直签',
      },
      {
        title: '状态',
        key: 'status',
        render: (_: unknown, record) => (
          <div>
            <Tag color={record.status === 'active' ? 'blue' : 'default'}>
              {props.statusLabels[record.status]}
            </Tag>
            {record.warnings.map(warning => (
              <Tag key={warning.code} color="gold">
                {WARNING_LABELS[warning.code] ?? warning.code}
              </Tag>
            ))}
          </div>
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
        <div>
          <label>
            <input
              type="checkbox"
              checked={rentUnpaid}
              onChange={event => {
                setRentUnpaid(event.target.checked);
                setDepositUnsettled(false);
                setPagination(previous => ({ ...previous, current: 1 }));
              }}
            />
            租金未到账
          </label>
          <label>
            <input
              type="checkbox"
              checked={depositUnsettled}
              onChange={event => {
                setDepositUnsettled(event.target.checked);
                setRentUnpaid(false);
                setPagination(previous => ({ ...previous, current: 1 }));
              }}
            />
            押金未结清
          </label>
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

function ContractPageShell<T extends { id: string }>(props: {
  extra?: React.ReactNode;
  title: string;
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
        aria-label="搜索合同编号"
        placeholder="搜索合同编号"
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
