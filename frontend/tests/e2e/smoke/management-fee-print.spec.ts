import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

test('管理费打印不继承应用外壳或页面切换动画', async ({ page }) => {
  await ensureAuthenticated(page);
  await page.goto('/asset-operations/ledgers?ledger_type=management_fee', {
    waitUntil: 'domcontentloaded',
  });
  // 测试库须有当前年度、当前账号可读取的对账单；缺少种子时明确失败。
  const statementLink = page.locator('a[href^="/asset-operations/management-fees/"]').first();
  await expect(statementLink).toBeVisible();
  await statementLink.click();
  const paper = page.locator('article').filter({
    has: page.getByRole('heading', {
      name: '委托管理费对账单',
      exact: true,
    }),
  });
  await expect(paper).toBeVisible();

  // 模拟用户在真实切换动画尚未结束时立即打印。
  await paper.evaluate(element => {
    const transition = element.parentElement?.parentElement;
    if (transition == null) throw new Error('对账单页面容器缺失');
    transition.style.transform = 'translateY(20px)';
    transition.style.opacity = '0.5';
  });
  await page.emulateMedia({ media: 'print' });
  await expect
    .poll(async () => paper.evaluate(element => element.getBoundingClientRect().width))
    .toBeGreaterThan(700);
  const layout = await paper.evaluate(element => {
    const box = element.getBoundingClientRect();
    let opacity = 1;
    let current: Element | null = element;
    while (current != null) {
      opacity *= Number(getComputedStyle(current).opacity);
      current = current.parentElement;
    }
    return { x: box.x, y: box.y, width: box.width, viewport: innerWidth, opacity };
  });
  expect(layout.width).toBeGreaterThan(700);
  expect(layout.x).toBeLessThanOrEqual(1);
  expect(layout.y).toBeLessThanOrEqual(1);
  expect(layout.x + layout.width).toBeLessThanOrEqual(layout.viewport + 1);
  expect(layout.opacity).toBe(1);
  await expect(page.getByRole('button', { name: '打印对账单', exact: true })).toBeHidden();
  await expect(page.locator('aside')).toBeHidden();
});
