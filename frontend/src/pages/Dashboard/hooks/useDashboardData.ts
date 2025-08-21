import { useQuery } from '@tanstack/react-query'

// 模拟获取仪表板数据
const fetchDashboardData = async () => {
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  return {
    metrics: {
      totalAssets: 156,
      totalArea: 125000,
      occupancyRate: 78.4,
      monthlyRevenue: 2850000,
      rentedAssets: 136,
      vacantAssets: 20,
    },
    todoItems: [
      {
        id: '1',
        title: '审核新增资产申请',
        description: '珠江新城写字楼项目',
        priority: 'high',
        dueDate: '2024-01-20',
        status: 'pending',
      },
      {
        id: '2',
        title: '更新租赁合同',
        description: '示例科技有限公司合同到期',
        priority: 'medium',
        dueDate: '2024-01-25',
        status: 'pending',
      },
      {
        id: '3',
        title: '物业维护检查',
        description: '工业园区B区设施检查',
        priority: 'low',
        dueDate: '2024-01-30',
        status: 'pending',
      },
    ],
    chartData: {
      propertyTypes: [
        { name: '写字楼', value: 45, color: '#1890ff' },
        { name: '商业', value: 32, color: '#52c41a' },
        { name: '工业', value: 28, color: '#faad14' },
        { name: '住宅', value: 35, color: '#722ed1' },
        { name: '其他', value: 16, color: '#eb2f96' },
      ],
      occupancyTrend: [
        { month: '1月', rate: 75.2 },
        { month: '2月', rate: 76.8 },
        { month: '3月', rate: 78.1 },
        { month: '4月', rate: 77.5 },
        { month: '5月', rate: 78.9 },
        { month: '6月', rate: 78.4 },
      ],
    },
    recentActivities: [
      {
        id: '1',
        title: '新增资产',
        description: '添加了示例商业大厦C座',
        time: '2小时前',
        icon: '🏢',
      },
      {
        id: '2',
        title: '更新出租信息',
        description: '更新了工业园区A区的租户信息',
        time: '4小时前',
        icon: '📝',
      },
      {
        id: '3',
        title: '合同到期提醒',
        description: '示例科技有限公司合同将于下月到期',
        time: '6小时前',
        icon: '⏰',
      },
      {
        id: '4',
        title: '数据导入',
        description: '成功导入45条资产记录',
        time: '1天前',
        icon: '📊',
      },
    ],
  }
}

export const useDashboardData = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardData,
  })

  return {
    metrics: data?.metrics,
    todoItems: data?.todoItems || [],
    chartData: data?.chartData,
    recentActivities: data?.recentActivities || [],
    isLoading,
    error,
  }
}