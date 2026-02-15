import React from 'react';
import { Divider, Modal, Transfer, Tree, Typography } from 'antd';
import type { DataNode } from 'antd/es/tree';
import type { TransferItem } from 'antd/es/transfer';
import styles from '../../RoleManagementPage.module.css';

const { Text } = Typography;

interface RolePermissionModalProps {
  open: boolean;
  roleName: string | undefined;
  transferData: TransferItem[];
  targetPermissions: string[];
  permissionTreeData: DataNode[];
  onTargetPermissionsChange: (keys: string[]) => void;
  onCancel: () => void;
  onSave: () => void | Promise<void>;
}

const RolePermissionModal: React.FC<RolePermissionModalProps> = ({
  open,
  roleName,
  transferData,
  targetPermissions,
  permissionTreeData,
  onTargetPermissionsChange,
  onCancel,
  onSave,
}) => {
  return (
    <Modal
      title={`权限配置 - ${roleName}`}
      open={open}
      onCancel={onCancel}
      onOk={onSave}
      width={1000}
      okText="保存权限"
      cancelText="取消"
      okButtonProps={{
        className: styles.permissionModalActionButton,
      }}
      cancelButtonProps={{
        className: styles.permissionModalActionButton,
      }}
    >
      <div className={styles.permissionDesc}>
        <Text type="secondary">
          为角色 <strong>{roleName}</strong> 配置系统权限
        </Text>
      </div>

      <Transfer
        dataSource={transferData}
        targetKeys={targetPermissions}
        onChange={keys => onTargetPermissionsChange(keys as string[])}
        className={styles.permissionTransfer}
        render={item => (
          <div>
            <div className={styles.transferTitle}>{item.title}</div>
            <div className={styles.transferDesc}>{item.description}</div>
          </div>
        )}
        titles={['可选权限', '已选权限']}
        showSearch
        locale={{ searchPlaceholder: '搜索权限' }}
      />

      <Divider />

      <div>
        <Text strong>权限预览：</Text>
        <div className={styles.treePreview}>
          <Tree
            treeData={permissionTreeData}
            checkable
            checkedKeys={targetPermissions}
            className={styles.permissionTree}
          />
        </div>
      </div>
    </Modal>
  );
};

export default RolePermissionModal;
