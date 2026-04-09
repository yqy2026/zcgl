import React from 'react';
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  FileTextOutlined,
  LoginOutlined,
  LogoutOutlined,
  PlusOutlined,
  SecurityScanOutlined,
} from '@ant-design/icons';
import type { ActionMeta, ModuleMeta, StatusFilterOption, Tone } from './types';

export const ACTION_OPTIONS: ActionMeta[] = [
  { value: 'create', label: '创建', tone: 'success', icon: <PlusOutlined /> },
  { value: 'update', label: '更新', tone: 'primary', icon: <EditOutlined /> },
  { value: 'delete', label: '删除', tone: 'error', icon: <DeleteOutlined /> },
  { value: 'read', label: '查看', tone: 'primary', icon: <EyeOutlined /> },
  { value: 'login', label: '登录', tone: 'success', icon: <LoginOutlined /> },
  { value: 'logout', label: '登出', tone: 'warning', icon: <LogoutOutlined /> },
  { value: 'export', label: '导出', tone: 'warning', icon: <FileTextOutlined /> },
  { value: 'import', label: '导入', tone: 'primary', icon: <FileTextOutlined /> },
  { value: 'security', label: '安全操作', tone: 'error', icon: <SecurityScanOutlined /> },
];

export const ACTION_META_MAP = ACTION_OPTIONS.reduce<Record<string, ActionMeta>>(
  (accumulator, option) => {
    accumulator[option.value] = option;
    return accumulator;
  },
  {}
);

ACTION_META_MAP.view = ACTION_META_MAP.read;

export const MODULE_OPTIONS: ModuleMeta[] = [
  { value: 'dashboard', label: '数据看板', tone: 'primary' },
  { value: 'assets', label: '资产管理', tone: 'success' },
  { value: 'rental', label: '旧租赁前端已退休', tone: 'warning' },
  { value: 'ownership', label: '权属方管理', tone: 'primary' },
  { value: 'project', label: '项目管理', tone: 'success' },
  { value: 'system', label: '系统管理', tone: 'error' },
  { value: 'auth', label: '认证授权', tone: 'warning' },
];

export const MODULE_META_MAP = MODULE_OPTIONS.reduce<Record<string, ModuleMeta>>(
  (accumulator, option) => {
    accumulator[option.value] = option;
    return accumulator;
  },
  {}
);

export const STATUS_OPTIONS: StatusFilterOption[] = [
  { value: 'success', label: '成功' },
  { value: 'error', label: '失败' },
  { value: 'warning', label: '警告' },
];

export const REQUEST_METHOD_TONE_MAP: Record<string, Tone> = {
  GET: 'success',
  POST: 'primary',
  PUT: 'warning',
  PATCH: 'warning',
  DELETE: 'error',
};
