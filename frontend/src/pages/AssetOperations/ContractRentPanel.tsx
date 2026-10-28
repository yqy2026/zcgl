import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { Alert, Button } from 'antd';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import { assetLedgerService, commandKey } from '@/services/assetLedgerService';
import type {
  ContractKind,
  CorrectionPreview,
  RentScheduleInput,
  RentSummary,
} from '@/services/assetLedgerService';
import RentScheduleEditor from './RentScheduleEditor';
import { money, RentImpactSummary } from './LedgersPage';
import styles from './LedgersPage.module.css';

export default function ContractRentPanel({
  kind,
  contractId,
  startDate,
  endDate,
  schedules,
  summary,
  canCorrect = true,
}: {
  kind: ContractKind;
  contractId: string;
  startDate: string;
  endDate: string;
  schedules: RentScheduleInput[];
  summary: RentSummary | null;
  canCorrect?: boolean;
}): React.ReactElement {
  const ledgerType = kind === 'upstream' ? 'upstream_rent' : 'terminal_rent';
  const [editing, setEditing] = useState(false);
  return (
    <section className={styles.panel}>
      <h3>{kind === 'upstream' ? '付款计划' : '本月收租'}</h3>
      {summary != null ? (
        <>
          <p>
            已结清 {summary.paid_period_count}/{summary.period_count} 期 · 未完成{' '}
            {money(summary.total_remaining_amount)}
          </p>
          <p>
            {summary.current_period}：应付／应收 {money(summary.due_amount_this_month)}，已登记{' '}
            {money(summary.paid_amount_this_month)}，未完成{' '}
            {money(summary.remaining_amount_this_month)}
          </p>
          {summary.next_due_date != null ? <p>下期待登记：{summary.next_due_date}</p> : null}
          {summary.warnings.map(code => (
            <Alert
              type="warning"
              key={code}
              title={
                code === 'RENT_SCHEDULE_GAP'
                  ? '租金阶段存在缺口，缺口期间不出账'
                  : '已登记账期与当前条款不一致，请核对原登记'
              }
            />
          ))}
        </>
      ) : null}
      {schedules.length === 0 ? (
        <Alert type="warning" title="尚未核对租金阶段，缺口期间不出账" />
      ) : null}
      <Link to={`/asset-operations/ledgers?ledger_type=${ledgerType}`}>查看租金台账</Link>
      <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
        {canCorrect ? (
          <Button onClick={() => setEditing(value => !value)}>
            {editing ? '收起阶段更正' : '更正租金阶段'}
          </Button>
        ) : null}
      </CapabilityGuard>
      {editing ? (
        <RentScheduleCorrection
          key={contractId}
          kind={kind}
          contractId={contractId}
          startDate={startDate}
          endDate={endDate}
          schedules={schedules}
          onSaved={() => setEditing(false)}
        />
      ) : null}
    </section>
  );
}

function RentScheduleCorrection({
  kind,
  contractId,
  startDate,
  endDate,
  schedules,
  onSaved,
}: {
  kind: ContractKind;
  contractId: string;
  startDate: string;
  endDate: string;
  schedules: RentScheduleInput[];
  onSaved: () => void;
}): React.ReactElement {
  const client = useQueryClient();
  const form = useForm({ defaultValues: { reason: '', rentSchedules: schedules } });
  const values = form.watch();
  const [valid, setValid] = useState(true);
  const [preview, setPreview] = useState<CorrectionPreview | null>(null);
  const proposalRevision = useRef(0);
  const invalidatePreview = (): void => {
    proposalRevision.current += 1;
    setPreview(null);
  };
  const previewMutation = useMutation({
    mutationFn: async (revision: number) => ({
      revision,
      result: await assetLedgerService.previewCorrection(kind, contractId, {
        reason: values.reason.trim(),
        rent_schedules: values.rentSchedules,
      }),
    }),
    retry: false,
    onSuccess: ({ revision, result }) => {
      if (revision === proposalRevision.current) setPreview(result);
    },
  });
  const commit = useMutation({
    mutationFn: () => {
      if (preview == null) throw new Error('请先预览更正影响');
      return assetLedgerService.commitCorrection(
        kind,
        contractId,
        { preview_token: preview.preview_token, expected_version: preview.contract_version },
        commandKey()
      );
    },
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['rent-ledgers'] });
      void client.invalidateQueries({
        queryKey: [`asset-operations-${kind}-contract`, contractId],
      });
      onSaved();
    },
  });
  return (
    <section className={styles.panel} aria-label="租金阶段更正">
      <h3>更正租金阶段</h3>
      <p>已有往月阶段保留不变，往月空白期间可以补录。已登记账期不会被直接改写。</p>
      <h4>原租金阶段</h4>
      {schedules.length === 0 ? (
        <p>尚无阶段</p>
      ) : (
        schedules.map((stage, index) => (
          <p key={`${stage.stage_start}-${index}`}>
            {stage.stage_start} 至 {stage.stage_end} · 实际月租{' '}
            {money(Number(stage.actual_monthly_rent))}
          </p>
        ))
      )}
      <RentScheduleEditor
        startDate={startDate}
        endDate={endDate}
        initialSchedules={schedules}
        onValidityChange={next => {
          setValid(next);
          if (!next) invalidatePreview();
        }}
        onChange={next => {
          form.setValue('rentSchedules', next);
          invalidatePreview();
        }}
      />
      <label className={styles.field}>
        更正原因
        <input {...form.register('reason', { onChange: invalidatePreview })} />
      </label>
      {previewMutation.isError ? (
        <Alert
          type="error"
          title={
            previewMutation.error instanceof Error
              ? previewMutation.error.message
              : '预览失败，请核对后重试'
          }
        />
      ) : null}
      <Button
        disabled={!valid || values.reason.trim() === ''}
        loading={previewMutation.isPending}
        onClick={() => {
          setPreview(null);
          previewMutation.mutate(proposalRevision.current);
        }}
      >
        预览更正影响
      </Button>
      {preview != null ? (
        <>
          <RentImpactSummary impact={preview.impact} />
          <p>新阶段 {preview.rent_schedules.length} 段，原阶段将保留更正记录。</p>
          <Button type="primary" loading={commit.isPending} onClick={() => commit.mutate()}>
            确认更正租金阶段
          </Button>
        </>
      ) : null}
      {commit.isError ? (
        <Alert
          type="error"
          title={commit.error instanceof Error ? commit.error.message : '更正失败，请重新预览'}
        />
      ) : null}
    </section>
  );
}
