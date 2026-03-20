import React, { useEffect, useState } from 'react';
import { Popover, Space, Tag, Typography } from 'antd';
import type { FormInstance } from 'antd/es/form';
import dayjs from 'dayjs';

import type { CompleteResult, ConfirmedContractData } from '@/services/pdfImportService';
import { ContractStatus } from '@/types/rentContract';
import styles from './ContractImportReview.module.css';

const { Text } = Typography;

export interface FormValues {
  revenue_mode?: ConfirmedContractData['revenue_mode'];
  contract_direction?: ConfirmedContractData['contract_direction'];
  group_relation_type?: ConfirmedContractData['group_relation_type'];
  operator_party_id?: string;
  contract_number: string;
  asset_id?: string;
  owner_party_id?: string;
  lessor_party_id?: string;
  lessee_party_id?: string;
  tenant_name: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date?: dayjs.Dayjs;
  start_date?: dayjs.Dayjs;
  end_date?: dayjs.Dayjs;
  rentable_area?: number;
  monthly_rent?: number;
  total_deposit?: number;
  contract_status?: string;
  payment_terms?: string;
  contract_notes?: string;
  settlement_rule_json?: string;
  service_fee_ratio?: string;
  fee_calculation_base?: string;
  agency_scope?: string;
  rent_terms?: Array<{
    start_date: string;
    end_date: string;
    monthly_rent: string;
    rent_description?: string;
  }>;
}

interface EvidenceSnippet {
  snippet?: string;
  match?: string;
  match_type?: string;
  source?: string;
}

export type ReviewFieldLabelRenderer = (label: string, fieldKey: string) => React.ReactNode;

interface UseReviewDataOptions {
  form: FormInstance<FormValues>;
  result: CompleteResult;
}

interface UseReviewDataResult {
  currentRevenueMode: ConfirmedContractData['revenue_mode'] | undefined;
  handleFieldChange: (changedValues: Record<string, unknown>) => void;
  renderFieldLabel: ReviewFieldLabelRenderer;
}

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return value != null && typeof value === 'object' && !Array.isArray(value);
};

const toOptionalString = (value: unknown): string | undefined => {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  return undefined;
};

const toNumber = (value: unknown): number | undefined => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const normalized = value.trim();
    if (normalized !== '') {
      const parsed = Number(normalized);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }
  return undefined;
};

const toDateValue = (value: unknown): dayjs.Dayjs | undefined => {
  if (typeof value === 'string' || typeof value === 'number' || value instanceof Date) {
    const parsed = dayjs(value);
    return parsed.isValid() ? parsed : undefined;
  }
  return undefined;
};

const toRevenueMode = (value: unknown): ConfirmedContractData['revenue_mode'] | undefined => {
  switch (value) {
    case 'LEASE':
    case 'AGENCY':
      return value;
    default:
      return undefined;
  }
};

const toContractDirection = (
  value: unknown
): ConfirmedContractData['contract_direction'] | undefined => {
  switch (value) {
    case 'LESSOR':
    case 'LESSEE':
      return value;
    default:
      return undefined;
  }
};

const toGroupRelationType = (
  value: unknown
): ConfirmedContractData['group_relation_type'] | undefined => {
  switch (value) {
    case 'UPSTREAM':
    case 'DOWNSTREAM':
    case 'ENTRUSTED':
    case 'DIRECT_LEASE':
      return value;
    default:
      return undefined;
  }
};

const toRentTerms = (value: unknown): NonNullable<FormValues['rent_terms']> => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap(term => {
    if (!isRecord(term)) {
      return [];
    }

    const rentDescription = toOptionalString(term.rent_description);
    return [
      {
        start_date: toOptionalString(term.start_date) ?? '',
        end_date: toOptionalString(term.end_date) ?? '',
        monthly_rent: toOptionalString(term.monthly_rent) ?? '',
        ...(rentDescription != null ? { rent_description: rentDescription } : {}),
      },
    ];
  });
};

