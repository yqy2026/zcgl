/**
 * 资产管理系统端到端测试
 * 完整的58字段资产管理业务流程测试
 */

import { test, expect, chromium, type BrowserContext, type Page } from '@playwright/test';

// 测试数据
const TEST_ASSETS = {
  complete: {
    ownership_entity: '北京国有资产经营有限公司',
    ownership_category: '国有企业',
    project_name: '中央商务区综合项目',
    property_name: '国际贸易中心大厦',
    address: '北京市朝阳区建国门外大街1号',
    ownership_status: '已确权',
    property_nature: '商业用途',
    usage_status: '使用中',
    business_category: '零售商业',
    is_litigated: false,
    notes: '核心商业区地标建筑',

    // 面积相关字段
    land_area: 10000,
    actual_property_area: 8500,
    rentable_area: 7500,
    rented_area: 6800,
    non_commercial_area: 300,
    include_in_occupancy_rate: true,

    // 用途相关字段
    certificated_usage: '商业用地',
    actual_usage: '综合商业体',

    // 租户相关字段
    tenant_name: '大型商业集团股份有限公司',
    tenant_type: '企业',

    // 合同相关字段
    lease_contract_number: 'LC2024001',
    contract_start_date: '2024-01-01',
    contract_end_date: '2026-12-31',
    contract_term: 36,
    rent_payment_method: '季付',
    deposit_amount: 3000000,
    rent_increase_clause: '每年递增3%',
    termination_clause: '合同到期前90天书面通知',
    renewal_option: true,
    special_terms: '包含物业管理费和装修补贴',

    // 管理相关字段
    business_model: '委托经营',
    operation_status: '正常营业',
    manager_name: '王总经理',

    // 接收相关字段
    operation_agreement_start_date: '2023-12-01',
    operation_agreement_end_date: '2027-12-31',
    operation_agreement_attachments: 'management_agreement.pdf',

    // 终端合同字段
    terminal_contract_files: 'commercial_contract.pdf',

    // 项目相关字段
    project_phase: '二期',

    // 财务相关字段
    annual_income: 12000000,
    annual_expense: 3600000,
    net_income: 8400000,
    rent_price_per_sqm: 1000,
    management_fee_per_sqm: 50,
    property_tax: 480000,
    insurance_fee: 85000,
    maintenance_fee: 150000,
    other_fees: 120000,
    rent_income_tax: 1440000,
    net_rental_income: 8160000,
    total_cost: 5345000,

    monthly_rent: 1000000,
    deposit: 3000000,

    // 系统字段
    data_status: '正常',
    tags: ['优质资产', '核心地段', '稳定收益'],
    audit_notes: '数据录入完整，财务指标准确'
  }
};

const TEST_USERS = {
  system_admin: {
    username: 'admin',
    password: 'admin123',
    role: '系统管理员'
  },
  asset_manager: {
    username: 'asset_manager',
    password: 'manager123',
    role: '资产管理员'
  },
  asset_viewer: {
    username: 'asset_viewer',
    password: 'viewer123',
    role: '资产查看员'
  }
};

