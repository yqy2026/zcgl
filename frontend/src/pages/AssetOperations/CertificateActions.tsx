import { useId, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Drawer } from 'antd';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import ArchiveDocumentsPanel from './ArchiveDocumentsPanel';
import type { AssetUnitCertificate } from '@/services/assetOperationsService';
import styles from './AssetUnitsPage.module.css';

export function businessToday(): string {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  return ['year', 'month', 'day']
    .map(type => parts.find(part => part.type === type)?.value ?? '')
    .join('-');
}

function failure(error: unknown, action: 'link' | 'unlink' = 'link'): string {
  if (error instanceof AssetOperationsError) {
    if (error.code === 'ARCHIVE_DUPLICATE_CONTENT') return '此文件已归档，请选择内容不同的文件。';
    if (error.code === 'ARCHIVE_VERSION_STALE') return '此版本已被替换，请重新加载后选择现行版本。';
    if (error.code === 'CERTIFICATE_LINK_HISTORY_PROTECTED')
      return action === 'unlink'
        ? '此操作会改变已生效的关联历史，请选择今天之后的解除日期。'
        : '此证照已有历史关联，不能重新关联；请刷新候选并另选证照。';
    if (error.code === 'CERTIFICATE_LINK_OVERLAP') return '此证照已有关联记录，请刷新后重新选择。';
    if (error.code.startsWith('PARTY_SCOPE_') || error.code === 'ASSET_OPS_PERMISSION_DENIED')
      return '访问范围或操作权限已变化，请联系管理员后重试。';
    if (error.code === 'RESOURCE_NOT_FOUND' || error.code === 'NOT_FOUND')
      return '证照已不可访问，请刷新后重新选择。';
    return error.message;
  }
  return '操作失败，请重新加载后重试。';
}

export function CertificateLink({ unitId }: { unitId: string }): React.ReactElement {
  const [open, setOpen] = useState(false);
  return (
    <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
      <Button onClick={() => setOpen(!open)}>{open ? '收起关联表单' : '关联产权证'}</Button>
      {open ? <LinkForm unitId={unitId} /> : null}
    </CapabilityGuard>
  );
}

function LinkForm({ unitId }: { unitId: string }): React.ReactElement {
  const certificatePickerId = useId();
  const [q, setQ] = useState('');
  const [offset, setOffset] = useState(0);
  const [saved, setSaved] = useState('');
  const client = useQueryClient();
  const form = useForm<{ certificate_id: string; effective_from: string; effective_to: string }>({
    defaultValues: { certificate_id: '', effective_from: businessToday(), effective_to: '' },
  });
  const options = useQuery({
    queryKey: ['certificate-options', unitId, q, offset],
    queryFn: () => assetOperationsService.listCertificateOptions(unitId, q, offset),
  });
  const mutation = useMutation({
    mutationFn: (values: {
      certificate_id: string;
      effective_from: string;
      effective_to: string;
    }) =>
      assetOperationsService.linkCertificate(unitId, {
        ...values,
        effective_to: values.effective_to === '' ? undefined : values.effective_to,
      }),
    onSuccess: (_, values) => {
      setSaved(`已保存关联，自 ${values.effective_from} 生效。`);
      form.reset({ ...values, certificate_id: '' });
      void client.invalidateQueries({ queryKey: ['asset-operations-unit-certificates', unitId] });
      void client.invalidateQueries({ queryKey: ['certificate-options', unitId] });
    },
  });
  return (
    <form
      className={styles.certificateForm}
      onSubmit={form.handleSubmit(values => {
        setSaved('');
        mutation.mutate(values);
      })}
    >
      <label>
        搜索证号或证载坐落
        <input
          value={q}
          onChange={event => {
            setQ(event.target.value);
            setOffset(0);
            form.setValue('certificate_id', '');
          }}
        />
      </label>
      {options.isPending ? (
        <p role="status">候选证照加载中…</p>
      ) : options.isError ? (
        <>
          <Alert type="error" title={failure(options.error)} />
          <Button onClick={() => void options.refetch()}>重新加载候选</Button>
        </>
      ) : (
        <>
          <label htmlFor={certificatePickerId}>选择产权证</label>
          <select
            id={certificatePickerId}
            {...form.register('certificate_id', { required: true })}
            required
            disabled={mutation.isPending}
          >
            <option value="">请选择产权证</option>
            {options.data.items.map(item => (
              <option key={item.id} value={item.id}>
                {item.certificate_number} · {item.property_address ?? '未登记坐落'}
              </option>
            ))}
          </select>
          {options.data.items.length === 0 ? (
            <p>没有符合当前绑定条件的证照。</p>
          ) : (
            <p>共 {options.data.total} 本符合条件的证照</p>
          )}
          <div>
            <Button
              disabled={offset === 0}
              onClick={() => {
                setOffset(Math.max(0, offset - 20));
                form.setValue('certificate_id', '');
              }}
            >
              上一页候选
            </Button>
            <Button
              disabled={offset + 20 >= options.data.total}
              onClick={() => {
                setOffset(offset + 20);
                form.setValue('certificate_id', '');
              }}
            >
              下一页候选
            </Button>
          </div>
        </>
      )}
      <label>
        关联生效日
        <input type="date" required {...form.register('effective_from', { required: true })} />
      </label>
      <label>
        关联截止日（可不填）
        <input
          type="date"
          {...form.register('effective_to', {
            validate: value => value === '' || value >= form.getValues('effective_from'),
          })}
        />
      </label>
      {form.formState.errors.effective_to != null ? (
        <p role="alert">截止日不能早于生效日。</p>
      ) : null}
      {mutation.isError ? <Alert type="error" title={failure(mutation.error)} /> : null}
      {saved !== '' ? <p role="status">{saved}</p> : null}
      <Button
        htmlType="submit"
        type="primary"
        loading={mutation.isPending}
        disabled={options.isPending || options.isError}
      >
        保存关联
      </Button>
    </form>
  );
}

