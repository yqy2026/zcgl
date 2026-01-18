import React, { createContext, useContext, useState, useCallback } from 'react';
import type { FormInstance } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import dayjs from 'dayjs';
import type { RentContract } from '../../../types/rentContract';
import { rentContractService } from '../../../services/rentContractService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '../../../utils/logger';

const componentLogger = createLogger('AssetFormContext');

export interface AssetFormContextValue {
  form: FormInstance;
  mode: 'create' | 'edit';
  loading: boolean;
  showAdvanced: boolean;
  setShowAdvanced: (show: boolean) => void;
  completionRate: number;
  setCompletionRate: (rate: number) => void;
  // File uploads
  fileList: UploadFile[];
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  terminalContractFileList: UploadFile[];
  setTerminalContractFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  // Rent contracts
  rentContracts: RentContract[];
  loadingContracts: boolean;
  loadRentContracts: (assetId?: string) => Promise<void>;
  handleContractChange: (contractId: string) => void;
}

const AssetFormContext = createContext<AssetFormContextValue | null>(null);

export function useAssetFormContext(): AssetFormContextValue {
  const context = useContext(AssetFormContext);
  if (!context) {
    throw new Error('useAssetFormContext must be used within AssetFormProvider');
  }
  return context;
}

interface AssetFormProviderProps {
  form: FormInstance;
  mode: 'create' | 'edit';
  loading: boolean;
  children: React.ReactNode;
}

export const AssetFormProvider: React.FC<AssetFormProviderProps> = ({
  form,
  mode,
  loading,
  children,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [completionRate, setCompletionRate] = useState(0);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [terminalContractFileList, setTerminalContractFileList] = useState<UploadFile[]>([]);
  const [rentContracts, setRentContracts] = useState<RentContract[]>([]);
  const [loadingContracts, setLoadingContracts] = useState(false);

  const loadRentContracts = useCallback(async (assetId?: string) => {
    if (assetId == null) {
      setRentContracts([]);
      return;
    }

    setLoadingContracts(true);
    try {
      const response = await rentContractService.getAssetContracts(assetId);
      setRentContracts(response);
    } catch (error) {
      MessageManager.error('加载租赁合同数据失败');
      componentLogger.error('加载租赁合同数据失败:', error as Error);
    } finally {
      setLoadingContracts(false);
    }
  }, []);

  const handleContractChange = useCallback(
    (contractId: string) => {
      const selectedContract = rentContracts.find(contract => contract.id === contractId);

      if (selectedContract !== undefined && selectedContract !== null) {
        // Auto-fill tenant and contract info
        form.setFieldsValue({
          tenant_name: selectedContract.tenant_name,
          tenant_contact: selectedContract.tenant_contact,
          tenant_type: selectedContract.tenant_id != null ? 'enterprise' : 'individual',
          lease_contract_number: selectedContract.contract_number,
          contract_start_date: selectedContract.start_date
            ? dayjs(selectedContract.start_date)
            : undefined,
          contract_end_date: selectedContract.end_date
            ? dayjs(selectedContract.end_date)
            : undefined,
          monthly_rent: selectedContract.monthly_rent_base,
          deposit: selectedContract.total_deposit,
        });
      } else {
        // Clear related fields
        form.setFieldsValue({
          tenant_name: undefined,
          tenant_contact: undefined,
          tenant_type: undefined,
          lease_contract_number: undefined,
          contract_start_date: undefined,
          contract_end_date: undefined,
          monthly_rent: undefined,
          deposit: undefined,
        });
      }
    },
    [form, rentContracts]
  );

  const value: AssetFormContextValue = {
    form,
    mode,
    loading,
    showAdvanced,
    setShowAdvanced,
    completionRate,
    setCompletionRate,
    fileList,
    setFileList,
    terminalContractFileList,
    setTerminalContractFileList,
    rentContracts,
    loadingContracts,
    loadRentContracts,
    handleContractChange,
  };

  return <AssetFormContext.Provider value={value}>{children}</AssetFormContext.Provider>;
};

export default AssetFormContext;
