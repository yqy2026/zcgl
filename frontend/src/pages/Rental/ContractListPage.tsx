/**
 * 租金合同列表页面
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import RentContractExcelImport from '@/components/Rental/RentContractExcelImport';
import { useContractList } from '@/hooks/useContractList';
import ContractStatsCards from '@/components/Rental/ContractList/ContractStatsCards';
import ContractFilterBar from '@/components/Rental/ContractList/ContractFilterBar';
import ContractTable from '@/components/Rental/ContractList/ContractTable';
import { RentContract } from '@/types/rentContract';

const ContractListPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    state,
    assets,
    ownerships,
    statistics,
    handleTableChange,
    handleSearch,
    handleReset,
    handleDelete,
    handleGenerateLedger,
    handleTerminate,
    handleImportSuccess,
  } = useContractList();

  // Navigation handlers
  const handleCreate = () => {
    navigate('/rental/contracts/create');
  };

  const handleViewDetail = (contract: RentContract) => {
    navigate(`/rental/contracts/${contract.id}`);
  };

  const handleEdit = (contract: RentContract) => {
    navigate(`/rental/contracts/${contract.id}/edit`);
  };

  const handleRenew = (contract: RentContract) => {
    navigate(`/rental/contracts/${contract.id}/renew`);
  };

  return (
    <PageContainer title="租金合同管理" subTitle="管理物业租赁合同，支持租金条款设置和台账生成">

      {/* 统计卡片 */}
      <ContractStatsCards statistics={statistics ?? null} />

      {/* 搜索区域 */}
      <ContractFilterBar
        assets={assets}
        ownerships={ownerships}
        onSearch={handleSearch}
        onReset={handleReset}
        onCreate={handleCreate}
      />

      {/* Excel导入导出 */}
      <RentContractExcelImport onImportSuccess={handleImportSuccess} />

      {/* 合同列表 */}
      <ContractTable
        loading={state.loading}
        contracts={state.contracts}
        pagination={state.pagination}
        onTableChange={handleTableChange}
        onView={handleViewDetail}
        onEdit={handleEdit}
        onGenerateLedger={handleGenerateLedger}
        onRenew={handleRenew}
        onTerminate={handleTerminate}
        onDelete={handleDelete}
      />
    </PageContainer>
  );
};

export default ContractListPage;
