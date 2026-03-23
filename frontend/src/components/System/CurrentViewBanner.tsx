import React from 'react';
import { Alert } from 'antd';

import { useRoutePerspective } from '@/routes/perspective';

const CurrentViewBanner: React.FC = () => {
  const { perspective } = useRoutePerspective();

  if (perspective == null) {
    return null;
  }

  const description = perspective === 'owner' ? '业主视角' : '经营视角';

  return (
    <Alert
      title="当前视角"
      description={description}
      type="info"
      showIcon
      style={{ marginBottom: 16 }}
    />
  );
};

export default CurrentViewBanner;
