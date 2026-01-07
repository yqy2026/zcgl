import React from 'react';
import { Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface LoadingSpinnerProps {
  size?: 'small' | 'default' | 'large';
  tip?: string;
  spinning?: boolean;
  children?: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  delay?: number;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'default',
  tip,
  spinning = true,
  children,
  style,
  className,
  delay = 0,
}) => {
  const antIcon = (
    <LoadingOutlined
      style={{ fontSize: size === 'large' ? 24 : size === 'small' ? 14 : 18 }}
      spin
    />
  );

  if (children !== null && children !== undefined) {
    return (
      <Spin
        spinning={spinning}
        tip={tip}
        size={size}
        indicator={antIcon}
        style={style}
        className={className}
        delay={delay}
      >
        {children}
      </Spin>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '50px 20px',
        ...style,
      }}
      className={className}
    >
      <Spin spinning={spinning} size={size} indicator={antIcon} delay={delay} />
      {tip !== null && tip !== undefined && (
        <Text
          type="secondary"
          style={{
            marginTop: 16,
            fontSize: size === 'large' ? 16 : size === 'small' ? 12 : 14,
          }}
        >
          {tip}
        </Text>
      )}
    </div>
  );
};

export default LoadingSpinner;
