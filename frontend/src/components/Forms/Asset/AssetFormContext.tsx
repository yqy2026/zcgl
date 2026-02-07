import React, { createContext, useContext, useState } from 'react';
import type { FormInstance } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';

export interface AssetFormContextValue {
  form: FormInstance;
  mode: 'create' | 'edit';
  isLoading: boolean;
  showAdvanced: boolean;
  setShowAdvanced: (show: boolean) => void;
  completionRate: number;
  setCompletionRate: (rate: number) => void;
  fileList: UploadFile[];
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  terminalContractFileList: UploadFile[];
  setTerminalContractFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
}

const AssetFormContext = createContext<AssetFormContextValue | null>(null);

export function useAssetFormContext(): AssetFormContextValue {
  const context = useContext(AssetFormContext);
  if (context == null) {
    throw new Error('useAssetFormContext must be used within AssetFormProvider');
  }
  return context;
}

interface AssetFormProviderProps {
  form: FormInstance;
  mode: 'create' | 'edit';
  isLoading: boolean;
  children: React.ReactNode;
}

export const AssetFormProvider: React.FC<AssetFormProviderProps> = ({
  form,
  mode,
  isLoading,
  children,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [completionRate, setCompletionRate] = useState(0);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [terminalContractFileList, setTerminalContractFileList] = useState<UploadFile[]>([]);

  const value: AssetFormContextValue = {
    form,
    mode,
    isLoading,
    showAdvanced,
    setShowAdvanced,
    completionRate,
    setCompletionRate,
    fileList,
    setFileList,
    terminalContractFileList,
    setTerminalContractFileList,
  };

  return <AssetFormContext.Provider value={value}>{children}</AssetFormContext.Provider>;
};

export default AssetFormContext;
