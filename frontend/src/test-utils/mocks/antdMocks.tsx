/**
 * 类型安全的 Ant Design 组件 Mock
 * 用于测试中替代真实的 Ant Design 组件
 */

import type { ReactNode, FC, PropsWithChildren, ButtonHTMLAttributes } from 'react';
import React from 'react';

// Card 组件 Mock
export interface MockCardProps {
  children?: ReactNode;
  className?: string;
  hoverable?: boolean;
  style?: React.CSSProperties;
  actions?: ReactNode[];
  title?: ReactNode;
  extra?: ReactNode;
  loading?: boolean;
  bordered?: boolean;
}

export const MockCard: FC<MockCardProps> = ({
  children,
  className,
  hoverable,
  style,
  actions,
  title,
}) => (
  <div data-testid="card" className={className} style={style} data-hoverable={hoverable}>
    {title && <div data-testid="card-title">{title}</div>}
    {actions && <div data-testid="card-actions">{actions}</div>}
    {children}
  </div>
);

// Tag 组件 Mock
export interface MockTagProps {
  children?: ReactNode;
  color?: string;
  closable?: boolean;
  onClose?: () => void;
}

export const MockTag: FC<MockTagProps> = ({ children, color, closable }) => (
  <div data-testid="tag" data-color={color} data-closable={closable}>
    {children}
  </div>
);

// Button 组件 Mock
export interface MockButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type'> {
  children?: ReactNode;
  icon?: ReactNode;
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  danger?: boolean;
  loading?: boolean;
  htmlType?: 'button' | 'submit' | 'reset';
}

export const MockButton: FC<MockButtonProps> = ({
  children,
  icon,
  onClick,
  type,
  danger,
  disabled,
  htmlType = 'button',
}) => (
  <button
    data-testid="button"
    data-type={type}
    data-danger={danger}
    onClick={onClick}
    disabled={disabled}
    type={htmlType}
  >
    {icon}
    {children}
  </button>
);

// Space 组件 Mock
export interface MockSpaceProps {
  children?: ReactNode;
  direction?: 'horizontal' | 'vertical';
  size?: 'small' | 'middle' | 'large' | number;
}

export const MockSpace: FC<MockSpaceProps> = ({ children }) => (
  <div data-testid="space">{children}</div>
);

// Tooltip 组件 Mock
export interface MockTooltipProps {
  children?: ReactNode;
  title?: ReactNode;
  placement?: string;
}

export const MockTooltip: FC<MockTooltipProps> = ({ children, title }) => (
  <div data-testid="tooltip" data-title={String(title)}>
    {children}
  </div>
);

// Row 组件 Mock
export interface MockRowProps {
  children?: ReactNode;
  gutter?: number | [number, number];
  justify?: string;
  align?: string;
}

export const MockRow: FC<MockRowProps> = ({ children, gutter }) => (
  <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
    {children}
  </div>
);

// Col 组件 Mock
export interface MockColProps {
  children?: ReactNode;
  span?: number;
  xs?: number;
  sm?: number;
  md?: number;
  lg?: number;
  xl?: number;
}

export const MockCol: FC<MockColProps> = ({ children, span }) => (
  <div data-testid="col" data-span={span}>
    {children}
  </div>
);

// Statistic 组件 Mock
export interface MockStatisticProps {
  title?: ReactNode;
  value?: string | number;
  suffix?: ReactNode;
  prefix?: ReactNode;
  precision?: number;
  valueStyle?: React.CSSProperties;
}

export const MockStatistic: FC<MockStatisticProps> = ({
  title,
  value,
  suffix,
  precision,
  valueStyle,
}) => (
  <div data-testid="statistic" data-title={String(title)}>
    <div
      data-value={value}
      data-precision={precision}
      data-value-style={JSON.stringify(valueStyle)}
    >
      {value}
      {suffix}
    </div>
    <div data-testid="statistic-title">{title}</div>
  </div>
);

// Progress 组件 Mock
export interface MockProgressProps {
  percent?: number;
  strokeColor?: string;
  size?: 'small' | 'default';
  showInfo?: boolean;
  status?: 'success' | 'exception' | 'normal' | 'active';
}

export const MockProgress: FC<MockProgressProps> = ({ percent, strokeColor, size, showInfo }) => (
  <div
    data-testid="progress"
    data-percent={percent}
    data-stroke-color={strokeColor}
    data-size={size}
    data-show-info={showInfo}
  >
    {percent}%
  </div>
);

// Form 组件 Mock
export interface MockFormProps {
  children?: ReactNode;
  form?: unknown;
  onFinish?: (values: unknown) => void;
  onFinishFailed?: (errorInfo: unknown) => void;
  initialValues?: Record<string, unknown>;
  layout?: 'horizontal' | 'vertical' | 'inline';
}

export const MockForm: FC<MockFormProps> & {
  Item: FC<PropsWithChildren<{ name?: string; label?: ReactNode; rules?: unknown[] }>>;
  useForm: () => [unknown];
} = ({ children, onFinish }) => (
  <form
    data-testid="form"
    onSubmit={e => {
      e.preventDefault();
      onFinish?.({});
    }}
  >
    {children}
  </form>
);

