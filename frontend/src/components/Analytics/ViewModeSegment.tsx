import React from 'react';
import { Segmented, Space, Typography } from 'antd';
import { useDataScopeStore } from '@/stores/dataScopeStore';

const { Text } = Typography;

// rc-segmented 在 value 为 undefined（非受控）时会自动选中第一项；
// 用不匹配任何选项的哨兵值保持受控，实现「未选择」态
const UNSELECTED_VIEW_MODE = '__unselected__';

const ViewModeSegment: React.FC = () => {
  const isAdmin = useDataScopeStore(state => state.isAdmin);
  const isDualBinding = useDataScopeStore(state => state.isDualBinding);
  const currentViewMode = useDataScopeStore(state => state.currentViewMode);
  const setCurrentViewMode = useDataScopeStore(state => state.setCurrentViewMode);

  if (!isAdmin && !isDualBinding) {
    return null;
  }

  return (
    <Space size={8} wrap>
      <Segmented
        aria-label="看板口径切换"
        options={[
          { label: '产权方口径', value: 'owner' },
          { label: '运营方口径', value: 'manager' },
        ]}
        value={currentViewMode ?? UNSELECTED_VIEW_MODE}
        onChange={value => {
          setCurrentViewMode(value === 'manager' ? 'manager' : 'owner');
        }}
      />
      {currentViewMode == null && <Text type="secondary">请选择产权方或运营方口径后查看数据</Text>}
    </Space>
  );
};

export default ViewModeSegment;
