import React, { useEffect, useRef } from 'react';
import { Form, Button, Space, Card, Row, Col, Progress, Typography } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Asset, AssetCreateRequest } from '@/types/asset';
import type { UploadFile } from 'antd/es/upload/interface';
import { useDictionaries } from '@/hooks/useDictionary';
import { COLORS } from '@/styles/colorMap';
import { announceToScreenReader } from '@/utils/accessibility';

// Section components
import {
  AssetFormProvider,
  useAssetFormContext,
  AssetBasicInfoSection,
  AssetAreaSection,
  AssetStatusSection,
  AssetReceptionSection,
  AssetDetailedSection,
} from './Asset';

const { Text } = Typography;

interface AssetFormProps {
  initialData?: Partial<Asset>;
  onSubmit?: (data: AssetCreateRequest) => Promise<void>;
  onCancel?: () => void;
  isLoading?: boolean;
  mode?: 'create' | 'edit';
}

/**
 * Form completion progress bar component
 */
const FormCompletionProgress: React.FC = () => {
  const { completionRate } = useAssetFormContext();

  return (
    <Card style={{ marginBottom: '16px' }}>
      <Row justify="space-between" align="middle">
        <Col>
          <Text>表单完成度</Text>
        </Col>
        <Col flex="auto" style={{ marginLeft: '16px' }}>
          <Progress
            percent={completionRate}
            size="small"
            strokeColor={completionRate === 100 ? COLORS.success : COLORS.primary}
            showInfo={false}
          />
        </Col>
        <Col>
          <Text strong>{completionRate.toFixed(0)}%</Text>
        </Col>
      </Row>
    </Card>
  );
};

/**
 * Form action buttons component
 */
interface FormActionsProps {
  isLoading: boolean;
  mode: 'create' | 'edit';
  onCancel?: () => void;
  onReset: () => void;
}

const FormActions: React.FC<FormActionsProps> = ({ isLoading, mode, onCancel, onReset }) => {
  return (
    <Card>
      <Row justify="end">
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={onReset}
            aria-label="重置表单"
            title="重置表单"
          >
            重置
          </Button>
          {onCancel && (
            <Button onClick={onCancel} aria-label="取消操作" title="取消">
              取消
            </Button>
          )}
          <Button
            type="primary"
            htmlType="submit"
            icon={<SaveOutlined />}
            loading={isLoading}
            aria-label={mode === 'create' ? '创建资产' : '保存修改'}
            title={mode === 'create' ? '创建新资产' : '保存修改'}
          >
            {mode === 'create' ? '创建资产' : '保存修改'}
          </Button>
        </Space>
      </Row>
    </Card>
  );
};

/**
 * Internal form component that uses context
 */
interface AssetFormInnerProps {
  initialData?: Partial<Asset>;
  onSubmit?: (data: AssetCreateRequest) => Promise<void>;
  onCancel?: () => void;
  isLoading: boolean;
  mode: 'create' | 'edit';
}

