import React from 'react';
import { Alert } from 'antd';

import { useView } from '@/contexts/ViewContext';

const CurrentViewBanner: React.FC = () => {
  const { currentView } = useView();

  if (currentView == null) {
    return null;
  }

  return (
    <Alert
      title="当前视角"
      description={currentView.label}
      type="info"
      showIcon
      style={{ marginBottom: 16 }}
    />
  );
};

export default CurrentViewBanner;
