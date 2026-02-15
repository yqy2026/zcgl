import React from 'react';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FireOutlined,
  InfoCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { PromptStatus } from '@/types/llmPrompt';
import type { OptimizationSuggestion, PromptStatusMeta, SuggestionPriorityMeta } from './types';

export const PROMPT_STATUS_META_MAP: Record<PromptStatus, PromptStatusMeta> = {
  [PromptStatus.ACTIVE]: {
    label: '使用中',
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

export const PRIORITY_META_MAP: Record<OptimizationSuggestion['priority'], SuggestionPriorityMeta> =
  {
    high: {
      label: '高优先级',
      hint: '建议尽快处理',
      tone: 'error',
      icon: <FireOutlined />,
      alertType: 'error',
    },
    medium: {
      label: '中优先级',
      hint: '建议本周处理',
      tone: 'warning',
      icon: <ExclamationCircleOutlined />,
      alertType: 'warning',
    },
    low: {
      label: '低优先级',
      hint: '可排期处理',
      tone: 'success',
      icon: <InfoCircleOutlined />,
      alertType: 'info',
    },
  };
