/**
 * PDF合同信息确认界面
 */

import React, { useState } from 'react';
import { Button, Card, Form, Space } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import { normalizeOptionalId } from '@/utils/normalize';

import {
  type CompleteResult,
  type ConfirmedContractData,
  type ConfirmImportResponse,
} from '@/services/pdfImportService';
import { CONTRACT_GROUP_ROUTES } from '@/constants/routes';
import ReviewSections from './ReviewSections';
import ReviewSummary from './ReviewSummary';
import useReviewData, { type FormValues } from './useReviewData';
import styles from './ContractImportReview.module.css';

export { normalizeOptionalId } from '@/utils/normalize';

const pageLogger = createLogger('ContractImportReview');

type AgencyFeeCalculationBase = NonNullable<
  ConfirmedContractData['agency_detail']
>['fee_calculation_base'];

interface ContractImportReviewProps {
  sessionId: string;
  result: CompleteResult;
  onConfirm: (data: ConfirmedContractData) => Promise<ConfirmImportResponse>;
  onCancel: () => void;
  onBack: () => void;
}

type OwnerReferenceFields = Pick<FormValues, 'owner_party_id'>;

export const parseJsonObjectField = (value: string): ConfirmedContractData['settlement_rule'] => {
  const normalized = value.trim();
  if (normalized === '') {
    throw new Error('结算规则 JSON 不能为空');
  }
  const parsed: unknown = JSON.parse(normalized);
  if (parsed == null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('结算规则必须是合法 JSON 对象');
  }
  return parsed as ConfirmedContractData['settlement_rule'];
};

export const resolveOwnerReferences = (
  validatedValues: OwnerReferenceFields,
  storedValues: OwnerReferenceFields
): { ownerPartyId: string | undefined } => {
  const ownerPartyId = normalizeOptionalId(
    validatedValues.owner_party_id ?? storedValues.owner_party_id
  );
  return { ownerPartyId };
};

const VALID_AGENCY_FEE_BASES = new Set<AgencyFeeCalculationBase>(['actual_received', 'due_amount']);

const normalizeAgencyFeeCalculationBase = (
  value: string | undefined
): AgencyFeeCalculationBase | undefined => {
  if (value == null) {
    return undefined;
  }
  const normalized = value.trim();
  if (VALID_AGENCY_FEE_BASES.has(normalized as AgencyFeeCalculationBase)) {
    return normalized as AgencyFeeCalculationBase;
  }
  return undefined;
};

const ContractImportReview: React.FC<ContractImportReviewProps> = ({
  result,
  onConfirm,
  onBack,
}) => {
  const navigate = useNavigate();
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');
  const [showAdvancedFields, setShowAdvancedFields] = useState(false);
  const { currentRevenueMode, handleFieldChange, renderFieldLabel } = useReviewData({ form, result });

  // 确认导入
  const handleConfirm = async () => {
    try {
      const validatedValues = (await form.validateFields()) as FormValues;
      const storedValues = form.getFieldsValue(true) as FormValues;
      const values: FormValues = {
        ...storedValues,
        ...validatedValues,
      };

      // 转换日期格式
      const { ownerPartyId } = resolveOwnerReferences(validatedValues, storedValues);
      const settlementRule = parseJsonObjectField(values.settlement_rule_json ?? '');
      const operatorPartyId = normalizeOptionalId(values.operator_party_id);
      const lessorPartyId = normalizeOptionalId(values.lessor_party_id);
      const lesseePartyId = normalizeOptionalId(values.lessee_party_id);
      if (
        values.revenue_mode == null ||
        values.contract_direction == null ||
        values.group_relation_type == null ||
        operatorPartyId == null ||
        ownerPartyId == null ||
        lessorPartyId == null ||
        lesseePartyId == null
      ) {
        MessageManager.error('请补全新合同上下文');
        return;
      }

      const serviceFeeRatio = values.service_fee_ratio?.trim() ?? '';
      const feeCalculationBase = normalizeAgencyFeeCalculationBase(values.fee_calculation_base);
      if (values.revenue_mode === 'AGENCY' && feeCalculationBase == null) {
        form.setFields([
          {
            name: 'fee_calculation_base',
            errors: ['计费基数必须是 actual_received 或 due_amount'],
          },
        ]);
        MessageManager.error('请检查表单填写是否正确');
        return;
      }
      const confirmedData: ConfirmedContractData = {
        revenue_mode: values.revenue_mode,
        contract_direction: values.contract_direction,
        group_relation_type: values.group_relation_type,
        operator_party_id: operatorPartyId,
        contract_number: values.contract_number,
        asset_id: normalizeOptionalId(values.asset_id),
        owner_party_id: ownerPartyId,
        lessor_party_id: lessorPartyId,
        lessee_party_id: lesseePartyId,
        tenant_name: values.tenant_name,
        tenant_contact: values.tenant_contact,
        tenant_phone: values.tenant_phone,
        tenant_address: values.tenant_address,
        sign_date: values.sign_date != null ? values.sign_date.format('YYYY-MM-DD') : undefined,
        start_date: values.start_date != null ? values.start_date.format('YYYY-MM-DD') : '',
        end_date: values.end_date != null ? values.end_date.format('YYYY-MM-DD') : '',
        monthly_rent_base: values.monthly_rent?.toString() ?? '',
        total_deposit: values.total_deposit?.toString() ?? '0',
        contract_status: values.contract_status,
        payment_terms: values.payment_terms,
        contract_notes: values.contract_notes,
        settlement_rule: settlementRule,
        ...(values.revenue_mode === 'AGENCY'
          ? {
              agency_detail: {
                service_fee_ratio: serviceFeeRatio,
                fee_calculation_base: feeCalculationBase!,
                agency_scope: values.agency_scope?.trim() ?? '',
              },
            }
          : {}),
        rent_terms:
          values.rent_terms?.map(term => ({
            start_date: term.start_date,
            end_date: term.end_date,
            monthly_rent: term.monthly_rent,
            rent_description: term.rent_description,
          })) ?? [],
      };

      setLoading(true);
      const response = await onConfirm(confirmedData);

      if (response.success) {
        MessageManager.success('合同导入成功！');
        if (response.contract_group_id != null && response.contract_group_id.trim() !== '') {
          navigate(CONTRACT_GROUP_ROUTES.DETAIL(response.contract_group_id));
        }
      } else {
        MessageManager.error(response.error ?? '导入失败');
      }
    } catch (error: unknown) {
      pageLogger.error('表单验证失败', error);
      const _errorMessage = error instanceof Error ? error.message : '表单验证失败';
      MessageManager.error('请检查表单填写是否正确');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.reviewContainer}>
      <ReviewSummary result={result} />

      <Card title="合同信息确认">
        <ReviewSections
          form={form}
          result={result}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          currentRevenueMode={currentRevenueMode}
          showAdvancedFields={showAdvancedFields}
          onShowAdvancedFieldsChange={setShowAdvancedFields}
          onValuesChange={handleFieldChange}
          renderFieldLabel={renderFieldLabel}
          parseJsonObjectField={parseJsonObjectField}
          normalizeAgencyFeeCalculationBase={normalizeAgencyFeeCalculationBase}
        />
      </Card>

      <div className={styles.actionFooter}>
        <Space size="large" className={styles.actionSpace}>
          <Button size="large" onClick={onBack}>
            返回
          </Button>
          <Button
            size="large"
            type="primary"
            icon={<SaveOutlined />}
            loading={loading}
            onClick={handleConfirm}
            disabled={result.validation_result.errors.length > 0}
            aria-label="确认导入"
          >
            确认导入
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default ContractImportReview;
