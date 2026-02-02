import React from 'react';
import { Card, Col, Row } from 'antd';
import type { CardProps } from 'antd';
import type { ColProps } from 'antd/es/col';

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
  const content = (
    <Row gutter={gutter} align={align}>
      {items.map(item => (
        <Col key={item.key} {...item.col}>
          {item.content}
        </Col>
      ))}
    </Row>
  );

  if (variant === 'plain') {
    return content;
  }

  return (
    <Card style={{ marginBottom: 16, ...(cardProps?.style ?? {}) }} {...cardProps}>
      {content}
    </Card>
  );
};
