/**
 * Playwright 全局测试设置
 * 在所有测试运行前执行的初始化工作
 */

import { chromium, FullConfig } from '@playwright/test';
import path from 'path';
import fs from 'fs';

async function globalSetup(config: FullConfig) {
  console.log('🚀 开始Playwright全局设置...');

  const testResultsDir = path.join(__dirname, 'test-results');
  const reportsDir = path.join(__dirname, 'reports');
  const storageDir = path.join(__dirname, 'storage');

  // 创建必要的目录
  [testResultsDir, reportsDir, storageDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`📁 创建目录: ${dir}`);
    }
  });

  // 生成测试用户认证状态
  console.log('🔐 生成用户认证状态...');

  const browser = await chromium.launch();
  const context = await browser.newContext();

  // 生成管理员用户状态
  const adminContext = await browser.newContext();
  const adminPage = await adminContext.newPage();
  await generateUserState(adminPage, {
    username: 'admin',
    password: 'admin123',
    storageFile: path.join(storageDir, 'admin-state.json')
  });

  // 生成资产管理员状态
  const assetManagerContext = await browser.newContext();
  const assetManagerPage = await assetManagerContext.newPage();
  await generateUserState(assetManagerPage, {
    username: 'asset_manager',
    password: 'manager123',
    storageFile: path.join(storageDir, 'asset-manager-state.json')
  });

  // 生成资产查看员状态
  const assetViewerContext = await browser.newContext();
  const assetViewerPage = await assetViewerContext.newPage();
  await generateUserState(assetViewerPage, {
    username: 'asset_viewer',
    password: 'viewer123',
    storageFile: path.join(storageDir, 'asset-viewer-state.json')
  });

  await adminContext.close();
  await assetManagerContext.close();
  await assetViewerContext.close();
  await browser.close();

  // 创建测试数据文件
  console.log('📊 创建测试数据文件...');
  await createTestFixtures();

  // 设置环境变量
  process.env.TEST_BASE_URL = config.webServer?.url || 'http://localhost:5173';
  process.env.TEST_TIMEOUT = '60000';

  console.log('✅ Playwright全局设置完成');
}

async function generateUserState(page: any, user: { username: string; password: string; storageFile: string }) {
  const baseURL = process.env.BASE_URL || 'http://localhost:5173';

  try {
    // 等待应用启动
    await page.goto(baseURL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

    // 检查是否已经登录
    const isLoggedIn = await page.locator('[data-testid="user-menu"]').isVisible().catch(() => false);

    if (!isLoggedIn) {
      // 执行登录
      await page.click('[data-testid="login-button"]');
      await page.waitForSelector('[data-testid="login-form"]');

      await page.fill('[data-testid="username-input"]', user.username);
      await page.fill('[data-testid="password-input"]', user.password);
      await page.click('[data-testid="submit-login"]');

      // 等待登录成功
      await page.waitForSelector('[data-testid="user-menu"]', { timeout: 10000 });
    }

    // 保存认证状态
    const storageState = await page.context().storageState();
    fs.writeFileSync(user.storageFile, JSON.stringify(storageState, null, 2));

    console.log(`✅ 生成用户状态文件: ${user.storageFile}`);
  } catch (error) {
    console.warn(`⚠️ 生成用户状态失败: ${user.username}`, error);

    // 创建一个空的存储状态文件
    const emptyState = {
      cookies: [],
      origins: []
    };
    fs.writeFileSync(user.storageFile, JSON.stringify(emptyState, null, 2));
  }
}

async function createTestFixtures() {
  const fixturesDir = path.join(__dirname, 'fixtures');
  if (!fs.existsSync(fixturesDir)) {
    fs.mkdirSync(fixturesDir, { recursive: true });
  }

  // 创建Excel测试文件
  await createSampleExcelFile(fixturesDir);

  // 创建PDF测试文件
  await createSamplePDFFile(fixturesDir);

  // 创建图片测试文件
  await createSampleImageFiles(fixturesDir);
}

async function createSampleExcelFile(dir: string) {
  const excelPath = path.join(dir, 'sample_assets.xlsx');

  // 这里应该创建一个真实的Excel文件
  // 由于我们在Node.js环境中，可以使用xlsx库
  try {
    const XLSX = require('xlsx');

    const workbook = XLSX.utils.book_new();

    // 创建测试数据
    const testData = [
      ['物业名称', '权属方', '地址', '权属状态', '物业性质', '使用状态', '土地面积', '实际房产面积', '可出租面积', '已出租面积', '月租金'],
      ['测试大厦A', '测试公司A', '北京市朝阳区测试路1号', '已确权', '商业用途', '使用中', '10000', '8000', '7000', '6300', '700000'],
      ['测试大厦B', '测试公司B', '北京市海淀区测试路2号', '已确权', '办公用途', '出租', '8000', '6500', '5500', '4400', '550000'],
      ['测试大厦C', '测试公司C', '北京市西城区测试路3号', '已确权', '工业用途', '空置', '12000', '10000', '8500', '0', '0']
    ];

    const worksheet = XLSX.utils.aoa_to_sheet(testData);
    XLSX.utils.book_append_sheet(workbook, worksheet, '资产数据');

    XLSX.writeFile(workbook, excelPath);
    console.log(`✅ 创建Excel测试文件: ${excelPath}`);
  } catch (error) {
    console.warn('⚠️ 创建Excel文件失败，请确保已安装xlsx库:', error);
  }
}

async function createSamplePDFFile(dir: string) {
  const pdfPath = path.join(dir, 'sample_contract.pdf');

  // 创建一个简单的文本文件作为PDF占位符
  const sampleContent = `
合同编号: LC2024001
合同名称: 租赁合同
甲方: 测试公司A
乙方: 测试租户B
租赁面积: 1000平方米
月租金: 100000元
租赁期限: 2024-01-01 至 2026-12-31

这是一个PDF文件的示例内容。
在实际测试中，应该使用真实的PDF文件。
`;

  fs.writeFileSync(pdfPath.replace('.pdf', '.txt'), sampleContent);
  console.log(`✅ 创建PDF测试文件占位符: ${pdfPath.replace('.pdf', '.txt')}`);
}

async function createSampleImageFiles(dir: string) {
  // 创建图片目录
  const imagesDir = path.join(dir, 'images');
  if (!fs.existsSync(imagesDir)) {
    fs.mkdirSync(imagesDir);
  }

  // 图片文件列表
  const imageFiles = [
    'building-photo-1.jpg',
    'building-photo-2.png',
    'floor-plan.pdf',
    'location-map.png'
  ];

  imageFiles.forEach(filename => {
    const imagePath = path.join(imagesDir, filename);
    const placeholderContent = `这是 ${filename} 的占位符文件。
在实际测试中，应该使用真实的图片文件。`;

    fs.writeFileSync(imagePath.replace(/\.(jpg|png|pdf)$/, '.txt'), placeholderContent);
  });

  console.log(`✅ 创建图片测试文件占位符: ${imagesDir}`);
}

export default globalSetup;