/**
 * 资产运营 · 已签合同录入向导
 *
 * 会话流（契约 §5.4）：选类型 + 上传扫描件 → 服务端会话（自动提取不可用
 * 只降级 warning，操作员手工核对）→ 确认上游/终端（幂等键）→ 成功回执；
 * 未确认可取消并补偿删除。确认请求不能提交类型/扫描件/续签前驱——由会话
 * 注入。四态分离；单选文件、label 可见、唯一 Primary。
 */

import { useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { Alert, Button, Input, Tag } from 'antd';

import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { ContractIntakeSession, ContractIntakeType } from '@/services/assetOperationsService';

import styles from './ContractIntakePage.module.css';
import RentScheduleEditor from './RentScheduleEditor';
import type { RentScheduleInput } from '@/services/assetLedgerService';

const TYPE_LABELS: Record<ContractIntakeType, string> = {
  upstream_lease: '上游承租合同',
  management_agreement: '委托管理协议',
  terminal: '终端合同',
};

const WARNING_LABELS: Record<string, string> = {
  EXTRACTION_UNAVAILABLE: '自动提取暂不可用，请手工核对并填写全部字段',
  UPSTREAM_CONTRACT_MISSING: '暂无上游',
  TERMINAL_TERM_EXCEEDS_UPSTREAM: '租期越界',
  ARCHIVE_DOCUMENT_MISSING: '缺扫描件',
};

interface FormState {
  rentSchedules: RentScheduleInput[];
  contractNumber: string;
  name: string;
  ownerPartyId: string;
  operatorPartyId: string;
  tenantPartyId: string;
  lessorPartyId: string;
  upstreamContractId: string;
  startDate: string;
  endDate: string;
  depositAmount: string;
  paymentCycle: string;
  paymentDay: string;
  managementFeeRate: string;
  oaReference: string;
  assetUnitIds: string;
}

const EMPTY_FORM: FormState = {
  rentSchedules: [],
  contractNumber: '',
  name: '',
  ownerPartyId: '',
  operatorPartyId: '',
  tenantPartyId: '',
  lessorPartyId: '',
  upstreamContractId: '',
  startDate: '',
  endDate: '',
  depositAmount: '0',
  paymentCycle: 'monthly',
  paymentDay: '15',
  managementFeeRate: '',
  oaReference: '',
  assetUnitIds: '',
};

function newIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `intake-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function ContractIntakePage(): React.ReactElement {
  const [contractType, setContractType] = useState<ContractIntakeType>('terminal');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [session, setSession] = useState<ContractIntakeSession | null>(null);
  const { control, getValues, handleSubmit, reset, watch, setValue } = useForm<FormState>({
    defaultValues: EMPTY_FORM,
  });
  const [created, setCreated] = useState<{
    contractNumber: string;
    idempotencyKey: string;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [scheduleValid, setScheduleValid] = useState(true);

  const sessionQuery = useQuery({
    queryKey: ['contract-intake-session', session?.id],
    queryFn: () => assetOperationsService.getIntakeSession(session?.id ?? ''),
    enabled: session?.id != null && session.id !== '',
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => assetOperationsService.createIntakeSession(contractType, file),
    retry: false,
    onSuccess: createdSession => setSession(createdSession),
  });

  const confirmMutation = useMutation({
    mutationFn: (idempotencyKey: string) => {
      if (session == null) {
        throw new Error('会话不存在');
      }
      const form = getValues();
      const unitIds = form.assetUnitIds
        .split(/[,，\s]+/)
        .map(value => value.trim())
        .filter(value => value !== '');
      if (contractType === 'terminal') {
        return assetOperationsService.confirmTerminalIntake(
          session.id,
          {
            contract_number: form.contractNumber.trim(),
            tenant_party_id: form.tenantPartyId.trim(),
            lessor_party_id: form.lessorPartyId.trim(),
            ...(form.upstreamContractId.trim() !== ''
              ? { upstream_contract_id: form.upstreamContractId.trim() }
              : {}),
            start_date: form.startDate,
            end_date: form.endDate,
            ...(form.depositAmount.trim() !== '' ? { deposit_amount: form.depositAmount } : {}),
            asset_unit_ids: unitIds,
            rent_schedules: form.rentSchedules,
          },
          idempotencyKey
        );
      }
      return assetOperationsService.confirmUpstreamIntake(
        session.id,
        {
          contract_number: form.contractNumber.trim(),
          name: form.name.trim(),
          owner_party_id: form.ownerPartyId.trim(),
          operator_party_id: form.operatorPartyId.trim(),
          start_date: form.startDate,
          end_date: form.endDate,
          ...(contractType === 'upstream_lease' && form.paymentCycle !== ''
            ? { payment_cycle: form.paymentCycle }
            : {}),
          ...(contractType === 'upstream_lease' && form.paymentDay !== ''
            ? { payment_day: Number(form.paymentDay) }
            : {}),
          ...(contractType === 'management_agreement' && form.managementFeeRate.trim() !== ''
            ? { management_fee_rate: form.managementFeeRate }
            : {}),
          ...(contractType === 'management_agreement'
            ? { deposit_amount: '0' }
            : form.depositAmount.trim() !== ''
              ? { deposit_amount: form.depositAmount }
              : {}),
          ...(form.oaReference.trim() !== '' ? { oa_reference: form.oaReference } : {}),
          asset_unit_ids: unitIds,
          rent_schedules: contractType === 'management_agreement' ? [] : form.rentSchedules,
        },
        idempotencyKey
      );
    },
    onSuccess: (result, idempotencyKey) =>
      setCreated({
        contractNumber: result.contractNumber,
        idempotencyKey,
      }),
  });

  const cancelMutation = useMutation({
    mutationFn: (sessionId: string) => assetOperationsService.cancelIntakeSession(sessionId),
    onSuccess: () => {
      setSession(null);
      reset(EMPTY_FORM);
      setSelectedFile(null);
      if (fileInputRef.current != null) {
        fileInputRef.current.value = '';
      }
    },
  });

  const isTerminal = contractType === 'terminal';
  const setUpstreamType = contractType !== 'terminal';
  const form = watch();

  const confirmDisabled =
    !scheduleValid ||
    confirmMutation.isPending ||
    form.contractNumber.trim() === '' ||
    form.startDate === '' ||
    form.endDate === '' ||
    form.assetUnitIds.trim() === '' ||
    (isTerminal
      ? form.tenantPartyId.trim() === '' || form.lessorPartyId.trim() === ''
      : form.ownerPartyId.trim() === '' || form.operatorPartyId.trim() === '');

  const renderField = (
    label: string,
    field: Exclude<keyof FormState, 'rentSchedules'>,
    options: { placeholder?: string; type?: string } = {}
  ): React.ReactElement => (
    <label className={styles.fieldColumn}>
      {label}
      <Controller
        control={control}
        name={field}
        render={({ field: inputField }) => (
          <Input {...inputField} placeholder={options.placeholder} type={options.type ?? 'text'} />
        )}
      />
    </label>
  );

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>录入已签合同</h1>
      <p className={styles.hintText} style={{ margin: 0 }}>
        签订在 OA 完成，这里只登记结果。扫描件必须为已签署盖章版；确认后扫描件
        绑定合同且不能重复使用。
      </p>

      {created != null ? (
        <div className={styles.stepCard}>
          <Alert type="success" showIcon title={`已登记合同 ${created.contractNumber}`} />
          <p className={styles.hintText}>
            幂等键 {created.idempotencyKey}
            （相同键重试不会创建第二份合同）。
          </p>
          <Button
            onClick={() => {
              setCreated(null);
              setSession(null);
              reset(EMPTY_FORM);
              setSelectedFile(null);
            }}
          >
            继续录入下一份
          </Button>
        </div>
      ) : session == null ? (
        <div className={styles.stepCard}>
          <h2 className={styles.stepTitle}>第一步 · 选择类型并上传扫描件</h2>
          <div role="radiogroup" aria-label="合同类型" style={{ display: 'flex', gap: 8 }}>
            {(Object.keys(TYPE_LABELS) as ContractIntakeType[]).map(type => (
              <Button
                key={type}
                type={contractType === type ? 'primary' : 'default'}
                onClick={() => setContractType(type)}
              >
                {TYPE_LABELS[type]}
              </Button>
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            <label htmlFor="intake-file-input" style={{ display: 'block', fontSize: 13 }}>
              已签扫描件（PDF/图片）
            </label>
            <input
              id="intake-file-input"
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={event => {
                const file = event.target.files?.[0] ?? null;
                setSelectedFile(file);
              }}
            />
          </div>
          {uploadMutation.isError ? (
            <Alert
              type="error"
              showIcon
              style={{ marginTop: 8 }}
              title={
                uploadMutation.error instanceof Error ? uploadMutation.error.message : '上传失败'
              }
            />
          ) : null}
          <Button
            type="primary"
            style={{ marginTop: 12, alignSelf: 'flex-start' }}
            disabled={selectedFile == null || uploadMutation.isPending}
            loading={uploadMutation.isPending}
            onClick={() => {
              if (selectedFile != null) {
                uploadMutation.mutate(selectedFile);
              }
            }}
          >
            上传并创建会话
          </Button>
        </div>
      ) : session != null ? (
        <>
          {(() => {
            const currentSession: ContractIntakeSession = sessionQuery.data ?? session;
            return (
              <div className={styles.stepCard}>
                <h2 className={styles.stepTitle}>
                  第二步 · 核对信息（{TYPE_LABELS[currentSession.contractType]}）
                </h2>
                <p style={{ margin: '0 0 var(--spacing-sm)' }}>
                  会话状态 <Tag>{currentSession.status}</Tag>
                  <span className={styles.hintText}>有效期至 {currentSession.expiresAt}</span>
                </p>
                {currentSession.warnings.map(warning => (
                  <Alert
                    key={warning.code}
                    type={warning.severity === 'error' ? 'error' : 'warning'}
                    showIcon
                    style={{ marginBottom: 8 }}
                    title={WARNING_LABELS[warning.code] ?? warning.message ?? warning.code}
                  />
                ))}
                <div className={styles.fieldGrid}>
                  {renderField('合同编号', 'contractNumber')}
                  {!isTerminal ? renderField('合同名称', 'name') : null}
                  {isTerminal ? renderField('租户 Party ID', 'tenantPartyId') : null}
                  {isTerminal ? renderField('出租方 Party ID', 'lessorPartyId') : null}
                  {setUpstreamType ? renderField('产权方 Party ID', 'ownerPartyId') : null}
                  {setUpstreamType ? renderField('运营方 Party ID', 'operatorPartyId') : null}
                  {renderField('起租日', 'startDate', { type: 'date' })}
                  {renderField('到期日', 'endDate', { type: 'date' })}
                  {contractType !== 'management_agreement'
                    ? renderField('押金金额', 'depositAmount')
                    : null}
                  {isTerminal ? renderField('上游合同 ID（可留空）', 'upstreamContractId') : null}
                  {contractType === 'upstream_lease'
                    ? renderField('付款周期', 'paymentCycle')
                    : null}
                  {contractType === 'upstream_lease' ? renderField('付款日', 'paymentDay') : null}
                  {contractType === 'management_agreement'
                    ? renderField('管理费比例（0-1）', 'managementFeeRate')
                    : null}
                  {setUpstreamType ? renderField('OA 单号（可选）', 'oaReference') : null}
                  {renderField('覆盖资产单元 ID（逗号分隔）', 'assetUnitIds', {
                    placeholder: 'unit-1, unit-2',
                  })}
                </div>
                {contractType !== 'management_agreement' ? (
                  <RentScheduleEditor
                    key={currentSession.id}
                    startDate={form.startDate}
                    endDate={form.endDate}
                    onChange={stages => setValue('rentSchedules', stages)}
                    onValidityChange={setScheduleValid}
                  />
                ) : null}
                <p className={styles.hintText}>
                  合同类型与扫描件由会话携带，租金阶段与合同一起确认。
                </p>
                {confirmMutation.isError ? (
                  <Alert
                    type="error"
                    showIcon
                    style={{ marginTop: 8 }}
                    title={
                      confirmMutation.error instanceof Error
                        ? confirmMutation.error.message
                        : '确认失败'
                    }
                  />
                ) : null}
                {cancelMutation.isError ? (
                  <Alert
                    type="error"
                    showIcon
                    style={{ marginTop: 8 }}
                    title={
                      cancelMutation.error instanceof Error
                        ? cancelMutation.error.message
                        : '取消失败'
                    }
                  />
                ) : null}
                <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                  <Button
                    type="primary"
                    disabled={confirmDisabled}
                    loading={confirmMutation.isPending}
                    onClick={() =>
                      void handleSubmit(() => confirmMutation.mutate(newIdempotencyKey()))()
                    }
                  >
                    确认登记
                  </Button>
                  <Button
                    disabled={cancelMutation.isPending}
                    loading={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate(currentSession.id)}
                  >
                    取消录入
                  </Button>
                </div>
              </div>
            );
          })()}
        </>
      ) : null}
    </div>
  );
}

export default ContractIntakePage;

export function isIntakeScopeForbidden(error: unknown): boolean {
  return (
    error instanceof AssetOperationsError &&
    (error.code === 'PARTY_SCOPE_MISSING' || error.code === 'ASSET_OPS_PERMISSION_DENIED')
  );
}
