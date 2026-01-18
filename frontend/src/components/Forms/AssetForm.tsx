import React, { useEffect } from 'react';
import { Form, Button, Space, Card, Row, Col, Progress, Typography } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Asset, AssetCreateRequest } from '../../types/asset';
import type { UploadFile } from 'antd/es/upload/interface';
import { useDictionaries } from '../../hooks/useDictionary';
import { COLORS } from '@/styles/colorMap';

// Section components
import {
  AssetFormProvider,
  useAssetFormContext,
  AssetBasicInfoSection,
  AssetAreaSection,
  AssetStatusSection,
  AssetReceptionSection,
  AssetAdvancedSection,
} from './Asset';

const { Text } = Typography;

interface AssetFormProps {
  initialData?: Partial<Asset>;
  onSubmit?: (data: AssetCreateRequest) => Promise<void>;
  onCancel?: () => void;
  loading?: boolean;
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
  loading: boolean;
  mode: 'create' | 'edit';
  onCancel?: () => void;
  onReset: () => void;
}

const FormActions: React.FC<FormActionsProps> = ({ loading, mode, onCancel, onReset }) => {
  return (
    <Card>
      <Row justify="end">
        <Space>
          <Button icon={<ReloadOutlined />} onClick={onReset}>
            重置
          </Button>
          {onCancel && <Button onClick={onCancel}>取消</Button>}
          <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
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
  loading: boolean;
  mode: 'create' | 'edit';
}

const AssetFormInner: React.FC<AssetFormInnerProps> = ({
  initialData,
  onSubmit,
  onCancel,
  loading,
  mode,
}) => {
  const {
    form,
    setCompletionRate,
    fileList,
    setFileList,
    terminalContractFileList,
    setTerminalContractFileList,
    loadRentContracts,
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

  // Load rent contracts when asset ID changes
  useEffect(() => {
    const assetId = String(initialData?.id ?? form.getFieldValue('id'));
    if (assetId !== undefined && assetId !== null && assetId !== 'undefined') {
      loadRentContracts(assetId);
    }
  }, [initialData?.id, form, loadRentContracts]);

  // Handle form values change for completion rate calculation
  const handleValuesChange = (
    _changedValues: Record<string, unknown>,
    allValues: Record<string, unknown>
  ) => {
    const requiredFields = [
      'property_name',
      'ownership_entity',
      'address',
      'ownership_status',
      'property_nature',
      'usage_status',
    ];

    const filledFields = requiredFields.filter(field => allValues[field] != null);
    const rate = (filledFields.length / requiredFields.length) * 100;
    setCompletionRate(rate);

    // Auto-calculate occupancy
    const rentableArea = Number(allValues.rentable_area) ?? 0;
    const rentedArea = Number(allValues.rented_area) ?? 0;

    if (rentableArea > 0) {
      const occupancyRate = ((rentedArea / rentableArea) * 100).toFixed(2);
      const unrentedArea = rentableArea - rentedArea;

      form.setFieldsValue({
        occupancy_rate: parseFloat(occupancyRate),
        unrented_area: unrentedArea,
      });
    }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const formatDate = (val: unknown): string | undefined => {
        if (val == null) return undefined;
        if (dayjs.isDayjs(val)) return (val as dayjs.Dayjs).format('YYYY-MM-DD');
        const parsed = dayjs(String(val));
        return parsed.isValid() ? parsed.format('YYYY-MM-DD') : undefined;
      };

      const submitData = {
        ...values,
        contract_start_date: formatDate(values.contract_start_date),
        contract_end_date: formatDate(values.contract_end_date),
        operation_agreement_start_date: formatDate(values.operation_agreement_start_date),
        operation_agreement_end_date: formatDate(values.operation_agreement_end_date),
        operation_agreement_attachments: fileList.map(file => file.name).join(','),
        terminal_contract_files: terminalContractFileList.map(file => file.name).join(','),
      };

      if (onSubmit !== undefined && onSubmit !== null) {
        await onSubmit(submitData as unknown as AssetCreateRequest);
      }
    } catch {
      MessageManager.error('提交失败，请重试');
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
        <AssetAdvancedSection />
        <FormActions loading={loading} mode={mode} onCancel={onCancel} onReset={handleReset} />
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
  loading = false,
  mode = 'create',
}) => {
  const [form] = Form.useForm();

  return (
    <AssetFormProvider form={form} mode={mode} loading={loading}>
      <AssetFormInner
        initialData={initialData}
        onSubmit={onSubmit}
        onCancel={onCancel}
        loading={loading}
        mode={mode}
      />
    </AssetFormProvider>
  );
};

export default AssetForm;
