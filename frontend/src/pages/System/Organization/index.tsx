import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, Form, Tag } from 'antd';
import type { DataNode } from 'antd/es/tree';
import PageContainer from '@/components/Common/PageContainer';
import { MessageManager } from '@/utils/messageManager';
import { organizationService } from '@/services/organizationService';
import { useArrayListData } from '@/hooks/useArrayListData';
import { useDictionary } from '@/hooks/useDictionary';
import type { Organization, OrganizationHistory } from '@/types/organization';
import { organizationTypeIconMap } from './constants';
import { useOrganizationData } from './hooks/useOrganizationData';
import {
  buildOptionLabelMap,
  buildStatusToneMap,
  convertOrganizationTreeToDataNodes,
  countActiveOrganizationFilters,
  resolveOrganizationTypeIcon,
  resolveOrganizationTypeLabel,
} from './utils';
import type {
  OrganizationFilters,
  OrganizationFormData,
  OrganizationPaginationState,
  OrganizationSelectOption,
  Tone,
} from './types';
import OrganizationStatisticsCards from './components/OrganizationStatisticsCards';
import OrganizationTabsPanel from './components/OrganizationTabsPanel';
import OrganizationFormModal from './components/OrganizationFormModal';
import OrganizationHistoryModal from './components/OrganizationHistoryModal';
import styles from '../OrganizationPage.module.css';

const toneClassMap: Record<Tone, string> = {
  primary: styles.tonePrimary,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  error: styles.toneError,
  neutral: styles.toneNeutral,
};