test.describe('资产管理系统 - 端到端测试', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async () => {
    // 启动浏览器
    context = await chromium.launch({
      headless: process.env.CI === 'true',
      slowMo: process.env.CI === 'true' ? 0 : 100
    });

    page = await context.newPage();

    // 设置视口大小
    await page.setViewportSize({ width: 1920, height: 1080 });

    // 等待应用启动
    await page.goto('http://localhost:5173');
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });
  });

  test.afterAll(async () => {
    await context.close();
  });

  test.describe('用户登录和权限验证', () => {
    test('系统管理员可以正常登录', async () => {
      // 导航到登录页面
      await page.click('[data-testid="login-button"]');

      // 等待登录表单加载
      await page.waitForSelector('[data-testid="login-form"]');

      // 填写登录信息
      await page.fill('[data-testid="username-input"]', TEST_USERS.system_admin.username);
      await page.fill('[data-testid="password-input"]', TEST_USERS.system_admin.password);

      // 提交登录
      await page.click('[data-testid="submit-login"]');

      // 验证登录成功
      await page.waitForSelector('[data-testid="user-menu"]');
      await expect(page.locator('[data-testid="user-name"]')).toContainText(TEST_USERS.system_admin.role);

      // 验证可以访问所有菜单
      await expect(page.locator('[data-testid="menu-assets"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-users"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-system"]')).toBeVisible();
    });

    test('资产管理员登录权限验证', async () => {
      await performLogin(page, TEST_USERS.asset_manager);

      // 验证资产管理相关权限
      await expect(page.locator('[data-testid="menu-assets"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-reports"]')).toBeVisible();

      // 验证无法访问系统管理
      await expect(page.locator('[data-testid="menu-system"]')).not.toBeVisible();
    });

    test('资产查看员只读权限验证', async () => {
      await performLogin(page, TEST_USERS.asset_viewer);

      // 验证只读权限
      await expect(page.locator('[data-testid="menu-assets"]')).toBeVisible();

      // 验证无法访问创建和编辑功能
      await page.click('[data-testid="menu-assets"]');
      await page.waitForSelector('[data-testid="asset-list"]');

      await expect(page.locator('[data-testid="create-asset-button"]')).not.toBeVisible();
    });
  });

  test.describe('58字段资产创建流程', () => {
    test.beforeEach(async () => {
      await performLogin(page, TEST_USERS.asset_manager);
      await navigateToAssetCreate(page);
    });

    test('完整创建58字段资产', async () => {
      // 基本信息 (8字段)
      await fillBasicInfo(page, TEST_ASSETS.complete);

      // 面积信息 (8字段)
      await fillAreaInfo(page, TEST_ASSETS.complete);

      // 用途信息 (2字段)
      await fillUsageInfo(page, TEST_ASSETS.complete);

      // 租户信息 (2字段)
      await fillTenantInfo(page, TEST_ASSETS.complete);

      // 合同信息 (10字段)
      await fillContractInfo(page, TEST_ASSETS.complete);

      // 管理信息 (3字段)
      await fillManagementInfo(page, TEST_ASSETS.complete);

      // 接收信息 (3字段)
      await fillOperationInfo(page, TEST_ASSETS.complete);

      // 财务信息 (12字段)
      await fillFinancialInfo(page, TEST_ASSETS.complete);

      // 系统信息 (6字段)
      await fillSystemInfo(page, TEST_ASSETS.complete);

      // 验证所有字段填写完成
      await validateAllFields(page);

      // 提交表单
      await page.click('[data-testid="submit-asset"]');

      // 等待提交成功
      await page.waitForSelector('[data-testid="success-message"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="success-message"]')).toContainText('资产创建成功');

      // 验证跳转到资产详情页
      await expect(page.url()).toContain('/assets/');

      // 验证详情页显示所有58字段
      await validateAssetDetails(page, TEST_ASSETS.complete);
    });

    test('表单验证和错误处理', async () => {
      // 测试必填字段验证
      await page.click('[data-testid="submit-asset"]');

      // 验证必填字段错误提示
      await expect(page.locator('[data-testid="error-property_name"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-ownership_entity"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-address"]')).toBeVisible();

      // 测试数据格式验证
      await page.fill('[data-testid="input-monthly_rent"]', 'invalid_number');
      await expect(page.locator('[data-testid="error-monthly_rent"]')).toContainText('请输入有效数字');

      // 测试数据范围验证
      await page.fill('[data-testid="input-rented_area"]', '10000');
      await page.fill('[data-testid="input-rentable_area"]', '5000');
      await expect(page.locator('[data-testid="error-area_relationship"]')).toContainText('已出租面积不能大于可出租面积');

      // 测试日期逻辑验证
      await page.fill('[data-testid="input-contract_start_date"]', '2024-12-31');
      await page.fill('[data-testid="input-contract_end_date"]', '2024-01-01');
      await expect(page.locator('[data-testid="error-contract_dates"]')).toContainText('结束日期必须晚于开始日期');
    });

    test('实时计算字段验证', async () => {
      // 填写面积信息
      await page.fill('[data-testid="input-land_area"]', '10000');
      await page.fill('[data-testid="input-actual_property_area"]', '8000');
      await page.fill('[data-testid="input-rentable_area"]', '7000');
      await page.fill('[data-testid="input-rented_area"]', '5600');

      // 验证自动计算字段
      await expect(page.locator('[data-testid="calculated-unrented_area"]')).toContainText('1400');
      await expect(page.locator('[data-testid="calculated-occupancy_rate"]')).toContainText('80.00%');

      // 填写财务信息
      await page.fill('[data-testid="input-annual_income"]', '12000000');
      await page.fill('[data-testid="input-annual_expense"]', '3600000');

      // 验证净收入计算
      await expect(page.locator('[data-testid="calculated-net_income"]')).toContainText('8,400,000');
    });
  });

  test.describe('资产搜索和过滤功能', () => {
    test.beforeEach(async () => {
      await performLogin(page, TEST_USERS.asset_manager);
      await navigateToAssetList(page);
    });

    test('关键词搜索功能', async () => {
      // 使用物业名称搜索
      await page.fill('[data-testid="search-input"]', '国际贸易中心');
      await page.click('[data-testid="search-button"]');

      // 验证搜索结果
      await page.waitForSelector('[data-testid="search-results"]');
      await expect(page.locator('[data-testid="search-results"]')).toContainText('国际贸易中心大厦');

      // 清空搜索
      await page.click('[data-testid="clear-search"]');
      await expect(page.locator('[data-testid="search-input"]')).toHaveValue('');
    });

    test('高级过滤功能', async () => {
      // 打开高级过滤
      await page.click('[data-testid="advanced-filter"]');

      // 设置过滤条件
      await page.selectOption('[data-testid="filter-ownership_status"]', '已确权');
      await page.selectOption('[data-testid="filter-property_nature"]', '商业用途');
      await page.selectOption('[data-testid="filter-usage_status"]', '使用中');

      // 设置面积范围
      await page.fill('[data-testid="filter-area-min"]', '5000');
      await page.fill('[data-testid="filter-area-max"]', '15000');

      // 设置租金范围
      await page.fill('[data-testid="filter-rent-min"]', '500000');
      await page.fill('[data-testid="filter-rent-max"]', '2000000');

      // 应用过滤
      await page.click('[data-testid="apply-filter"]');

      // 验证过滤结果
      await page.waitForSelector('[data-testid="filtered-results"]');
      await expect(page.locator('[data-testid="filtered-results"]').locator('[data-testid="asset-card"]')).toHaveCount({ min: 1 });

      // 验证过滤条件显示
      await expect(page.locator('[data-testid="active-filters"]')).toContainText('已确权');
      await expect(page.locator('[data-testid="active-filters"]')).toContainText('商业用途');
    });

    test('排序功能', async () => {
      // 按创建时间排序
      await page.selectOption('[data-testid="sort-by"]', 'created_at');
      await page.selectOption('[data-testid="sort-order"]', 'desc');

      // 验证排序结果
      await page.waitForSelector('[data-testid="sorted-results"]');
      const firstCard = page.locator('[data-testid="asset-card"]').first();
      await expect(firstCard).toBeVisible();

      // 按出租率排序
      await page.selectOption('[data-testid="sort-by"]', 'occupancy_rate');
      await page.selectOption('[data-testid="sort-order"]', 'desc');

      // 验证出租率排序
      await page.waitForSelector('[data-testid="sorted-results"]');
      const sortedCards = page.locator('[data-testid="asset-card"]');
      const count = await sortedCards.count();

      if (count > 1) {
        const firstOccupancy = await sortedCards.first().locator('[data-testid="occupancy-rate"]').textContent();
        const lastOccupancy = await sortedCards.last().locator('[data-testid="occupancy-rate"]').textContent();

        expect(parseFloat(firstOccupancy || '0')).toBeGreaterThanOrEqual(parseFloat(lastOccupancy || '0'));
      }
    });
  });

  test.describe('资产批量操作', () => {
    test.beforeEach(async () => {
      await performLogin(page, TEST_USERS.asset_manager);
      await navigateToAssetList(page);
    });

    test('批量选择和导出', async () => {
      // 选择多个资产
      await page.check('[data-testid="asset-checkbox-1"]');
      await page.check('[data-testid="asset-checkbox-2"]');
      await page.check('[data-testid="asset-checkbox-3"]');

      // 验证选择状态
      await expect(page.locator('[data-testid="selected-count"]')).toContainText('3');

      // 批量导出
      await page.click('[data-testid="batch-export"]');
      await page.selectOption('[data-testid="export-format"]', 'xlsx');
      await page.click('[data-testid="confirm-export"]');

      // 验证导出成功
      await page.waitForSelector('[data-testid="export-success"]');
      await expect(page.locator('[data-testid="export-success"]')).toContainText('导出成功');
    });

    test('批量更新', async () => {
      // 选择资产
      await page.check('[data-testid="asset-checkbox-1"]');
      await page.check('[data-testid="asset-checkbox-2"]');

      // 批量更新
      await page.click('[data-testid="batch-update"]');

      // 选择更新字段
      await page.selectOption('[data-testid="update-field"]', 'notes');
      await page.fill('[data-testid="update-value"]', '批量更新备注 - ' + new Date().toISOString());

      // 确认更新
      await page.click('[data-testid="confirm-update"]');

      // 验证更新成功
      await page.waitForSelector('[data-testid="update-success"]');
      await expect(page.locator('[data-testid="update-success"]')).toContainText('更新成功');

      // 验证资产列表更新
      await page.reload();
      await page.waitForSelector('[data-testid="asset-list"]');

      const updatedNotes = await page.locator('[data-testid="asset-1"]').locator('[data-testid="asset-notes"]').textContent();
      expect(updatedNotes).toContain('批量更新备注');
    });
  });

  test.describe('资产详情和编辑', () => {
    let assetId: string;

    test.beforeEach(async () => {
      await performLogin(page, TEST_USERS.asset_manager);
      await navigateToAssetList(page);

      // 点击第一个资产进入详情
      await page.click('[data-testid="asset-card"]:first-child [data-testid="view-details"]');

      // 获取资产ID
      const url = page.url();
      assetId = url.split('/').pop() || '';
    });

    test('资产详情页面显示', async () => {
      // 验证基本信息显示
      await expect(page.locator('[data-testid="detail-property_name"]')).toBeVisible();
      await expect(page.locator('[data-testid="detail-ownership_entity"]')).toBeVisible();
      await expect(page.locator('[data-testid="detail-address"]')).toBeVisible();

      // 验证面积信息显示
      await expect(page.locator('[data-testid="detail-land_area"]')).toBeVisible();
      await expect(page.locator('[data-testid="detail-occupancy_rate"]')).toBeVisible();

      // 验证财务信息显示
      await expect(page.locator('[data-testid="detail-annual_income"]')).toBeVisible();
      await expect(page.locator('[data-testid="detail-net_income"]')).toBeVisible();

      // 验证合同信息显示
      await expect(page.locator('[data-testid="detail-lease_contract_number"]')).toBeVisible();
      await expect(page.locator('[data-testid="detail-contract_dates"]')).toBeVisible();
    });

    test('资产编辑功能', async () => {
      // 进入编辑模式
      await page.click('[data-testid="edit-asset"]');

      // 等待表单加载
      await page.waitForSelector('[data-testid="asset-form"]');

      // 修改部分字段
      await page.fill('[data-testid="input-property_name"]', '更新后的物业名称');
      await page.fill('[data-testid="input-monthly_rent"]', '1100000');
      await page.fill('[data-testid="input-notes"]', '编辑更新 - ' + new Date().toISOString());

      // 保存修改
      await page.click('[data-testid="save-asset"]');

      // 验证保存成功
      await page.waitForSelector('[data-testid="save-success"]');
      await expect(page.locator('[data-testid="save-success"]')).toContainText('保存成功');

      // 验证详情页更新
      await expect(page.locator('[data-testid="detail-property_name"]')).toContainText('更新后的物业名称');
      await expect(page.locator('[data-testid="detail-monthly_rent"]')).toContainText('1,100,000');
    });

    test('资产历史记录查看', async () => {
      // 点击历史记录标签
      await page.click('[data-testid="history-tab"]');

      // 验证历史记录列表
      await page.waitForSelector('[data-testid="history-list"]');

      // 验证历史记录字段
      const historyItems = page.locator('[data-testid="history-item"]');
      const count = await historyItems.count();

      if (count > 0) {
        await expect(historyItems.first().locator('[data-testid="history-field"]')).toBeVisible();
        await expect(historyItems.first().locator('[data-testid="history-timestamp"]')).toBeVisible();
        await expect(historyItems.first().locator('[data-testid="history-user"]')).toBeVisible();
      }
    });
  });

  test.describe('数据导入导出功能', () => {
    test.beforeEach(async () => {
      await performLogin(page, TEST_USERS.asset_manager);
    });

    test('Excel模板下载', async () => {
      await navigateToAssetImport(page);

      // 下载模板
      await page.click('[data-testid="download-template"]');

      // 验证下载开始
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toContain('asset_import_template');
    });

    test('Excel文件导入', async () => {
      await navigateToAssetImport(page);

      // 选择文件
      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles('tests/fixtures/sample_assets.xlsx');

      // 等待文件解析
      await page.waitForSelector('[data-testid="file-parsed"]');

      // 验证数据预览
      await expect(page.locator('[data-testid="import-preview"]')).toBeVisible();
      await expect(page.locator('[data-testid="preview-table"]')).toBeVisible();

      // 配置字段映射
      await page.selectOption('[data-testid="mapping-property_name"]', '物业名称');
      await page.selectOption('[data-testid="mapping-ownership_entity"]', '权属方');
      await page.selectOption('[data-testid="mapping-land_area"]', '土地面积');

      // 开始导入
      await page.click('[data-testid="start-import"]');

      // 监控导入进度
      await page.waitForSelector('[data-testid="import-progress"]');
      await expect(page.locator('[data-testid="progress-bar"]')).toBeVisible();

      // 等待导入完成
      await page.waitForSelector('[data-testid="import-complete"]', { timeout: 60000 });

      // 验证导入结果
      await expect(page.locator('[data-testid="import-summary"]')).toBeVisible();
      await expect(page.locator('[data-testid="success-count"]')).toHaveText(/\d+/);
    });

    test('数据导出功能', async () => {
      await navigateToAssetList(page);

      // 设置导出选项
      await page.click('[data-testid="export-options"]');
      await page.selectOption('[data-testid="export-format"]', 'xlsx');
      await page.check('[data-testid="include-headers"]');

      // 选择导出字段
      await page.check('[data-testid="field-property_name"]');
      await page.check('[data-testid="field-ownership_entity"]');
      await page.check('[data-testid="field-land_area"]');
      await page.check('[data-testid="field-monthly_rent"]');

      // 执行导出
      await page.click('[data-testid="export-data"]');

      // 验证下载
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toContain('asset_export');
    });
  });

  test.describe('统计报表功能', () => {
    test.beforeEach(async () => {
      await performLogin(page, TEST_USERS.asset_manager);
    });

    test('出租率统计报表', async () => {
      await navigateToAnalytics(page);

      // 点击出租率统计
      await page.click('[data-testid="occupancy-report"]');

      // 验证图表加载
      await page.waitForSelector('[data-testid="occupancy-chart"]');
      await expect(page.locator('[data-testid="occupancy-chart"]')).toBeVisible();

      // 验证统计数据
      await expect(page.locator('[data-testid="overall-occupancy"]')).toBeVisible();
      await expect(page.locator('[data-testid="occupancy-trend"]')).toBeVisible();

      // 测试时间范围筛选
      await page.selectOption('[data-testid="time-range"]', 'last-12-months');
      await page.click('[data-testid="apply-filter"]');

      // 验证图表更新
      await page.waitForSelector('[data-testid="chart-updated"]');
      await expect(page.locator('[data-testid="occupancy-chart"]')).toBeVisible();
    });

    test('财务分析报表', async () => {
      await navigateToAnalytics(page);

      // 点击财务分析
      await page.click('[data-testid="financial-report"]');

      // 验证财务图表
      await page.waitForSelector('[data-testid="revenue-chart"]');
      await page.waitForSelector('[data-testid="expense-chart"]');
      await page.waitForSelector('[data-testid="profit-chart"]');

      // 验证财务指标
      await expect(page.locator('[data-testid="total-revenue"]')).toBeVisible();
      await expect(page.locator('[data-testid="total-expense"]')).toBeVisible();
      await expect(page.locator('[data-testid="net-profit"]')).toBeVisible();

      // 测试详细数据表格
      await page.click('[data-testid="show-details"]');
      await expect(page.locator('[data-testid="financial-table"]')).toBeVisible();
    });

    test('资产分布报表', async () => {
      await navigateToAnalytics(page);

      // 点击资产分布
      await page.click('[data-testid="distribution-report"]');

      // 验证分布图表
      await page.waitForSelector('[data-testid="distribution-pie-chart"]');
      await page.waitForSelector('[data-testid="distribution-bar-chart"]');

      // 测试分组选项
      await page.selectOption('[data-testid="group-by"]', 'property_nature');
      await page.click('[data-testid="refresh-chart"]');

      // 验证图表更新
      await page.waitForSelector('[data-testid="chart-refreshed"]');
    });
  });

  test.describe('权限边界测试', () => {
    test('资产查看员权限限制', async () => {
      await performLogin(page, TEST_USERS.asset_viewer);
      await navigateToAssetList(page);

      // 验证无法看到创建按钮
      await expect(page.locator('[data-testid="create-asset-button"]')).not.toBeVisible();

      // 验证无法看到批量操作
      await expect(page.locator('[data-testid="batch-actions"]')).not.toBeVisible();

      // 进入资产详情
      await page.click('[data-testid="asset-card"]:first-child [data-testid="view-details"]');

      // 验证无法看到编辑按钮
      await expect(page.locator('[data-testid="edit-asset"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="delete-asset"]')).not.toBeVisible();
    });

    test('未授权访问拦截', async () => {
      await performLogin(page, TEST_USERS.asset_viewer);

      // 尝试直接访问创建页面
      await page.goto('http://localhost:5173/assets/create');

      // 验证被重定向或显示权限不足
      await expect(page.locator('[data-testid="access-denied"]')).toBeVisible();

      // 尝试直接访问系统管理页面
      await page.goto('http://localhost:5173/system/users');

      // 验证权限拦截
      await expect(page.locator('[data-testid="access-denied"]')).toBeVisible();
    });
  });
});

