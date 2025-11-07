/**
 * 统一的Mock配置
 * 用于解决测试中的模块导入问题
 */

// Mock API服务
export const mockApiClient = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  patch: jest.fn(),
}

// Mock Asset Service
export const mockAssetService = {
  getAssets: jest.fn(),
  getAssetById: jest.fn(),
  createAsset: jest.fn(),
  updateAsset: jest.fn(),
  deleteAsset: jest.fn(),
  searchAssets: jest.fn(),
  getAssetStats: jest.fn(),
  exportAssets: jest.fn(),
  importAssets: jest.fn(),
}

// Mock Auth Service
export const mockAuthService = {
  login: jest.fn(),
  logout: jest.fn(),
  register: jest.fn(),
  refreshToken: jest.fn(),
  getCurrentUser: jest.fn(),
  updateProfile: jest.fn(),
  changePassword: jest.fn(),
}

// Mock Statistics Service
export const mockStatisticsService = {
  getDashboardStats: jest.fn(),
  getAssetAnalytics: jest.fn(),
  getRentalStats: jest.fn(),
  getFinancialReports: jest.fn(),
  getOccupancyRate: jest.fn(),
}

// Mock Route Cache
export const mockRouteCache = {
  get: jest.fn(),
  set: jest.fn(),
  clear: jest.fn(),
  getMetrics: jest.fn(() => ({
    hitRate: 0.8,
    size: 100,
    totalHits: 1000,
    totalMisses: 200,
  })),
}

// Mock Route Performance Monitor
export const mockRoutePerformanceMonitor = jest.fn().mockImplementation(({ children }) => children)

// Mock PDF Import Service
export const mockPdfImportService = {
  uploadPDF: jest.fn(),
  processPDF: jest.fn(),
  extractFields: jest.fn(),
  validatePDF: jest.fn(),
  getProcessingStatus: jest.fn(),
}

// Mock Excel Service
export const mockExcelService = {
  downloadTemplate: jest.fn(),
  importExcel: jest.fn(),
  exportExcel: jest.fn(),
  validateExcel: jest.fn(),
}

// Mock Notification Service
export const mockNotificationService = {
  success: jest.fn(),
  error: jest.fn(),
  warning: jest.fn(),
  info: jest.fn(),
  confirm: jest.fn(),
}

// Mock React Router
export const mockNavigate = jest.fn()
export const mockLocation = {
  pathname: '/',
  search: '',
  hash: '',
  state: null,
}

// Mock Ant Design Message
export const mockMessage = {
  success: jest.fn(),
  error: jest.fn(),
  warning: jest.fn(),
  info: jest.fn(),
  loading: jest.fn(),
}

// Mock Ant Design Modal
export const mockModal = {
  confirm: jest.fn(),
  info: jest.fn(),
  success: jest.fn(),
  error: jest.fn(),
  warning: jest.fn(),
}

// Mock Ant Design Notification
export const mockNotification = {
  success: jest.fn(),
  error: jest.fn(),
  warning: jest.fn(),
  info: jest.fn(),
  open: jest.fn(),
}

// Mock User and Permission
export const mockUser = {
  id: 'test-user-id',
  username: 'testuser',
  email: 'test@example.com',
  fullName: 'Test User',
  role: 'user',
  isActive: true,
  permissions: ['asset.read', 'asset.create'],
  organization: {
    id: 'test-org-id',
    name: 'Test Organization',
  },
}

export const mockHasPermission = jest.fn(() => true)

// Mock Environment Variables
export const mockEnv = {
  VITE_API_BASE_URL: '/api/v1',
  VITE_API_TIMEOUT: '30000',
  NODE_ENV: 'test',
}

// Mock Common React Components
export const mockComponent = (name: string) => {
  return jest.fn().mockImplementation(({ children, ...props }) => (
    `<div data-testid="${name}" data-props="${JSON.stringify(props)}">${children}</div>`
  ))
}

// Mock Loading Components
export const mockLoadingSpinner = mockComponent('loading-spinner')
export const mockSkeletonLoader = mockComponent('skeleton-loader')

// Mock Error Components
export const mockErrorBoundary = mockComponent('error-boundary')
export const mockErrorPage = mockComponent('error-page')

// Mock Layout Components
export const mockAppLayout = mockComponent('app-layout')
export const mockAppHeader = mockComponent('app-header')
export const mockAppSidebar = mockComponent('app-sidebar')

// 设置默认的Mock返回值
export const setupDefaultMocks = () => {
  // API Client默认返回
  mockApiClient.get.mockResolvedValue({
    data: [],
    success: true,
    message: 'Success',
  })

  mockApiClient.post.mockResolvedValue({
    data: {},
    success: true,
    message: 'Created successfully',
  })

  mockApiClient.put.mockResolvedValue({
    data: {},
    success: true,
    message: 'Updated successfully',
  })

  mockApiClient.delete.mockResolvedValue({
    success: true,
    message: 'Deleted successfully',
  })

  // Asset Service默认返回
  mockAssetService.getAssets.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    pageSize: 20,
  })

  mockAssetService.createAsset.mockResolvedValue({
    ...mockAssetData,
    id: 'new-asset-id',
  })

  // Auth Service默认返回
  mockAuthService.login.mockResolvedValue({
    user: mockUser,
    token: 'mock-jwt-token',
    refreshToken: 'mock-refresh-token',
  })

  // Notification默认返回
  mockMessage.success.mockReturnValue('success-message-id')
  mockMessage.error.mockReturnValue('error-message-id')
}

// Mock Asset Data
export const mockAssetData = {
  id: 'test-asset-id',
  ownershipEntity: '测试集团',
  ownershipCategory: '企业自用',
  projectName: '测试项目',
  propertyName: '测试物业',
  address: '测试地址123号',
  actualPropertyArea: 1000.0,
  rentableArea: 800.0,
  rentedArea: 600.0,
  ownershipStatus: '已确权',
  propertyNature: '经营性',
  usageStatus: '出租',
  businessCategory: '商业',
  isLitigated: false,
  includeInOccupancyRate: true,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
}

// 清理所有Mock
export const clearAllMocks = () => {
  jest.clearAllMocks()

  // 重新设置默认Mock
  setupDefaultMocks()
}

// 导出所有Mock的配置对象
export const mocks = {
  apiClient: mockApiClient,
  assetService: mockAssetService,
  authService: mockAuthService,
  statisticsService: mockStatisticsService,
  routeCache: mockRouteCache,
  routePerformanceMonitor: mockRoutePerformanceMonitor,
  pdfImportService: mockPdfImportService,
  excelService: mockExcelService,
  notificationService: mockNotificationService,
  navigate: mockNavigate,
  location: mockLocation,
  message: mockMessage,
  modal: mockModal,
  notification: mockNotification,
  user: mockUser,
  hasPermission: mockHasPermission,
  env: mockEnv,
  component: mockComponent,
  loadingSpinner: mockLoadingSpinner,
  skeletonLoader: mockSkeletonLoader,
  errorBoundary: mockErrorBoundary,
  errorPage: mockErrorPage,
  appLayout: mockAppLayout,
  appHeader: mockAppHeader,
  appSidebar: mockAppSidebar,
}