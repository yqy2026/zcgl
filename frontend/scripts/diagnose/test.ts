/**
 * 诊断工具测试脚本
 * 验证 Puppeteer 是否正确安装并能够启动浏览器
 */

import fs from 'fs';
import path from 'path';
import puppeteer from 'puppeteer';

async function testPuppeteer() {
  console.log('🧪 测试 Puppeteer 安装...\n');

  try {
    console.log('1️⃣ 启动浏览器...');
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    console.log('✅ 浏览器启动成功');

    console.log('\n2️⃣ 打开新页面...');
    const page = await browser.newPage();

    console.log('✅ 页面创建成功');

    console.log('\n3️⃣ 访问测试页面...');
    await page.goto('https://example.com', { waitUntil: 'networkidle0' });

    console.log('✅ 页面加载成功');

    console.log('\n4️⃣ 获取页面标题...');
    const title = await page.title();
    console.log(`   标题: ${title}`);

    console.log('\n5️⃣ 截图测试...');
    const screenshotPath = path.resolve(
      __dirname,
      '../../..',
      'test-results',
      'frontend',
      'diagnostics',
      'test-screenshot.png'
    );
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`✅ 截图保存成功: ${screenshotPath}`);

    console.log('\n6️⃣ 监听控制台...');
    page.on('console', (msg) => {
      console.log(`   [Console] ${msg.type()}: ${msg.text()}`);
    });

    // 执行一些 JavaScript
    await page.evaluate(() => {
      console.log('测试日志消息');
      console.warn('测试警告消息');
    });

    await page.waitForTimeout(1000);

    console.log('\n7️⃣ 关闭浏览器...');
    await browser.close();

    console.log('\n✅ 所有测试通过! Puppeteer 工作正常\n');
    console.log('💡 下一步: 运行 pnpm diagnose 开始实际诊断\n');

    process.exit(0);
  } catch (error) {
    console.error('\n❌ 测试失败:', error);
    console.error('\n可能的原因:');
    console.error('  1. Puppeteer 未正确安装');
    console.error('  2. Chromium 未下载');
    console.error('  3. 系统缺少必要的依赖\n');
    console.error('解决方案:');
    console.error('  pnpm install -D puppeteer\n');

    process.exit(1);
  }
}

testPuppeteer();
