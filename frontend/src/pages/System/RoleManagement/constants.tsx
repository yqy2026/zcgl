import React from 'react';
import {
  ApartmentOutlined,
  KeyOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { StatusTone } from './types';

export const roleStatusOptions: Array<{
  value: 'active' | 'inactive';
  label: string;
  tone: StatusTone;
}> = [
  { value: 'active', label: '启用', tone: 'success' },
  { value: 'inactive', label: '停用', tone: 'error' },
];

export const rolePermissionModules = [
  { value: 'dashboard', label: '数据看板', icon: <SettingOutlined /> },
  { value: 'assets', label: '资产管理', icon: <ApartmentOutlined /> },
  { value: 'rental', label: '旧租赁前端已退休', icon: <UserOutlined /> },
  { value: 'ownership', label: '权属方管理', icon: <KeyOutlined /> },
  { value: 'project', label: '项目管理', icon: <TeamOutlined /> },
  { value: 'system', label: '系统管理', icon: <SettingOutlined /> },
] as const;
