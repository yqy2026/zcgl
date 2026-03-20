/**
 * Shared constants, types, and utility functions for the PromptList feature.
 * Extracted from PromptListPage.tsx to support sub-component splitting.
 */

import type { ReactNode } from 'react';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { DocType, LLMProvider, PromptStatus } from '@/types/llmPrompt';
import styles from './PromptListPage.module.css';

export type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
export type MetricTone = Extract<Tone, 'success' | 'warning' | 'error'>;

export interface MetaTagConfig {
  label: string;
  hint?: string;
  tone: Tone;
  icon?: ReactNode;
}

export interface PromptFilters {
  doc_type?: DocType;
  status?: PromptStatus;
  provider?: LLMProvider;
}

export const DOC_TYPE_META_MAP: Record<DocType, MetaTagConfig> = {
  [DocType.CONTRACT]: { label: '租赁合同', tone: 'primary' },
  [DocType.PROPERTY_CERT]: { label: '产权证', tone: 'success' },
};

export const PROVIDER_META_MAP: Record<LLMProvider, MetaTagConfig> = {
  [LLMProvider.QWEN]: { label: 'Qwen', tone: 'primary' },
  [LLMProvider.HUNYUAN]: { label: '混元', tone: 'warning' },
  [LLMProvider.DEEPSEEK]: { label: 'DeepSeek', tone: 'error' },
  [LLMProvider.GLM]: { label: '智谱', tone: 'neutral' },
};

export const STATUS_META_MAP: Record<PromptStatus, MetaTagConfig> = {
  [PromptStatus.ACTIVE]: {
    label: '活跃',
    hint: '在线生效',
    tone: 'success',
    icon: <CheckCircleOutlined />,
  },
  [PromptStatus.DRAFT]: {
    label: '草稿',
    hint: '待发布',
    tone: 'warning',
    icon: <ClockCircleOutlined />,
  },
  [PromptStatus.ARCHIVED]: {
    label: '已归档',
    hint: '仅历史',
    tone: 'neutral',
    icon: <StopOutlined />,
  },
};

export const VERSION_SOURCE_META = {
  auto: { label: '自动', hint: '系统生成', tone: 'primary' as Tone },
  manual: { label: '手动', hint: '人工维护', tone: 'neutral' as Tone },
};

export const getAccuracyTone = (value: number): MetricTone => {
  if (value >= 0.9) {
    return 'success';
  }
  if (value >= 0.7) {
    return 'warning';
  }
  return 'error';
};

export const getConfidenceTone = (value: number): MetricTone => {
  if (value >= 0.8) {
    return 'success';
  }
  if (value >= 0.6) {
    return 'warning';
  }
  return 'error';
};

export const getToneClassName = (tone: Tone): string => {
  if (tone === 'primary') {
    return styles.tonePrimary;
  }
  if (tone === 'success') {
    return styles.toneSuccess;
  }
  if (tone === 'warning') {
    return styles.toneWarning;
  }
  if (tone === 'neutral') {
    return styles.toneNeutral;
  }
  return styles.toneError;
};

export const normalizeVersion = (version: string | number): string => {
  const versionText = String(version).trim();
  if (versionText.toLowerCase().startsWith('v')) {
    return versionText;
  }
  return `v${versionText}`;
};
