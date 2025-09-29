import React, { useState, useEffect, useCallback } from 'react';
import { Card, Tree, Button, Space, message, Spin, Empty } from 'antd';
import {
  ApartmentOutlined,
  ReloadOutlined,
  ExpandOutlined,
  CompressOutlined,
  DownloadOutlined,
  EditOutlined
} from '@ant-design/icons';
import type { DataNode, TreeProps } from 'antd/es/tree';
import { Organization } from '../types/organization';
import { organizationService } from '../services/organizationService';
import styles from './OrganizationChart.module.css';

interface OrganizationChartProps {
  onEdit?: (organization: Organization) => void;
  onRefresh?: () => void;
  height?: number;
}

interface DraggableTreeNode extends DataNode {
  organization: Organization;
  children?: DraggableTreeNode[];
}

const OrganizationChart: React.FC<OrganizationChartProps> = ({
  onEdit,
  onRefresh,
  height = 600
}) => {
  const [treeData, setTreeData] = useState<DraggableTreeNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([]);
  const [autoExpandParent, setAutoExpandParent] = useState(true);
  const [allExpanded, setAllExpanded] = useState(false);

  // 加载组织树数据
  const loadOrganizationTree = useCallback(async () => {
    setLoading(true);
    try {
      const organizations = await organizationService.getOrganizations();
      const treeNodes = buildTreeData(organizations);
      setTreeData(treeNodes);
      
      // 自动展开第一层
      const firstLevelKeys = treeNodes.map(node => node.key);
      setExpandedKeys(firstLevelKeys);
    } catch (error) {
      message.error('加载组织架构失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOrganizationTree();
  }, [loadOrganizationTree]);

  // 构建树形数据结构
  const buildTreeData = (organizations: Organization[]): DraggableTreeNode[] => {
    const organizationMap = new Map<string, Organization>();
    const rootNodes: DraggableTreeNode[] = [];

    // 创建组织映射
    organizations.forEach(org => {
      organizationMap.set(org.id, org);
    });

    // 构建树形结构
    const buildNode = (org: Organization): DraggableTreeNode => {
      const children = organizations
        .filter(child => child.parent_id === org.id)
        .sort((a, b) => a.sort_order - b.sort_order)
        .map(child => buildNode(child));

      return {
        key: org.id,
        title: renderNodeTitle(org),
        organization: org,
        children: children.length > 0 ? children : undefined,
        icon: getOrganizationIcon(org.type),
        className: styles[`org${org.status.charAt(0).toUpperCase() + org.status.slice(1)}`] || ''
      };
    };

    // 找到根节点
    organizations
      .filter(org => !org.parent_id)
      .sort((a, b) => a.sort_order - b.sort_order)
      .forEach(org => {
        rootNodes.push(buildNode(org));
      });

    return rootNodes;
  };

  // 渲染节点标题
  const renderNodeTitle = (org: Organization) => (
    <div className={styles.orgNodeContent}>
      <div className={styles.orgNodeMain}>
        <span className={styles.orgName}>{org.name}</span>
        <span className={styles.orgCode}>({org.code})</span>
      </div>
      <div className={styles.orgNodeInfo}>
        {org.leader_name && (
          <span className={styles.orgLeader}>负责人: {org.leader_name}</span>
        )}
        <span className={`${styles.orgStatus} ${styles[`status${org.status.charAt(0).toUpperCase() + org.status.slice(1)}`] || ''}`}>
          {getStatusLabel(org.status)}
        </span>
      </div>
      <div className={styles.orgNodeActions}>
        <Button
          type="text"
          size="small"
          icon={<EditOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            onEdit?.(org);
          }}
        >
          编辑
        </Button>
      </div>
    </div>
  );

  // 获取组织图标
  const getOrganizationIcon = (type: string) => {
    const iconMap: { [key: string]: React.ReactNode } = {
      company: <ApartmentOutlined style={{ color: '#1890ff' }} />,
      department: <ApartmentOutlined style={{ color: '#52c41a' }} />,
      group: <ApartmentOutlined style={{ color: '#722ed1' }} />,
      division: <ApartmentOutlined style={{ color: '#fa8c16' }} />,
      team: <ApartmentOutlined style={{ color: '#13c2c2' }} />,
      branch: <ApartmentOutlined style={{ color: '#eb2f96' }} />,
      office: <ApartmentOutlined style={{ color: '#faad14' }} />
    };
    return iconMap[type] || <ApartmentOutlined />;
  };

  // 获取状态标签
  const getStatusLabel = (status: string) => {
    const statusMap: { [key: string]: string } = {
      active: '活跃',
      inactive: '停用',
      suspended: '暂停'
    };
    return statusMap[status] || status;
  };

  // 处理节点拖拽
  const handleDrop: TreeProps['onDrop'] = async (info) => {
    const dropKey = info.node.key;
    const dragKey = info.dragNode.key;
    const dropPos = info.node.pos.split('-');
    const dropPosition = info.dropPosition - Number(dropPos[dropPos.length - 1]);

    // 防止拖拽到自己或子节点
    if (dragKey === dropKey || isDescendant(dragKey as string, dropKey as string)) {
      message.warning('不能将组织移动到自己或子组织下');
      return;
    }

    try {
      const dragOrg = findOrganizationById(dragKey as string);
      const dropOrg = findOrganizationById(dropKey as string);

      if (!dragOrg || !dropOrg) {
        message.error('找不到相关组织信息');
        return;
      }

      let newParentId: string | undefined;
      let newSortOrder = 0;

      if (dropPosition === -1) {
        // 拖拽到节点上方，与目标节点同级
        newParentId = dropOrg.parent_id;
        newSortOrder = dropOrg.sort_order;
      } else if (dropPosition === 1) {
        // 拖拽到节点下方，与目标节点同级
        newParentId = dropOrg.parent_id;
        newSortOrder = dropOrg.sort_order + 1;
      } else {
        // 拖拽到节点内部，成为子节点
        newParentId = dropOrg.id;
        newSortOrder = 0;
      }

      // 调用API移动组织
      await organizationService.moveOrganization(dragKey as string, {
        target_parent_id: newParentId,
        sort_order: newSortOrder,
        updated_by: 'current_user' // 这里应该是当前用户ID
      });

      message.success('组织移动成功');
      
      // 重新加载数据
      await loadOrganizationTree();
      onRefresh?.();

    } catch (error) {
      message.error('组织移动失败');
    }
  };

  // 检查是否为子孙节点
  const isDescendant = (ancestorId: string, nodeId: string): boolean => {
    const findInTree = (nodes: DraggableTreeNode[], targetId: string, ancestorId: string): boolean => {
      for (const node of nodes) {
        if (node.key === ancestorId) {
          return findDescendant(node, targetId);
        }
        if (node.children && findInTree(node.children, targetId, ancestorId)) {
          return true;
        }
      }
      return false;
    };

    const findDescendant = (node: DraggableTreeNode, targetId: string): boolean => {
      if (node.children) {
        for (const child of node.children) {
          if (child.key === targetId || findDescendant(child, targetId)) {
            return true;
          }
        }
      }
      return false;
    };

    return findInTree(treeData, nodeId, ancestorId);
  };

  // 根据ID查找组织
  const findOrganizationById = (id: string): Organization | null => {
    const findInTree = (nodes: DraggableTreeNode[]): Organization | null => {
      for (const node of nodes) {
        if (node.key === id) {
          return node.organization;
        }
        if (node.children) {
          const found = findInTree(node.children);
          if (found) return found;
        }
      }
      return null;
    };

    return findInTree(treeData);
  };

  // 展开/收起所有节点
  const toggleExpandAll = () => {
    if (allExpanded) {
      setExpandedKeys([]);
    } else {
      const allKeys = getAllKeys(treeData);
      setExpandedKeys(allKeys);
    }
    setAllExpanded(!allExpanded);
    setAutoExpandParent(false);
  };

  // 获取所有节点的key
  const getAllKeys = (nodes: DraggableTreeNode[]): string[] => {
    const keys: string[] = [];
    const traverse = (nodeList: DraggableTreeNode[]) => {
      nodeList.forEach(node => {
        keys.push(node.key as string);
        if (node.children) {
          traverse(node.children);
        }
      });
    };
    traverse(nodes);
    return keys;
  };

  // 导出组织架构图
  const handleExport = async () => {
    try {
      const blob = await organizationService.exportOrganizations('excel');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `组织架构_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    }
  };

  // 处理展开/收起
  const handleExpand = (expandedKeysValue: React.Key[]) => {
    setExpandedKeys(expandedKeysValue);
    setAutoExpandParent(false);
  };

  // 处理选择
  const handleSelect = (selectedKeysValue: React.Key[]) => {
    setSelectedKeys(selectedKeysValue);
  };

  return (
    <Card
      title={
        <Space>
          <ApartmentOutlined />
          组织架构图
        </Space>
      }
      extra={
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadOrganizationTree}
            loading={loading}
          >
            刷新
          </Button>
          <Button
            icon={allExpanded ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={toggleExpandAll}
          >
            {allExpanded ? '收起全部' : '展开全部'}
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
          >
            导出
          </Button>
        </Space>
      }
      style={{ height }}
    >
      <div className={styles.organizationChartContainer} style={{ height: height - 100, overflow: 'auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            <Spin size="large" />
          </div>
        ) : treeData.length === 0 ? (
          <Empty
            description="暂无组织架构数据"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Tree
            className={styles.organizationTree}
            treeData={treeData}
            draggable
            blockNode
            onDrop={handleDrop}
            expandedKeys={expandedKeys}
            selectedKeys={selectedKeys}
            onExpand={handleExpand}
            onSelect={handleSelect}
            autoExpandParent={autoExpandParent}
            showIcon
            showLine={{ showLeafIcon: false }}
          />
        )}
      </div>

    </Card>
  );
};

export default OrganizationChart;