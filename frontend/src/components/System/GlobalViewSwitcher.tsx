import React, { useEffect, useMemo, useState } from 'react';
import { Button, Modal, Select, Space, Tag, Typography } from 'antd';
import { SwapOutlined } from '@ant-design/icons';

import { useView } from '@/contexts/ViewContext';

const { Text, Paragraph } = Typography;

const GlobalViewSwitcher: React.FC = () => {
  const {
    currentView,
    availableViews,
    selectionRequired,
    selectorOpen,
    openSelector,
    closeSelector,
    selectView,
  } = useView();
  const [pendingKey, setPendingKey] = useState<string | undefined>(undefined);

  useEffect(() => {
    setPendingKey(currentView?.key);
  }, [currentView?.key]);

  const selectOptions = useMemo(
    () =>
      availableViews.map(view => ({
        label: view.label,
        value: view.key,
      })),
    [availableViews]
  );

  const handleConfirm = () => {
    if (pendingKey == null || pendingKey.trim() === '') {
      return;
    }
    selectView(pendingKey);
  };

  if (availableViews.length === 0) {
    return null;
  }

  return (
    <>
      <Button type="text" onClick={openSelector} icon={<SwapOutlined />}>
        {currentView?.label ?? '选择视角'}
      </Button>

      <Modal
        open={selectorOpen}
        title="请选择当前主体/视角"
        closable={selectionRequired !== true}
        maskClosable={selectionRequired !== true}
        keyboard={selectionRequired !== true}
        onCancel={closeSelector}
        okText="确认使用"
        cancelText="取消"
        okButtonProps={{
          disabled: pendingKey == null || pendingKey.trim() === '',
        }}
        cancelButtonProps={{
          style: selectionRequired ? { display: 'none' } : undefined,
        }}
        onOk={handleConfirm}
      >
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          {selectionRequired ? (
            <Tag color="warning">当前默认视角已失效，请重新选择</Tag>
          ) : null}
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            视角用于标记当前正在使用的主体与角色口径。后续查询和页面标签将基于该选择展示。
          </Paragraph>
          <div>
            <Text strong>当前主体/视角</Text>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              placeholder="请选择当前主体/视角"
              value={pendingKey}
              onChange={value => setPendingKey(value)}
              options={selectOptions}
            />
          </div>
        </Space>
      </Modal>
    </>
  );
};

export default GlobalViewSwitcher;
