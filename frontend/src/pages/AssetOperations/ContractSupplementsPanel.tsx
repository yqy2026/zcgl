import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Drawer } from 'antd';
import ArchiveDocumentsPanel from './ArchiveDocumentsPanel';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import { contractSupplementService } from '@/services/contractSupplementService';
import type { ContractSupplement, SupplementKind } from '@/services/contractSupplementService';
import { AssetOperationsError } from '@/services/assetOperationsService';
import styles from './ContractSupplementsPanel.module.css';
function errorText(error: unknown): string {
  if (error instanceof AssetOperationsError) {
    if (error.code.startsWith('PARTY_SCOPE_') || error.code === 'ASSET_OPS_PERMISSION_DENIED')
      return '访问范围或权限已变化，请联系管理员后重新加载。';
    if (error.code === 'SUPPLEMENT_NUMBER_EXISTS')
      return '此合同已有相同协议编号，请核对登记清单。';
    if (error.code.includes('VERSION')) return '登记记录已变化，请重新加载后重试。';
    return error.message;
  }
  return '操作失败，请重新加载后重试。';
}
export default function ContractSupplementsPanel({
  kind,
  contractId,
}: {
  kind: SupplementKind;
  contractId: string;
}): React.ReactElement {
  return <Panel key={kind + ':' + contractId} kind={kind} contractId={contractId} />;
}
function Panel({
  kind,
  contractId,
}: {
  kind: SupplementKind;
  contractId: string;
}): React.ReactElement {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ['contract-supplements', kind, contractId],
    queryFn: () => contractSupplementService.list(kind, contractId),
    refetchOnMount: 'always',
    retry: false,
  });
  const refresh = (): void => {
    void client.invalidateQueries({ queryKey: ['contract-supplements', kind, contractId] });
    void client.invalidateQueries({ queryKey: ['archive-completion'] });
    void client.invalidateQueries({ queryKey: ['archive-matrix'] });
  };
  return (
    <section className={styles.panel}>
      <h3>补充协议登记清单</h3>
      <p>每份有效登记计一份应有档案；文件替换保留历史，撤回登记后仅可查看和下载。</p>
      <Button onClick={() => void query.refetch()}>重新加载协议清单</Button>
      {query.isPending ? (
        <p role="status">协议清单加载中…</p>
      ) : query.isError ? (
        <Alert type="error" title={errorText(query.error)} />
      ) : query.data.length === 0 ? (
        <p>尚未登记补充协议。</p>
      ) : (
        <ul className={styles.list}>
          {query.data.map(item => (
            <li key={item.id}>
              <strong>
                {item.agreement_number} · {item.title}
              </strong>
              <p>
                {item.signed_on == null ? '未填写签署日期' : '签署日期：' + item.signed_on} ·{' '}
                {item.withdrawn_at == null ? '有效登记' : '已撤回登记'}
              </p>
              <SupplementDocuments item={item} />
              {item.withdrawn_at == null ? (
                <CapabilityGuard action="archive" resource="asset_ops" fallback={<></>}>
                  <Withdrawal item={item} onSaved={refresh} />
                </CapabilityGuard>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <CapabilityGuard action="archive" resource="asset_ops" fallback={<></>}>
        <Registration kind={kind} contractId={contractId} onSaved={refresh} />
      </CapabilityGuard>
    </section>
  );
}
function SupplementDocuments({ item }: { item: ContractSupplement }): React.ReactElement {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>查看档案</Button>
      <Drawer
        title={`${item.agreement_number} · 档案版本`}
        open={open}
        onClose={() => setOpen(false)}
        size="large"
        destroyOnHidden
      >
        {open ? (
          <ArchiveDocumentsPanel
            targetType="contract_supplement"
            targetId={item.id}
            readOnly={item.withdrawn_at != null}
          />
        ) : null}
      </Drawer>
    </>
  );
}
function Registration({
  kind,
  contractId,
  onSaved,
}: {
  kind: SupplementKind;
  contractId: string;
  onSaved: () => void;
}): React.ReactElement {
  const form = useForm<{ number: string; title: string; date: string }>({
    defaultValues: { number: '', title: '', date: '' },
  });
  const mutation = useMutation({
    retry: false,
    mutationFn: (values: { number: string; title: string; date: string }) =>
      contractSupplementService.register({
        contract_kind: kind,
        contract_id: contractId,
        agreement_number: values.number.trim(),
        title: values.title.trim(),
        signed_on: values.date === '' ? null : values.date,
      }),
    onSuccess: () => {
      form.reset();
      onSaved();
    },
  });
  return (
    <form
      className={styles.form}
      onSubmit={form.handleSubmit(values => {
        if (!mutation.isPending) mutation.mutate(values);
      })}
    >
      <label>
        协议编号
        <input
          required
          maxLength={100}
          disabled={mutation.isPending}
          {...form.register('number', { validate: value => value.trim() !== '' })}
        />
      </label>
      <label>
        协议名称
        <input
          required
          maxLength={200}
          disabled={mutation.isPending}
          {...form.register('title', { validate: value => value.trim() !== '' })}
        />
      </label>
      <label>
        签署日期（可不填）
        <input type="date" disabled={mutation.isPending} {...form.register('date')} />
      </label>
      <Button htmlType="submit" loading={mutation.isPending}>
        登记补充协议
      </Button>
      {mutation.isError ? <Alert type="error" title={errorText(mutation.error)} /> : null}
      {mutation.isSuccess ? <p role="status">已登记补充协议，请在档案中维护扫描件。</p> : null}
    </form>
  );
}
function Withdrawal({
  item,
  onSaved,
}: {
  item: ContractSupplement;
  onSaved: () => void;
}): React.ReactElement {
  const [open, setOpen] = useState(false);
  const form = useForm<{ reason: string }>({ defaultValues: { reason: '' } });
  const mutation = useMutation({
    retry: false,
    mutationFn: (reason: string) =>
      contractSupplementService.withdraw(item.id, item.version, reason.trim()),
    onSuccess: onSaved,
  });
  return open ? (
    <form
      className={styles.form}
      onSubmit={form.handleSubmit(values => {
        if (!mutation.isPending) mutation.mutate(values.reason);
      })}
    >
      <p>撤回后不计入应有份数，登记和档案历史保留。</p>
      <label>
        撤回原因
        <input
          required
          maxLength={1000}
          disabled={mutation.isPending}
          {...form.register('reason', { validate: value => value.trim() !== '' })}
        />
      </label>
      <Button htmlType="submit" loading={mutation.isPending}>
        确认撤回登记
      </Button>
      <Button disabled={mutation.isPending} onClick={() => setOpen(false)}>
        取消撤回
      </Button>
      {mutation.isError ? <Alert type="error" title={errorText(mutation.error)} /> : null}
    </form>
  ) : (
    <Button onClick={() => setOpen(true)}>撤回登记</Button>
  );
}
