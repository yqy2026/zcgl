import React from 'react';
import { SettingOutlined } from '@ant-design/icons';
import { Tag, Typography } from 'antd';
import { ACTION_META_MAP, MODULE_META_MAP, REQUEST_METHOD_TONE_MAP } from '../constants';
import type { Tone } from '../types';
import { getResponseTimeLabel, getResponseTimeTone, getStatusMeta } from '../utils';
import styles from '../../OperationLogPage.module.css';

const { Text } = Typography;

interface ToneResolverProps {
  resolveToneClassName: (tone: Tone) => string;
}

interface ActionTagProps extends ToneResolverProps {
  action: string;
}

interface ModuleTagProps extends ToneResolverProps {
  module?: string | null;
  moduleName?: string | null;
}

interface StatusTagProps extends ToneResolverProps {
  status?: number | null;
}

interface RequestMethodTagProps extends ToneResolverProps {
  requestMethod?: string | null;
}

interface ResponseTimeProps extends ToneResolverProps {
  time?: number | null;
  fallback?: string;
}

export const OperationActionTag: React.FC<ActionTagProps> = ({ action, resolveToneClassName }) => {
  const actionConfig = ACTION_META_MAP[action];
  const label = actionConfig?.label ?? (action.trim() === '' ? '未知操作' : action);
  const icon = actionConfig?.icon ?? <SettingOutlined />;
  const toneClassName = resolveToneClassName(actionConfig?.tone ?? 'neutral');

  return (
    <Tag className={`${styles.statusTag} ${styles.actionTag} ${toneClassName}`} icon={icon}>
      {label}
    </Tag>
  );
};

export const OperationModuleTag: React.FC<ModuleTagProps> = ({
  module,
  moduleName,
  resolveToneClassName,
}) => {
  const moduleKey = module == null ? '' : module;
  const moduleMeta = MODULE_META_MAP[moduleKey];

  const derivedLabel = (() => {
    if (moduleName != null && moduleName.trim() !== '') {
      return moduleName;
    }
    if (moduleMeta != null) {
      return moduleMeta.label;
    }
    if (moduleKey !== '') {
      return moduleKey;
    }
    return '-';
  })();

  return (
    <Tag
      className={`${styles.statusTag} ${styles.moduleTag} ${resolveToneClassName(moduleMeta?.tone ?? 'neutral')}`}
    >
      {derivedLabel}
    </Tag>
  );
};

export const OperationStatusTag: React.FC<StatusTagProps> = ({ status, resolveToneClassName }) => {
  const meta = getStatusMeta(status);
  const statusCodeText = typeof status === 'number' ? ` ${status}` : '';

  return (
    <Tag className={`${styles.statusTag} ${resolveToneClassName(meta.tone)}`}>
      {meta.label}
      {statusCodeText}
    </Tag>
  );
};

export const OperationRequestMethodTag: React.FC<RequestMethodTagProps> = ({
  requestMethod,
  resolveToneClassName,
}) => {
  if (requestMethod == null || requestMethod.trim() === '') {
    return <Text type="secondary">-</Text>;
  }

  const normalizedMethod = requestMethod.toUpperCase();
  const tone = REQUEST_METHOD_TONE_MAP[normalizedMethod] ?? 'neutral';

  return (
    <Tag className={`${styles.statusTag} ${styles.methodTag} ${resolveToneClassName(tone)}`}>
      {normalizedMethod}
    </Tag>
  );
};

export const OperationResponseTimeText: React.FC<ResponseTimeProps> = ({
  time,
  resolveToneClassName,
  fallback = '-',
}) => {
  if (typeof time !== 'number') {
    return <>{fallback}</>;
  }

  return (
    <span className={`${styles.responseTime} ${resolveToneClassName(getResponseTimeTone(time))}`}>
      <span className={styles.responseTimeValue}>{time}ms</span>
      <span className={styles.responseTimeLabel}>{getResponseTimeLabel(time)}</span>
    </span>
  );
};
