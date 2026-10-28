import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Alert, Button } from 'antd';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import { assetDepositService } from '@/services/assetDepositService';
import type { DepositDetail } from '@/services/assetDepositService';
import { businessToday, commandKey, isLedgerForbidden } from '@/services/assetLedgerService';
import styles from './LedgersPage.module.css';

const labels: Record<string, string> = {
  collect: '收取押金',
  refund: '退还押金',
  pay: '支付押金',
  recover: '收回押金',
  owner_reported_collect: '登记产权方收取',
  owner_reported_refund: '登记产权方退还',
  forfeit: '押金扣除',
  deduct: '抵扣租金',
  reversal: '撤销',
  receivable_uncollected: '应收未收',
  payable_unpaid: '应付未付',
  refundable_unreturned: '应退未退',
  recoverable_unreceived: '应收回',
  settled: '已结清',
};
const money = (value: number): string =>
  new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value);

export default function ContractDepositPanel({
  kind,
  contractId,
  contractType,
}: {
  kind: 'upstream' | 'terminal';
  contractId: string;
  contractType?: string;
}): React.ReactElement | null {
  const query = useQuery({
    queryKey: ['contract-deposit', kind, contractId],
    enabled: contractType !== 'management_agreement',
    queryFn: async () => {
      const lists = await Promise.all([
        assetDepositService.list(kind, contractId),
        assetDepositService.list(kind, contractId, 'settled'),
      ]);
      const entry = lists.flatMap(list => list.items)[0];
      return entry == null ? null : assetDepositService.detail(entry.id);
    },
  });
  if (contractType === 'management_agreement') return null;
  return (
    <section className={styles.panel}>
      <h3>押金明细</h3>
      {query.isPending ? (
        <p>正在读取押金…</p>
      ) : query.isError ? (
        <Alert
          type="error"
          showIcon
          title={isLedgerForbidden(query.error) ? '没有权限查看押金' : '押金读取失败'}
          action={<Button onClick={() => void query.refetch()}>重试</Button>}
        />
      ) : query.data == null ? (
        <p>尚无押金条目，请先核对合同。</p>
      ) : (
        <DepositContent key={`${query.data.id}-${query.data.version}`} entry={query.data} />
      )}
    </section>
  );
}

