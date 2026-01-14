import React, { createContext, useContext, useState, useEffect } from 'react';
import type { FormInstance } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { MessageManager } from '@/utils/messageManager';
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
    asset_ids: string[]; // V2
    ownership_id: string;
    // V2: Contract Type & Upstream
    contract_type?: string;
    upstream_contract_id?: string;
    service_fee_rate?: number;
    // Tenant Info
    tenant_name: string;
    tenant_contact?: string;
    tenant_phone?: string;
    tenant_address?: string;
    tenant_usage?: string; // V2
    // Dates
    sign_date?: string;
    start_date: string;
    end_date: string;
    // Financials
    total_deposit?: number;
    monthly_rent_base?: number;
    payment_cycle?: string; // V2
    payment_terms?: string;
    // Status & Notes
    contract_status?: string;
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
                MessageManager.error('加载资产列表失败');
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
                MessageManager.error('加载权属方列表失败');
            } finally {
                setLoadingOwnerships(false);
            }
        };

        loadAssets();
        loadOwnerships();
    }, []);

    // Initialize form data
    useEffect(() => {
        if (initialData !== undefined && initialData !== null &&  mode === 'edit') {
            const formData = {
                ...initialData,
                sign_date: initialData.sign_date != null ? dayjs(initialData.sign_date) : undefined,
                start_date: initialData.start_date != null ? dayjs(initialData.start_date) : undefined,
                end_date: initialData.end_date != null ? dayjs(initialData.end_date) : undefined,
            };
            form.setFieldsValue(formData);

            if (initialData.rent_terms != null) {
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
            const values = await form.validateFields();

            if (rentTerms.length === 0) {
                MessageManager.error('请至少添加一个租金条款');
                return;
            }

            const rent_terms: RentTermCreate[] = rentTerms.map(term => ({
                start_date: term.start_date.format('YYYY-MM-DD'),
                end_date: term.end_date.format('YYYY-MM-DD'),
                monthly_rent: term.monthly_rent,
                rent_description: term.rent_description,
                management_fee: term.management_fee ?? 0,
                other_fees: term.other_fees ?? 0,
                total_monthly_amount: term.monthly_rent + (term.management_fee ?? 0) + (term.other_fees ?? 0),
            }));

            const contractData: RentContractCreate = {
                contract_number: values.contract_number as string,
                asset_ids: values.asset_ids as string[], // V2
                ownership_id: values.ownership_id as string,
                contract_type: values.contract_type as string | undefined, // V2
                upstream_contract_id: values.upstream_contract_id as string | undefined, // V2
                service_fee_rate: values.service_fee_rate as number | undefined, // V2
                tenant_name: values.tenant_name as string,
                tenant_usage: values.tenant_usage as string | undefined, // V2
                tenant_contact: values.tenant_contact as string | undefined,
                tenant_phone: values.tenant_phone as string | undefined,
                tenant_address: values.tenant_address as string | undefined,
                sign_date: values.sign_date.format('YYYY-MM-DD'),
                start_date: values.start_date.format('YYYY-MM-DD'),
                end_date: values.end_date.format('YYYY-MM-DD'),
                total_deposit: values.total_deposit ?? 0,
                monthly_rent_base: values.monthly_rent_base as number,
                contract_status: values.contract_status ?? '有效',
                payment_cycle: values.payment_cycle as string | undefined, // V2
                payment_terms: values.payment_terms as string | undefined,
                contract_notes: values.contract_notes as string | undefined,
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
            const values = await termForm.validateFields();
            const termData: RentTermFormData = {
                key: editingTerm ? editingTerm.key : `term-${Date.now()}`,
                start_date: values.start_date,
                end_date: values.end_date,
                monthly_rent: values.monthly_rent,
                rent_description: values.rent_description,
                management_fee: values.management_fee ?? 0,
                other_fees: values.other_fees ?? 0,
            };

            if (editingTerm !== undefined && editingTerm !== null) {
                setRentTerms(prev => prev.map(term =>
                    term.key === editingTerm.key ? termData : term
                ));
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
        <RentContractFormContext.Provider value={value}>
            {children}
        </RentContractFormContext.Provider>
    );
};

export default RentContractFormContext;
