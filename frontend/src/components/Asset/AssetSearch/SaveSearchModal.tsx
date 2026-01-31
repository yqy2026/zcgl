import React from 'react';
import { Modal, Input } from 'antd';

interface SaveSearchModalProps {
  open: boolean;
  value: string;
  onSave: () => void;
  onCancel: () => void;
  onChange: (value: string) => void;
}

export const SaveSearchModal = React.memo(function SaveSearchModal({
  open,
  value,
  onSave,
  onCancel,
  onChange,
}: SaveSearchModalProps) {
  return (
    <Modal
      title="保存搜索条件"
      open={open}
      onOk={onSave}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Input
        placeholder="输入保存名称"
        value={value}
        onChange={event => onChange(event.target.value)}
        onPressEnter={onSave}
      />
    </Modal>
  );
});
