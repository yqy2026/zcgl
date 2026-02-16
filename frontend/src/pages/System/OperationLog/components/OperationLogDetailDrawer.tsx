import React, { useCallback, type ReactNode } from 'react';
import { Descriptions, Drawer, Space, Typography } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { OperationLog } from '@/services/systemService';
import type { Tone } from '../types';
import { formatJsonValue } from '../utils';
import {
  OperationActionTag,
  OperationModuleTag,
  OperationRequestMethodTag,
  OperationResponseTimeText,
  OperationStatusTag,
} from './OperationLogTags';
import styles from '../../OperationLogPage.module.css';

const { Text } = Typography;

interface OperationLogDetailDrawerProps {
  open: boolean;
  selectedLog: OperationLog | null;
  onClose: () => void;
  resolveToneClassName: (tone: Tone) => string;
}

const OperationLogDetailDrawer: React.FC<OperationLogDetailDrawerProps> = ({
  open,
  selectedLog,
  onClose,
  resolveToneClassName,
}) => {
  const renderJsonBlock = useCallback((value: unknown): ReactNode => {
    const formatted = formatJsonValue(value);
    if (formatted === '-') {
      return '-';
    }
    return <pre className={styles.jsonBlock}>{formatted}</pre>;
  }, []);

  return (
    <Drawer
      title="操作日志详情"
      placement="right"
      onClose={onClose}
      open={open}
      size={800}
      className={styles.detailDrawer}
    >
      {selectedLog != null && (
        <div className={styles.detailContent}>
          <Descriptions column={1} bordered>
            <Descriptions.Item label="操作时间">
              {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="用户信息">
              <Space>
                <UserOutlined />
                <Space orientation="vertical" size={0} className={styles.userCell}>
                  <span className={styles.primaryText}>
                    {selectedLog.user_name ?? selectedLog.username ?? '-'}
                  </span>
                  <span className={styles.secondaryText}>
                    {selectedLog.username != null && selectedLog.username.trim() !== ''
                      ? `账号 @${selectedLog.username}`
                      : '-'}
                  </span>
                </Space>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="操作类型">
              <OperationActionTag
                action={selectedLog.action}
                resolveToneClassName={resolveToneClassName}
              />
            </Descriptions.Item>
            <Descriptions.Item label="所属模块">
              <OperationModuleTag
                module={selectedLog.module}
                moduleName={selectedLog.module_name}
                resolveToneClassName={resolveToneClassName}
              />
            </Descriptions.Item>
            <Descriptions.Item label="资源信息">
              {selectedLog.resource_name != null && selectedLog.resource_name.trim() !== '' ? (
                <div>
                  <div>{selectedLog.resource_name}</div>
                  <div className={styles.secondaryText}>
                    {selectedLog.resource_type} (ID: {selectedLog.resource_id})
                  </div>
                </div>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="请求信息">
              <div>
                <div className={styles.requestMetaRow}>
                  <OperationRequestMethodTag
                    requestMethod={selectedLog.request_method}
                    resolveToneClassName={resolveToneClassName}
                  />
                  {selectedLog.request_url != null && selectedLog.request_url.trim() !== '' ? (
                    <code className={styles.requestUrl}>{selectedLog.request_url}</code>
                  ) : (
                    <Text type="secondary">-</Text>
                  )}
                </div>
                <div className={styles.ipText}>
                  IP:{' '}
                  {selectedLog.ip_address != null && selectedLog.ip_address.trim() !== ''
                    ? selectedLog.ip_address
                    : '-'}
                </div>
              </div>
            </Descriptions.Item>
            <Descriptions.Item label="请求参数">
              {renderJsonBlock(selectedLog.request_params)}
            </Descriptions.Item>
            <Descriptions.Item label="请求体">
              {renderJsonBlock(selectedLog.request_body)}
            </Descriptions.Item>
            <Descriptions.Item label="响应信息">
              <div className={styles.responseMeta}>
                <div className={styles.responseMetaRow}>
                  <Text strong>状态：</Text>
                  <OperationStatusTag
                    status={selectedLog.response_status}
                    resolveToneClassName={resolveToneClassName}
                  />
                </div>
                <div className={styles.responseMetaRow}>
                  <Text strong>耗时：</Text>
                  <OperationResponseTimeText
                    time={selectedLog.response_time}
                    resolveToneClassName={resolveToneClassName}
                  />
                </div>
              </div>
            </Descriptions.Item>
            {selectedLog.error_message != null && (
              <Descriptions.Item label="错误信息">
                <div className={styles.errorMessage}>{selectedLog.error_message}</div>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="用户代理">
              <div className={styles.userAgent}>
                {selectedLog.user_agent != null && selectedLog.user_agent.trim() !== ''
                  ? selectedLog.user_agent
                  : '-'}
              </div>
            </Descriptions.Item>
            <Descriptions.Item label="详细信息">
              {selectedLog.details == null ? (
                '-'
              ) : typeof selectedLog.details === 'string' ? (
                <Text type="secondary">{selectedLog.details}</Text>
              ) : Array.isArray(selectedLog.details) ? (
                renderJsonBlock(selectedLog.details)
              ) : (
                <div className={styles.detailsObject}>
                  {Object.entries(selectedLog.details).map(([key, value]) => (
                    <div key={key} className={styles.detailsRow}>
                      <Text strong className={styles.detailKey}>
                        {key}:
                      </Text>
                      <Text type="secondary">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </Text>
                    </div>
                  ))}
                </div>
              )}
            </Descriptions.Item>
          </Descriptions>
        </div>
      )}
    </Drawer>
  );
};

export default OperationLogDetailDrawer;