export const useReviewData = ({ form, result }: UseReviewDataOptions): UseReviewDataResult => {
  const [, setModifiedFields] = useState<Set<string>>(new Set());
  const [currentRevenueMode, setCurrentRevenueMode] = useState<
    ConfirmedContractData['revenue_mode'] | undefined
  >(undefined);

  const fieldEvidence = result.extraction_result.field_evidence ?? undefined;
  const fieldSources = result.extraction_result.field_sources ?? undefined;

  const hasExtractedValue = (fieldKey: string): boolean => {
    const value = result.extraction_result.data[fieldKey];
    if (value == null) {
      return false;
    }
    if (typeof value === 'string') {
      return value.trim() !== '';
    }
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return true;
  };

  const getEvidenceSnippet = (fieldKey: string): EvidenceSnippet | null => {
    if (fieldEvidence == null) {
      return null;
    }
    const rawEvidence = fieldEvidence[fieldKey];
    if (rawEvidence == null || Array.isArray(rawEvidence) || typeof rawEvidence !== 'object') {
      return null;
    }
    return rawEvidence as EvidenceSnippet;
  };

  const resolveSourceLabel = (sourceKey?: string): string => {
    if (sourceKey == null || sourceKey.trim() === '') {
      return '未知';
    }
    const labels: Record<string, string> = {
      ocr_llm: 'OCR+大模型',
      ocr_regex: 'OCR+正则',
      vision: '视觉模型',
      regex: '正则',
      text: '文本解析',
      smart: '智能合并',
    };
    return labels[sourceKey] ?? sourceKey;
  };

  const renderEvidenceTag = (fieldKey: string) => {
    const evidence = getEvidenceSnippet(fieldKey);
    const evidenceSource = evidence?.source;
    const mappedSource = fieldSources != null ? fieldSources[fieldKey] : undefined;
    const sourceKey =
      typeof evidenceSource === 'string' && evidenceSource.trim() !== ''
        ? evidenceSource
        : typeof mappedSource === 'string' && mappedSource.trim() !== ''
          ? mappedSource
          : undefined;
    const snippet = evidence?.snippet;
    const hasSnippet = typeof snippet === 'string' && snippet.trim() !== '';
    const matchValue = evidence?.match;
    const hasMatch = matchValue != null && String(matchValue).trim() !== '';

    if (!hasSnippet && !hasMatch && sourceKey == null) {
      return null;
    }

    const content = (
      <div className={styles.evidencePopover}>
        <Text type="secondary" className={styles.evidenceMetaText}>
          来源: {resolveSourceLabel(sourceKey)}
        </Text>
        {hasSnippet ? (
          <Text className={styles.evidenceSnippetText}>{snippet}</Text>
        ) : (
          <Text type="secondary">未提供原文片段</Text>
        )}
        {hasMatch && (
          <Text type="secondary" className={styles.evidenceMetaWithGap}>
            匹配: {String(matchValue)}
          </Text>
        )}
        {evidence?.match_type != null && String(evidence.match_type).trim() !== '' && (
          <Text type="secondary" className={styles.evidenceMetaText}>
            匹配类型: {String(evidence.match_type)}
          </Text>
        )}
      </div>
    );

    return (
      <Popover content={content} title="提取证据" placement="topLeft">
        <Tag color="geekblue">证据</Tag>
      </Popover>
    );
  };

  const renderFieldLabel: ReviewFieldLabelRenderer = (label, fieldKey) => (
    <Space size={6} wrap>
      <span>{label}</span>
      {hasExtractedValue(fieldKey) && <Tag color="blue">自动提取</Tag>}
      {renderEvidenceTag(fieldKey)}
    </Space>
  );

  useEffect(() => {
    const validatedData = result.validation_result.validated_data;
    const recommendations = result.matching_result.recommendations;
    const agencyDetail = isRecord(validatedData.agency_detail) ? validatedData.agency_detail : undefined;
    const revenueMode = toRevenueMode(validatedData.revenue_mode);

    form.setFieldsValue({
      revenue_mode: revenueMode,
      contract_direction: toContractDirection(validatedData.contract_direction),
      group_relation_type: toGroupRelationType(validatedData.group_relation_type),
      operator_party_id: toOptionalString(validatedData.operator_party_id) ?? '',
      contract_number: toOptionalString(validatedData.contract_number) ?? '',
      asset_id: recommendations.asset_id ?? '',
      owner_party_id: recommendations.owner_party_id ?? '',
      lessor_party_id: toOptionalString(validatedData.lessor_party_id) ?? '',
      lessee_party_id: toOptionalString(validatedData.lessee_party_id) ?? '',
      tenant_name: toOptionalString(validatedData.tenant_name) ?? '',
      tenant_contact: toOptionalString(validatedData.tenant_contact) ?? '',
      sign_date: toDateValue(validatedData.sign_date),
      start_date: toDateValue(validatedData.start_date),
      end_date: toDateValue(validatedData.end_date),
      rentable_area: toNumber(validatedData.rentable_area),
      monthly_rent: toNumber(validatedData.monthly_rent),
      total_deposit: toNumber(validatedData.total_deposit) ?? 0,
      contract_status: toOptionalString(validatedData.contract_status) ?? ContractStatus.ACTIVE,
      payment_terms: toOptionalString(validatedData.payment_terms) ?? '',
      contract_notes: toOptionalString(validatedData.contract_notes) ?? '',
      settlement_rule_json:
        validatedData.settlement_rule != null
          ? JSON.stringify(validatedData.settlement_rule, null, 2)
          : '',
      service_fee_ratio: toOptionalString(agencyDetail?.service_fee_ratio) ?? '',
      fee_calculation_base: toOptionalString(agencyDetail?.fee_calculation_base),
      agency_scope: toOptionalString(agencyDetail?.agency_scope) ?? '',
      rent_terms: toRentTerms(validatedData.rent_terms),
    });

    setCurrentRevenueMode(revenueMode);
  }, [form, result]);

  const handleFieldChange = (changedValues: Record<string, unknown>) => {
    setModifiedFields(prev => {
      const next = new Set(prev);
      Object.keys(changedValues).forEach(fieldName => {
        next.add(fieldName);
      });
      return next;
    });

    if (Object.prototype.hasOwnProperty.call(changedValues, 'revenue_mode')) {
      setCurrentRevenueMode(toRevenueMode(changedValues.revenue_mode));
    }
  };

  return {
    currentRevenueMode,
    handleFieldChange,
    renderFieldLabel,
  };
};

export default useReviewData;
