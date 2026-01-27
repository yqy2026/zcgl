/**
 * 租金合同列表页面
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Typography } from 'antd';
import { COLORS } from '@/styles/colorMap';
import RentContractExcelImport from '../../components/Rental/RentContractExcelImport';
import { useContractList } from '../../hooks/useContractList';
import ContractStatsCards from '../../components/Rental/ContractList/ContractStatsCards';
import ContractFilterBar from '../../components/Rental/ContractList/ContractFilterBar';
import ContractTable from '../../components/Rental/ContractList/ContractTable';
import { RentContract } from '../../types/rentContract';

const { Title } = Typography;

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
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>租金合同管理</Title>
        <p style={{ color: COLORS.textSecondary }}>管理物业租赁合同，支持租金条款设置和台账生成</p>
      </div>

      {/* 统计卡片 */}
      <ContractStatsCards statistics={statistics} />

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
    </div>
  );
};

export default ContractListPage;
