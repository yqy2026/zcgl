/**
 * 租户合同创建/编辑表单组件
 * Refactored to use section components for better maintainability
 */

import React from 'react';
import { Form } from 'antd';

import { RentContractCreate } from '../../types/rentContract';

// Import section components
import {
  RentContractFormProvider,
  RentContractInitialData,
  BasicInfoSection,
  RelationInfoSection,
  TenantInfoSection,
  ContractPeriodSection,
  RentTermsSection,
  OtherInfoSection,
  FormActionsSection,
  RentTermModal,
} from './RentContract';

interface RentContractFormProps {
  initialData?: RentContractInitialData;
  onSubmit: (data: RentContractCreate) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  mode?: 'create' | 'edit';
}

/**
 * Inner component that uses context
 */
const RentContractFormInner: React.FC = () => {
  return (
    <>
      <BasicInfoSection />
      <RelationInfoSection />
      <TenantInfoSection />
      <ContractPeriodSection />
      <RentTermsSection />
      <OtherInfoSection />
      <FormActionsSection />
      <RentTermModal />
    </>
  );
};

/**
 * RentContractForm - Main form component for creating/editing rent contracts
 * Refactored to use section components for better maintainability
 */
const RentContractForm: React.FC<RentContractFormProps> = ({
  initialData,
  onSubmit,
  onCancel,
  loading = false,
  mode = 'create',
}) => {
  const [form] = Form.useForm();
  const [termForm] = Form.useForm();

  return (
    <RentContractFormProvider
      form={form}
      termForm={termForm}
      initialData={initialData}
      onSubmit={onSubmit}
      onCancel={onCancel}
      loading={loading}
      mode={mode}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          contract_status: '有效',
        }}
      >
        <RentContractFormInner />
      </Form>
    </RentContractFormProvider>
  );
};

export default RentContractForm;