const AssetFormInner: React.FC<AssetFormInnerProps> = ({
  initialData,
  onSubmit,
  onCancel,
  isLoading,
  mode,
}) => {
  const {
    form,
    completionRate,
    setCompletionRate,
    fileList,
    setFileList,
    terminalContractFileList,
    setTerminalContractFileList,
  } = useAssetFormContext();

  // Load dictionaries
  useDictionaries([
    'property_nature',
    'usage_status',
    'ownership_status',
    'ownership_category',
    'business_category',
    'certificated_usage',
    'actual_usage',
    'tenant_type',
    'business_model',
  ]);

  // Initialize form data
  useEffect(() => {
    if (initialData !== undefined && initialData !== null) {
      const formData = {
        ...initialData,
        contract_start_date:
          initialData.contract_start_date != null
            ? dayjs(String(initialData.contract_start_date))
            : undefined,
        contract_end_date:
          initialData.contract_end_date != null
            ? dayjs(String(initialData.contract_end_date))
            : undefined,
        operation_agreement_start_date:
          initialData.operation_agreement_start_date != null
            ? dayjs(String(initialData.operation_agreement_start_date))
            : undefined,
        operation_agreement_end_date:
          initialData.operation_agreement_end_date != null
            ? dayjs(String(initialData.operation_agreement_end_date))
            : undefined,
      };
      form.setFieldsValue(formData);

      // Initialize attachment lists
      if (initialData.operation_agreement_attachments != null) {
        const fileNames = String(initialData.operation_agreement_attachments)
          .split(',')
          .filter(Boolean);
        const initialFileList: UploadFile[] = fileNames.map((name: string, index: number) => ({
          uid: `-${index}`,
          name: name,
          status: 'done' as const,
          url: `/assets/attachments/${name}`,
          size: 0,
        }));
        setFileList(initialFileList);
      }

      if (initialData.terminal_contract_files != null) {
        const fileNames = String(initialData.terminal_contract_files).split(',').filter(Boolean);
        const initialTerminalFileList: UploadFile[] = fileNames.map(
          (name: string, index: number) => ({
            uid: `terminal-${index}`,
            name: name,
            status: 'done' as const,
            url: `/assets/terminal-contracts/${name}`,
            size: 0,
          })
        );
        setTerminalContractFileList(initialTerminalFileList);
      }
    }
  }, [initialData, form, setFileList, setTerminalContractFileList]);

  // Handle form values change for completion rate calculation
  const valuesChangeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (valuesChangeTimer.current) {
        clearTimeout(valuesChangeTimer.current);
        valuesChangeTimer.current = null;
      }
    };
  }, []);

  const handleValuesChange = (
    _changedValues: Record<string, unknown>,
    allValues: Record<string, unknown>
  ) => {
    if (valuesChangeTimer.current) {
      clearTimeout(valuesChangeTimer.current);
    }

    valuesChangeTimer.current = setTimeout(() => {
      const requiredFields = [
        'property_name',
        'ownership_id',
        'address',
        'ownership_status',
        'property_nature',
        'usage_status',
      ];

      const filledFields = requiredFields.filter(field => allValues[field] != null);
      const rate = (filledFields.length / requiredFields.length) * 100;
      if (rate !== completionRate) {
        setCompletionRate(rate);
      }

      const rentableArea = Number(allValues.rentable_area) ?? 0;
      const rentedArea = Number(allValues.rented_area) ?? 0;

      if (rentableArea > 0) {
        const occupancyRate = Number(((rentedArea / rentableArea) * 100).toFixed(2));
        const unrentedArea = rentableArea - rentedArea;
        const currentOccupancy = form.getFieldValue('occupancy_rate');
        const currentUnrented = form.getFieldValue('unrented_area');

        if (currentOccupancy !== occupancyRate || currentUnrented !== unrentedArea) {
          form.setFieldsValue({
            occupancy_rate: occupancyRate,
            unrented_area: unrentedArea,
          });
        }
      }
    }, 120);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const toBoolean = (value: unknown) =>
        value === true || value === 'true' || value === 1 || value === '1';

      const isAssetCreateRequest = (
        value: Record<string, unknown>
      ): value is AssetCreateRequest => {
        const requiredFields = [
          'property_name',
          'ownership_id',
          'address',
          'ownership_status',
          'property_nature',
          'usage_status',
        ];
        return requiredFields.every(
          field => typeof value[field] === 'string' && value[field] !== ''
        );
      };

      const formatDate = (val: unknown): string | undefined => {
        if (val == null) return undefined;
        if (dayjs.isDayjs(val)) return (val as dayjs.Dayjs).format('YYYY-MM-DD');
        const parsed = dayjs(String(val));
        return parsed.isValid() ? parsed.format('YYYY-MM-DD') : undefined;
      };

      const submitData = {
        ...values,
        include_in_occupancy_rate: toBoolean(values.include_in_occupancy_rate),
        is_sublease: toBoolean(values.is_sublease),
        is_litigated: toBoolean(values.is_litigated),
        operation_agreement_start_date: formatDate(values.operation_agreement_start_date),
        operation_agreement_end_date: formatDate(values.operation_agreement_end_date),
        operation_agreement_attachments: fileList.map(file => file.name).join(','),
        terminal_contract_files: terminalContractFileList.map(file => file.name).join(','),
      } as Record<string, unknown>;

      if (onSubmit !== undefined && onSubmit !== null) {
        if (isAssetCreateRequest(submitData)) {
          await onSubmit(submitData);
          // 通知屏幕阅读器提交成功
          announceToScreenReader('资产保存成功', 'polite');
        } else {
          MessageManager.error('表单数据不完整，请检查必填字段');
          // 通知屏幕阅读器验证失败
          announceToScreenReader('表单数据不完整，请检查必填字段', 'assertive');
        }
      }
    } catch {
      MessageManager.error('提交失败，请重试');
      // 通知屏幕阅读器提交失败
      announceToScreenReader('提交失败，请重试', 'assertive');
    }
  };

  const handleReset = () => {
    form.resetFields();
    setCompletionRate(0);
    setFileList([]);
    setTerminalContractFileList([]);
  };

  return (
    <div>
      {/* 屏幕阅读器专用表单状态通知 */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        id="asset-form-status"
      >
        {mode === 'create' ? '创建资产表单' : '编辑资产表单'}，表单完成度 {completionRate.toFixed(0)}%
      </div>

      <FormCompletionProgress />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        onValuesChange={handleValuesChange}
      >
        <AssetBasicInfoSection />
        <AssetAreaSection />
        <AssetStatusSection />
        <AssetReceptionSection />
        <AssetDetailedSection />
        <FormActions isLoading={isLoading} mode={mode} onCancel={onCancel} onReset={handleReset} />
      </Form>
    </div>
  );
};

/**
 * AssetForm - Main form component for creating/editing assets
 * Refactored to use section components for better maintainability
 */
const AssetForm: React.FC<AssetFormProps> = ({
  initialData,
  onSubmit,
  onCancel,
  isLoading = false,
  mode = 'create',
}) => {
  const [form] = Form.useForm();

  return (
    <AssetFormProvider form={form} mode={mode} isLoading={isLoading}>
      <AssetFormInner
        initialData={initialData}
        onSubmit={onSubmit}
        onCancel={onCancel}
        isLoading={isLoading}
        mode={mode}
      />
    </AssetFormProvider>
  );
};

export default AssetForm;
