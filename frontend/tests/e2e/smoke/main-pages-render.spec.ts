import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

/**
 * 主页面渲染冒烟（2026-08-09 点检回归收口）：
 * 点检曾用非规范路径（/contracts、/parties、/ledger、/system）访问核心页面，
 * 得到「空白 main + 无 API 请求」——实为未注册路由被 React Router 渲染为 null。
 * 本套件锁定：规范路径必须渲染出关键内容标记，且绝不渲染 404 页。
 */

const main = (page: import('@playwright/test').Page) => page.locator('main');

const PAGES: Array<{ name: string; path: string; marker: RegExp }> = [
  { name: '工作台', path: '/dashboard', marker: /整体出租率/ },
  { name: '资产台账', path: '/assets/list', marker: /资产列表/ },
  { name: '合同中心', path: '/contract-center/list', marker: /合同中心/ },
  { name: '经营台账', path: '/operations/ledger', marker: /经营台账/ },
  { name: '主体主档', path: '/system/parties', marker: /主体主档管理/ },
];

test.describe('主页面渲染冒烟', () => {
  for (const { name, path, marker } of PAGES) {
    test(`访问 ${name} (${path}) 渲染出页面内容而非空白`, async ({ page }) => {
      await ensureAuthenticated(page);
      await page.goto(path);
      await expect(page).toHaveURL(new RegExp(path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));

      // 关键内容标记必须出现在 main 内
      await expect(main(page).getByText(marker).first()).toBeVisible({ timeout: 15_000 });

      // 不得是 404 页
      await expect(main(page).getByText(/页面不存在/)).toHaveCount(0);
    });
  }

  test('未注册路由渲染 404 页而非空白 main', async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/no-such-page-xyz');

    await expect(page.getByText(/页面不存在/)).toBeVisible({ timeout: 15_000 });
    await expect(main(page)).not.toBeEmpty();
  });
});
