import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Link, useSearchParams } from 'react-router-dom';
import { Alert, Button } from 'antd';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import {
  assetLedgerService,
  businessToday,
  commandKey,
  isLedgerForbidden,
} from '@/services/assetLedgerService';
import type { LedgerType, RentEntry, LedgerRow, RentImpact } from '@/services/assetLedgerService';
import styles from './LedgersPage.module.css';

const STATUS: Record<RentEntry['status'], string> = {
  upcoming: '未到付款月',
  unpaid: '待登记',
  partial: '部分完成',
  overdue: '已逾期',
  paid: '已结清',
  void: '已作废',
};
const WARNINGS: Record<string, string> = {
  RENT_SCHEDULE_GAP: '合同期限内存在未核对租金阶段的期间',
  RENT_LEDGER_PLAN_MISMATCH: '已登记金额与当前合同条款不一致，请核对原登记',
};
export function money(value: number): string {
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function errorText(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请重试';
}

export function RentImpactSummary({ impact }: { impact: RentImpact }): React.ReactElement {
  return (
    <p>
      租金影响：新增 {impact.created_count} 期、更新 {impact.updated_count} 期、作废{' '}
      {impact.voided_count} 期、恢复 {impact.restored_count} 期；需核对{' '}
      {impact.mismatched_entry_ids.length} 期。
    </p>
  );
}

export function RentEntryPanel({
  entry,
  onChanged,
}: {
  entry: RentEntry;
  onChanged: () => void;
}): React.ReactElement {
  const form = useForm({
    defaultValues: {
      amount: String(entry.remaining_amount),
      occurredOn: businessToday(),
      documentId: '',
      reason: '',
    },
  });
  const values = form.watch();
  const [notice, setNotice] = useState('');
  const records = entry.records ?? [];
  const reversed = new Set(
    records.flatMap(record =>
      record.reverses_record_id == null ? [] : [record.reverses_record_id]
    )
  );
  const recordType =
    entry.entry_type === 'upstream_payable'
      ? 'payment'
      : entry.entry_type === 'owner_receipt_expected'
        ? 'owner_reported_receipt'
        : 'receipt';
  const mutation = useMutation({
    mutationFn: async (action: {
      type: 'record' | 'reverse' | 'void';
      id?: string;
    }): Promise<unknown> => {
      if (action.type === 'record')
        return assetLedgerService.record(
          entry.id,
          {
            record_type: recordType,
            amount: values.amount,
            occurred_on: values.occurredOn,
            expected_version: entry.version,
            ...(values.documentId.trim() !== '' ? { document_id: values.documentId.trim() } : {}),
          },
          commandKey()
        );
      if (action.type === 'reverse')
        return assetLedgerService.reverse(
          action.id ?? '',
          { reason: values.reason.trim(), expected_version: entry.version },
          commandKey()
        );
      return assetLedgerService.voidEntry(
        entry.id,
        { reason: values.reason.trim(), expected_version: entry.version },
        commandKey()
      );
    },
    retry: false,
    onSuccess: () => {
      setNotice('登记已保存，金额和状态已重新计算。');
      onChanged();
    },
  });
  return (
    <section className={styles.panel} aria-label="账期详情">
      <h2>
        {entry.period} · {STATUS[entry.status]}
      </h2>
      <p>
        账期 {entry.period_start} 至 {entry.period_end} · 到期日 {entry.due_date}
      </p>
      <div className={styles.summary}>
        <span>应付／应收 {money(entry.due_amount)}</span>
        <span>有效登记 {money(entry.effective_paid_amount)}</span>
        <strong>剩余 {money(entry.remaining_amount)}</strong>
      </div>
      {entry.basis_note != null ? <p>依据：{entry.basis_note}</p> : null}
      {(entry.warnings ?? []).map(code => (
        <Alert key={code} type="warning" showIcon title={WARNINGS[code] ?? code} />
      ))}
      {notice !== '' ? <Alert type="success" title={notice} /> : null}
      {mutation.isError ? <Alert type="error" showIcon title={errorText(mutation.error)} /> : null}
      <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
        {entry.status !== 'void' && entry.remaining_amount > 0 ? (
          <form
            onSubmit={event =>
              void form.handleSubmit(() => mutation.mutate({ type: 'record' }))(event)
            }
            className={styles.grid}
          >
            <label className={styles.field}>
              登记金额
              <input
                type="number"
                min="0.01"
                max={entry.remaining_amount}
                step="0.01"
                required
                {...form.register('amount')}
              />
            </label>
            <label className={styles.field}>
              实际发生日期
              <input type="date" required {...form.register('occurredOn')} />
            </label>
            <label className={styles.field}>
              凭证编号（可选）
              <input {...form.register('documentId')} />
            </label>
            <div>
              <Button htmlType="submit" type="primary" loading={mutation.isPending}>
                {recordType === 'payment'
                  ? '登记付款'
                  : recordType === 'owner_reported_receipt'
                    ? '登记产权方报告到账'
                    : '登记到账'}
              </Button>
            </div>
          </form>
        ) : null}
        <label className={styles.field}>
          撤销或作废原因
          <input {...form.register('reason')} />
        </label>
        {entry.origin !== 'generated' && entry.status !== 'void' ? (
          <div>
            <Button
              disabled={
                values.reason.trim() === '' || entry.effective_paid_amount > 0 || mutation.isPending
              }
              onClick={() => mutation.mutate({ type: 'void' })}
            >
              作废手工义务
            </Button>
          </div>
        ) : null}
      </CapabilityGuard>
      <h3>登记与撤销记录</h3>
      {records.length === 0 ? (
        <p className={styles.muted}>本期尚无登记。</p>
      ) : (
        records.map(record => (
          <div className={styles.record} key={record.id}>
            <span>
              {record.occurred_on} ·{' '}
              {record.record_type === 'reversal' ? '撤销登记' : '付款／到账登记'} ·{' '}
              {money(record.amount)}
              {reversed.has(record.id) ? ' · 已撤销' : ''}
              {record.reason != null ? ` · ${record.reason}` : ''} · 操作者 {record.created_by}
            </span>
            {record.record_type !== 'reversal' && !reversed.has(record.id) ? (
              <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
                <Button
                  disabled={values.reason.trim() === '' || mutation.isPending}
                  onClick={() => mutation.mutate({ type: 'reverse', id: record.id })}
                >
                  撤销该笔登记
                </Button>
              </CapabilityGuard>
            ) : null}
          </div>
        ))
      )}
    </section>
  );
}

function ManualEntryForm({
  rows,
  onChanged,
}: {
  rows: LedgerRow[];
  onChanged: () => void;
}): React.ReactElement {
  const form = useForm({
    defaultValues: {
      contractId: '',
      origin: 'manual',
      periodStart: '',
      periodEnd: '',
      dueDate: '',
      amount: '',
      basis: '',
    },
  });
  const values = form.watch();
  const mutation = useMutation({
    mutationFn: () => {
      const contract = rows.find(row => row.contract_id === values.contractId);
      if (contract == null) throw new Error('请选择合同');
      return assetLedgerService.createManual(
        {
          contract_kind: contract.contract_kind,
          contract_id: contract.contract_id,
          origin: values.origin === 'clawback' ? 'clawback' : 'manual',
          amount: values.amount,
          basis_note: values.basis,
          ...(values.origin === 'manual'
            ? {
                period_start: values.periodStart,
                period_end: values.periodEnd,
                due_date: values.dueDate,
              }
            : {}),
        },
        commandKey()
      );
    },
    retry: false,
    onSuccess: () => {
      form.reset();
      onChanged();
    },
  });
  return (
    <details className={styles.panel}>
      <summary>登记自定义账期或补收免租</summary>
      <form
        className={styles.grid}
        onSubmit={event => void form.handleSubmit(() => mutation.mutate())(event)}
      >
        <label className={styles.field}>
          合同
          <select required {...form.register('contractId')}>
            <option value="">选择合同</option>
            {rows.map(row => (
              <option key={row.contract_id} value={row.contract_id}>
                {row.contract_number}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          登记类型
          <select {...form.register('origin')}>
            <option value="manual">自定义账期</option>
            <option value="clawback">提前退租补收免租</option>
          </select>
        </label>
        {values.origin === 'manual' ? (
          <>
            <label className={styles.field}>
              账期开始
              <input type="date" required {...form.register('periodStart')} />
            </label>
            <label className={styles.field}>
              账期结束
              <input type="date" required {...form.register('periodEnd')} />
            </label>
            <label className={styles.field}>
              到期日
              <input type="date" required {...form.register('dueDate')} />
            </label>
          </>
        ) : (
          <p>补收免租仅适用已提前终止的转租合同，日期由终止事实确定。</p>
        )}
        <label className={styles.field}>
          金额
          <input type="number" min="0.01" step="0.01" required {...form.register('amount')} />
        </label>
        <label className={styles.field}>
          依据说明
          <input required {...form.register('basis')} />
        </label>
        <div>
          <Button htmlType="submit" loading={mutation.isPending}>
            保存手工义务
          </Button>
        </div>
        {mutation.isError ? <Alert type="error" title={errorText(mutation.error)} /> : null}
        {mutation.isSuccess ? <Alert type="success" title="手工义务已保存" /> : null}
      </form>
    </details>
  );
}

export default function LedgersPage(): React.ReactElement {
  const [params, setParams] = useSearchParams();
  const [yearText, setYearText] = useState(businessToday().slice(0, 4));
  const year = Number(yearText);
  const [ledgerType, setLedgerType] = useState<LedgerType>(
    params.get('ledger_type') === 'upstream_rent' ? 'upstream_rent' : 'terminal_rent'
  );
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['rent-ledgers', ledgerType, year],
    queryFn: () => assetLedgerService.getMatrix(ledgerType, year),
    enabled: /^[1-9][0-9]{3}$/.test(yearText),
  });
  const entryId = params.get('entry_id') ?? '';
  const detail = useQuery({
    queryKey: ['rent-ledger-entry', entryId],
    queryFn: () => assetLedgerService.getEntry(entryId),
    enabled: entryId !== '',
  });
  const changed = (): void => {
    void queryClient.invalidateQueries({ queryKey: ['rent-ledgers'] });
    void queryClient.invalidateQueries({ queryKey: ['rent-ledger-entry'] });
  };
  const selectEntry = (id: string): void => {
    const next = new URLSearchParams(params);
    next.set('entry_id', id);
    setParams(next);
  };
  const rows = query.data?.rows ?? [];
  return (
    <div className={styles.page}>
      <h1>租金台账</h1>
      <div className={styles.toolbar}>
        <label className={styles.field}>
          台账类型
          <select
            value={ledgerType}
            onChange={event => {
              setLedgerType(
                event.target.value === 'upstream_rent' ? 'upstream_rent' : 'terminal_rent'
              );
              setParams({});
            }}
          >
            <option value="upstream_rent">承租租金（应付）</option>
            <option value="terminal_rent">终端租金（应收）</option>
          </select>
        </label>
        <label className={styles.field}>
          年份
          <input
            type="number"
            min={1900}
            max={9998}
            value={yearText}
            onChange={event => {
              setYearText(event.target.value);
            }}
          />
        </label>
        <Button onClick={() => void query.refetch()}>刷新台账</Button>
      </div>
      {query.isLoading ? <p role="status">正在读取租金台账…</p> : null}
      {query.isError ? (
        <Alert
          type="error"
          showIcon
          title={
            isLedgerForbidden(query.error)
              ? '暂无台账访问权限'
              : '台账读取失败，请重试；已读取的数据继续保留'
          }
        />
      ) : null}
      {!query.isLoading && !query.isError && rows.length === 0 ? (
        <section className={styles.panel}>
          <h2>本年暂无租金义务</h2>
          <p>请先核对已签合同的租金阶段，自定义账期请登记手工义务。</p>
          <Link to="/asset-operations/contracts/terminal">核对合同租金阶段</Link>
        </section>
      ) : null}
      {query.data != null &&
      !(query.isError && isLedgerForbidden(query.error)) &&
      rows.length > 0 ? (
        <>
          <div className={styles.summary}>
            <strong>全年应付／应收 {money(query.data.total_due_amount)}</strong>
            <span>有效登记 {money(query.data.total_paid_amount)}</span>
            <span>尚未完成 {money(query.data.total_remaining_amount)}</span>
          </div>
          <p className={styles.muted}>
            按账期首月归列，选择金额查看该期条款与登记记录。表格可横向滚动查看全部月份。
          </p>
          <div className={styles.scroll} tabIndex={0} role="region" aria-label="全年租金台账">
            <table className={styles.matrix}>
              <thead>
                <tr>
                  <th scope="col">合同</th>
                  {Array.from({ length: 12 }, (_, index) => (
                    <th
                      key={index}
                      scope="col"
                      className={index + 1 === query.data?.current_month ? styles.current : ''}
                    >
                      {index + 1}月
                    </th>
                  ))}
                  <th scope="col">全年合计</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={row.contract_id}>
                    <th scope="row">
                      <Link
                        to={`/asset-operations/contracts/${row.contract_kind}?contract_id=${encodeURIComponent(row.contract_id)}`}
                      >
                        {row.contract_number}
                      </Link>
                      <div>{row.contract_name}</div>
                    </th>
                    {row.months.map(month => (
                      <td
                        key={month.month}
                        className={
                          month.month === query.data?.current_month
                            ? styles.current
                            : month.month > (query.data?.current_month ?? 0)
                              ? styles.future
                              : ''
                        }
                      >
                        <div className={styles.cell}>
                          {month.entries.length === 0
                            ? month.label
                            : month.entries.map(entry => (
                                <button key={entry.id} onClick={() => selectEntry(entry.id)}>
                                  {money(entry.due_amount)}
                                  <br />
                                  {STATUS[entry.status]}
                                  {entry.remaining_amount > 0 && entry.effective_paid_amount > 0
                                    ? ` · 欠 ${money(entry.remaining_amount)}`
                                    : ''}
                                </button>
                              ))}
                        </div>
                      </td>
                    ))}
                    <td>
                      {money(row.total_due_amount)}
                      <br />
                      未完成 {money(row.total_remaining_amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
        {!(query.isError && isLedgerForbidden(query.error)) && rows.length > 0 ? (
          <ManualEntryForm rows={rows} onChanged={changed} />
        ) : null}
      </CapabilityGuard>
      {detail.isLoading && entryId !== '' ? <p role="status">正在读取账期…</p> : null}
      {detail.isError ? (
        <Alert
          type="error"
          title={
            isLedgerForbidden(detail.error)
              ? '暂无该账期访问权限'
              : '账期读取失败，请重新选择或重试'
          }
        />
      ) : null}
      {detail.data != null &&
      !detail.isError &&
      !(query.isError && isLedgerForbidden(query.error)) ? (
        <RentEntryPanel
          key={`${detail.data.id}-${detail.data.version}`}
          entry={detail.data}
          onChanged={changed}
        />
      ) : null}
    </div>
  );
}