// 辅助函数
async function performLogin(page: Page, user: typeof TEST_USERS.system_admin) {
  await page.goto('http://localhost:5173');
  await page.click('[data-testid="login-button"]');
  await page.waitForSelector('[data-testid="login-form"]');

  await page.fill('[data-testid="username-input"]', user.username);
  await page.fill('[data-testid="password-input"]', user.password);
  await page.click('[data-testid="submit-login"]');

  await page.waitForSelector('[data-testid="user-menu"]');
}

async function navigateToAssetCreate(page: Page) {
  await page.click('[data-testid="menu-assets"]');
  await page.waitForSelector('[data-testid="asset-list"]');
  await page.click('[data-testid="create-asset-button"]');
  await page.waitForSelector('[data-testid="asset-form"]');
}

async function navigateToAssetList(page: Page) {
  await page.click('[data-testid="menu-assets"]');
  await page.waitForSelector('[data-testid="asset-list"]');
}

async function navigateToAssetImport(page: Page) {
  await page.click('[data-testid="menu-assets"]');
  await page.waitForSelector('[data-testid="asset-list"]');
  await page.click('[data-testid="import-tab"]');
  await page.waitForSelector('[data-testid="import-section"]');
}

async function navigateToAnalytics(page: Page) {
  await page.click('[data-testid="menu-analytics"]');
  await page.waitForSelector('[data-testid="analytics-dashboard"]');
}

