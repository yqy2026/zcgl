/**
 * PR #113 产品验收走查（代裁决）：登录 → 本月/物业/终端/上游/报送/档案/导入
 * 逐页程序化断言原型关键元素，截图存档。数字断言一律 page 内取值。
 */
import { chromium } from '@playwright/test';
import fs from 'node:fs';

const EXE = process.env.CHROME_EXE;
const BASE = 'http://localhost:5173';
const OUT = 'D:/work/zcgl/test-results/frontend/walkthrough-113';
fs.mkdirSync(OUT, { recursive: true });

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ' — ' + detail : ''}`);
};

const browser = await chromium.launch({ executablePath: EXE, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => {
  if (m.type() === 'error') errors.push('console: ' + m.text());
});

// 登录
await page.goto(BASE + '/login');
await page.waitForLoadState('networkidle');
await page.locator('input[type="text"], input[name="identifier"], input#identifier, input[name="username"]').first().fill('admin');
await page.locator('input[type="password"]').first().fill('admin123');
await Promise.all([
  page.waitForURL(u => !u.pathname.includes('/login'), { timeout: 20000 }),
  page.locator('button[type="submit"], button:has-text("登录")').first().click(),
]);
check('登录成功跳转', !page.url().includes('/login'), page.url());

// 1. 本月
const wbResponse = page.waitForResponse(r => r.url().includes('/monthly-workbench'), { timeout: 20000 }).catch(() => null);
await page.goto(BASE + '/asset-operations/monthly');
await wbResponse.then(r => { if (r) console.log('workbench status:', r.status()); });
await page.waitForTimeout(1500);
const headline = await page.locator('h1').first().textContent().catch(() => null);
check('本月页标题（本月还有 N 件 / 全部完成）', /本月还有|本月任务已全部完成/.test(headline ?? ''), (headline ?? '').trim());
for (const card of ['支付', '收取', '对账', '报送']) {
  const found = await page.getByRole('region', { name: new RegExp(card) }).count()
    || await page.locator(`section:has-text("${card}")`).count();
  check(`本月任务卡「${card}」`, found > 0, `count=${found}`);
}
check('本月随时处理区', (await page.getByText('随时处理').count()) > 0);
const progressText = await page.locator('text=/完成进度/').count();
check('本月完成进度条', progressText > 0);
await page.screenshot({ path: `${OUT}/1-monthly.png`, fullPage: true });

// 2. 物业
await page.goto(BASE + '/asset-operations/units');
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1500);
check('物业页标题', (await page.locator('h1:has-text("物业")').count()) > 0);
const segTexts = await page.locator('.ant-segmented-item-label').allTextContents();
check('物业分段筛选带数量', /全部|纳入报送|空置可租|不可租|缺产权证/.test(segTexts.join('|')), segTexts.join(' / ').slice(0, 120));
const searchPlaceholder = await page.locator('input[placeholder*="搜地址"]').count();
check('物业搜索占位符（地址/单元/租户/证号）', searchPlaceholder > 0);
const hasExport = await page.locator('button:has-text("导出台账")').count();
check('物业导出台账按钮', hasExport > 0);
await page.screenshot({ path: `${OUT}/2-units.png`, fullPage: true });

// 3. 终端合同
await page.goto(BASE + '/asset-operations/contracts/terminal');
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1500);
const termSegs = await page.locator('.ant-segmented-item-label').allTextContents();
check('终端六值筛选带数量', /生效中|180 天内到期|租金未到账|押金未结清|缺扫描件|已结束/.test(termSegs.join('|')), termSegs.join(' / ').slice(0, 150));
const intakeBtn = await page.locator('button:has-text("录入已签合同")').count();
check('终端页 ＋ 录入已签合同按钮', intakeBtn > 0);
await page.screenshot({ path: `${OUT}/3-terminal.png`, fullPage: true });

// 4. 上游合同（选中一行验证到期框/付款计划/单元矩阵）
await page.goto(BASE + '/asset-operations/contracts/upstream');
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1500);
const upstreamRows = page.locator('.ant-table-tbody .ant-table-row');
const rowCount = await upstreamRows.count();
if (rowCount > 0) {
  await upstreamRows.first().click();
  await page.waitForTimeout(1500);
  const expiry = await page.locator('[aria-label="到期剩余"]').count();
  check('上游详情到期色框', expiry > 0);
  const plan = await page.locator('[aria-label="付款计划"]').count();
  const matrix = await page.locator('[aria-label="资产单元与终端合同"]').count();
  check('上游付款计划/单元矩阵区（有租约时至少其一）', plan > 0 || matrix > 0, `plan=${plan} matrix=${matrix}`);
}
check('上游页 ＋ 录入已签合同按钮', (await page.locator('button:has-text("录入已签合同")').count()) > 0);
await page.screenshot({ path: `${OUT}/4-upstream.png`, fullPage: true });

// 5. 报送
await page.goto(BASE + '/asset-operations/occupancy-reports');
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1800);
check('报送页标题', (await page.locator('h1:has-text("月度出租率报送"), h1:has-text("报送")').count()) > 0);
const historyStrip = await page.getByText('报送记录').count();
check('报送记录卡片条', historyStrip > 0);
await page.waitForTimeout(4000);
const statement = await page.getByText('公司在管存量物业项目').count();
check('报送说明固定句式', statement > 0);
await page.screenshot({ path: `${OUT}/5-report.png`, fullPage: true });

// 6. 档案
await page.goto(BASE + '/asset-operations/archive');
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1500);
check('档案完成率卡区', (await page.getByText('档案完成情况').count()) > 0);
const dropZone = await page.locator('[aria-label*="拖入"]').count();
check('档案拖放区', dropZone > 0);
const batchMatch = await page.getByText('批量配对扫描件').count();
check('批量配对面板', batchMatch > 0);
await page.screenshot({ path: `${OUT}/6-archive.png`, fullPage: true });

// 7. 导入
await page.goto(BASE + '/asset-operations/imports');
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1500);
check('导入步骤条', (await page.locator('[aria-label="导入步骤"]').count()) > 0);
check('模板说明卡', (await page.getByText('下载模板').count()) > 0);
check('导入批次右栏', (await page.getByText('导入批次').count()) > 0);
await page.screenshot({ path: `${OUT}/7-import.png`, fullPage: true });

// 侧栏徽标
await page.goto(BASE + '/asset-operations/monthly');
await page.waitForTimeout(1500);
const navTexts = await page.locator('aside [role="menuitem"], aside li').allTextContents();
check('侧栏「本月」徽标/「档案 缺 N 份」', /本月/.test(navTexts.join('|')) && /档案/.test(navTexts.join('|')), navTexts.filter(t => /本月|档案/.test(t)).join(' / ').slice(0, 100));

check('无 pageerror/console.error', errors.length === 0, errors.slice(0, 3).join(' | '));

fs.writeFileSync(`${OUT}/results.json`, JSON.stringify(results, null, 2));
const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} PASS, ${failed.length} FAIL ==`);
await browser.close();
process.exit(failed.length > 0 ? 1 : 0);
