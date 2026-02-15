import React from 'react';
import { Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import styles from './LoadingSpinner.module.css';

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
  const iconSizeClass =
    size === 'large' ? styles.iconLarge : size === 'small' ? styles.iconSmall : styles.iconDefault;

  const tipSizeClass =
    size === 'large' ? styles.tipLarge : size === 'small' ? styles.tipSmall : styles.tipDefault;

  const antIcon = <LoadingOutlined className={`${styles.spinnerIcon} ${iconSizeClass}`} spin />;

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
      style={style}
      className={
        className != null && className !== ''
          ? `${styles.spinnerContainer} ${className}`
          : styles.spinnerContainer
      }
    >
      <Spin spinning={spinning} size={size} indicator={antIcon} delay={delay} />
      {tip !== null && tip !== undefined && (
        <Text type="secondary" className={`${styles.tipText} ${tipSizeClass}`}>
          {tip}
        </Text>
      )}
    </div>
  );
};

export default LoadingSpinner;
