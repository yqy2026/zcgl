import { useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Alert, Button } from 'antd';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import { managementFeeService, type ManagementFeeStatement } from '@/services/managementFeeService';
import {
  assetLedgerService,
  businessToday,
  commandKey,
  isLedgerForbidden,
} from '@/services/assetLedgerService';
import styles from './ManagementFeeStatementPage.module.css';

const money = (value: number) =>
  value.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' });
const MAX_STAMP_FILE_BYTES = 20 * 1024 * 1024;
const statusNames = {
  collecting: '收租中',
  pending_stamp: '待盖章',
  confirmed: '已确认',
  superseded: '已更正',
};
const errorText = (error: unknown) => (error instanceof Error ? error.message : '操作失败，请重试');

export function capitalMoney(amount: number): string {
  const digits = '零壹贰叁肆伍陆柒捌玖';
  const cents = Math.round(amount * 100);
  const integer = Math.floor(cents / 100);
  const group = (value: number): string => {
    const units = ['', '拾', '佰', '仟'];
    let result = '';
    for (let i = 3; i >= 0; i--) {
      const digit = Math.floor(value / 10 ** i) % 10;
      if (digit > 0) result += `${digits[digit]}${units[i]}`;
      else if (result !== '' && !result.endsWith('零') && value % 10 ** i > 0) result += '零';
    }
    return result;
  };
  let result = '';
  let skippedGroup = false;
  for (let i = 3; i >= 0; i--) {
    const value = Math.floor(integer / 10000 ** i) % 10000;
    if (value > 0) {
      if (result !== '' && (skippedGroup || value < 1000)) result += '零';
      result += `${group(value)}${['', '万', '亿', '万亿'][i]}`;
      skippedGroup = false;
    } else if (result !== '') {
      skippedGroup = true;
    }
  }
  result = `${result === '' ? '零' : result}元`;
  const jiao = Math.floor(cents / 10) % 10;
  const fen = cents % 10;
  if (jiao === 0 && fen === 0) return `${result}整`;
  if (jiao > 0) result += `${digits[jiao]}角`;
  else if (integer > 0) result += '零';
  if (fen > 0) result += `${digits[fen]}分`;
  return result;
}

