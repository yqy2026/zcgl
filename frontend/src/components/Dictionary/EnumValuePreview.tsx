import React from 'react';
import { Tag, Tooltip, Space } from 'antd';
import type { EnumFieldValue } from '@/types/dictionary';

interface EnumValuePreviewProps {
  values: EnumFieldValue[];
  maxDisplay?: number;
  showInactiveCount?: boolean;
  _showInactiveCount?: boolean;
  size?: 'small' | 'middle' | 'large';
  className?: string;
}

/**
 * 统一的枚举值预览组件
 * 提供一致的枚举值显示格式
 */
const EnumValuePreview: React.FC<EnumValuePreviewProps> = ({
  values,
  maxDisplay = 5,
  _showInactiveCount = true,
  size = 'small',
  className = '',
}) => {
  if (values === undefined || values === null || !Array.isArray(values) || values.length === 0) {
    return (
      <span
        className={`enum-preview-empty ${className}`}
        style={{ color: '#999', fontSize: '12px' }}
      >
        暂无枚举值
      </span>
    );
  }

  // 过滤活跃值并按排序排序
  const activeValues = values
    .filter(value => value.is_active)
    .sort((a, b) => a.sort_order - b.sort_order)
    .slice(0, maxDisplay);

  // 计算非活跃数量
  const inactiveCount = values.filter(value => !value.is_active).length;
  const remainingCount = values.length - activeValues.length;

  // 根据size设置样式
  const getTagSize = () => {
    switch (size) {
      case 'large':
        return { fontSize: '14px', padding: '4px 8px', marginBottom: '4px' };
      case 'middle':
        return { fontSize: '12px', padding: '2px 6px', marginBottom: '3px' };
      case 'small':
      default:
        return { fontSize: '11px', padding: '1px 4px', marginBottom: '2px' };
    }
  };

  const tagStyle = getTagSize();

  return (
    <div className={`enum-value-preview ${className}`}>
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
                {value.code !== undefined && value.code !== null && value.code !== '' && (
                  <div>
                    <strong>编码:</strong> {value.code}
                  </div>
                )}
                {value.description !== undefined &&
                  value.description !== null &&
                  value.description !== '' && (
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
              color={
                value.color !== undefined && value.color !== null && value.color !== ''
                  ? value.color
                  : value.is_default
                    ? 'gold'
                    : 'green'
              }
              style={{
                ...tagStyle,
                cursor: 'default',
                border:
                  value.color !== undefined && value.color !== null && value.color !== ''
                    ? 'none'
                    : '1px solid #d9d9d9',
              }}
            >
              {value.label}
              {value.is_default && <span style={{ marginLeft: '4px', fontWeight: 'bold' }}>★</span>}
            </Tag>
          </Tooltip>
        ))}

        {/* 显示剩余数量 */}
        {remainingCount > 0 && (
          <Tag color="processing" style={tagStyle}>
            +{remainingCount}
          </Tag>
        )}
      </Space>

      {/* 显示非活跃数量 */}
      {_showInactiveCount && inactiveCount > 0 && (
        <div
          style={{
            fontSize: '11px',
            color: '#ff4d4f',
            marginTop: '2px',
            lineHeight: 1.2,
          }}
        >
          {inactiveCount} 个已禁用
        </div>
      )}
    </div>
  );
};

export default EnumValuePreview;
