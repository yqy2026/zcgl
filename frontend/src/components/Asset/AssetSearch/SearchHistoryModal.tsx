import React from 'react';
import { Modal, List, Space, Button, Typography, Popconfirm, Input } from 'antd';
import dayjs from 'dayjs';

import type { SearchHistoryItem } from '@/hooks/useSearchHistory';

const { Text } = Typography;

interface SearchHistoryModalProps {
  open: boolean;
  historyItems: SearchHistoryItem[];
  editingHistoryId: string | null;
  editingName: string;
  onApply: (historyId: string) => void;
  onEdit: (historyId: string, currentName: string) => void;
  onDelete: (historyId: string) => void;
  onSaveEdit: () => void;
  onEditNameChange: (value: string) => void;
  onClear: () => void;
  onCancel: () => void;
}

export const SearchHistoryModal = React.memo(function SearchHistoryModal({
  open,
  historyItems,
  editingHistoryId,
  editingName,
  onApply,
  onEdit,
  onDelete,
  onSaveEdit,
  onEditNameChange,
  onClear,
  onCancel,
}: SearchHistoryModalProps) {
  return (
    <Modal
      title="搜索历史"
      open={open}
      onCancel={onCancel}
      footer={null}
      width={600}
      destroyOnHidden
    >
      <List
        dataSource={historyItems}
        locale={{
          emptyText: '暂无搜索历史',
        }}
        renderItem={item => (
          <List.Item
            key={item.id}
            actions={[
              <Button
                key="apply"
                type="link"
                size="small"
                onClick={() => onApply(item.id)}
              >
                应用
              </Button>,
              <Button
                key="edit"
                type="link"
                size="small"
                onClick={() => onEdit(item.id, item.name)}
              >
                编辑
              </Button>,
              <Popconfirm
                key="delete"
                title="确定要删除这条历史记录吗？"
                onConfirm={() => onDelete(item.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="link" size="small" danger>
                  删除
                </Button>
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              title={
                editingHistoryId === item.id ? (
                  <Input
                    size="small"
                    value={editingName}
                    onChange={event => onEditNameChange(event.target.value)}
                    onBlur={onSaveEdit}
                    onPressEnter={onSaveEdit}
                    style={{ width: 200 }}
                  />
                ) : (
                  <Text>{item.name}</Text>
                )
              }
              description={
                <Space orientation="vertical" size="small">
                  <Text type="secondary">
                    保存时间: {dayjs(item.createdAt).format('YYYY-MM-DD HH:mm:ss')}
                  </Text>
                  <Text type="secondary">条件数: {Object.keys(item.conditions).length}</Text>
                </Space>
              }
            />
          </List.Item>
        )}
      />

      {historyItems.length > 0 && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Popconfirm
            title="确定要清空所有搜索历史吗？"
            onConfirm={onClear}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small">
              清空历史
            </Button>
          </Popconfirm>
        </div>
      )}
    </Modal>
  );
});