MockForm.Item = ({ children, name, label }) => (
  <div data-testid="form-item" data-name={name}>
    {label && <label>{label}</label>}
    {children}
  </div>
);

MockForm.useForm = () => [{}];
MockForm.displayName = 'MockForm';
MockForm.Item.displayName = 'MockFormItem';

// Input 组件 Mock
export interface MockInputProps {
  value?: string;
  defaultValue?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  disabled?: boolean;
  maxLength?: number;
}

export const MockInput: FC<MockInputProps> = ({
  value,
  defaultValue,
  onChange,
  placeholder,
  disabled,
}) => (
  <input
    data-testid="input"
    value={value}
    defaultValue={defaultValue}
    onChange={onChange}
    placeholder={placeholder}
    disabled={disabled}
  />
);

// Select 组件 Mock
export interface MockSelectProps {
  value?: string | string[];
  defaultValue?: string | string[];
  onChange?: (value: string) => void;
  options?: Array<{ label: string; value: string }>;
  placeholder?: string;
  disabled?: boolean;
  mode?: 'multiple' | 'tags';
}

export const MockSelect: FC<MockSelectProps> = ({
  value,
  onChange,
  options,
  placeholder,
  disabled,
}) => (
  <select
    data-testid="select"
    value={value as string}
    onChange={e => onChange?.(e.target.value)}
    disabled={disabled}
  >
    {placeholder && <option value="">{placeholder}</option>}
    {options?.map(opt => (
      <option key={opt.value} value={opt.value}>
        {opt.label}
      </option>
    ))}
  </select>
);

// Modal 组件 Mock
export interface MockModalProps {
  children?: ReactNode;
  open?: boolean;
  visible?: boolean;
  title?: ReactNode;
  onOk?: () => void;
  onCancel?: () => void;
  confirmLoading?: boolean;
  footer?: ReactNode;
}

export const MockModal: FC<MockModalProps> = ({
  children,
  open,
  visible,
  title,
  onOk,
  onCancel,
}) => {
  const isOpen = open ?? visible;
  if (!isOpen) return null;

  return (
    <div data-testid="modal">
      <div data-testid="modal-title">{title}</div>
      <div data-testid="modal-content">{children}</div>
      <div data-testid="modal-footer">
        <button onClick={onCancel}>取消</button>
        <button onClick={onOk}>确定</button>
      </div>
    </div>
  );
};

// Table 组件 Mock
export interface MockTableProps<T = unknown> {
  dataSource?: T[];
  columns?: Array<{
    title: string;
    dataIndex: string;
    key?: string;
    render?: (value: unknown, record: T, index: number) => ReactNode;
  }>;
  loading?: boolean;
  pagination?: boolean | object;
  rowKey?: string | ((record: T) => string);
  onChange?: (pagination: unknown, filters: unknown, sorter: unknown) => void;
}

export const MockTable = <T extends object>({
  dataSource,
  columns,
  loading,
  rowKey,
}: MockTableProps<T>) => {
  const resolveRowKey = (record: T): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record);
    }
    if (typeof rowKey === 'string') {
      const value = (record as Record<string, unknown>)[rowKey];
      if (typeof value === 'string' || typeof value === 'number') {
        return String(value);
      }
    }

    const recordId = (record as Record<string, unknown>).id;
    if (typeof recordId === 'string' || typeof recordId === 'number') {
      return String(recordId);
    }

    return JSON.stringify(record);
  };

  return (
    <div data-testid="table" data-loading={loading}>
      <table>
        <thead>
          <tr>
            {columns?.map(col => (
              <th key={col.dataIndex}>{col.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataSource?.map((record, index) => (
            <tr key={resolveRowKey(record)}>
              {columns?.map(col => (
                <td key={col.dataIndex}>
                  {col.render
                    ? col.render((record as Record<string, unknown>)[col.dataIndex], record, index)
                    : String((record as Record<string, unknown>)[col.dataIndex] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Message Mock
export const mockMessage = {
  success: (content: string) => console.log('[message.success]', content),
  error: (content: string) => console.log('[message.error]', content),
  warning: (content: string) => console.log('[message.warning]', content),
  info: (content: string) => console.log('[message.info]', content),
  loading: (content: string) => console.log('[message.loading]', content),
};

/**
 * 创建完整的 Ant Design Mock 对象
 * 用于 vi.mock('antd', () => createAntdMock())
 */
export function createAntdMock() {
  return {
    Card: MockCard,
    Tag: MockTag,
    Button: MockButton,
    Space: MockSpace,
    Tooltip: MockTooltip,
    Row: MockRow,
    Col: MockCol,
    Statistic: MockStatistic,
    Progress: MockProgress,
    Form: MockForm,
    Input: MockInput,
    Select: MockSelect,
    Modal: MockModal,
    Table: MockTable,
    message: mockMessage,
  };
}