export function CertificateControls({
  unitId,
  certificate,
}: {
  unitId: string;
  certificate: AssetUnitCertificate;
}): React.ReactElement {
  const [documentsOpen, setDocumentsOpen] = useState(false);
  const [unlinkOpen, setUnlinkOpen] = useState(false);
  return (
    <>
      <div className={styles.certificateButtons}>
        <Button onClick={() => setDocumentsOpen(true)}>查看档案</Button>
        <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
          <Button onClick={() => setUnlinkOpen(!unlinkOpen)}>
            {unlinkOpen ? '取消解除安排' : '解除关联'}
          </Button>
        </CapabilityGuard>
      </div>
      <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
        {unlinkOpen ? <UnlinkForm unitId={unitId} certificate={certificate} /> : null}
      </CapabilityGuard>
      <Drawer
        title={`${certificate.certificate_number} · 档案版本`}
        open={documentsOpen}
        onClose={() => setDocumentsOpen(false)}
        size="large"
        destroyOnHidden
      >
        {documentsOpen ? (
          <ArchiveDocumentsPanel targetId={certificate.id} targetType="property_certificate" />
        ) : null}
      </Drawer>
    </>
  );
}

function UnlinkForm({
  unitId,
  certificate,
}: {
  unitId: string;
  certificate: AssetUnitCertificate;
}): React.ReactElement {
  const client = useQueryClient();
  const form = useForm<{ date: string }>({ defaultValues: { date: businessToday() } });
  const mutation = useMutation({
    mutationFn: (values: { date: string }) =>
      assetOperationsService.unlinkCertificate(unitId, certificate.id, values.date),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['asset-operations-unit-certificates', unitId] });
      void client.invalidateQueries({ queryKey: ['certificate-options', unitId] });
    },
  });
  return (
    <form
      className={styles.certificateForm}
      onSubmit={form.handleSubmit(values => mutation.mutate(values))}
    >
      <p>安排解除 {certificate.certificate_number} 与此物业的关联；证照及档案历史保留。</p>
      <label>
        解除生效日
        <input
          type="date"
          required
          min={businessToday()}
          {...form.register('date', { required: true })}
        />
      </label>
      {mutation.isError ? <Alert type="error" title={failure(mutation.error, 'unlink')} /> : null}
      {mutation.isSuccess ? (
        <p role="status">已保存解除安排，自 {mutation.variables.date} 生效。</p>
      ) : null}
      <Button htmlType="submit" loading={mutation.isPending} disabled={mutation.isSuccess}>
        确认解除关联
      </Button>
    </form>
  );
}
