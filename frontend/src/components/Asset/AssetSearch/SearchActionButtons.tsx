import React from 'react';
import { Space, Button } from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  DownOutlined,
  UpOutlined,
  SaveOutlined,
  HistoryOutlined,
} from '@ant-design/icons';

interface SearchActionButtonsProps {
  expanded: boolean;
  loading?: boolean;
  showSaveButton?: boolean;
  showHistoryButton?: boolean;
  onSearch: () => void;
  onReset: () => void;
  onToggleExpanded: () => void;
  onSave: () => void;
  onShowHistory: () => void;
}

export const SearchActionButtons: React.FC<SearchActionButtonsProps> = ({
  expanded,
  loading = false,
  showSaveButton = true,
  showHistoryButton = true,
  onSearch,
  onReset,
  onToggleExpanded,
  onSave,
  onShowHistory,
}) => {
  return (
    <Space>
      {showSaveButton && (
        <Button
          type="default"
          icon={<SaveOutlined />}
          onClick={onSave}
          disabled={loading}
        >
          保存条件
        </Button>
      )}
      {showHistoryButton && (
        <Button
          type="default"
          icon={<HistoryOutlined />}
          onClick={onShowHistory}
        >
          搜索历史
        </Button>
      )}
      <Button
        type="primary"
        icon={<SearchOutlined />}
        onClick={onSearch}
        loading={loading}
      >
        搜索
      </Button>
      <Button icon={<ReloadOutlined />} onClick={onReset} disabled={loading}>
        重置
      </Button>
      <Button
        type="text"
        icon={expanded ? <UpOutlined /> : <DownOutlined />}
        onClick={onToggleExpanded}
      >
        {expanded ? '收起' : '展开'}
      </Button>
    </Space>
  );
};
