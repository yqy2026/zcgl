/**
 * 资产运营 · 合同生命周期操作（终止/退出/撤销/续签）
 *
 * 预览-确认两步：预览返回逐单元覆盖截止影响与 token（不落库），确认携带
 * token、当前版本与前端生成的幂等键；预览失效/版本漂移返回 409 需重新
 * 预览。撤销须显式指向原事件。续签走录入会话上传新扫描件后提交后继条款。
 */

import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { Alert, Button, Input } from 'antd';

import {
  assetOperationsService,
  AssetOperationsError,
} from '@/services/assetOperationsService';
import type {
  ExitPreview,
  TerminationPreview,
} from '@/services/assetOperationsService';

import styles from './LifecycleActionsPage.module.css';

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

  const [form, setForm] = useState({
    effectiveDate: '',
    terminationType: 'early',
    handoverStatus: 'pending',
    depositSettlementStatus: 'pending',
    reason: '',
  });
  const [reversal, setReversal] = useState({
    targetEventId: '',
    effectiveDate: '',
    reason: '',
  });
  const [preview, setPreview] = useState<TerminationPreview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const renewFileRef = useRef<HTMLInputElement>(null);
  const [renewForm, setRenewForm] = useState({
    contractNumber: '',
    tenantPartyId: '',
    lessorPartyId: '',
    startDate: '',
    endDate: '',
    depositAmount: '0',
    assetUnitIds: '',
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      assetOperationsService.previewTerminalTermination(contractId, {
        effective_date: form.effectiveDate,
        termination_type: form.terminationType,
        handover_status: form.handoverStatus,
        deposit_settlement_status: form.depositSettlementStatus,
        reason: form.reason.trim(),
      }),
    onSuccess: (result) => {
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
        idempotencyKey,
      );
    },
    onSuccess: () => {
      setNotice('终止已登记，覆盖期已截止到生效日前一日。');
      setPreview(null);
    },
  });

  const reversalMutation = useMutation({
    mutationFn: (idempotencyKey: string) =>
      assetOperationsService.reverseTerminalTermination(
        contractId,
        {
          target_event_id: reversal.targetEventId.trim(),
          effective_date: reversal.effectiveDate,
          reason: reversal.reason.trim(),
        },
        idempotencyKey,
      ),
    onSuccess: () => {
      setNotice('终止已撤销，覆盖期已恢复到合同到期日。');
    },
  });

  const renewSessionMutation = useMutation({
    mutationFn: (file: File) =>
      assetOperationsService.createIntakeSession('terminal', file),
  });

  const renewMutation = useMutation({
    mutationFn: (input: {
      session: { id: string; documentId: string };
      idempotencyKey: string;
    }) => {
      const unitIds = renewForm.assetUnitIds
        .split(/[,，\s]+/)
        .map((value) => value.trim())
        .filter((value) => value !== '');
      return assetOperationsService.renewTerminal(
        contractId,
        {
          contract_number: renewForm.contractNumber.trim(),
          tenant_party_id: renewForm.tenantPartyId.trim(),
          lessor_party_id: renewForm.lessorPartyId.trim(),
          start_date: renewForm.startDate,
          end_date: renewForm.endDate,
          deposit_amount: renewForm.depositAmount,
          asset_unit_ids: unitIds,
          rent_schedules: [],
          scan_document_id: input.session.documentId,
          scan_owner_id: input.session.id,
        },
        input.idempotencyKey,
      );
    },
    onSuccess: (result) => {
      setNotice(`续签后继合同 ${result.contractNumber} 已登记，原合同不变。`);
    },
  });

  const previewCommitted = conflictMessage(previewMutation.error) ?? conflictMessage(commitMutation.error);

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>终端合同 · 生命周期操作</h1>
      {notice != null ? <Alert type="success" showIcon title={notice} /> : null}

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>终止</h2>
        <label className={styles.fieldColumn}>
          终止生效日（该日起合同不再有效）
          <Input
            type="date"
            value={form.effectiveDate}
            onChange={(event) =>
              setForm((previous) => ({
                ...previous,
                effectiveDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          终止类型
          <Input
            value={form.terminationType}
            onChange={(event) =>
              setForm((previous) => ({
                ...previous,
                terminationType: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Input
            value={form.reason}
            onChange={(event) =>
              setForm((previous) => ({ ...previous, reason: event.target.value }))
            }
          />
        </label>
        <Button
          disabled={form.effectiveDate === '' || form.reason.trim() === '' || previewMutation.isPending}
          loading={previewMutation.isPending}
          onClick={() => previewMutation.mutate()}
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
            {preview.coverageImpact.map((impact) => (
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
                  commitMutation.error instanceof Error
                    ? commitMutation.error.message
                    : '提交失败'
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
          <Input
            value={reversal.targetEventId}
            onChange={(event) =>
              setReversal((previous) => ({
                ...previous,
                targetEventId: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          撤销生效日
          <Input
            type="date"
            value={reversal.effectiveDate}
            onChange={(event) =>
              setReversal((previous) => ({
                ...previous,
                effectiveDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Input
            value={reversal.reason}
            onChange={(event) =>
              setReversal((previous) => ({
                ...previous,
                reason: event.target.value,
              }))
            }
          />
        </label>
        {reversalMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              reversalMutation.error instanceof Error
                ? reversalMutation.error.message
                : '撤销失败'
            }
          />
        ) : null}
        <Button
          disabled={
            reversal.targetEventId.trim() === '' ||
            reversal.effectiveDate === '' ||
            reversal.reason.trim() === '' ||
            reversalMutation.isPending
          }
          loading={reversalMutation.isPending}
          onClick={() => reversalMutation.mutate(newIdempotencyKey())}
        >
          撤销终止
        </Button>
      </div>

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>登记续签（创建后继合同，不改原合同）</h2>
        <label className={styles.fieldColumn}>
          续签扫描件（新签署的合同）
          <input
            ref={renewFileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            aria-label="续签扫描件"
            onChange={(event) => {
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
          <Input
            value={renewForm.contractNumber}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                contractNumber: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          租户 Party ID
          <Input
            value={renewForm.tenantPartyId}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                tenantPartyId: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          出租方 Party ID
          <Input
            value={renewForm.lessorPartyId}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                lessorPartyId: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          后继起租日（必须晚于原合同覆盖结束）
          <Input
            type="date"
            value={renewForm.startDate}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                startDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          后继到期日
          <Input
            type="date"
            value={renewForm.endDate}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                endDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          覆盖资产单元 ID（逗号分隔，由原合同带出核对）
          <Input
            value={renewForm.assetUnitIds}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                assetUnitIds: event.target.value,
              }))
            }
          />
        </label>
        {renewMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              renewMutation.error instanceof Error
                ? renewMutation.error.message
                : '续签失败'
            }
          />
        ) : null}
        <Button
          type="primary"
          disabled={
            renewSessionMutation.data == null ||
            renewForm.contractNumber.trim() === '' ||
            renewForm.startDate === '' ||
            renewForm.endDate === '' ||
            renewForm.assetUnitIds.trim() === '' ||
            renewMutation.isPending
          }
          loading={renewMutation.isPending}
          onClick={() =>
            renewSessionMutation.data != null &&
            renewMutation.mutate({
              session: {
                id: renewSessionMutation.data.id,
                documentId: renewSessionMutation.data.documentId,
              },
              idempotencyKey: newIdempotencyKey(),
            })
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

  const [form, setForm] = useState({ effectiveDate: '', reason: '' });
  const [reversal, setReversal] = useState({
    targetEventId: '',
    effectiveDate: '',
    reason: '',
  });
  const [preview, setPreview] = useState<ExitPreview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const renewFileRef = useRef<HTMLInputElement>(null);
  const [renewForm, setRenewForm] = useState({
    contractNumber: '',
    name: '',
    startDate: '',
    endDate: '',
    paymentCycle: 'monthly',
    paymentDay: '15',
    depositAmount: '0',
    assetUnitIds: '',
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      assetOperationsService.previewUpstreamExit(contractId, {
        effective_date: form.effectiveDate,
        reason: form.reason.trim(),
      }),
    onSuccess: (result) => {
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
        idempotencyKey,
      );
    },
    onSuccess: () => {
      setNotice('退出已登记，上游覆盖期已截止到生效日前一日。');
      setPreview(null);
    },
  });

  const reversalMutation = useMutation({
    mutationFn: (idempotencyKey: string) =>
      assetOperationsService.reverseUpstreamExit(
        contractId,
        {
          target_event_id: reversal.targetEventId.trim(),
          effective_date: reversal.effectiveDate,
          reason: reversal.reason.trim(),
        },
        idempotencyKey,
      ),
    onSuccess: () => {
      setNotice('退出已撤销，覆盖期已恢复到合同到期日。');
    },
  });

  const renewSessionMutation = useMutation({
    mutationFn: (file: File) =>
      assetOperationsService.createIntakeSession('upstream_lease', file),
  });

  const renewMutation = useMutation({
    mutationFn: (input: {
      session: { id: string; documentId: string };
      idempotencyKey: string;
    }) => {
      const unitIds = renewForm.assetUnitIds
        .split(/[,，\s]+/)
        .map((value) => value.trim())
        .filter((value) => value !== '');
      return assetOperationsService.renewUpstream(
        contractId,
        {
          contract_number: renewForm.contractNumber.trim(),
          name: renewForm.name.trim(),
          owner_party_id: '',
          operator_party_id: '',
          start_date: renewForm.startDate,
          end_date: renewForm.endDate,
          payment_cycle: renewForm.paymentCycle,
          payment_day: Number(renewForm.paymentDay),
          deposit_amount: renewForm.depositAmount,
          asset_unit_ids: unitIds,
          rent_schedules: [],
          scan_document_id: input.session.documentId,
          scan_owner_id: input.session.id,
        },
        input.idempotencyKey,
      );
    },
    onSuccess: (result) => {
      setNotice(`续签后继合同 ${result.contractNumber} 已登记，各方由原合同带出。`);
    },
  });

  const previewCommitted = conflictMessage(previewMutation.error) ?? conflictMessage(commitMutation.error);

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>上游合同 · 生命周期操作</h1>
      {notice != null ? <Alert type="success" showIcon title={notice} /> : null}

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>退出在管</h2>
        <label className={styles.fieldColumn}>
          退出生效日（该日起合同不再有效）
          <Input
            type="date"
            value={form.effectiveDate}
            onChange={(event) =>
              setForm((previous) => ({
                ...previous,
                effectiveDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Input
            value={form.reason}
            onChange={(event) =>
              setForm((previous) => ({ ...previous, reason: event.target.value }))
            }
          />
        </label>
        <Button
          disabled={form.effectiveDate === '' || form.reason.trim() === '' || previewMutation.isPending}
          loading={previewMutation.isPending}
          onClick={() => previewMutation.mutate()}
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
            {preview.coverageImpact.map((impact) => (
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
                  commitMutation.error instanceof Error
                    ? commitMutation.error.message
                    : '提交失败'
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
          <Input
            value={reversal.targetEventId}
            onChange={(event) =>
              setReversal((previous) => ({
                ...previous,
                targetEventId: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          撤销生效日
          <Input
            type="date"
            value={reversal.effectiveDate}
            onChange={(event) =>
              setReversal((previous) => ({
                ...previous,
                effectiveDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          原因
          <Input
            value={reversal.reason}
            onChange={(event) =>
              setReversal((previous) => ({
                ...previous,
                reason: event.target.value,
              }))
            }
          />
        </label>
        {reversalMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              reversalMutation.error instanceof Error
                ? reversalMutation.error.message
                : '撤销失败'
            }
          />
        ) : null}
        <Button
          disabled={
            reversal.targetEventId.trim() === '' ||
            reversal.effectiveDate === '' ||
            reversal.reason.trim() === '' ||
            reversalMutation.isPending
          }
          loading={reversalMutation.isPending}
          onClick={() => reversalMutation.mutate(newIdempotencyKey())}
        >
          撤销退出
        </Button>
      </div>

      <div className={styles.actionCard}>
        <h2 className={styles.actionTitle}>登记续签</h2>
        <label className={styles.fieldColumn}>
          续签扫描件
          <input
            ref={renewFileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            aria-label="续签扫描件"
            onChange={(event) => {
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
        <label className={styles.fieldColumn}>
          后继合同编号
          <Input
            value={renewForm.contractNumber}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                contractNumber: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          后继合同名称
          <Input
            value={renewForm.name}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                name: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          后继起租日
          <Input
            type="date"
            value={renewForm.startDate}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                startDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          后继到期日
          <Input
            type="date"
            value={renewForm.endDate}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                endDate: event.target.value,
              }))
            }
          />
        </label>
        <label className={styles.fieldColumn}>
          覆盖资产单元 ID（由原合同带出核对）
          <Input
            value={renewForm.assetUnitIds}
            onChange={(event) =>
              setRenewForm((previous) => ({
                ...previous,
                assetUnitIds: event.target.value,
              }))
            }
          />
        </label>
        {renewMutation.isError ? (
          <Alert
            type="error"
            showIcon
            title={
              renewMutation.error instanceof Error
                ? renewMutation.error.message
                : '续签失败'
            }
          />
        ) : null}
        <Button
          type="primary"
          disabled={
            renewSessionMutation.data == null ||
            renewForm.contractNumber.trim() === '' ||
            renewForm.name.trim() === '' ||
            renewForm.startDate === '' ||
            renewForm.endDate === '' ||
            renewForm.assetUnitIds.trim() === '' ||
            renewMutation.isPending
          }
          loading={renewMutation.isPending}
          onClick={() =>
            renewSessionMutation.data != null &&
            renewMutation.mutate({
              session: {
                id: renewSessionMutation.data.id,
                documentId: renewSessionMutation.data.documentId,
              },
              idempotencyKey: newIdempotencyKey(),
            })
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
