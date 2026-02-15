import React, { type ReactNode } from 'react';
import type { DataNode } from 'antd/es/tree';
import type { OrganizationTree } from '@/types/organization';
import { defaultOrganizationTypeIcon } from './constants';
import type {
  HistoryActionMeta,
  OrganizationFilters,
  OrganizationSelectOption,
  Tone,
} from './types';

interface ConvertOrganizationTreeParams {
  treeNodes: OrganizationTree[];
  getTypeIcon: (type: string) => ReactNode;
  getStatusTag: (status: string, className?: string) => ReactNode;
  treeNodeLabelClassName: string;
  treeNodeTitleClassName: string;
  treeStatusTagClassName: string;
}

export const buildOptionLabelMap = (options: OrganizationSelectOption[]): Map<string, string> => {
  const map = new Map<string, string>();
  options.forEach(option => {
    map.set(option.value, option.label);
  });
  return map;
};

export const buildStatusToneMap = (options: OrganizationSelectOption[]): Map<string, Tone> => {
  const map = new Map<string, Tone>();

  options.forEach(option => {
    const rawColor = typeof option.color === 'string' ? option.color.toLowerCase() : '';
    if (rawColor.includes('green')) {
      map.set(option.value, 'success');
      return;
    }
    if (rawColor.includes('red')) {
      map.set(option.value, 'error');
      return;
    }
    if (rawColor.includes('orange') || rawColor.includes('yellow')) {
      map.set(option.value, 'warning');
      return;
    }
    if (rawColor.includes('blue')) {
      map.set(option.value, 'primary');
      return;
    }
    map.set(option.value, 'neutral');
  });

  if (!map.has('active')) {
    map.set('active', 'success');
  }
  if (!map.has('inactive')) {
    map.set('inactive', 'error');
  }
  if (!map.has('suspended')) {
    map.set('suspended', 'warning');
  }

  return map;
};

export const countActiveOrganizationFilters = (filters: OrganizationFilters): number => {
  if (filters.keyword.trim() !== '') {
    return 1;
  }
  return 0;
};

export const resolveOrganizationTypeIcon = (
  type: string,
  iconMap: Record<string, ReactNode>
): ReactNode => {
  return iconMap[type] ?? defaultOrganizationTypeIcon;
};

export const resolveOrganizationTypeLabel = (
  type: string,
  typeLabelMap: Map<string, string>
): string => {
  return typeLabelMap.get(type) ?? type;
};

export const resolveHistoryActionMeta = (
  action: string,
  actionMap: Record<string, HistoryActionMeta>
): HistoryActionMeta => {
  return actionMap[action] ?? { label: action === '' ? '未知' : action, tone: 'neutral' };
};

export const convertOrganizationTreeToDataNodes = ({
  treeNodes,
  getTypeIcon,
  getStatusTag,
  treeNodeLabelClassName,
  treeNodeTitleClassName,
  treeStatusTagClassName,
}: ConvertOrganizationTreeParams): DataNode[] => {
  return treeNodes.map(node => ({
    key: node.id,
    title: (
      <span className={treeNodeLabelClassName}>
        <span className={treeNodeTitleClassName}>
          {getTypeIcon(node.type)} {node.name} ({node.code})
        </span>
        {getStatusTag(node.status, treeStatusTagClassName)}
      </span>
    ),
    children:
      node.children != null && node.children.length > 0
        ? convertOrganizationTreeToDataNodes({
            treeNodes: node.children,
            getTypeIcon,
            getStatusTag,
            treeNodeLabelClassName,
            treeNodeTitleClassName,
            treeStatusTagClassName,
          })
        : [],
  }));
};
