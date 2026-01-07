import React, { createContext, useContext, useState, useEffect } from 'react';
import type { FormInstance } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { message } from 'antd';
import { Asset } from '../../../types/asset';
import { Ownership } from '../../../types/ownership';
import { RentContractCreate, RentTermCreate } from '../../../types/rentContract';
import { assetService } from '../../../services/assetService';
import { ownershipService } from '../../../services/ownershipService';
import { createLogger } from '../../../utils/logger';

const componentLogger = createLogger('RentContractFormContext');

// Rent term data interface (for editing)
export interface RentTermData {
  start_date: string;
  end_date: string;
  monthly_rent: number;
  rent_description?: string;
  management_fee?: number;
  other_fees?: number;
}

// Rent contract form initial data interface
export interface RentContractInitialData {
  contract_number?: string;
  asset_id: string;
  ownership_id: string;
  tenant_name: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date?: string;
  start_date: string;
  end_date: string;
  total_deposit?: number;
  monthly_rent_base?: number;
  contract_status?: string;
  payment_terms?: string;
  contract_notes?: string;
  rent_terms?: RentTermData[];
}

export interface RentTermFormData {
  key: string;
  start_date: Dayjs;
  end_date: Dayjs;
  monthly_rent: number;
  rent_description?: string;
  management_fee?: number;
  other_fees?: number;
}

export interface RentContractFormContextValue {
  form: FormInstance;
  termForm: FormInstance;
  mode: 'create' | 'edit';
  loading: boolean;
  // Data
  assets: Asset[];
  ownerships: Ownership[];
  rentTerms: RentTermFormData[];
  setRentTerms: React.Dispatch<React.SetStateAction<RentTermFormData[]>>;
  loadingAssets: boolean;
  loadingOwnerships: boolean;
  // Modal state
  showRentTermModal: boolean;
  setShowRentTermModal: (show: boolean) => void;
  editingTerm: RentTermFormData | null;
  setEditingTerm: (term: RentTermFormData | null) => void;
  // Handlers
  handleSubmit: () => Promise<void>;
  handleAddRentTerm: () => void;
  handleEditRentTerm: (term: RentTermFormData) => void;
  handleDeleteRentTerm: (key: string) => void;
  handleSaveRentTerm: () => Promise<void>;
  onCancel: () => void;
}

const RentContractFormContext = createContext<RentContractFormContextValue | null>(null);

export function useRentContractFormContext(): RentContractFormContextValue {
  const context = useContext(RentContractFormContext);
  if (!context) {
    throw new Error('useRentContractFormContext must be used within RentContractFormProvider');
  }
  return context;
}

interface RentContractFormProviderProps {
  form: FormInstance;
  termForm: FormInstance;
  initialData?: RentContractInitialData;
  onSubmit: (data: RentContractCreate) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  mode?: 'create' | 'edit';
  children: React.ReactNode;
}

