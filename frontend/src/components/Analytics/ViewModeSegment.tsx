import React from 'react';
import { Segmented } from 'antd';
import { useDataScopeStore } from '@/stores/dataScopeStore';

const ViewModeSegment: React.FC = () => {
  const isAdmin = useDataScopeStore(state => state.isAdmin);
  const isDualBinding = useDataScopeStore(state => state.isDualBinding);
  const currentViewMode = useDataScopeStore(state => state.currentViewMode);
  const setCurrentViewMode = useDataScopeStore(state => state.setCurrentViewMode);

  if (isAdmin || !isDualBinding) {
    return null;
  }

  return (
    <Segmented
      aria-label="看板口径切换"
      options={[
        { label: '产权方口径', value: 'owner' },
        { label: '运营方口径', value: 'manager' },
      ]}
      value={currentViewMode ?? 'owner'}
      onChange={value => {
        setCurrentViewMode(value === 'manager' ? 'manager' : 'owner');
      }}
    />
  );
};

export default ViewModeSegment;
