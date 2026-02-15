import React from 'react';
import { Modal, Typography, Space } from 'antd';
import {
  ExclamationCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  SaveOutlined,
  LogoutOutlined,
  StopOutlined,
  QuestionCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import styles from './ConfirmDialog.module.css';

const { Text, Paragraph } = Typography;

export type ConfirmType = 'delete' | 'edit' | 'save' | 'logout' | 'cancel' | 'warning' | 'info';

interface ConfirmDialogProps {
  type?: ConfirmType;
  title?: string;
  content?: React.ReactNode;
  visible?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
  confirmText?: string;
  cancelText?: string;
  confirmLoading?: boolean;
  danger?: boolean;
  width?: number;
  centered?: boolean;
  maskClosable?: boolean;
  itemName?: string;
  itemCount?: number;
  details?: string[];
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  type = 'warning',
  title,
  content,
  visible = false,
  onConfirm,
  onCancel,
  confirmText,
  cancelText = '取消',
  confirmLoading = false,
  danger,
  width = 416,
  centered = true,
  maskClosable = false,
  itemName,
  itemCount,
  details,
}) => {
  // 预设配置
  const presetConfigs = {
    delete: {
      icon: <DeleteOutlined className={`${styles.confirmIcon} ${styles.confirmIconDanger}`} />,
      title: '确认删除',
      confirmText: '删除',
      danger: true,
      getContent: () => (
        <div>
          <Paragraph>
            {itemCount != null && itemCount > 1
              ? `确定要删除这 ${itemCount} 个${itemName ?? '项目'}吗？`
              : `确定要删除${itemName != null ? `"${itemName}"` : '此项目'}吗？`}
          </Paragraph>
          {details != null && details.length > 0 && (
            <div className={styles.confirmDetailsContainer}>
              <Text type="secondary">将要删除的内容：</Text>
              <ul className={styles.confirmDetailsList}>
                {details.map(detail => (
                  <li key={detail}>
                    <Text type="secondary">{detail}</Text>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Paragraph type="danger" className={styles.confirmDangerParagraph}>
            <Text strong>此操作不可撤销，请谨慎操作！</Text>
          </Paragraph>
        </div>
      ),
    },
    edit: {
      icon: <EditOutlined className={`${styles.confirmIcon} ${styles.confirmIconInfo}`} />,
      title: '确认编辑',
      confirmText: '继续编辑',
      danger: false,
      getContent: () => (
        <div>
          <Paragraph>您有未保存的更改，确定要继续编辑吗？</Paragraph>
          <Paragraph type="warning">
            <Text>继续编辑将丢失当前的更改。</Text>
          </Paragraph>
        </div>
      ),
    },
    save: {
      icon: <SaveOutlined className={`${styles.confirmIcon} ${styles.confirmIconSuccess}`} />,
      title: '确认保存',
      confirmText: '保存',
      danger: false,
      getContent: () => (
        <div>
          <Paragraph>确定要保存当前的更改吗？</Paragraph>
          {details != null && details.length > 0 && (
            <div className={styles.confirmDetailsContainer}>
              <Text type="secondary">将要保存的更改：</Text>
              <ul className={styles.confirmDetailsList}>
                {details.map(detail => (
                  <li key={detail}>
                    <Text type="secondary">{detail}</Text>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ),
    },
    logout: {
      icon: <LogoutOutlined className={`${styles.confirmIcon} ${styles.confirmIconWarning}`} />,
      title: '确认退出',
      confirmText: '退出',
      danger: false,
      getContent: () => (
        <div>
          <Paragraph>确定要退出登录吗？</Paragraph>
          <Paragraph type="secondary">退出后需要重新登录才能使用系统功能。</Paragraph>
        </div>
      ),
    },
    cancel: {
      icon: <StopOutlined className={`${styles.confirmIcon} ${styles.confirmIconWarning}`} />,
      title: '确认取消',
      confirmText: '确认取消',
      danger: false,
      getContent: () => (
        <div>
          <Paragraph>确定要取消当前操作吗？</Paragraph>
          <Paragraph type="warning">取消后将丢失所有未保存的更改。</Paragraph>
        </div>
      ),
    },
    warning: {
      icon: (
        <ExclamationCircleOutlined
          className={`${styles.confirmIcon} ${styles.confirmIconWarning}`}
        />
      ),
      title: '警告',
      confirmText: '确定',
      danger: false,
      getContent: () => <Paragraph>请确认您要执行此操作。</Paragraph>,
    },
    info: {
      icon: <InfoCircleOutlined className={`${styles.confirmIcon} ${styles.confirmIconInfo}`} />,
      title: '提示',
      confirmText: '确定',
      danger: false,
      getContent: () => <Paragraph>请确认相关信息。</Paragraph>,
    },
  };

  const config = presetConfigs[type];

  return (
    <Modal
      title={
        <Space>
          {config.icon}
          <span>{title ?? config.title}</span>
        </Space>
      }
      open={visible}
      onOk={onConfirm}
      onCancel={onCancel}
      okText={confirmText ?? config.confirmText}
      cancelText={cancelText}
      confirmLoading={confirmLoading}
      width={width}
      centered={centered}
      maskClosable={maskClosable}
      okButtonProps={{
        danger: danger !== undefined ? danger : config.danger,
      }}
      destroyOnHidden
    >
      {content ?? config.getContent()}
    </Modal>
  );
};

// 预设的确认对话框
export const DeleteConfirmDialog: React.FC<Omit<ConfirmDialogProps, 'type'>> = props => (
  <ConfirmDialog type="delete" {...props} />
);

export const EditConfirmDialog: React.FC<Omit<ConfirmDialogProps, 'type'>> = props => (
  <ConfirmDialog type="edit" {...props} />
);

export const SaveConfirmDialog: React.FC<Omit<ConfirmDialogProps, 'type'>> = props => (
  <ConfirmDialog type="save" {...props} />
);

export const LogoutConfirmDialog: React.FC<Omit<ConfirmDialogProps, 'type'>> = props => (
  <ConfirmDialog type="logout" {...props} />
);

export const CancelConfirmDialog: React.FC<Omit<ConfirmDialogProps, 'type'>> = props => (
  <ConfirmDialog type="cancel" {...props} />
);

// 便捷方法
export const showDeleteConfirm = (options: Omit<ConfirmDialogProps, 'type' | 'visible'>) => {
  return new Promise<boolean>(resolve => {
    Modal.confirm({
      title: (
        <Space>
          <DeleteOutlined className={styles.confirmShortcutDeleteIcon} />
          <span>{options.title ?? '确认删除'}</span>
        </Space>
      ),
      content: options.content ?? (
        <div>
          <Paragraph>
            {options.itemCount != null && options.itemCount > 1
              ? `确定要删除这 ${options.itemCount} 个${options.itemName ?? '项目'}吗？`
              : `确定要删除${options.itemName != null ? `"${options.itemName}"` : '此项目'}吗？`}
          </Paragraph>
          <Paragraph type="danger">
            <Text strong>此操作不可撤销，请谨慎操作！</Text>
          </Paragraph>
        </div>
      ),
      okText: options.confirmText ?? '删除',
      cancelText: options.cancelText ?? '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        if (options.onConfirm) {
          options.onConfirm();
        }
        resolve(true);
      },
      onCancel: () => {
        if (options.onCancel) {
          options.onCancel();
        }
        resolve(false);
      },
    });
  });
};

export const showSaveConfirm = (options: Omit<ConfirmDialogProps, 'type' | 'visible'>) => {
  return new Promise<boolean>(resolve => {
    Modal.confirm({
      title: (
        <Space>
          <QuestionCircleOutlined className={styles.confirmShortcutSaveIcon} />
          <span>{options.title ?? '确认保存'}</span>
        </Space>
      ),
      content: options.content ?? '确定要保存当前的更改吗？',
      okText: options.confirmText ?? '保存',
      cancelText: options.cancelText ?? '取消',
      onOk: () => {
        if (options.onConfirm) {
          options.onConfirm();
        }
        resolve(true);
      },
      onCancel: () => {
        if (options.onCancel) {
          options.onCancel();
        }
        resolve(false);
      },
    });
  });
};

export default ConfirmDialog;
