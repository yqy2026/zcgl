/**
 * 资产运营 · 合同生命周期操作（终止/退出/撤销/续签）
 *
 * 预览-确认两步：预览返回逐单元覆盖截止影响与 token（不落库），确认携带
 * token、当前版本与前端生成的幂等键；预览失效/版本漂移返回 409 需重新
 * 预览。撤销须显式指向原事件。续签走录入会话上传新扫描件后提交后继条款。
 */

import { useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { Controller, useForm } from 'react-hook-form';
import { Alert, Button, Input } from 'antd';

import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { ExitPreview, TerminationPreview } from '@/services/assetOperationsService';

import styles from './LifecycleActionsPage.module.css';
import RentScheduleEditor from './RentScheduleEditor';
import { RentImpactSummary } from './LedgersPage';
import type { RentScheduleInput } from '@/services/assetLedgerService';

interface TerminalTerminationForm {
  effectiveDate: string;
  terminationType: string;
  handoverStatus: string;
  depositSettlementStatus: string;
  reason: string;
}

interface ReversalForm {
  targetEventId: string;
  effectiveDate: string;
  reason: string;
}

interface TerminalRenewalForm {
  rentSchedules: RentScheduleInput[];
  contractNumber: string;
  tenantPartyId: string;
  lessorPartyId: string;
  startDate: string;
  endDate: string;
  depositAmount: string;
  assetUnitIds: string;
}

interface UpstreamExitForm {
  effectiveDate: string;
  reason: string;
}

interface UpstreamRenewalForm {
  rentSchedules: RentScheduleInput[];
  contractNumber: string;
  name: string;
  startDate: string;
  endDate: string;
  paymentCycle: string;
  paymentDay: string;
  managementFeeRate: string;
  depositAmount: string;
  assetUnitIds: string;
}

const TERMINAL_TERMINATION_DEFAULTS: TerminalTerminationForm = {
  effectiveDate: '',
  terminationType: 'early',
  handoverStatus: 'pending',
  depositSettlementStatus: 'pending',
  reason: '',
};

const REVERSAL_DEFAULTS: ReversalForm = {
  targetEventId: '',
  effectiveDate: '',
  reason: '',
};

const TERMINAL_RENEWAL_DEFAULTS: TerminalRenewalForm = {
  rentSchedules: [],
  contractNumber: '',
  tenantPartyId: '',
  lessorPartyId: '',
  startDate: '',
  endDate: '',
  depositAmount: '0',
  assetUnitIds: '',
};

const UPSTREAM_EXIT_DEFAULTS: UpstreamExitForm = {
  effectiveDate: '',
  reason: '',
};

const UPSTREAM_RENEWAL_DEFAULTS: UpstreamRenewalForm = {
  rentSchedules: [],
  contractNumber: '',
  name: '',
  startDate: '',
  endDate: '',
  paymentCycle: 'monthly',
  paymentDay: '25',
  managementFeeRate: '',
  depositAmount: '0',
  assetUnitIds: '',
};

function newIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `lifecycle-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function conflictMessage(error: unknown): string | null {
  if (
    error instanceof AssetOperationsError &&
    (error.code === 'PREVIEW_STALE' || error.code === 'VERSION_CONFLICT')
  ) {
    return '预览已失效或版本已变化，请重新预览后再提交。';
  }
  return null;
}

export function TerminalActionsPage(): React.ReactElement {
  const params = useParams<{ contractId: string }>();
  const navigate = useNavigate();
  const contractId = params.contractId ?? '';

  const {
    control: terminationControl,
    handleSubmit: handleTerminationSubmit,
    watch: watchTermination,
  } = useForm<TerminalTerminationForm>({
    defaultValues: TERMINAL_TERMINATION_DEFAULTS,
  });
  const {
    control: reversalControl,
    handleSubmit: handleReversalSubmit,
    watch: watchReversal,
  } = useForm<ReversalForm>({
    defaultValues: REVERSAL_DEFAULTS,
  });
  const [preview, setPreview] = useState<TerminationPreview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const renewFileRef = useRef<HTMLInputElement>(null);
  const [scheduleValid, setScheduleValid] = useState(true);
  const {
    control: renewalControl,
    handleSubmit: handleRenewalSubmit,
    watch: watchRenewal,
    setValue: setRenewalValue,
  } = useForm<TerminalRenewalForm>({
    defaultValues: TERMINAL_RENEWAL_DEFAULTS,
  });
  const terminationForm = watchTermination();
  const reversalForm = watchReversal();
  const renewalForm = watchRenewal();

  const previewMutation = useMutation({
    mutationFn: (values: TerminalTerminationForm) =>
      assetOperationsService.previewTerminalTermination(contractId, {
        effective_date: values.effectiveDate,
        termination_type: values.terminationType,
        handover_status: values.handoverStatus,
        deposit_settlement_status: values.depositSettlementStatus,
        reason: values.reason.trim(),
      }),
    onSuccess: result => {
      setPreview(result);
      setNotice(null);
    },
  });

  const commitMutation = useMutation({
    mutationFn: (idempotencyKey: string) => {
      if (preview == null) {
        throw new Error('请先预览');
      }
      return assetOperationsService.commitTerminalTermination(
        contractId,
        {
          preview_token: preview.previewToken,
          expected_version: preview.contractVersion,
        },
        idempotencyKey
      );
    },
    onSuccess: () => {
      setNotice('终止已登记，覆盖期已截止到生效日前一日。');
      setPreview(null);
    },
  });

  const reversalMutation = useMutation({
    mutationFn: (input: { values: ReversalForm; idempotencyKey: string }) =>
      assetOperationsService.reverseTerminalTermination(
        contractId,
        {
          target_event_id: input.values.targetEventId.trim(),
          effective_date: input.values.effectiveDate,
          reason: input.values.reason.trim(),
        },
        input.idempotencyKey
      ),
    onSuccess: () => {
      setNotice('终止已撤销，覆盖期已恢复到合同到期日。');
    },
  });

  const renewSessionMutation = useMutation({
    mutationFn: (file: File) => assetOperationsService.createIntakeSession('terminal', file),
    retry: false,
  });

  const renewMutation = useMutation({
    mutationFn: (input: {
      session: { id: string; documentId: string };
      idempotencyKey: string;
      values: TerminalRenewalForm;
    }) => {
      const unitIds = input.values.assetUnitIds
        .split(/[,，\s]+/)
        .map(value => value.trim())
        .filter(value => value !== '');
      return assetOperationsService.renewTerminal(
        contractId,
        {
          contract_number: input.values.contractNumber.trim(),
          tenant_party_id: input.values.tenantPartyId.trim(),
          lessor_party_id: input.values.lessorPartyId.trim(),
          start_date: input.values.startDate,
          end_date: input.values.endDate,
          deposit_amount: input.values.depositAmount,
          asset_unit_ids: unitIds,
          rent_schedules: input.values.rentSchedules,
          scan_document_id: input.session.documentId,
          scan_owner_id: input.session.id,
        },
        input.idempotencyKey
      );
    },
    onSuccess: result => {
      setNotice(`续签后继合同 ${result.contractNumber} 已登记，原合同不变。`);
    },
  });

  const previewCommitted =
    conflictMessage(previewMutation.error) ?? conflictMessage(commitMutation.error);

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>终端合同 · 生命周期操作</h1>
      {notice != null ? <Alert type="success" showIcon title={notice} /> : null}

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>终止</h2>
        <label className={styles.fieldColumn}>
          终止生效日（该日起合同不再有效）
          <Controller
            control={terminationControl}
            name="effectiveDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          终止类型
          <Controller
            control={terminationControl}
            name="terminationType"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Controller
            control={terminationControl}
            name="reason"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <Button
          disabled={
            terminationForm.effectiveDate === '' ||
            terminationForm.reason.trim() === '' ||
            previewMutation.isPending
          }
          loading={previewMutation.isPending}
          onClick={() => void handleTerminationSubmit(values => previewMutation.mutate(values))()}
        >
          预览终止影响
        </Button>

        {preview != null ? (
          <div style={{ marginTop: 12 }}>
            <Alert
              type="warning"
              showIcon
              title={`最后有效日 ${preview.lastValidDay}；请核对以下覆盖截止变化后确认。`}
            />
            {preview.rentImpact != null ? <RentImpactSummary impact={preview.rentImpact} /> : null}
            {preview.coverageImpact.map(impact => (
              <div className={styles.impactRow} key={impact.assetUnitId}>
                <span>{impact.assetUnitId}</span>
                <span>
                  {impact.currentEffectiveTo ?? '开放'} → {impact.newEffectiveTo}
                </span>
              </div>
            ))}
            {previewCommitted != null ? (
              <Alert type="warning" showIcon title={previewCommitted} />
            ) : null}
            {commitMutation.isError && previewCommitted == null ? (
              <Alert
                type="error"
                showIcon
                title={
                  commitMutation.error instanceof Error ? commitMutation.error.message : '提交失败'
                }
              />
            ) : null}
            <Button
              type="primary"
              style={{ marginTop: 8 }}
              loading={commitMutation.isPending}
              onClick={() => commitMutation.mutate(newIdempotencyKey())}
            >
              确认终止
            </Button>
          </div>
        ) : null}
      </div>

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>撤销终止（纠错）</h2>
        <label className={styles.fieldColumn}>
          原终止事件 ID（来自合同详情的生命周期事件）
          <Controller
            control={reversalControl}
            name="targetEventId"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          撤销生效日
          <Controller
            control={reversalControl}
            name="effectiveDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Controller
            control={reversalControl}
            name="reason"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        {reversalMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              reversalMutation.error instanceof Error ? reversalMutation.error.message : '撤销失败'
            }
          />
        ) : null}
        <Button
          disabled={
            reversalForm.targetEventId.trim() === '' ||
            reversalForm.effectiveDate === '' ||
            reversalForm.reason.trim() === '' ||
            reversalMutation.isPending
          }
          loading={reversalMutation.isPending}
          onClick={() =>
            void handleReversalSubmit(values =>
              reversalMutation.mutate({ values, idempotencyKey: newIdempotencyKey() })
            )()
          }
        >
          撤销终止
        </Button>
      </div>

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>登记续签（创建后继合同，不改原合同）</h2>
        <RentScheduleEditor
          startDate={renewalForm.startDate}
          endDate={renewalForm.endDate}
          onChange={stages => setRenewalValue('rentSchedules', stages)}
          onValidityChange={setScheduleValid}
        />
        <label className={styles.fieldColumn}>
          续签扫描件（新签署的合同）
          <input
            ref={renewFileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            aria-label="续签扫描件"
            onChange={event => {
              const file = event.target.files?.[0] ?? null;
              if (file != null) {
                renewSessionMutation.mutate(file);
              }
            }}
          />
        </label>
        {renewSessionMutation.isPending ? <p>扫描件上传中…</p> : null}
        {renewSessionMutation.data != null ? (
          <p className={styles.hintText}>扫描件已上传，可填写后继条款。</p>
        ) : null}
        {renewSessionMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              renewSessionMutation.error instanceof Error
                ? renewSessionMutation.error.message
                : '扫描件上传失败'
            }
          />
        ) : null}
        <label className={styles.fieldColumn}>
          后继合同编号
          <Controller
            control={renewalControl}
            name="contractNumber"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          租户 Party ID
          <Controller
            control={renewalControl}
            name="tenantPartyId"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          出租方 Party ID
          <Controller
            control={renewalControl}
            name="lessorPartyId"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          后继起租日（必须晚于原合同覆盖结束）
          <Controller
            control={renewalControl}
            name="startDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          后继到期日
          <Controller
            control={renewalControl}
            name="endDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          覆盖资产单元 ID（逗号分隔，由原合同带出核对）
          <Controller
            control={renewalControl}
            name="assetUnitIds"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        {renewMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={renewMutation.error instanceof Error ? renewMutation.error.message : '续签失败'}
          />
        ) : null}
        <Button
          type="primary"
          disabled={
            !scheduleValid ||
            renewSessionMutation.data == null ||
            renewalForm.contractNumber.trim() === '' ||
            renewalForm.startDate === '' ||
            renewalForm.endDate === '' ||
            renewalForm.assetUnitIds.trim() === '' ||
            renewMutation.isPending
          }
          loading={renewMutation.isPending}
          onClick={() =>
            void handleRenewalSubmit(values => {
              if (renewSessionMutation.data != null) {
                renewMutation.mutate({
                  session: {
                    id: renewSessionMutation.data.id,
                    documentId: renewSessionMutation.data.documentId,
                  },
                  idempotencyKey: newIdempotencyKey(),
                  values,
                });
              }
            })()
          }
        >
          登记续签
        </Button>
      </div>

      <Button onClick={() => navigate(-1)}>返回</Button>
    </div>
  );
}

export function UpstreamActionsPage(): React.ReactElement {
  const params = useParams<{ contractId: string }>();
  const navigate = useNavigate();
  const contractId = params.contractId ?? '';
  const contractQuery = useQuery({
    queryKey: ['upstream-contract', contractId],
    queryFn: () => assetOperationsService.getUpstreamContract(contractId),
    enabled: contractId !== '',
  });
  const isManagement = contractQuery.data?.contractType === 'management_agreement';

  const {
    control: exitControl,
    handleSubmit: handleExitSubmit,
    watch: watchExit,
  } = useForm<UpstreamExitForm>({
    defaultValues: UPSTREAM_EXIT_DEFAULTS,
  });
  const {
    control: reversalControl,
    handleSubmit: handleReversalSubmit,
    watch: watchReversal,
  } = useForm<ReversalForm>({
    defaultValues: REVERSAL_DEFAULTS,
  });
  const [preview, setPreview] = useState<ExitPreview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const renewFileRef = useRef<HTMLInputElement>(null);
  const [scheduleValid, setScheduleValid] = useState(true);
  const {
    control: renewalControl,
    handleSubmit: handleRenewalSubmit,
    watch: watchRenewal,
    setValue: setRenewalValue,
  } = useForm<UpstreamRenewalForm>({
    defaultValues: UPSTREAM_RENEWAL_DEFAULTS,
  });
  const exitForm = watchExit();
  const reversalForm = watchReversal();
  const renewalForm = watchRenewal();

  const previewMutation = useMutation({
    mutationFn: (values: UpstreamExitForm) =>
      assetOperationsService.previewUpstreamExit(contractId, {
        effective_date: values.effectiveDate,
        reason: values.reason.trim(),
      }),
    onSuccess: result => {
      setPreview(result);
      setNotice(null);
    },
  });

  const commitMutation = useMutation({
    mutationFn: (idempotencyKey: string) => {
      if (preview == null) {
        throw new Error('请先预览');
      }
      return assetOperationsService.commitUpstreamExit(
        contractId,
        {
          preview_token: preview.previewToken,
          expected_version: preview.contractVersion,
        },
        idempotencyKey
      );
    },
    onSuccess: () => {
      setNotice('退出已登记，上游覆盖期已截止到生效日前一日。');
      setPreview(null);
    },
  });

  const reversalMutation = useMutation({
    mutationFn: (input: { values: ReversalForm; idempotencyKey: string }) =>
      assetOperationsService.reverseUpstreamExit(
        contractId,
        {
          target_event_id: input.values.targetEventId.trim(),
          effective_date: input.values.effectiveDate,
          reason: input.values.reason.trim(),
        },
        input.idempotencyKey
      ),
    onSuccess: () => {
      setNotice('退出已撤销，覆盖期已恢复到合同到期日。');
    },
  });

  const renewSessionMutation = useMutation({
    mutationFn: (file: File) => {
      if (contractQuery.data == null || contractQuery.isError) throw new Error('请先读取原合同');
      return assetOperationsService.createIntakeSession(
        isManagement ? 'management_agreement' : 'upstream_lease',
        file
      );
    },
    retry: false,
  });

  const renewMutation = useMutation({
    mutationFn: (input: {
      session: { id: string; documentId: string };
      idempotencyKey: string;
      values: UpstreamRenewalForm;
    }) => {
      const unitIds = input.values.assetUnitIds
        .split(/[,，\s]+/)
        .map(value => value.trim())
        .filter(value => value !== '');
      return assetOperationsService.renewUpstream(
        contractId,
        {
          contract_number: input.values.contractNumber.trim(),
          name: input.values.name.trim(),
          owner_party_id: '',
          operator_party_id: '',
          start_date: input.values.startDate,
          end_date: input.values.endDate,
          ...(isManagement
            ? { management_fee_rate: input.values.managementFeeRate, deposit_amount: '0' }
            : {
                payment_cycle: input.values.paymentCycle,
                payment_day: Number(input.values.paymentDay),
                deposit_amount: input.values.depositAmount,
              }),
          asset_unit_ids: unitIds,
          rent_schedules: isManagement ? [] : input.values.rentSchedules,
          scan_document_id: input.session.documentId,
          scan_owner_id: input.session.id,
        },
        input.idempotencyKey
      );
    },
    onSuccess: result => {
      setNotice(`续签后继合同 ${result.contractNumber} 已登记，各方由原合同带出。`);
    },
  });

  const previewCommitted =
    conflictMessage(previewMutation.error) ?? conflictMessage(commitMutation.error);

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>上游合同 · 生命周期操作</h1>
      {notice != null ? <Alert type="success" showIcon title={notice} /> : null}

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>退出在管</h2>
        <label className={styles.fieldColumn}>
          退出生效日（该日起合同不再有效）
          <Controller
            control={exitControl}
            name="effectiveDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Controller
            control={exitControl}
            name="reason"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <Button
          disabled={
            exitForm.effectiveDate === '' ||
            exitForm.reason.trim() === '' ||
            previewMutation.isPending
          }
          loading={previewMutation.isPending}
          onClick={() => void handleExitSubmit(values => previewMutation.mutate(values))()}
        >
          预览退出影响
        </Button>

        {preview != null ? (
          <div style={{ marginTop: 12 }}>
            <Alert
              type="warning"
              showIcon
              title={`最后有效日 ${preview.lastValidDay}；请核对覆盖截止变化后确认。`}
            />
            {preview.rentImpact != null ? <RentImpactSummary impact={preview.rentImpact} /> : null}
            {preview.coverageImpact.map(impact => (
              <div className={styles.impactRow} key={impact.assetUnitId}>
                <span>{impact.assetUnitId}</span>
                <span>
                  {impact.currentEffectiveTo ?? '开放'} → {impact.newEffectiveTo}
                </span>
              </div>
            ))}
            {previewCommitted != null ? (
              <Alert type="warning" showIcon title={previewCommitted} />
            ) : null}
            {commitMutation.isError && previewCommitted == null ? (
              <Alert
                type="error"
                showIcon
                title={
                  commitMutation.error instanceof Error ? commitMutation.error.message : '提交失败'
                }
              />
            ) : null}
            <Button
              type="primary"
              style={{ marginTop: 8 }}
              loading={commitMutation.isPending}
              onClick={() => commitMutation.mutate(newIdempotencyKey())}
            >
              确认退出
            </Button>
          </div>
        ) : null}
      </div>

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>撤销退出（纠错）</h2>
        <label className={styles.fieldColumn}>
          原退出事件 ID
          <Controller
            control={reversalControl}
            name="targetEventId"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          撤销生效日
          <Controller
            control={reversalControl}
            name="effectiveDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Controller
            control={reversalControl}
            name="reason"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        {reversalMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              reversalMutation.error instanceof Error ? reversalMutation.error.message : '撤销失败'
            }
          />
        ) : null}
        <Button
          disabled={
            reversalForm.targetEventId.trim() === '' ||
            reversalForm.effectiveDate === '' ||
            reversalForm.reason.trim() === '' ||
            reversalMutation.isPending
          }
          loading={reversalMutation.isPending}
          onClick={() =>
            void handleReversalSubmit(values =>
              reversalMutation.mutate({ values, idempotencyKey: newIdempotencyKey() })
            )()
          }
        >
          撤销退出
        </Button>
      </div>

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>登记续签</h2>
        {!isManagement ? (
          <RentScheduleEditor
            startDate={renewalForm.startDate}
            endDate={renewalForm.endDate}
            onChange={stages => setRenewalValue('rentSchedules', stages)}
            onValidityChange={setScheduleValid}
          />
        ) : null}
        <label className={styles.fieldColumn}>
          续签扫描件
          <input
            ref={renewFileRef}
            disabled={contractQuery.data == null || contractQuery.isError}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            aria-label="续签扫描件"
            onChange={event => {
              const file = event.target.files?.[0] ?? null;
              if (file != null) {
                renewSessionMutation.mutate(file);
              }
            }}
          />
        </label>
        {renewSessionMutation.isPending ? <p>扫描件上传中…</p> : null}
        {renewSessionMutation.data != null ? (
          <p className={styles.hintText}>扫描件已上传，可填写后继条款。</p>
        ) : null}
        {renewSessionMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              renewSessionMutation.error instanceof Error
                ? renewSessionMutation.error.message
                : '扫描件上传失败'
            }
          />
        ) : null}
        <label className={styles.fieldColumn}>
          后继合同编号
          <Controller
            control={renewalControl}
            name="contractNumber"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        {contractQuery.isPending ? <p>正在读取原合同…</p> : null}
        {contractQuery.isError ? (
          <Alert
            type="error"
            showIcon
            title="原合同读取失败，请重试"
            action={<Button onClick={() => void contractQuery.refetch()}>重试</Button>}
          />
        ) : null}
        {isManagement ? (
          <label className={styles.fieldColumn}>
            管理费比例（0–1）
            <Controller
              control={renewalControl}
              name="managementFeeRate"
              render={({ field }) => <Input {...field} type="number" min={0} max={1} step="0.01" />}
            />
          </label>
        ) : null}
        <label className={styles.fieldColumn}>
          后继合同名称
          <Controller
            control={renewalControl}
            name="name"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          后继起租日
          <Controller
            control={renewalControl}
            name="startDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          后继到期日
          <Controller
            control={renewalControl}
            name="endDate"
            render={({ field }) => <Input type="date" {...field} />}
          />
        </label>
        <label className={styles.fieldColumn}>
          覆盖资产单元 ID（由原合同带出核对）
          <Controller
            control={renewalControl}
            name="assetUnitIds"
            render={({ field }) => <Input {...field} />}
          />
        </label>
        {renewMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={renewMutation.error instanceof Error ? renewMutation.error.message : '续签失败'}
          />
        ) : null}
        <Button
          type="primary"
          disabled={
            !scheduleValid ||
            contractQuery.data == null ||
            contractQuery.isError ||
            (isManagement && renewalForm.managementFeeRate.trim() === '') ||
            renewSessionMutation.data == null ||
            renewalForm.contractNumber.trim() === '' ||
            renewalForm.name.trim() === '' ||
            renewalForm.startDate === '' ||
            renewalForm.endDate === '' ||
            renewalForm.assetUnitIds.trim() === '' ||
            renewMutation.isPending
          }
          loading={renewMutation.isPending}
          onClick={() =>
            void handleRenewalSubmit(values => {
              if (renewSessionMutation.data != null) {
                renewMutation.mutate({
                  session: {
                    id: renewSessionMutation.data.id,
                    documentId: renewSessionMutation.data.documentId,
                  },
                  idempotencyKey: newIdempotencyKey(),
                  values,
                });
              }
            })()
          }
        >
          登记续签
        </Button>
      </div>

      <Button onClick={() => navigate(-1)}>返回</Button>
    </div>
  );
}

export default TerminalActionsPage;
