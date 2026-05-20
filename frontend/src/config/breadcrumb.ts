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
  '/assets/analytics-simple': '简易分析',

  // 财务台账
  '/finance': '财务台账',
  '/finance/ledger': '财务台账',
  '/finance/billing': '账单管理',
  '/finance/payment': '收付款记录',
  // 兼容旧路径
  '/financial': '财务台账',
  '/financial/billing': '账单管理',
  '/financial/payment': '收付款记录',

  // 统计分析
  '/analytics': '经营分析',
  '/analysis': '分析统计',
  '/analysis/overview': '概览统计',
  '/analysis/report': '报表生成',

  // 产权证管理
  '/property-certificates': '产权证管理',
  '/property-certificates/import': '导入产权证',

  // 权属方管理
  '/ownership': '权属方管理',

  // 项目运营
  '/project': '项目运营',

  // 合同中心
  '/contract-center': '合同中心',
  '/contract-center/import': 'PDF导入',
  '/contract-center/new': '新建合同关系',
  '/contract-groups': '合同关系管理',
  '/contract-groups/import': 'PDF导入',
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

  // 产权证
  '/property-certificates/:id': '产权证详情',

  // 权属方
  '/ownership/:id': '权属方详情',
  '/ownership/:id/edit': '编辑权属方',

  // 项目
  '/project/:id': '项目详情',
  '/project/:id/edit': '编辑项目',
  '/customers/:id': '客户详情',

  // 主体管理
  '/system/parties/:id': '主体详情',
};
