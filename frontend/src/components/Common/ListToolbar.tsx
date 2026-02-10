import React from 'react';
import { Card, Col, Row } from 'antd';
import type { CardProps } from 'antd';
import type { ColProps } from 'antd/es/col';
import styles from './ListToolbar.module.css';

export interface ListToolbarItem {
  key: string;
  content: React.ReactNode;
  col?: ColProps;
}

interface ListToolbarProps {
  items: ListToolbarItem[];
  gutter?: [number, number];
  align?: 'top' | 'middle' | 'bottom';
  cardProps?: Omit<CardProps, 'children'>;
  variant?: 'card' | 'plain';
}

export const ListToolbar: React.FC<ListToolbarProps> = ({
  items,
  gutter = [16, 16],
  align = 'middle',
  cardProps,
  variant = 'card',
}) => {
  const toolbarCardClassName = [styles.toolbarCard, cardProps?.className]
    .filter((className): className is string => className != null && className !== '')
    .join(' ');

  const content = (
    <Row gutter={gutter} align={align} className={styles.toolbarRow}>
      {items.map(item => (
        <Col key={item.key} {...item.col}>
          <div className={styles.toolbarItem}>{item.content}</div>
        </Col>
      ))}
    </Row>
  );

  if (variant === 'plain') {
    return content;
  }

  return (
    <Card
      {...cardProps}
      className={toolbarCardClassName}
      style={{ ...(cardProps?.style ?? {}) }}
    >
      {content}
    </Card>
  );
};
