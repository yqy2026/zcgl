/**
 * 面包屑导航配置
 * v5 一次性切换后的路由中文名称映射
 */

// 静态路由映射 (精确匹配)
export const staticBreadcrumbMap: Record<string, string> = {
  // 资产运营
  '/asset-operations/units': '资产单元',
  '/asset-operations/contracts/intake': '录入已签合同',
  '/asset-operations/contracts/upstream': '上游合同',
  '/asset-operations/contracts/terminal': '终端合同',

  // 系统管理
  '/system': '系统管理',
  '/system/parties': '主体管理',
  '/system/users': '用户管理',
  '/system/roles': '角色权限',
  '/system/logs': '操作日志',
  '/system/organizations': '组织架构',
  '/system/dictionaries': '字典管理',
  '/system/settings': '系统设置',

  // 其他
  '/profile': '个人中心',
};

// 动态路由映射 (模式匹配)
// 使用 :id 等参数占位符
export const dynamicBreadcrumbMap: Record<string, string> = {
  // 生命周期操作
  '/asset-operations/contracts/terminal/:contractId/actions': '终端合同操作',
  '/asset-operations/contracts/upstream/:contractId/actions': '上游合同操作',

  // 主体管理
  '/system/parties/:id': '主体详情',
};