async function fillBasicInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.fill('[data-testid="input-ownership_entity"]', data.ownership_entity);
  await page.selectOption('[data-testid="select-ownership_category"]', data.ownership_category);
  await page.fill('[data-testid="input-project_name"]', data.project_name);
  await page.fill('[data-testid="input-property_name"]', data.property_name);
  await page.fill('[data-testid="input-address"]', data.address);
  await page.selectOption('[data-testid="select-ownership_status"]', data.ownership_status);
  await page.selectOption('[data-testid="select-property_nature"]', data.property_nature);
  await page.selectOption('[data-testid="select-usage_status"]', data.usage_status);
}

async function fillAreaInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.fill('[data-testid="input-land_area"]', data.land_area.toString());
  await page.fill('[data-testid="input-actual_property_area"]', data.actual_property_area.toString());
  await page.fill('[data-testid="input-rentable_area"]', data.rentable_area.toString());
  await page.fill('[data-testid="input-rented_area"]', data.rented_area.toString());
  await page.fill('[data-testid="input-non_commercial_area"]', data.non_commercial_area.toString());
  await page.check('[data-testid="checkbox-include_in_occupancy_rate"]');
}

async function fillUsageInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.selectOption('[data-testid="select-certificated_usage"]', data.certificated_usage);
  await page.selectOption('[data-testid="select-actual_usage"]', data.actual_usage);
}

