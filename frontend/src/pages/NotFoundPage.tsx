import React from 'react';
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

/**
 * 404 兜底页：受保护路由未匹配（死 URL）时渲染，
 * 避免 React Router 无匹配渲染 null 导致 main 静默空白（2026-08-09 点检发现）。
 */
const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Result
      status="404"
      title="404"
      subTitle="页面不存在或已被移除"
      extra={
        <Button type="primary" onClick={() => navigate('/dashboard')}>
          返回工作台
        </Button>
      }
    />
  );
};

export default NotFoundPage;