const OrganizationPage: React.FC = () => {
  const [filters, setFilters] = useState<OrganizationFilters>({ keyword: '' });
  const [paginationState, setPaginationState] = useState<OrganizationPaginationState>({
    current: 1,
    pageSize: 10,
  });
  const [modalVisible, setModalVisible] = useState(false);
  const [historyModalVisible, setHistoryModalVisible] = useState(false);
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  const [selectedOrganization, setSelectedOrganization] = useState<Organization | null>(null);
  const [organizationHistory, setOrganizationHistory] = useState<OrganizationHistory[]>([]);
  const [activeTab, setActiveTab] = useState('list');

  const [form] = Form.useForm<OrganizationFormData>();

  const { options: organizationTypeOptionsRaw, isLoading: isTypeOptionsLoading } =
    useDictionary('organization_type');
  const { options: organizationStatusOptionsRaw, isLoading: isStatusOptionsLoading } =
    useDictionary('organization_status');

  const organizationTypeOptions = useMemo<OrganizationSelectOption[]>(
    () => organizationTypeOptionsRaw,
    [organizationTypeOptionsRaw]
  );
  const organizationStatusOptions = useMemo<OrganizationSelectOption[]>(
    () => organizationStatusOptionsRaw,
    [organizationStatusOptionsRaw]
  );

  const {
    organizations,
    organizationTree,
    statistics,
    loading,
    isOrganizationTreeFetching,
    organizationsError,
    organizationTreeError,
    statisticsError,
    tablePagination,
    refetchOrganizations,
    refetchOrganizationTree,
    refetchStatistics,
  } = useOrganizationData({
    filters,
    pagination: paginationState,
  });

  useEffect(() => {
    if (organizationsError != null) {
      MessageManager.error('加载组织列表失败');
    }
  }, [organizationsError]);

  useEffect(() => {
    if (organizationTreeError != null) {
      MessageManager.error('加载组织树失败');
    }
  }, [organizationTreeError]);

  useEffect(() => {
    if (statisticsError != null) {
      MessageManager.error('加载统计信息失败');
    }
  }, [statisticsError]);

  const typeLabelMap = useMemo(
    () => buildOptionLabelMap(organizationTypeOptions),
    [organizationTypeOptions]
  );
  const statusLabelMap = useMemo(
    () => buildOptionLabelMap(organizationStatusOptions),
    [organizationStatusOptions]
  );
  const statusToneMap = useMemo(
    () => buildStatusToneMap(organizationStatusOptions),
    [organizationStatusOptions]
  );

  const getToneClassName = useCallback((tone: Tone): string => {
    return toneClassMap[tone];
  }, []);

  const getTypeIcon = useCallback((type: string) => {
    return resolveOrganizationTypeIcon(type, organizationTypeIconMap);
  }, []);

  const getTypeLabel = useCallback(
    (type: string) => {
      return resolveOrganizationTypeLabel(type, typeLabelMap);
    },
    [typeLabelMap]
  );

  const getStatusTone = useCallback(
    (status: string): Tone => {
      return statusToneMap.get(status) ?? 'neutral';
    },
    [statusToneMap]
  );

  const getStatusLabel = useCallback(
    (status: string): string => {
      return statusLabelMap.get(status) ?? status;
    },
    [statusLabelMap]
  );

  const getStatusTag = useCallback(
    (status: string, className?: string) => {
      const toneClassName = getToneClassName(getStatusTone(status));
      const extraClassName = className != null ? ` ${className}` : '';
      return (
        <Tag className={`${styles.statusTag} ${toneClassName}${extraClassName}`}>
          {getStatusLabel(status)}
        </Tag>
      );
    },
    [getStatusLabel, getStatusTone, getToneClassName]
  );

  const organizationTreeDataNodes = useMemo<DataNode[]>(() => {
    return convertOrganizationTreeToDataNodes({
      treeNodes: organizationTree,
      getTypeIcon,
      getStatusTag,
      treeNodeLabelClassName: styles.treeNodeLabel,
      treeNodeTitleClassName: styles.treeNodeTitle,
      treeStatusTagClassName: styles.treeStatusTag,
    });
  }, [getStatusTag, getTypeIcon, organizationTree]);

  const activeFilterCount = useMemo(() => {
    return countActiveOrganizationFilters(filters);
  }, [filters]);

  const refreshOrganizations = useCallback(() => {
    void refetchOrganizations();
    void refetchOrganizationTree();
    void refetchStatistics();
  }, [refetchOrganizations, refetchOrganizationTree, refetchStatistics]);

  const handleSearch = useCallback((keyword: string) => {
    setFilters({ keyword });
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

  const handleRefreshTree = useCallback(() => {
    void refetchOrganizationTree();
  }, [refetchOrganizationTree]);

  const handleCreate = useCallback(() => {
    setEditingOrganization(null);
    form.resetFields();
    setModalVisible(true);
  }, [form]);

  const handleEdit = useCallback(
    (organization: Organization) => {
      setEditingOrganization(organization);
      form.setFieldsValue({
        name: organization.name,
        code: organization.code,
        type: organization.type,
        parent_id: organization.parent_id ?? undefined,
        description: organization.description ?? '',
        status: organization.status,
        sort_order: organization.sort_order,
      });
      setModalVisible(true);
    },
    [form]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await organizationService.deleteOrganization(id);
        MessageManager.success('删除成功');
        refreshOrganizations();
      } catch {
        MessageManager.error('删除失败');
      }
    },
    [refreshOrganizations]
  );

  const handleViewHistory = useCallback(async (organization: Organization) => {
    setSelectedOrganization(organization);
    try {
      const history = await organizationService.getOrganizationHistory(organization.id);
      setOrganizationHistory(history);
      setHistoryModalVisible(true);
    } catch {
      MessageManager.error('加载历史记录失败');
    }
  }, []);

  const {
    data: historyPageItems,
    pagination: historyPagination,
    loadList: loadHistoryList,
    updatePagination: updateHistoryPagination,
  } = useArrayListData<OrganizationHistory, Record<string, never>>({
    items: organizationHistory,
    initialFilters: {},
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadHistoryList({ page: 1 });
  }, [loadHistoryList, organizationHistory]);

  const handleSubmit = useCallback(
    async (values: OrganizationFormData) => {
      try {
        if (editingOrganization != null) {
          await organizationService.updateOrganization(editingOrganization.id, values);
          MessageManager.success('更新成功');
        } else {
          await organizationService.createOrganization(values);
          MessageManager.success('创建成功');
        }
        setModalVisible(false);
        refreshOrganizations();
      } catch {
        MessageManager.error(editingOrganization != null ? '更新失败' : '创建失败');
      }
    },
    [editingOrganization, refreshOrganizations]
  );

  return (
    <PageContainer
      className={styles.pageShell}
      title="组织管理"
      subTitle="维护组织结构、层级关系与组织历史记录"
    >
      {statistics != null && <OrganizationStatisticsCards statistics={statistics} />}

      <Card>
        <OrganizationTabsPanel
          activeTab={activeTab}
          onTabChange={setActiveTab}
          listTabProps={{
            filters,
            total: tablePagination.total,
            activeFilterCount,
            loading,
            organizations,
            paginationState: tablePagination,
            getTypeIcon,
            getTypeLabel,
            getStatusTag,
            onSearch: handleSearch,
            onRefresh: refreshOrganizations,
            onCreate: handleCreate,
            onPageChange: handlePageChange,
            onEdit: handleEdit,
            onDelete: handleDelete,
            onViewHistory: handleViewHistory,
          }}
          treeData={organizationTreeDataNodes}
          isTreeLoading={isOrganizationTreeFetching}
          onTreeRefresh={handleRefreshTree}
        />
      </Card>

      <OrganizationFormModal
        open={modalVisible}
        editingOrganization={editingOrganization}
        form={form}
        organizationTree={organizationTreeDataNodes}
        organizationTypeOptions={organizationTypeOptions}
        organizationStatusOptions={organizationStatusOptions}
        isTypeOptionsLoading={isTypeOptionsLoading}
        isStatusOptionsLoading={isStatusOptionsLoading}
        getTypeIcon={getTypeIcon}
        getStatusTag={getStatusTag}
        onCancel={() => setModalVisible(false)}
        onSubmit={handleSubmit}
      />

      <OrganizationHistoryModal
        open={historyModalVisible}
        selectedOrganizationName={selectedOrganization?.name}
        historyItems={historyPageItems}
        paginationState={historyPagination}
        getToneClassName={getToneClassName}
        onClose={() => setHistoryModalVisible(false)}
        onPageChange={updateHistoryPagination}
      />
    </PageContainer>
  );
};

export default OrganizationPage;
