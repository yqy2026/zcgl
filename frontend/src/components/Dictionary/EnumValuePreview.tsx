import React from 'react';
import { Tag, Tooltip, Space } from 'antd';
import type { EnumFieldValue } from '@/types/dictionary';
import styles from './EnumValuePreview.module.css';

interface EnumValuePreviewProps {
  values: EnumFieldValue[];
  maxDisplay?: number;
  showInactiveCount?: boolean;
  _showInactiveCount?: boolean;
  size?: 'small' | 'middle' | 'large';
  className?: string;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const hasText = (value: string | null | undefined): boolean => value != null && value.trim() !== '';

const getToneByValue = (value: EnumFieldValue): Tone => {
  if (value.is_default === true) {
    return 'warning';
  }
  return 'success';
};

const getSizeClassName = (size: EnumValuePreviewProps['size']): string => {
  if (size === 'large') {
    return styles.sizeLarge;
  }
  if (size === 'middle') {
    return styles.sizeMiddle;
  }
  return styles.sizeSmall;
};

/**
 * 统一的枚举值预览组件
 * 提供一致的枚举值显示格式
 */
const EnumValuePreview: React.FC<EnumValuePreviewProps> = ({
  values,
  maxDisplay = 5,
  showInactiveCount = true,
  _showInactiveCount,
  size = 'small',
  className = '',
}) => {
  const shouldShowInactiveCount = _showInactiveCount ?? showInactiveCount;

  if (!Array.isArray(values) || values.length === 0) {
    return <span className={[styles.emptyState, className].join(' ').trim()}>暂无枚举值</span>;
  }

  // 过滤活跃值并按排序排序
  const activeValues = values
    .filter(value => value.is_active)
    .sort((a, b) => a.sort_order - b.sort_order)
    .slice(0, maxDisplay);

  // 计算非活跃数量
  const inactiveCount = values.filter(value => !value.is_active).length;
  const remainingCount = values.length - activeValues.length;
  const sizeClassName = getSizeClassName(size);
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  return (
    <div className={[styles.enumValuePreview, className].join(' ').trim()}>
      <Space wrap size={size === 'small' ? 2 : 4}>
        {activeValues.map(value => (
          <Tooltip
            key={value.id}
            title={
              <div>
                <div>
                  <strong>标签:</strong> {value.label}
                </div>
                <div>
                  <strong>值:</strong> {value.value}
                </div>
                {hasText(value.code) && (
                  <div>
                    <strong>编码:</strong> {value.code}
                  </div>
                )}
                {hasText(value.description) && (
                  <div>
                    <strong>描述:</strong> {value.description}
                  </div>
                )}
                <div>
                  <strong>排序:</strong> {value.sort_order}
                </div>
                {value.is_default && (
                  <div>
                    <strong>默认值:</strong> 是
                  </div>
                )}
              </div>
            }
          >
            <Tag
              color={hasText(value.color) ? value.color : undefined}
              className={[
                styles.valueTag,
                sizeClassName,
                hasText(value.color) ? styles.customColorTag : toneClassMap[getToneByValue(value)],
              ].join(' ')}
            >
              <span>{value.label}</span>
              {value.is_default === true && <span className={styles.defaultMarker}>★</span>}
            </Tag>
          </Tooltip>
        ))}

        {/* 显示剩余数量 */}
        {remainingCount > 0 && (
          <Tag className={[styles.remainingTag, sizeClassName, styles.tonePrimary].join(' ')}>
            +{remainingCount}
          </Tag>
        )}
      </Space>

      {/* 显示非活跃数量 */}
      {shouldShowInactiveCount === true && inactiveCount > 0 && (
        <div className={styles.inactiveCountText}>{inactiveCount} 个已禁用</div>
      )}
    </div>
  );
};

export default EnumValuePreview;
