import React from 'react';
import { Button, Result, Space } from 'antd';

import { BASE_PATHS } from '@/constants/routes';
import type { PerspectiveMismatchResolution } from '@/routes/perspectiveResolution';

export interface PerspectiveResolutionPageProps {
  resolution: PerspectiveMismatchResolution;
}

const getPerspectiveLabel = (perspective: 'owner' | 'manager'): string => {
  return perspective === 'owner' ? '业主视角' : '经营视角';
};

const PerspectiveResolutionPage: React.FC<PerspectiveResolutionPageProps> = ({ resolution }) => {
  if (resolution.targetPath == null || resolution.targetPerspective == null) {
    return (
      <Result
        status="403"
        title="当前视角已失效"
        subTitle="当前账号已没有可用视角，请联系管理员处理权限配置。"
        extra={
          <Button type="primary" href={BASE_PATHS.DASHBOARD}>
            返回工作台
          </Button>
        }
      />
    );
  }

  return (
    <Result
      status="warning"
      title="当前视角已失效"
      subTitle={`当前页面所需视角已不可用，请切换到仍可访问的${getPerspectiveLabel(
        resolution.targetPerspective
      )}。`}
      extra={
        <Space>
          <Button type="primary" href={resolution.targetPath}>
            {`切换到${getPerspectiveLabel(resolution.targetPerspective)}`}
          </Button>
          <Button href={BASE_PATHS.DASHBOARD}>返回工作台</Button>
        </Space>
      }
    />
  );
};

export default PerspectiveResolutionPage;