export const RentContractFormProvider: React.FC<RentContractFormProviderProps> = ({
  form,
  termForm,
  initialData,
  onSubmit,
  onCancel,
  loading = false,
  mode = 'create',
  children,
}) => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [rentTerms, setRentTerms] = useState<RentTermFormData[]>([]);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [loadingOwnerships, setLoadingOwnerships] = useState(false);
  const [showRentTermModal, setShowRentTermModal] = useState(false);
  const [editingTerm, setEditingTerm] = useState<RentTermFormData | null>(null);

  // Load assets and ownerships
  useEffect(() => {
    const loadAssets = async () => {
      setLoadingAssets(true);
      try {
        const response = await assetService.getAssets({ limit: 100 });
        setAssets(response.items);
      } catch (error) {
        componentLogger.error('加载资产列表失败:', error as Error);
        message.error('加载资产列表失败');
      } finally {
        setLoadingAssets(false);
      }
    };

    const loadOwnerships = async () => {
      setLoadingOwnerships(true);
      try {
        const response = await ownershipService.getOwnerships({ size: 100 });
        setOwnerships(response.items);
      } catch (error) {
        componentLogger.error('加载权属方列表失败:', error as Error);
        message.error('加载权属方列表失败');
      } finally {
        setLoadingOwnerships(false);
      }
    };

    void loadAssets();
    void loadOwnerships();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Initialize form data
  useEffect(() => {
    if (initialData != null && mode === 'edit') {
      const formData = {
        ...initialData,
        sign_date: initialData.sign_date != null ? dayjs(initialData.sign_date) : undefined,
        start_date: initialData.start_date != null ? dayjs(initialData.start_date) : undefined,
        end_date: initialData.end_date != null ? dayjs(initialData.end_date) : undefined,
      };
      form.setFieldsValue(formData);

      if (initialData.rent_terms) {
        const terms = initialData.rent_terms.map((term: RentTermData, index: number) => ({
          key: `term-${index}`,
          start_date: dayjs(term.start_date),
          end_date: dayjs(term.end_date),
          monthly_rent: term.monthly_rent,
          rent_description: term.rent_description,
          management_fee: term.management_fee ?? 0,
          other_fees: term.other_fees ?? 0,
        }));
        setRentTerms(terms);
      }
    }
  }, [initialData, mode, form]);

  const handleSubmit = async () => {
    try {
      const values = (await form.validateFields()) as Record<string, unknown>;

      if (rentTerms.length === 0) {
        message.error('请至少添加一个租金条款');
        return;
      }

      const rent_terms: RentTermCreate[] = rentTerms.map(term => ({
        start_date: term.start_date.format('YYYY-MM-DD'),
        end_date: term.end_date.format('YYYY-MM-DD'),
        monthly_rent: term.monthly_rent,
        rent_description: term.rent_description,
        management_fee: term.management_fee ?? 0,
        other_fees: term.other_fees ?? 0,
        total_monthly_amount:
          term.monthly_rent + (term.management_fee ?? 0) + (term.other_fees ?? 0),
      }));

      // Type-safe form field access
      const valuesRecord = values;
      const contract_number = valuesRecord.contract_number as string | undefined;
      const asset_id = valuesRecord.asset_id as string | undefined;
      const ownership_id = valuesRecord.ownership_id as string | undefined;
      const tenant_name = valuesRecord.tenant_name as string | undefined;
      const tenant_contact = valuesRecord.tenant_contact as string | undefined;
      const tenant_phone = valuesRecord.tenant_phone as string | undefined;
      const tenant_address = valuesRecord.tenant_address as string | undefined;
      const sign_date = valuesRecord.sign_date as Dayjs | undefined;
      const start_date = valuesRecord.start_date as Dayjs | undefined;
      const end_date = valuesRecord.end_date as Dayjs | undefined;
      const total_deposit = valuesRecord.total_deposit as number | undefined;
      const monthly_rent_base = valuesRecord.monthly_rent_base as number | undefined;
      const contract_status = valuesRecord.contract_status as string | undefined;
      const payment_terms = valuesRecord.payment_terms as string | undefined;
      const contract_notes = valuesRecord.contract_notes as string | undefined;

      const contractData: RentContractCreate = {
        contract_number: contract_number ?? undefined,
        asset_id: asset_id ?? '',
        ownership_id: ownership_id ?? '',
        tenant_name: tenant_name ?? '',
        tenant_contact: tenant_contact ?? undefined,
        tenant_phone: tenant_phone ?? undefined,
        tenant_address: tenant_address ?? undefined,
        sign_date:
          sign_date !== null && sign_date !== undefined ? sign_date.format('YYYY-MM-DD') : '',
        start_date:
          start_date !== null && start_date !== undefined ? start_date.format('YYYY-MM-DD') : '',
        end_date: end_date !== null && end_date !== undefined ? end_date.format('YYYY-MM-DD') : '',
        total_deposit: total_deposit ?? 0,
        monthly_rent_base: monthly_rent_base ?? 0,
        contract_status:
          contract_status !== null && contract_status !== undefined && contract_status !== ''
            ? contract_status
            : '有效',
        payment_terms: payment_terms ?? undefined,
        contract_notes: contract_notes ?? undefined,
        rent_terms,
      };

      await onSubmit(contractData);
    } catch (error) {
      componentLogger.error('表单验证失败:', error as Error);
    }
  };

  const handleAddRentTerm = () => {
    setEditingTerm(null);
    termForm.resetFields();
    setShowRentTermModal(true);
  };

  const handleEditRentTerm = (term: RentTermFormData) => {
    setEditingTerm(term);
    termForm.setFieldsValue(term);
    setShowRentTermModal(true);
  };

  const handleDeleteRentTerm = (key: string) => {
    setRentTerms(prev => prev.filter(term => term.key !== key));
  };

  const handleSaveRentTerm = async () => {
    try {
      const values = (await termForm.validateFields()) as Record<string, unknown>;

      // Type-safe form field access
      const valuesRecord = values;
      const start_date = valuesRecord.start_date as Dayjs | undefined;
      const end_date = valuesRecord.end_date as Dayjs | undefined;
      const monthly_rent = valuesRecord.monthly_rent as number | undefined;
      const rent_description = valuesRecord.rent_description as string | undefined;
      const management_fee = valuesRecord.management_fee as number | undefined;
      const other_fees = valuesRecord.other_fees as number | undefined;

      const termData: RentTermFormData = {
        key: editingTerm ? editingTerm.key : `term-${Date.now()}`,
        start_date: start_date ?? null,
        end_date: end_date ?? null,
        monthly_rent: monthly_rent ?? 0,
        rent_description: rent_description ?? undefined,
        management_fee: management_fee ?? 0,
        other_fees: other_fees ?? 0,
      };

      if (editingTerm) {
        setRentTerms(prev => prev.map(term => (term.key === editingTerm.key ? termData : term)));
      } else {
        setRentTerms(prev => [...prev, termData]);
      }

      setShowRentTermModal(false);
      termForm.resetFields();
    } catch (error) {
      componentLogger.error('租金条款验证失败:', error as Error);
    }
  };

  const value: RentContractFormContextValue = {
    form,
    termForm,
    mode,
    loading,
    assets,
    ownerships,
    rentTerms,
    setRentTerms,
    loadingAssets,
    loadingOwnerships,
    showRentTermModal,
    setShowRentTermModal,
    editingTerm,
    setEditingTerm,
    handleSubmit,
    handleAddRentTerm,
    handleEditRentTerm,
    handleDeleteRentTerm,
    handleSaveRentTerm,
    onCancel,
  };

  return (
    <RentContractFormContext.Provider value={value}>{children}</RentContractFormContext.Provider>
  );
};

export default RentContractFormContext;
