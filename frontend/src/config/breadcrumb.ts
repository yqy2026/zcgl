/**
 * 面包屑导航配置
 * 定义路由路径对应的中文名称
 */

// 静态路由映射 (精确匹配)
export const staticBreadcrumbMap: Record<string, string> = {
  '/dashboard': '工作台',

  // 资产资源
  '/assets': '资产资源',
  '/assets/list': '资产台账',
  '/assets/map': '资产地图',
  '/assets/new': '新增资产',
  '/assets/import': '数据导入',
  '/assets/analytics': '经营分析',

  // 经营台账
  '/operations': '经营台账',
  '/operations/ledger': '经营台账',

  // 统计分析
  '/analytics': '经营分析',
  '/analysis': '分析统计',
  '/analysis/overview': '概览统计',
  '/analysis/report': '报表生成',

  // 项目运营
  '/project': '项目运营',

  // 合同中心
  '/contract-center': '合同中心',
  '/contract-center/import': 'PDF导入',
  '/contract-center/new': '新建合同关系',
  '/contract-groups': '合同关系管理',
  '/contract-groups/new': '新建合同关系',

  // 系统管理
  '/system': '系统管理',
  '/system/parties': '主体管理',
  '/system/users': '用户管理',
  '/system/roles': '角色权限',
  '/system/logs': '操作日志',
  '/system/organizations': '组织架构',
  '/system/dictionaries': '字典管理',
  '/system/templates': '模板管理',
  '/system/settings': '系统设置',
  '/search': '全局搜索',

  // 其他
  '/profile': '个人中心',
};

// 动态路由映射 (模式匹配)
// 使用 :id 等参数占位符
export const dynamicBreadcrumbMap: Record<string, string> = {
  // 资产
  '/assets/:id': '资产详情',
  '/assets/:id/edit': '编辑资产',

  // 合同
  '/contract-center/:id': '合同关系明细',
  '/contract-center/:id/edit': '编辑合同关系',
  '/contract-groups/:id': '合同关系明细',
  '/contract-groups/:id/edit': '编辑合同关系',

  // 项目
  '/project/:id': '项目详情',
  '/project/:id/edit': '编辑项目',
  '/customers/:id': '客户详情',

  // 主体管理
  '/system/parties/:id': '主体详情',
};