function StatementActions({
  statement,
  changed,
  denied,
}: {
  statement: ManagementFeeStatement;
  changed: () => void;
  denied: () => void;
}) {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const keys = useRef(new Map<string, string>());
  const stableKey = (action: string, payload: unknown) => {
    const fingerprint = JSON.stringify([action, payload]);
    let key = keys.current.get(fingerprint);
    if (key == null) {
      key = commandKey();
      keys.current.set(fingerprint, key);
    }
    return key;
  };
  const form = useForm({
    defaultValues: { entryId: '', amount: '', date: businessToday(), reason: '' },
  });
  const values = form.watch();
  const selectedLine = statement.lines.find(line => line.rent_ledger_entry_id === values.entryId);
  const canDefer =
    selectedLine != null &&
    selectedLine.deferred_amount > 0 &&
    !selectedLine.processed &&
    selectedLine.deferral_reason == null &&
    businessToday() <= statement.deadline;
  const entry = useQuery({
    queryKey: ['rent-ledger-entry', values.entryId],
    queryFn: () => assetLedgerService.getEntry(values.entryId),
    enabled: values.entryId !== '',
  });
  const correction = useForm({ defaultValues: { reason: '' } });
  const correctionReason = correction.watch('reason');
  const mutation = useMutation({
    mutationFn: async (action: 'upload' | 'confirm' | 'correct' | 'receipt' | 'defer') => {
      if (action === 'upload') {
        if (file == null) throw new Error('请选择盖章文件');
        return managementFeeService.upload(statement.id, file, statement.version);
      }
      if (action === 'confirm') {
        const payload = { expected_version: statement.version };
        return managementFeeService.confirm(statement.id, payload, stableKey(action, payload));
      }
      if (action === 'correct') {
        const payload = { expected_version: statement.version, reason: correctionReason.trim() };
        const result = await managementFeeService.supersede(
          statement.id,
          payload,
          stableKey(action, payload)
        );
        navigate(
          `/asset-operations/management-fees/${encodeURIComponent(result.successor_statement_id)}`
        );
        return result;
      }
      if (action === 'defer') {
        const payload = {
          rent_ledger_entry_id: values.entryId,
          expected_version: statement.version,
          reason: values.reason.trim(),
        };
        return managementFeeService.defer(statement.id, payload, stableKey(action, payload));
      }
      if (entry.data == null || entry.isError) throw new Error('请先读取租金账期后再登记');
      const payload = {
        rent_ledger_entry_id: values.entryId,
        amount: Number(values.amount),
        occurred_on: values.date,
        expected_version: entry.data.version,
      };
      return managementFeeService.record(statement.id, payload, stableKey(action, payload));
    },
    retry: false,
    onSuccess: () => {
      changed();
    },
    onError: error => {
      if (isLedgerForbidden(error)) denied();
    },
  });
  const locked = statement.status === 'confirmed' || statement.status === 'superseded';
  const accessDenied = mutation.isError && isLedgerForbidden(mutation.error);
  return (
    <section className={styles.controls} aria-label="对账操作">
      {mutation.isError ? <Alert type="error" showIcon title={errorText(mutation.error)} /> : null}
      {mutation.isSuccess ? <p role="status">操作已保存，正在读取最新对账单。</p> : null}
      {accessDenied ? null : (
        <>
          {!locked ? (
            <>
              <h2>盖章与确认</h2>
              <p>核对明细后打印，上传双方盖章版本，再确认金额快照。</p>
              <label className={styles.field}>
                盖章文件
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={event => setFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <p>支持 PDF、JPG、PNG，最大 20 MiB。替换文件会保留历史附件。</p>
              <div className={styles.buttons}>
                <Button
                  type="primary"
                  disabled={
                    file == null ||
                    mutation.isPending ||
                    file.size > MAX_STAMP_FILE_BYTES
                  }
                  onClick={() => mutation.mutate('upload')}
                >
                  {statement.stamped_document_id == null ? '上传盖章件' : '替换盖章件'}
                </Button>
                <Button
                  disabled={
                    statement.status !== 'pending_stamp' ||
                    statement.stamped_document_id == null ||
                    mutation.isPending
                  }
                  onClick={() => mutation.mutate('confirm')}
                >
                  确认对账单
                </Button>
              </div>
              {file != null && file.size > MAX_STAMP_FILE_BYTES ? (
                <Alert type="error" title="文件超过 20 MiB，请压缩后重新选择" />
              ) : null}
              <h2>逐户核对</h2>
              <form
                className={styles.form}
                onSubmit={event => void form.handleSubmit(() => mutation.mutate('receipt'))(event)}
              >
                <label className={styles.field}>
                  租金账期
                  <select {...form.register('entryId')} required>
                    <option value="">选择待处理租户账期</option>
                    {statement.lines
                      .filter(line => line.deferred_amount > 0)
                      .map(line => (
                        <option key={line.rent_ledger_entry_id} value={line.rent_ledger_entry_id}>
                          {line.tenant_name_snapshot} · {line.rent_period}
                        </option>
                      ))}
                  </select>
                </label>
                {entry.isLoading ? <p role="status">正在核对账期版本…</p> : null}
                {entry.isError ? <Alert type="error" title={errorText(entry.error)} /> : null}
                <label className={styles.field}>
                  到账金额
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    required
                    {...form.register('amount')}
                  />
                </label>
                <label className={styles.field}>
                  到账日期
                  <input type="date" required {...form.register('date')} />
                </label>
                <Button
                  htmlType="submit"
                  disabled={entry.data == null || entry.isError || mutation.isPending}
                >
                  登记产权方到账
                </Button>
                <label className={styles.field}>
                  顺延原因
                  <input {...form.register('reason')} />
                </label>
                <Button
                  disabled={!canDefer || values.reason.trim() === '' || mutation.isPending}
                  onClick={() => mutation.mutate('defer')}
                >
                  标记顺延
                </Button>
              </form>
            </>
          ) : statement.status === 'confirmed' ? (
            <form
              onSubmit={event =>
                void correction.handleSubmit(() => mutation.mutate('correct'))(event)
              }
            >
              <h2>更正对账单</h2>
              <p>更正仅适用于最近一张已确认单；新单需重新核对并上传盖章件。</p>
              <label className={styles.field}>
                更正原因
                <input required {...correction.register('reason')} />
              </label>
              <Button
                htmlType="submit"
                disabled={correctionReason.trim() === '' || mutation.isPending}
              >
                创建更正单
              </Button>
            </form>
          ) : (
            <p>该单已更正，仅供历史查阅。</p>
          )}
        </>
      )}
    </section>
  );
}

export default function ManagementFeeStatementPage(): React.ReactElement {
  const { statement_id: id = '' } = useParams();
  const client = useQueryClient();
  const [deniedId, setDeniedId] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['management-fee-statement', id],
    queryFn: () => managementFeeService.get(id),
    enabled: id !== '',
    retry: false,
  });
  const statement = deniedId === id ? undefined : query.data;
  const changed = () => {
    void client.invalidateQueries({ queryKey: ['management-fee-statement', id] });
    void client.invalidateQueries({ queryKey: ['management-fee-statements'] });
    void client.invalidateQueries({ queryKey: ['management-fee-matrix'] });
    void client.invalidateQueries({ queryKey: ['rent-ledger-entry'] });
    void client.invalidateQueries({ queryKey: ['rent-ledgers'] });
  };
  return (
    <div className={styles.page}>
      <nav className={styles.toolbar}>
        <Link to="/asset-operations/ledgers?ledger_type=management_fee">返回委托管理费台账</Link>
        <Button
          onClick={() => {
            void query.refetch().then(result => {
              if (!result.isError) setDeniedId(null);
            });
          }}
        >
          刷新对账单
        </Button>
        {statement != null && !query.isError ? (
          <Button onClick={() => window.print()}>打印对账单</Button>
        ) : null}
      </nav>
      {query.isLoading ? <p role="status">正在读取对账单…</p> : null}
      {query.isError ? (
        <Alert
          type="error"
          showIcon
          title={
            isLedgerForbidden(query.error) ? '暂无该对账单访问权限' : '对账单读取失败，请刷新重试'
          }
        />
      ) : null}
      {deniedId === id ? <Alert type="error" title="暂无该对账单访问权限" /> : null}
      {statement != null && !query.isError ? (
        <>
          <article className={styles.paper}>
            <header className={styles.header}>
              <h1>委托管理费对账单</h1>
              <p>
                {statement.period} · {statusNames[statement.status]}
              </p>
            </header>
            <dl className={styles.meta}>
              <div>
                <dt>单据编号</dt>
                <dd>{statement.statement_number}</dd>
              </div>
              <div>
                <dt>核对截止日</dt>
                <dd>{statement.deadline}</dd>
              </div>
            </dl>
            {statement.upstream_missing_warning != null ? (
              <Alert type="warning" title={statement.upstream_missing_warning} />
            ) : null}
            {statement.carried_waiting_hint ? (
              <Alert type="info" title="前月尚未确认，顺延带入金额将在前月确认后更新" />
            ) : null}
            {statement.predecessor_statement_id != null ? (
              <p>
                更正来源：
                <Link
                  to={`/asset-operations/management-fees/${encodeURIComponent(statement.predecessor_statement_id)}`}
                >
                  查看原单
                </Link>
              </p>
            ) : null}
            {statement.successor_statement_id != null ? (
              <p>
                此单已被更正：
                <Link
                  to={`/asset-operations/management-fees/${encodeURIComponent(statement.successor_statement_id)}`}
                >
                  查看更正单
                </Link>
              </p>
            ) : null}
            <div className={styles.scroll} role="region" aria-label="管理费明细" tabIndex={0}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {[
                      '租户／账期',
                      '应收租金',
                      '计入实收',
                      '到账日期',
                      '管理费比例',
                      '管理费',
                      '顺延余额',
                    ].map(label => (
                      <th scope="col" key={label}>
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {statement.lines.map((line, index) => (
                    <tr key={`${line.rent_ledger_entry_id}-${index}`}>
                      <th scope="row">
                        {line.tenant_name_snapshot}
                        <div>
                          {line.rent_period}
                          {line.line_kind === 'carried' ? ' · 前期带入' : ''}
                        </div>
                        <Link
                          to={`/asset-operations/contracts/upstream?contract_id=${encodeURIComponent(line.upstream_contract_id)}`}
                        >
                          查看委托协议
                        </Link>
                        {line.deferral_reason != null ? (
                          <div>顺延原因：{line.deferral_reason}</div>
                        ) : null}
                      </th>
                      <td>{money(line.scheduled_rent)}</td>
                      <td>{money(line.owner_received_amount)}</td>
                      <td>{line.received_on ?? '尚未到账'}</td>
                      <td>
                        {(line.fee_rate * 100).toLocaleString('zh-CN', {
                          maximumFractionDigits: 4,
                        })}
                        %
                      </td>
                      <td>{money(line.fee_amount)}</td>
                      <td>{money(line.deferred_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {statement.lines.length === 0 ? (
              <p>本单暂无可计入明细，请核对委托协议与租金账期。</p>
            ) : null}
            <div className={styles.total}>
              <p>计费基数 {money(statement.base_amount)}</p>
              <p>
                <strong>管理费合计 {money(statement.fee_amount)}</strong>
              </p>
              <p>
                人民币大写：<strong>{capitalMoney(statement.fee_amount)}</strong>
              </p>
            </div>
            <footer className={styles.stamps}>
              <p>产权方（盖章）</p>
              <p>管理方（盖章）</p>
            </footer>
            <p>{statement.stamped_document_id == null ? '尚未上传盖章件' : '已上传盖章件'}</p>
            {statement.confirmed_at != null ? (
              <p>确认时间：{statement.confirmed_at}</p>
            ) : (
              <p>当前金额为试算，确认后保留金额及比例快照。</p>
            )}
          </article>
          <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
            <StatementActions
              key={`${statement.id}-${statement.version}`}
              statement={statement}
              changed={changed}
              denied={() => setDeniedId(id)}
            />
          </CapabilityGuard>
        </>
      ) : null}
    </div>
  );
}
