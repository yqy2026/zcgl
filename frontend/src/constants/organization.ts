export const ORGANIZATION_READ_ONLY_TITLE = '组织架构当前为只读模式';
export const ORGANIZATION_READ_ONLY_NOTICE = '已禁用新增/编辑/删除/移动/导入写操作。';
export const ORGANIZATION_READ_ONLY_BLOCK_MESSAGE = `${ORGANIZATION_READ_ONLY_TITLE}，${ORGANIZATION_READ_ONLY_NOTICE}`;

export const isOrganizationWriteEnabled = (): boolean => {
  return import.meta.env.VITE_ENABLE_ORGANIZATION_WRITE === 'true';
};

export const isOrganizationReadOnlyMode = (): boolean => {
  return isOrganizationWriteEnabled() === false;
};

export const getOrganizationReadOnlyErrorMessage = (actionLabel: string): string => {
  return `${ORGANIZATION_READ_ONLY_BLOCK_MESSAGE}（当前操作：${actionLabel}）`;
};
