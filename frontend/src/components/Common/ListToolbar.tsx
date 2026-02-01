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
}

export const ListToolbar: React.FC<ListToolbarProps> = ({
  items,
  gutter = [16, 16],
  align = 'middle',
  cardProps,
}) => {
  return (
    <Card style={{ marginBottom: 16, ...(cardProps?.style ?? {}) }} {...cardProps}>
      <Row gutter={gutter} align={align}>
        {items.map(item => (
          <Col key={item.key} {...item.col}>
            {item.content}
          </Col>
        ))}
      </Row>
    </Card>
  );
};