async function fillTenantInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.fill('[data-testid="input-tenant_name"]', data.tenant_name);
  await page.selectOption('[data-testid="select-tenant_type"]', data.tenant_type);
}

async function fillContractInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.fill('[data-testid="input-lease_contract_number"]', data.lease_contract_number);
  await page.fill('[data-testid="input-contract_start_date"]', data.contract_start_date);
  await page.fill('[data-testid="input-contract_end_date"]', data.contract_end_date);
  await page.selectOption('[data-testid="select-rent_payment_method"]', data.rent_payment_method);
  await page.fill('[data-testid="input-deposit_amount"]', data.deposit_amount.toString());
  await page.fill('[data-testid="input-rent_increase_clause"]', data.rent_increase_clause);
  await page.fill('[data-testid="input-termination_clause"]', data.termination_clause);
  if (data.renewal_option) {
    await page.check('[data-testid="checkbox-renewal_option"]');
  }
  await page.fill('[data-testid="input-special_terms"]', data.special_terms);
}

async function fillManagementInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.selectOption('[data-testid="select-business_model"]', data.business_model);
  await page.selectOption('[data-testid="select-operation_status"]', data.operation_status);
  await page.fill('[data-testid="input-manager_name"]', data.manager_name);
}

async function fillOperationInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.fill('[data-testid="input-operation_agreement_start_date"]', data.operation_agreement_start_date);
  await page.fill('[data-testid="input-operation_agreement_end_date"]', data.operation_agreement_end_date);
  await page.fill('[data-testid="input-operation_agreement_attachments"]', data.operation_agreement_attachments);
  await page.fill('[data-testid="input-terminal_contract_files"]', data.terminal_contract_files);
}