function DepositContent({ entry }: { entry: DepositDetail }): React.ReactElement {
  const client = useQueryClient();
  const [reverseId, setReverseId] = useState<string | null>(null);
  const types: string[] = [];
  const offsetTargets = entry.offset_candidates;
  if (
    entry.outstanding_amount > 0 &&
    ['receivable_uncollected', 'payable_unpaid'].includes(entry.status)
  ) {
    types.push(
      entry.contract_kind === 'upstream'
        ? 'pay'
        : entry.collector === 'owner'
          ? 'owner_reported_collect'
          : 'collect'
    );
  }
  if (entry.held_amount > 0) {
    types.push(
      entry.contract_kind === 'upstream'
        ? 'recover'
        : entry.collector === 'owner'
          ? 'owner_reported_refund'
          : 'refund'
    );
    if (entry.ended) {
      types.push('forfeit');
      if (
        entry.contract_kind === 'terminal' &&
        entry.collector === 'operator' &&
        offsetTargets.length > 0
      )
        types.push('deduct');
    }
  }
  const form = useForm({
    defaultValues: {
      recordType: types[0] ?? '',
      amount: entry.outstanding_amount > 0 ? entry.outstanding_amount : entry.held_amount,
      occurredOn: businessToday(),
      reason: '',
      offsetEntryId: '',
    },
  });
  const values = form.watch();
  const requestRef = useRef<{ signature: string; key: string } | null>(null);
  const mutation = useMutation({
    retry: false,
    mutationFn: async () => {
      const payload =
        reverseId != null
          ? { reason: values.reason.trim(), expected_version: entry.version }
          : {
              record_type: values.recordType,
              amount: values.amount,
              occurred_on: values.occurredOn,
              ...(values.recordType === 'deduct'
                ? { offset_ledger_entry_id: values.offsetEntryId }
                : {}),
              ...(values.reason.trim() !== '' ? { reason: values.reason.trim() } : {}),
              expected_version: entry.version,
            };
      const signature = JSON.stringify({ target: reverseId ?? entry.id, payload });
      if (requestRef.current?.signature !== signature)
        requestRef.current = { signature, key: commandKey() };
      if (reverseId != null)
        await assetDepositService.reverse(
          reverseId,
          { reason: values.reason.trim(), expected_version: entry.version },
          requestRef.current.key
        );
      else
        await assetDepositService.record(
          entry.id,
          {
            record_type: values.recordType,
            amount: values.amount,
            occurred_on: values.occurredOn,
            ...(values.recordType === 'deduct'
              ? { offset_ledger_entry_id: values.offsetEntryId }
              : {}),
            ...(values.reason.trim() !== '' ? { reason: values.reason.trim() } : {}),
            expected_version: entry.version,
          },
          requestRef.current.key
        );
    },
    onSuccess: async () => {
      requestRef.current = null;
      await client.invalidateQueries({ queryKey: ['contract-deposit'] });
      await client.invalidateQueries({ queryKey: ['rent-ledgers'] });
    },
  });
  const reversed = new Set(
    entry.records
      .filter(record => record.record_type === 'reversal')
      .map(record => record.reverses_record_id)
  );
  const requiresReason = reverseId != null || values.recordType === 'forfeit';
  return (
    <>
      <p>
        约定 {money(entry.agreed_amount)} · 当前持有 {money(entry.held_amount)}
      </p>
      <p>
        {labels[entry.status] ?? '押金待核对'} {money(entry.outstanding_amount)}
      </p>
      <p>
        续签转入 {money(entry.carried_in_amount)} · 转出 {money(entry.carried_out_amount)}
      </p>
      {entry.read_only ? <Alert type="info" title="已转入续签合同，请在后继合同登记押金" /> : null}
      {entry.ended &&
      !entry.read_only &&
      entry.collector === 'operator' &&
      offsetTargets.length === 0 ? (
        <p>当前合同及续签前合同没有可抵扣的未收租金。</p>
      ) : null}
      <ul>
        {entry.records.map(record => (
          <li key={record.id}>
            {record.occurred_on} · {labels[record.record_type] ?? '押金登记'} {money(record.amount)}
            {record.reason != null ? ` · ${record.reason}` : ''}
            {reversed.has(record.id) ? ' · 已撤销' : ''}
            <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
              {!entry.read_only && record.record_type !== 'reversal' && !reversed.has(record.id) ? (
                <Button
                  onClick={() => {
                    setReverseId(record.id);
                    form.setValue('reason', '');
                  }}
                >
                  撤销这笔登记
                </Button>
              ) : null}
            </CapabilityGuard>
          </li>
        ))}
      </ul>
      <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
        {!entry.read_only && (types.length > 0 || reverseId != null) ? (
          <form onSubmit={form.handleSubmit(() => mutation.mutate())}>
            {reverseId == null ? (
              <>
                <label>
                  押金处理
                  <select {...form.register('recordType')}>
                    {types.map(type => (
                      <option value={type} key={type}>
                        {labels[type]}
                      </option>
                    ))}
                  </select>
                </label>
                {values.recordType === 'deduct' ? (
                  <label>
                    抵扣租金账期
                    <select
                      {...form.register('offsetEntryId', {
                        validate: value => values.recordType !== 'deduct' || value !== '',
                      })}
                    >
                      <option value="">请选择账期</option>
                      {offsetTargets.map(rent => (
                        <option key={rent.id} value={rent.id}>
                          {rent.period_start} 至 {rent.period_end} · 未收{' '}
                          {money(rent.remaining_amount)}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                <label>
                  金额
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    {...form.register('amount', { valueAsNumber: true, required: true, min: 0.01 })}
                  />
                </label>
                <label>
                  发生日期
                  <input type="date" {...form.register('occurredOn', { required: true })} />
                </label>
              </>
            ) : (
              <p>撤销后将保留原登记及本次原因。</p>
            )}
            <label>
              {requiresReason ? '处理原因（必填）' : '处理说明'}
              <input {...form.register('reason')} />
            </label>
            {mutation.isError ? (
              <Alert
                type="error"
                title={mutation.error instanceof Error ? mutation.error.message : '押金处理失败'}
              />
            ) : null}
            <Button
              htmlType="submit"
              type="primary"
              loading={mutation.isPending}
              disabled={
                mutation.isPending ||
                (requiresReason && values.reason.trim() === '') ||
                (reverseId == null &&
                  values.recordType === 'deduct' &&
                  values.offsetEntryId === '') ||
                (reverseId == null && (!Number.isFinite(values.amount) || values.amount <= 0))
              }
            >
              {reverseId != null ? '确认撤销登记' : '登记押金处理'}
            </Button>
            {reverseId != null ? (
              <Button onClick={() => setReverseId(null)}>取消撤销</Button>
            ) : null}
          </form>
        ) : null}
      </CapabilityGuard>
    </>
  );
}
