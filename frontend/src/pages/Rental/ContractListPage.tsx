/**
 * 租金合同列表页面
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Modal,
  Tooltip,
  Row,
  Col,
  Statistic,
  Typography,
  type TableProps,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  DollarOutlined,
  SearchOutlined,
  SyncOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import {
  RentContract,
  RentContractQueryParams,
  RentContractPageState,
  RentStatisticsOverview,
  ContractStatus,
  ContractStatusLabels,
  ContractStatusColors,
} from '../../types/rentContract';
import { Asset } from '../../types/asset';
import { Ownership } from '../../types/ownership';
import { rentContractService } from '../../services/rentContractService';
import { assetService } from '../../services/assetService';
import { ownershipService } from '../../services/ownershipService';
import { useFormat } from '../../utils/format';
import RentContractExcelImport from '../../components/Rental/RentContractExcelImport';
import { createLogger } from '../../utils/logger';
import { COLORS } from '@/styles/colorMap';

const pageLogger = createLogger('ContractList');

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;

const ContractListPage: React.FC = () => {
  const [state, setState] = useState<RentContractPageState>({
    loading: false,
    contracts: [],
    pagination: {
      current: 1,
      pageSize: 10,
      total: 0,
    },
    filters: {},
    showModal: false,
    modalMode: 'create',
  });

  const [assets, setAssets] = useState<Asset[]>([]);
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [statistics, setStatistics] = useState<RentStatisticsOverview | null>(null);
  const navigate = useNavigate();

  const format = useFormat();

  // 加载合同列表
  const loadContracts = React.useCallback(
    async (params?: RentContractQueryParams) => {
      setState(prev => ({ ...prev, loading: true }));
      try {
        const response = await rentContractService.getContracts({
          page: state.pagination.current,
          pageSize: state.pagination.pageSize,
          ...state.filters,
          ...params,
        });

        // 确保items是一个数组
        const contracts = Array.isArray(response.items) ? response.items : [];

        setState(prev => ({
          ...prev,
          loading: false,
          contracts: contracts,
          pagination: {
            ...prev.pagination,
            total: response.total ?? 0,
            pages: response.pages ?? 0,
          },
        }));
      } catch (error) {
        pageLogger.error('加载合同列表失败:', error as Error);
        MessageManager.error(
          `加载合同列表失败: ${error instanceof Error ? error.message : '未知错误'}`
        );
        setState(prev => ({ ...prev, loading: false, contracts: [] }));
      }
    },
    [state.pagination.current, state.pagination.pageSize, state.filters]
  );

  // 加载统计数据
  const loadStatistics = React.useCallback(async () => {
    try {
      const stats = await rentContractService.getRentStatistics();
      setStatistics(stats);
    } catch (error) {
      pageLogger.error('加载统计数据失败:', error as Error);
    }
  }, []);

  // 加载资产和权属方数据
  const loadReferenceData = React.useCallback(async () => {
    try {
      const [assetsResponse, ownershipsData] = await Promise.all([
        assetService.getAssets({ pageSize: 100 }),
        ownershipService.getOwnershipOptions(true),
      ]);
      setAssets(assetsResponse.items);
      setOwnerships(ownershipsData);
    } catch {
      MessageManager.error('加载参考数据失败');
    }
  }, []);

  useEffect(() => {
    loadContracts();
    loadStatistics();
    loadReferenceData();
  }, [loadContracts, loadStatistics, loadReferenceData]);

  // 处理分页变化
  const handleTableChange: TableProps<RentContract>['onChange'] = pagination => {
    setState(prev => ({
      ...prev,
      pagination: {
        ...prev.pagination,
        current: pagination.current ?? 1,
        pageSize: pagination.pageSize ?? 10,
      },
    }));
    loadContracts({
      page: pagination.current ?? 1,
      pageSize: pagination.pageSize ?? 10,
    });
  };

  // 处理搜索
  const handleSearch = (values: Record<string, unknown>) => {
    setState(prev => ({
      ...prev,
      filters: values,
      pagination: { ...prev.pagination, current: 1 },
    }));
    loadContracts({ ...values, page: 1 });
  };

  // 重置搜索
  const handleReset = () => {
    setState(prev => ({
      ...prev,
      filters: {},
      pagination: { ...prev.pagination, current: 1 },
    }));
    loadContracts({ page: 1 });
  };

  // 删除合同
  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个合同吗？删除后将无法恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await rentContractService.deleteContract(id);
          MessageManager.success('删除成功');
        } catch {
          MessageManager.error('删除失败');
        }
      },
    });
  };

  // 生成台账
  const handleGenerateLedger = async (contractId: string) => {
    try {
      await rentContractService.generateMonthlyLedger({ contract_id: contractId });
      MessageManager.success('生成台账成功');
    } catch {
      MessageManager.error('生成台账失败');
    }
  };

  // V2: 续签合同
  const handleRenew = (contract: RentContract) => {
    navigate(`/rental/contracts/${contract.id}/renew`);
  };

  // V2: 终止合同
  const handleTerminate = async (contract: RentContract) => {
    Modal.confirm({
      title: '确认终止合同',
      content: `确定要终止合同「${contract.contract_number ?? ''}」吗？`,
      okText: '确认终止',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await rentContractService.terminateContract(
            contract.id,
            new Date().toISOString().split('T')[0]
          );
          MessageManager.success('合同已终止');
          loadContracts();
        } catch {
          MessageManager.error('终止合同失败');
        }
      },
    });
  };

  // 查看合同详情
  const handleViewDetail = (contract: RentContract) => {
    navigate(`/rental/contracts/${contract.id}`);
  };

  // 编辑合同
  const handleEdit = (contract: RentContract) => {
    navigate(`/rental/contracts/${contract.id}/edit`);
  };

  // 创建新合同
  const handleCreate = () => {
    navigate('/rental/contracts/create');
  };

  // 导入成功的回调
  const handleImportSuccess = () => {
    loadContracts(); // 重新加载数据
    loadStatistics(); // 重新加载统计数据
  };

  // 表格列定义
  const columns: ColumnsType<RentContract> = [
    {
      title: '合同编号',
      dataIndex: 'contract_number',
      key: 'contract_number',
      render: (text: string) => (
        <Tooltip title={text}>
          <Button type="link" size="small">
            {text}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: '承租方',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
      render: (text: string) => (
        <Space>
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '物业名称',
      key: 'assets',
      render: (_: unknown, record: RentContract) => {
        // V2: 多资产显示
        const assetList = record.assets ?? [];
        if (assetList.length === 0) return '未关联';
        if (assetList.length === 1) {
          return <Tooltip title={assetList[0].address ?? ''}>{assetList[0].property_name}</Tooltip>;
        }
        return (
          <Tooltip title={assetList.map(a => a.property_name).join(', ')}>
            <Tag>{assetList.length}个资产</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '权属方',
      dataIndex: ['ownership', 'name'],
      key: 'ownership_name',
      render: (text: string | undefined) => text ?? '未知',
    },
    {
      title: '租期',
      key: 'lease_period',
      render: (record: RentContract) => (
        <Space direction="vertical" size="small">
          <div>{dayjs(record.start_date).format('YYYY-MM-DD')}</div>
          <div>至</div>
          <div>{dayjs(record.end_date).format('YYYY-MM-DD')}</div>
        </Space>
      ),
    },
    {
      title: '月租金',
      dataIndex: 'monthly_rent_base',
      key: 'monthly_rent_base',
      render: (amount: number) => format.currency(amount),
      align: 'right' as const,
    },
    {
      title: '合同状态',
      dataIndex: 'contract_status',
      key: 'contract_status',
      render: (status: ContractStatus) => {
        return (
          <Tag color={ContractStatusColors[status] || 'default'}>
            {ContractStatusLabels[status] || status}
          </Tag>
        );
      },
    },
    {
      title: '签订日期',
      dataIndex: 'sign_date',
      key: 'sign_date',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_: unknown, record: RentContract) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button type="text" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title="生成台账">
            <Button
              type="text"
              icon={<FileTextOutlined />}
              onClick={() => handleGenerateLedger(record.id)}
            />
          </Tooltip>
          {record.contract_status === ContractStatus.ACTIVE && (
            <>
              <Tooltip title="续签">
                <Button type="text" icon={<SyncOutlined />} onClick={() => handleRenew(record)} />
              </Tooltip>
              <Tooltip title="终止">
                <Button
                  type="text"
                  danger
                  icon={<StopOutlined />}
                  onClick={() => handleTerminate(record)}
                />
              </Tooltip>
            </>
          )}
          <Tooltip title="删除">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>租金合同管理</Title>
        <p style={{ color: COLORS.textSecondary }}>管理物业租赁合同，支持租金条款设置和台账生成</p>
      </div>

      {/* 统计卡片 */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总合同数"
                value={statistics.total_records}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="应收总额"
                value={statistics.total_due}
                precision={2}
                prefix={<DollarOutlined />}
                suffix="元"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已收总额"
                value={statistics.total_paid}
                precision={2}
                prefix={<DollarOutlined />}
                suffix="元"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="收缴率"
                value={statistics.payment_rate}
                precision={2}
                suffix="%"
                valueStyle={{ color: statistics.payment_rate > 80 ? COLORS.success : COLORS.error }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 搜索区域 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={16}>
          <Col span={6}>
            <Search
              placeholder="搜索合同编号或承租方"
              onSearch={value => handleSearch({ keyword: value })}
              enterButton={<SearchOutlined />}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="选择物业"
              style={{ width: '100%' }}
              allowClear
              onChange={value => handleSearch({ asset_id: value })}
            >
              {assets.map(asset => (
                <Option key={asset.id} value={asset.id}>
                  {asset.property_name}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="选择权属方"
              style={{ width: '100%' }}
              allowClear
              onChange={value => handleSearch({ ownership_id: value })}
            >
              {ownerships.map(ownership => (
                <Option key={ownership.id} value={ownership.id}>
                  {ownership.name}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="合同状态"
              style={{ width: '100%' }}
              allowClear
              onChange={value => handleSearch({ contract_status: value })}
            >
              {Object.values(ContractStatus).map(status => (
                <Option key={status} value={status}>
                  {ContractStatusLabels[status]}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <Button onClick={handleReset}>重置</Button>
          </Col>
          <Col span={2}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建合同
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Excel导入导出 */}
      <RentContractExcelImport onImportSuccess={handleImportSuccess} />

      {/* 合同列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={state.contracts}
          rowKey="id"
          loading={state.loading}
          pagination={{
            current: state.pagination.current,
            pageSize: state.pagination.pageSize,
            total: state.pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
};

export default ContractListPage;
