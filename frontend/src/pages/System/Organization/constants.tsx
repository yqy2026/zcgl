import React from 'react';
import {
  ApartmentOutlined,
  BankOutlined,
  PartitionOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import type { HistoryActionMeta } from './types';

export const organizationTypeIconMap: Record<string, React.ReactNode> = {
  company: <BankOutlined />,
  department: <TeamOutlined />,
  group: <ApartmentOutlined />,
  division: <PartitionOutlined />,
  team: <TeamOutlined />,
  branch: <BankOutlined />,
  office: <SettingOutlined />,
};

export const defaultOrganizationTypeIcon = <TeamOutlined />;

export const historyActionMetaMap: Record<string, HistoryActionMeta> = {
  create: { label: '创建', tone: 'success' },
  update: { label: '更新', tone: 'primary' },
  delete: { label: '删除', tone: 'error' },
};