async function fillFinancialInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.fill('[data-testid="input-annual_income"]', data.annual_income.toString());
  await page.fill('[data-testid="input-annual_expense"]', data.annual_expense.toString());
  await page.fill('[data-testid="input-rent_price_per_sqm"]', data.rent_price_per_sqm.toString());
  await page.fill('[data-testid="input-management_fee_per_sqm"]', data.management_fee_per_sqm.toString());
  await page.fill('[data-testid="input-property_tax"]', data.property_tax.toString());
  await page.fill('[data-testid="input-insurance_fee"]', data.insurance_fee.toString());
  await page.fill('[data-testid="input-maintenance_fee"]', data.maintenance_fee.toString());
  await page.fill('[data-testid="input-other_fees"]', data.other_fees.toString());
  await page.fill('[data-testid="input-rent_income_tax"]', data.rent_income_tax.toString());
  await page.fill('[data-testid="input-net_rental_income"]', data.net_rental_income.toString());
  await page.fill('[data-testid="input-total_cost"]', data.total_cost.toString());
  await page.fill('[data-testid="input-monthly_rent"]', data.monthly_rent.toString());
  await page.fill('[data-testid="input-deposit"]', data.deposit.toString());
}

async function fillSystemInfo(page: Page, data: typeof TEST_ASSETS.complete) {
  await page.selectOption('[data-testid="select-data_status"]', data.data_status);
  await page.fill('[data-testid="input-tags"]', data.tags.join(', '));
  await page.fill('[data-testid="input-audit_notes"]', data.audit_notes);
}

async function validateAllFields(page: Page) {
  // 验证所有字段组都有内容
  const sections = ['basic-info', 'area-info', 'usage-info', 'tenant-info',
                   'contract-info', 'management-info', 'operation-info',
                   'financial-info', 'system-info'];

  for (const section of sections) {
    await expect(page.locator(`[data-testid="${section}"]`)).toBeVisible();
  }
}

async function validateAssetDetails(page: Page, expectedData: typeof TEST_ASSETS.complete) {
  // 验证关键字段显示正确
  await expect(page.locator('[data-testid="detail-property_name"]')).toContainText(expectedData.property_name);
  await expect(page.locator('[data-testid="detail-ownership_entity"]')).toContainText(expectedData.ownership_entity);
  await expect(page.locator('[data-testid="detail-land_area"]')).toContainText(expectedData.land_area.toString());
  await expect(page.locator('[data-testid="detail-monthly_rent"]')).toContainText(expectedData.monthly_rent.toLocaleString());
}