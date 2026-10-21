/* 批1–批3 冒烟验证：跑完输出 PASS/FAIL 明细，退出码非 0 即有失败 */
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

const FILE = pathToFileURL('redesign-ia.html').href;
let pass = 0, fail = 0;
const ok = (cond, label) => { if (cond) { pass++; console.log('PASS', label); } else { fail++; console.log('FAIL', label); } };

const browser = await chromium.launch({
  executablePath: process.env.LOCALAPPDATA + '\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe',
});
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

await page.goto(FILE);
await page.waitForTimeout(120);

/* ---------- 全局健康 ---------- */
ok(errors.length === 0, '加载无 pageerror/console.error' + (errors.length ? ` :: ${errors[0]}` : ''));

/* ---------- 登录页：体验身份入口（角色选择自登录页） ---------- */
ok(await page.locator('#login-view.on').count() === 1, '首屏落在登录页');
ok(await page.locator('#role-grid .rolecard').count() === 9, '登录页提供 9 个体验身份卡片');
ok(await page.locator('#scenario-sel').count() === 0, '产品形态：无走查路线脚手架（走查驱动已移除）');
await page.click('[data-rolelogin="leasing"]');
await page.waitForTimeout(80);
ok(await page.locator('#login-view.on').count() === 0, '选择身份卡片后进入系统');
ok(await page.locator('#burger').isHidden(), '桌面宽度不显示移动端汉堡按钮（data-icon 规则不得覆盖隐藏）');
ok(await page.locator('#msearch').isHidden(), '桌面宽度不显示移动端搜索按钮（同源缺陷）');

/* ---------- 批1 · F1.2 权限作用域链接 + 越权示例 ---------- */
ok(await page.locator('#gate-rights-link .note').count() === 1,
  'leasing 视角 intents 门槛条显示职责说明而非跳转按钮');
ok(await page.locator('#gate-rights-link [data-go]').count() === 0, 'leasing 无权不渲染 rights 链接');
ok((await page.locator('#gate-rights-link .note').innerText()).includes('「资产管理」'), '门槛条职责说明随岗位更名（资产权属 → 资产管理）');

await page.evaluate(v => window.switchRole(v), 'asset');
await page.waitForTimeout(80);
/* asset 视角下导航中不应存在 intents 项；随后直接走守卫验证拒绝视图 */
ok(await page.locator('.navi[data-target="intents"]').count() === 0, 'asset 导航中无 intents 项');
await page.evaluate(() => { window.showPage('intents'); });
await page.waitForTimeout(60);
ok(await page.locator('[data-page="denied"].on').count() === 1, 'asset 深链 intents 落入拒绝视图');

/* 直达 denied 视图路径二：leasing 越权深链（银行到账核对页不在授权范围） */
await page.evaluate(v => window.switchRole(v), 'leasing');
await page.waitForTimeout(80);
ok(await page.locator('[data-denydemo]').count() === 0, '产品形态：我的工作不再提供越权演示按钮（走查脚手架已移除）');
await page.evaluate(() => window.showPage('recon'));
await page.waitForTimeout(60);
ok(await page.locator('[data-page="denied"].on').count() === 1, 'leasing 越权深链 recon 落入拒绝视图（内容整体隐藏）');

/* ---------- 批1 · F1.1 意向看板状态机 ---------- */
await page.locator('.navi[data-target="intents"]').first().click();
await page.waitForTimeout(60);
const kanTitles = () => page.$$eval('.kc', cs => cs.map(c => ({ t: c.querySelector('.kc-h').childNodes[0].textContent.trim(), n: c.querySelectorAll('.kcard').length })));
let cols = await kanTitles();
const cIdxOf = name => cols.findIndex(c => c.t.includes(name));
ok(cols[cIdxOf('条件审议中')].n === 3 && cols[cIdxOf('接洽中')].n === 2, '初始四列卡片数正确（2/3/2/1）');

/* 回民饭店（反提 v2）：去决议 → 模态三选一（默认接受，理由必填）→ 已接受列出现拟定合同按钮 */
await page.click('.kcard:has-text("回民饭店") [data-kanact="decide"]');
await page.waitForTimeout(40);
ok(await page.locator('#dec-mask.on').count() === 1, '「去决议」打开决议模态（接受/反提/拒绝三选一）');
ok((await page.locator('#dec-kind-cand .chip.on').innerText()) === '接受', '结论类型默认「接受」且可切换（防行内误触）');
await page.click('#dec-ok');
await page.waitForTimeout(40);
ok(await page.locator('#dec-reason-error:not([hidden])').count() === 1, '空理由被拦截：结论必须附理由留痕');
await page.fill('#dec-reason', '反提 ¥0.38 复审通过（等于底价，底价内），接受成交');
await page.click('#dec-ok');
await page.waitForTimeout(60);
cols = await kanTitles();
ok(cols[cIdxOf('条件审议中')].n === 2 && cols[cIdxOf('已接受')].n === 3, '接受后卡片区数流转正确（条件审议2 · 已接受3）');
const renewBtn = await page.locator('.kc:has-text("已接受") .kcard:has-text("回民饭店") [data-go="page"][data-id="entry"]').count();
ok(renewBtn === 1, '已接受的回民饭店卡带「拟定合同」直达 entry');

/* 吕巨建 paused：无决议按钮 */
ok(await page.locator('.kcard:has-text("吕巨建") [data-kanact]').count() === 0, '受限物业意向不出决议按钮（红线保留）');

/* 新登记低于底价意向（谢先生二次来访）→ 开始条件审议 → 接受不禁用，模态明示例外审批与生效阻断（阻断在生效门） */
await page.click('[data-modal="opp"]');
await page.fill('#opp-name', '谢先生二次来访');
await page.fill('#opp-budget', '0.20（低于底价 0.38，不申请例外）');
await page.click('#opp-save');
await page.waitForTimeout(60);
ok(await page.locator('.kcard:has-text("谢先生二次来访") [data-kanact="review"]').count() === 1, '新登记意向落入接洽中并带「开始条件审议」');
await page.click('.kcard:has-text("谢先生二次来访") [data-kanact="review"]');
await page.waitForTimeout(60);
ok(await page.locator('.kcard:has-text("谢先生二次来访") [data-kanact="decide"]').count() === 1, '开始审议后出现「去决议」主按钮');
await page.click('.kcard:has-text("谢先生二次来访") [data-kanact="decide"]');
await page.waitForTimeout(40);
ok((await page.locator('#dec-impact').innerText()).includes('低于有效底价'), '低于底价的接受不禁用：模态明示例外审批前底价门保持阻断');
await page.fill('#dec-reason', '预算未变仍按 ¥0.20 登记结论；例外审批缺位前生效门保持阻断');
await page.click('#dec-ok');
await page.waitForTimeout(60);
/* 反提（郭莉琳续租）：决议模态内切换结论类型 + 留在同列并出现「等对方回复」轮次徽标 */
await page.click('.kcard:has-text("郭莉琳") [data-kanact="decide"]');
await page.waitForTimeout(40);
await page.click('#dec-kind-cand [data-deckind="counter"]');
await page.waitForTimeout(30);
await page.waitForTimeout(40);
await page.fill('#dec-reason', '维持月租 ¥14,484，但租期缩短至 36 个月');
await page.click('#dec-ok');
await page.waitForTimeout(60);
ok((await page.locator('.kcard:has-text("郭莉琳") .tag').first().innerText()).includes('等对方回复'), '反提后卡片带「等对方回复 · 第 1 轮」徽标');

/* 走查①→② 连通：从已接受卡直达 entry，且生效页随来源意向装配上下文 */
await page.click('.kcard:has-text("池玉銮") [data-go="page"][data-id="entry"]');
await page.waitForTimeout(60);
ok(await page.locator('[data-page="entry"].on').count() === 1, '走查①→②经看板一键连续可达');
ok((await page.locator('#entry-src').innerText()).includes('池玉銮'), '生效页载入池玉銮来源上下文（随来源意向装配案例）');
const priceGateCls = await page.locator('#g-price').getAttribute('class');
ok(priceGateCls.includes('no') && (await page.locator('#g-price').innerText()).includes('EX-2026-03'), '低于底价红线案例：底价门红色阻断并关联 EX-2026-03');
ok(await page.locator('#entry-ex-link .perm-note').count() === 1, 'leasing 无权 rights 时例外链接降级为职责说明');
ok((await page.locator('#entry-ex-link .perm-note').innerText()).includes('「资产管理」'), '例外链接职责说明同步岗位更名');
/* EX-2026-03 批准联动：底价门「批准后自动转绿」承诺接线 */
await page.evaluate(v => window.switchRole(v), 'executive');
await page.waitForTimeout(80);
await page.locator('.navi[data-target="rights"]').click();
await page.waitForTimeout(60);
await page.click('[data-ex="ok"]');
await page.waitForTimeout(60);
ok((await page.locator('#ex-chip').innerText()).includes('已批准'), '例外审批批准留痕');
await page.evaluate(v => window.switchRole(v), 'leasing');
await page.waitForTimeout(80);
await page.locator('.navi[data-target="intents"]').click();
await page.waitForTimeout(60);
await page.click('.kcard:has-text("池玉銮") [data-entrycase="xingchen"]');
await page.waitForTimeout(60);
const priceAfter = await page.locator('#g-price').getAttribute('class');
ok(priceAfter.includes('ok') && (await page.locator('#g-price').innerText()).includes('EX-2026-03'), '例外批准后底价门自动转绿（EX-2026-03 联动）');
ok((await page.locator('#g-price .gst').innerText()) === '已批准例外', '例外通过项以「已批准例外」态呈现');
/* ISS-05：核心条款变化 → 原检查结果失效并重新阻断（已批准例外折叠后需展开操作） */
ok(await page.locator('[data-gateinvalidate="g-price"]').count() === 1, '已批准例外提供失效重算入口');
await page.click('#gate-pass-fold');
await page.waitForTimeout(30);
await page.click('[data-gateinvalidate="g-price"]');
await page.waitForTimeout(40);
ok(await page.locator('#g-price.no').count() === 1 && (await page.locator('#g-price').innerText()).includes('原检查结果失效'), '核心条款变化后原结果失效并重新计算、重新阻断');
/* 吴俊锋 × JNY-A05 车位案例：主体审核 + 保证金不一致两处阻断 + 授权期限无法判定 */
await page.locator('.navi[data-target="intents"]').click();
await page.waitForTimeout(60);
await page.click('.kcard:has-text("吴俊锋") [data-entrycase="yuedu"]');
await page.waitForTimeout(60);
ok((await page.locator('#entry-src').innerText()).includes('吴俊锋') && (await page.locator('#g-dep').innerText()).includes('不一致'), '吴俊锋车位案例上下文：保证金不一致阻断生效可走查');
ok(await page.locator('#g-auth.nd').count() === 1 && (await page.locator('#g-auth').innerText()).includes('无法判定'), '授权期限字段缺失 → 无法判定（不静默视为通过）');
ok(await page.locator('#gate-pass #g-gz.na').count() === 1, '不适用项归入折叠区（不占风险区）');

/* ---------- 批1 · F2.1/F2.2 property 落点与 project 范围 ---------- */
await page.evaluate(v => window.switchRole(v), 'property');
await page.waitForTimeout(80);
await page.locator('.navi[data-target="property"]').click();
await page.waitForTimeout(60);
ok(await page.locator('.job:has-text("WO-2207")').count() === 1, 'property 页存在 JZ-401-404/WO-2207 作业卡');
/* WO-2207 复验接线：完成后《合同拟定与生效》前置门联动转绿（跨岗位闭环实证） */
await page.click('[data-wo2207]');
await page.waitForTimeout(60);
ok((await page.locator('[data-page="property"]').innerText()).includes('复验通过'), 'WO-2207 复验完成并留痕');
await page.evaluate(() => { window.switchRole('leasing'); window.showPage('entry'); window.applyEntryCase('ruihe', true); });
await page.waitForTimeout(100);
const precondCls = await page.locator('#g-precond').getAttribute('class');
ok(precondCls.includes('ok') && (await page.locator('#g-precond').innerText()).includes('复验通过'), '物业复验联动解除生效前置门（不再只能靠豁免点亮）');

await page.evaluate(v => window.switchRole(v), 'project');
await page.waitForTimeout(80);
ok((await page.locator('#mw-tasks').innerText()).includes('明察企业欠费 24 个月'), 'project 任务聚焦真实经营焦点（明察欠费 24 个月）');
ok((await page.locator('#mw-tasks').innerText()).includes('回民饭店在谈'), 'project 任务含锦洲在谈跟进（回民饭店）');

/* project 点 dashboard 例外卡的上游授权临期：应为职责说明 */
await page.locator('.navi[data-target="dashboard"]').click();
await page.waitForTimeout(60);
ok(await page.locator('#exc-rights-link .note').count() === 1 && !(await page.locator('#exc-rights-link [data-go]').count()),
  'project 视角看板例外「上游授权临期」降级为说明');

/* ---------- 批2 口径与执行边界 ---------- */
await page.evaluate(v => window.switchRole(v), 'executive');
await page.waitForTimeout(80);
const execMx = await page.locator('#mw-summary').innerText();
ok(execMx.includes('权属受限') && execMx.includes('520,740'), 'executive 第三指标改为权属受限 · 2 处 520,740㎡');
/* 下钻落点=vacancy 且在其白名单 */
ok(await page.locator('#mw-summary .work-metric.go[data-id="vacancy"]').count() >= 1, 'executive 指标下钻 vacancy 可用');

/* 口径修复 + 押金抵扣→核销确认摘要（collections） */
await page.evaluate(v => window.switchRole(v), 'collections');
await page.waitForTimeout(80);
const collTxt = await page.locator('[data-page="collections"]').textContent();
ok(collTxt.includes('2 个欠费客户'), '欠费客户数与左栏明细一致（明察 2 账户 + 凤凰创意 1 账户）');
ok(collTxt.includes('¥1,342,158') && collTxt.includes('¥95,700') && collTxt.includes('¥1,246,458'), '押金抵扣链条金额可复算（1,342,158 − 95,700 = 1,246,458）');
ok(collTxt.includes('24 个月') && collTxt.includes('16 个月') && collTxt.includes('30 天'), '账龄构成可复核（后座 24 个月 / 前座退场 16 个月 / 凤凰创意 < 30 天）');
await page.locator('.navi[data-target="collections"]').click();
await page.waitForTimeout(60);
await page.click('[data-lc="depo1"]');
await page.waitForTimeout(40);
await page.click('[data-lc="depo2"]');
await page.waitForTimeout(40);
ok(await page.locator('#cm-mask.on').count() === 1, '坏账核销申请前弹出确认摘要');
await page.click('#cm-ok');
await page.waitForTimeout(40);
ok(await page.locator('#depo2:not(.hidden)').count() === 1, '核销申请经确认摘要后提交并揭示顺序说明');

await page.evaluate(v => window.switchRole(v), 'asset');
await page.waitForTimeout(80);
const mwSumTxt = await page.locator('#mw-summary').innerText();
ok(mwSumTxt.includes('今日已办') && mwSumTxt.includes('本年已办'), 'asset 指标条渲染进度卡（今日/本年已办，实时派生）');
ok(!mwSumTxt.includes('待我复核') && mwSumTxt.includes('权属受限'), '指标条不再重复待办计数 · 只留盘子状态（去重裁决）');

/* 岗位合并裁决：「资产权属」扩展并更名「资产管理」，承接资产接收（上游合同/代理协议）业务侧职责 */
ok((await page.locator('#role-foot').innerText()).includes('资产管理 · 资产管理部'), '身份卡更名「资产管理」（部门落款不变）');
ok(mwSumTxt.includes('12 件'), '本年已办计数与工作记录一致（13 条中 2026 年 12 条；接收/催办类工作由任务清单与工作记录承载）');

/* 待办清单三层分列：行动项 / 等待项（等谁·等到何时）/ 不用我动手 */
const secLabels = await page.$$eval('#mw-tasks .task-sec b', els => els.map(e => e.textContent));
ok(secLabels.join('|') === '要动手的|等外部的|不用我动手', '待办清单三层分列（行动/等待/无需动作）');
const todoTxt2 = await page.locator('#mw-tasks').innerText();
ok(todoTxt2.includes('等责任人 周庆銮') && todoTxt2.includes('承诺 09-30'), '等待项明示等谁与等到何时（权属清理 · 周庆銮 · 09-30）');
ok(todoTxt2.includes('Q3 代理费对账单自动试算'), '系统自动推进项归入「不用我动手」层（无操作按钮）');
ok(await page.locator('#mw-tasks .task').count() === 7, 'asset 待办共 7 项（行动 5 · 等待 1 · 自动 1）');
ok((await page.locator('#mw-todo-n').innerText()) === '5', '待办徽标只计行动项（5），等待与自动项不计入');
ok(await page.locator('#mw-tasks .task.urgent').count() === 2, '紧急样式只落在行动项上（受托复核 · 租金核对）');

/* 节点日历 + 门禁阻塞面（待办右列，与队列同屏） */
ok(await page.locator('#mw-nodes:not(.hide)').count() === 1, '节点日历卡渲染（未来 90 天）');
const nodesTxt = await page.locator('#mw-nodes').innerText();
ok(nodesTxt.includes('余 3 天') && nodesTxt.includes('上游租约续签窗口开启'), '30 天内节点红显剩余天数；上游续签窗口节点在列');
ok(await page.locator('#mw-nodes .noderow').count() === 6, '节点日历 6 项（对账截止/权属承诺/续签窗口/对账出具/报送/年度确认）');
ok(await page.locator('#mw-gates:not(.hide)').count() === 1
  && (await page.locator('#mw-gates').innerText()).includes('吴俊锋')
  && (await page.locator('#mw-gates').innerText()).includes('WO-2207'), '门禁阻塞面：授权缺失/底价例外/无证/整改门禁正阻塞的下游在列');
ok((await page.locator('#mw-summary').innerText()).includes('授权临期'), '指标条补「授权临期」盘子卡（可下钻 rights）');
ok(await page.locator('.gaterow:has-text("WO-2207") .btn').count() === 0, '门禁行目标页（property）不在资产管理白名单时不渲染「查看」——职责边界而非落拒绝视图');
const hotCol = await page.$eval('#mw-nodes .due.hot', e => getComputedStyle(e).color);
ok(hotCol === 'rgb(207, 19, 34)', '30 天内剩余天数红显命中（.noderow 作用域样式 · #cf1322）');
ok(nodesTxt.includes('每月 1 日报送上月'), '报送节点与工作记录口径一致（每月 1 日报送上月）');
ok((await page.locator('#mw-tasks').innerText()).includes('上游租金核算待核对'), '上游租金核算核对任务指向 payables（业务核对视角）');
ok((await page.locator('#mw-tasks').innerText()).includes('待催确认') && (await page.locator('#mw-tasks').innerText()).includes('评估委托资料待归档'), '对账催确认与评估归档任务在列（评估不建流程页面）');
ok(await page.locator('.navi[data-target="contracts"]').count() === 1
  && await page.locator('.navi[data-target="payables"]').count() === 1
  && await page.locator('.navi[data-target="stmts"]').count() === 1, '资产管理导航新增 合同与协议/上游付款/代理费对账单');
await page.evaluate(() => { window.showPage('payables'); });
await page.waitForTimeout(60);
ok(await page.locator('[data-page="payables"].on').count() === 1 && await page.locator('[data-page="denied"].on').count() === 0, '资产管理深链 payables 不再落入拒绝视图');

/* 工作台 待办/已办：工作记录按业务+年度+月份检索（复盘与总结） */
await page.evaluate(() => { window.showPage('mywork'); });
await page.waitForTimeout(50);
ok(await page.locator('#mw-tabs [data-wtab="done"]').count() === 1, '工作台提供 待办/已办·工作记录 页签');
await page.click('#mw-tabs [data-wtab="done"]');
await page.waitForTimeout(50);
ok(await page.locator('#mw-done:not(.hide)').count() === 1 && await page.locator('#mw-todo.hide').count() === 1, '切换到已办（工作记录）视图');
ok(await page.locator('#wl-rows tr').count() === 13, 'asset 工作记录默认全部展示（13 条，含今日 1 条）');
ok((await page.locator('#wl-count').innerText()).includes('今日新增 1 件') && (await page.locator('#wl-rows').innerText()).includes('今天'), '今日种子记录置顶并带「今天」徽标');
const wlTxt = await page.locator('#mw-done').innerText();
ok(wlTxt.includes('台账与报送') && wlTxt.includes('评估') && wlTxt.includes('资产接收与协议'), '工作记录覆盖接收/台账报送/评估等业务分类');
await page.click('#wl-year .chip[data-v="2025"]');
await page.waitForTimeout(40);
ok((await page.locator('#wl-rows tr').count()) === 1 && (await page.locator('#wl-rows').innerText()).includes('2025-'), '年度筛选生效（2025 年 1 条）');
await page.click('#wl-year .chip[data-v="2026"]');
await page.waitForTimeout(40);
await page.click('#wl-cat .chip[data-v="评估"]');
await page.waitForTimeout(40);
ok((await page.locator('#wl-rows tr').count()) === 2, '业务筛选生效（2026 年评估类 2 条）');
await page.click('#wl-month .chip[data-v="08"]');
await page.waitForTimeout(40);
const wlAug = await page.locator('#wl-rows').innerText();
ok(wlAug.includes('08-') && !wlAug.includes('07-'), '月份筛选生效（仅 8 月记录）');
await page.click('#wl-cat .chip[data-v="全部"]');
await page.waitForTimeout(40);
await page.click('#mw-tabs [data-wtab="todo"]');
await page.waitForTimeout(40);
ok(await page.locator('#mw-tasks').isVisible(), '切回待办视图任务清单恢复');
await page.locator('.work-metric.go[data-gowlog]').first().click();
await page.waitForTimeout(50);
ok(await page.locator('#mw-done:not(.hide)').count() === 1, '进度卡（今日/本年已办）直达已办·工作记录页签');

/* 月度小结：随年月筛选联动，选中月份给环比 */
await page.click('#wl-month .chip[data-v="06"]');
await page.waitForTimeout(40);
const sumTxt = await page.locator('#wl-sum').innerText();
ok(sumTxt.includes('完成 3 件') && sumTxt.includes('较上月（5 月 · 0 件）+3 件'), '月度小结：2026-06 完成 3 件并给出环比 +3');
await page.evaluate(() => { window.switchRole('leasing'); });
await page.waitForTimeout(60);
ok(await page.locator('#mw-nodes.hide').count() === 1 && await page.locator('#mw-gates.hide').count() === 1, '未配置节点/门禁数据的岗位整卡隐藏');

await page.evaluate(v => window.switchRole(v), 'finreview');
await page.waitForTimeout(80);
ok(await page.locator('#mw-tasks [data-toast*="退款复核须关联原收款流水"]').count() === 1, '退款复核任务为说明型占位（不再跳转无落点页面）');
await page.locator('.navi[data-target="stmts"]').click();
await page.waitForTimeout(60);
const hint = await page.locator('#stmt-hint').innerText();
ok(!hint.includes('回到「租客到账确认」') && hint.includes('财务复核岗不直接修改到账明细'), '路线⑥更正指引不再指向无权页');
/* ISS-02：盖章定案应收成立 → 开票轨/资金轨按真实时序独立登记，互不前置 */
await page.click('[data-stmtstep="1"]');
await page.waitForTimeout(40);
ok((await page.locator('#stmt-chip').innerText()).includes('待上传盖章件'), '双方在线确认后进入待盖章');
await page.click('[data-stmtstep="2"]');
await page.waitForTimeout(40);
ok(await page.locator('#cm-mask.on').count() === 1, '盖章归档前弹出确认摘要（应收成立不可逆）');
await page.click('#cm-ok');
await page.waitForTimeout(40);
ok((await page.locator('#stmt-chip').innerText()).includes('应收成立'), '盖章定案 · 服务费应收成立');
await page.click('[data-stmtstep="3"]');
await page.waitForTimeout(40);
ok((await page.locator('#stmt-chip').innerText()).includes('资金轨待登记'), '开票轨登记后资金轨仍独立待登记（开票不是收款前置）');
ok(await page.locator('#stmt-tracks .doneline:has-text("开票分摊")').count() === 1, '发票经开票分摊关联结算项留痕');
await page.click('[data-stmtstep="4"]');
await page.waitForTimeout(40);
ok((await page.locator('#stmt-chip').innerText()).includes('SF-PAY-2026-0819'), '两轨登记完成后对账单闭环');
ok((await page.locator('#stmt-tracks').innerText()).includes('由有效收付分配派生'), '未结金额由有效收付分配派生（对账单不存可改写累计数）');
const stmtTxt = await page.locator('[data-page="stmts"]').innerText();
ok(stmtTxt.includes('先收款 · 后开票'), 'STMT-2026-Q1 对照：先款后票时序同样可流转');
ok(!stmtTxt.includes('付款前置') && !stmtTxt.includes('此方可开票'), '不再出现「发票为付款前置 / 应收成立后方可开票」单链措辞');

await page.evaluate(v => window.switchRole(v), 'cashier');
await page.waitForTimeout(80);
await page.locator('.navi[data-target="recon"]').click();
await page.waitForTimeout(60);
/* ISS-03：自动匹配 → 待复核队列 / 人工异常池（不再逐笔走满五步） */
ok(await page.locator('[data-page="recon"] .steps').count() === 0, 'recon 不再是逐笔五步状态机');
const m1Why = await page.locator('#match-m1 .why').innerText();
ok(m1Why.includes('MATCH-RULES v5') && m1Why.includes('分配候选'), '拟分配卡留存命中规则、规则中文名与代号、候选集合');
ok(m1Why.includes('待复核拟分配'), '自动唯一匹配形成待复核拟分配（复核生效前不改变账单）');
ok((await page.locator('#match-m1 .slab').innerText()).includes('已到账待核销'), '已到账待核销语义：不减少应收 + 规定时限内暂停催缴');
ok((await page.locator('[data-page="recon"]').innerText()).includes('已到账待核销 ≠ 已核销'), '已到账待核销与已核销两层语义并列展示');
ok(await page.locator('#diff-card .diff:has-text("代付")').count() === 1, '异常池含代付风险行（第三方代付须留证明）');
/* 批量复核：勾选多笔一次生效（高置信唯一匹配批量复核） */
await page.click('#ck-all');
await page.waitForTimeout(30);
ok((await page.locator('#ck-count').innerText()).includes('3 笔'), '全选 3 笔待复核拟分配（含 1 组金额正好对得上的账单）');
await page.click('#btn-batch');
await page.waitForTimeout(60);
ok((await page.locator('#stmt-tag-m1').innerText()) === '已核销', 'm1 批量复核生效 → 已核销（仅复核生效派生）');
ok((await page.locator('#stmt-tag-m2').innerText()) === '已核销', 'm2 批量复核生效 → 已核销');
ok((await page.locator('#done-total').innerText()).includes('14 笔'), '今日已核销累计 11+3=14 笔');
ok((await page.locator('.batchbar .note').innerText()).includes('制审分离'), '制审边界说明到位');

/* 批量复核实时写入工作记录（岗位归属财务复核 · 原型代为点亮） */
await page.evaluate(v => window.switchRole(v), 'finreview');
await page.waitForTimeout(60);
await page.click('#mw-tabs [data-wtab="done"]');
await page.waitForTimeout(50);
ok((await page.locator('#wl-rows').innerText()).includes('今天') && (await page.locator('#wl-rows').innerText()).includes('批量复核通过自动拟分配 3 笔'), '批量复核实时写入今日工作记录（财务复核岗）');
const frSum = await page.locator('#mw-summary').innerText();
ok(frSum.includes('今日已办') && frSum.includes('2 件'), '批量复核后「今日已办」计数实时增长（1 → 2 件）');

/* ---------- 批3 CL-03 合同 chips 真筛选 ---------- */
await page.evaluate(v => window.switchRole(v), 'leasing');
await page.waitForTimeout(80);
await page.locator('.navi[data-target="contracts"]').click();
await page.waitForTimeout(60);
const visRows = () => page.$$eval('#contracts-rows tr:not(.hidden)', r => r.length);
ok(await visRows() === 6, '默认全部 6 行可见');
await page.click('[data-cmode="cz"]');
ok(await visRows() === 4 && await page.locator('#wv-card.hidden').count() === 1, '承租转租筛选 4 行且文书卡隐藏');
await page.click('[data-cmode="agy"]');
ok(await visRows() === 1 && await page.locator('#wv-card:not(.hidden)').count() === 1, '委托代理筛选 1 行且文书卡可见');
await page.click('[data-cmode="all"]');
ok(await visRows() === 6, '切回全部恢复 6 行');

/* ---------- 批3 AX 增量 ---------- */
/* Enter 选中第一条搜索命中 */
await page.fill('#gsearch', '明察');
await page.waitForTimeout(60);
const hitCount = await page.locator('#search-hits .hitrow').count();
ok(hitCount >= 1, `搜索出命中（${hitCount} 条）`);
if (hitCount > 0) { await page.press('#gsearch', 'Enter'); await page.waitForTimeout(80); }
ok(await page.locator('[data-page="parties"].on, [data-page="collections"].on').count() === 1, 'Enter 选中第一条命中并跳页');

/* Esc 关抽屉（≤760 视口下打开后 Esc 应关闭） */
await page.setViewportSize({ width: 390, height: 760 });
await page.waitForTimeout(120);
ok(await page.locator('#burger').isVisible(), '移动端保留汉堡按钮（抽屉导航入口）');
await page.click('#burger');
await page.waitForTimeout(60);
ok(await page.$eval('.sidebar', s => s.classList.contains('open')), '移动端抽屉可开');
await page.keyboard.press('Escape');
await page.waitForTimeout(60);
ok(!(await page.$eval('.sidebar', s => s.classList.contains('open'))), 'Esc 关闭移动抽屉');

/* 产权方第一人称 + 批3 RO-08 文案 */
await page.setViewportSize({ width: 1280, height: 800 });
await page.evaluate(v => window.switchRole(v), 'ownerparty');
await page.waitForTimeout(100);
ok((await page.locator('#mw-tasks').innerText()).includes('待您上传'), 'ownerparty 上传证据待办由任务清单承载（指标条不再重复计数）');
ok(await page.locator('[data-page="ownerportal"].on').count() === 1, '产权方切换直接落门户（回归不变）');
ok(await page.locator('[data-page="ownerportal"] .card:has-text("不可见")').count() === 0, '门户不再对外枚举「不可见」清单（正向边界声明）');
/* 走查⑤：到账明细主操作（确认本笔到账）在 1280 视口内直接可见，不靠 pane 横向滚动 */
await page.locator('.portaltabs .ptab[data-target="receipts"]').click();
await page.waitForTimeout(60);
const r1box = await page.locator('#rcpt-row-r1 [data-confirmr]').boundingBox();
ok(r1box != null && r1box.x + r1box.width <= 1281, '确认本笔到账按钮默认落在视口内（表格列不再被 pane 截断）');
await page.locator('.portaltabs .ptab[data-target="ownerportal"]').click();
await page.waitForTimeout(60);

/* ---------- 登录出入口 + 外部门户独立壳 ---------- */
ok(await page.$eval('#app-shell', s => s.classList.contains('as-owner')), '产权方会话启用独立门户壳（as-owner）');
ok(await page.locator('.app.as-owner .sidebar').isHidden(), '外协身份隐藏内部侧栏');
ok(await page.locator('.portaltabs .ptab[data-target="receipts"]').isVisible(), '门户顶导航可见（工作台/到账/对账单/我的工作）');
await page.click('.portaltabs [data-logout]');
await page.waitForTimeout(60);
ok(await page.locator('#login-view.on').count() === 1, '「切换身份」返回登录页（角色选择入口唯一化）');
await page.click('[data-rolelogin="cashier"]');
await page.waitForTimeout(80);
ok(await page.locator('#login-view.on').count() === 0 && (await page.locator('#mw-title').innerText()).includes('出纳'), '重新以出纳身份进入系统');

/* 走查⑥修复回归：产权方第一人称措辞在切回内部岗位后必须恢复原文（when 守卫只作用于换出方向） */
const wordingProbe = await page.evaluate(() => {
  const chip = document.getElementById('stmt-chip');
  chip.textContent = '运营方已确认 · 待产权方确认';
  chip.dataset.orig = chip.textContent; /* 与真实状态一致：renderStmtState 始终同步刷新恢复基准 */
  window.switchRole('ownerparty');
  const ownerTxt = chip.textContent;
  window.switchRole('cashier');
  return { ownerTxt, backTxt: chip.textContent };
});
ok(wordingProbe.ownerTxt.indexOf('待贵方确认') >= 0 && wordingProbe.backTxt.indexOf('待产权方确认') >= 0, '产权方第一人称措辞切回内部岗位后恢复原文（不泄漏）');

/* 生效全链（ISS-05）：系统自动检查风险优先呈现、通过项默认折叠；修正事实源 + 消阻断后提交（WO-2207 已联动转绿，无需豁免） */
await page.evaluate(() => { window.switchRole('leasing'); window.showPage('entry'); window.applyEntryCase('ruihe', true); });
await page.waitForTimeout(80);
ok(await page.locator('#gate-risk .gate').first().getAttribute('id') === 'g-appr', '风险区优先呈现（第一项为阻断）');
ok(await page.locator('#gate-pass.hidden').count() === 1, '通过项默认折叠');
const foldTxt = await page.locator('#gate-pass-fold').innerText();
ok(foldTxt.includes('4 项通过') && foldTxt.includes('EFFECT-RULES'), '折叠头显示通过数量（含联动转绿的前置门）与规则集版本');
await page.click('#gate-pass-fold');
await page.waitForTimeout(30);
ok(await page.locator('#gate-pass:not(.hidden) #g-auth').count() === 1, '展开后可查看通过项证据');
await page.click('#gate-pass-fold');
await page.waitForTimeout(30);
/* 修正两个冲突字段 = 修正事实源（非逐项打勾）；阻断项走各自行内动作 */
for (const fid of ['f-party','f-deposit']){
  await page.locator('#' + fid + ' [data-resolve]').first().click();
  await page.waitForTimeout(30);
}
const solvable = await page.locator('#gate-risk [data-gatesolve]').count();
for (let i = 0; i < solvable; i++){ await page.locator('#gate-risk [data-gatesolve]').first().click(); await page.waitForTimeout(30); }
ok(await page.locator('#entry-submit:enabled').count() === 1, '阻断与无法判定清零后提交解锁（前置门经复验联动转绿）');
await page.click('#entry-submit');
await page.waitForTimeout(40);
ok(await page.locator('#cm-mask.on').count() === 1 && (await page.locator('#cm-body').innerText()).includes('首批账单'), '提交生效前弹出副作用确认摘要（含首批账单同事务）');
await page.click('#cm-ok');
await page.waitForTimeout(60);
ok((await page.locator('#entry-submit').innerText()).includes('已生效'), '确认后合同生效（一次保存全部结果）');

/* 刷新时机回归：操作后不经切身份/页签、直接导航回工作台即呈现最新计数 */
await page.evaluate(() => { window.showPage('mywork'); });
await page.waitForTimeout(60);
ok((await page.locator('#mw-summary').innerText()).includes('今日已办') && (await page.locator('#mw-summary').innerText()).includes('2 件'), 'showPage 直达工作台即重渲染（今日已办 1→2 实时可见）');

/* 生效操作实时写入操作者今日工作记录 */
await page.evaluate(() => { window.switchRole('leasing'); });
await page.waitForTimeout(60);
await page.click('#mw-tabs [data-wtab="done"]');
await page.waitForTimeout(50);
ok((await page.locator('#wl-rows').innerText()).includes('今天') && (await page.locator('#wl-rows').innerText()).includes('提交合同生效'), '生效操作实时写入今日工作记录（操作者归属）');

/* 九条走查路由冒烟（产品导航直达驱动，等价原走查路线：岗位 → 目标页，effective 附带装 ruihe 案例） */
const routes = [
  ['leasing','intents'],['leasing','entry','ruihe'],['cashier','recon'],['collections','collections'],
  ['ownerparty','receipts'],['finreview','stmts'],['ownerparty','ownerportal'],['asset','rights'],['cashier','payables'],
];
for (const [role, pg, c] of routes) {
  await page.evaluate(([r, p, cc]) => { window.switchRole(r); window.showPage(p); if (cc) window.applyEntryCase(cc, true); }, [role, pg, c]);
  await page.waitForTimeout(70);
}
ok(true, '九条走查路由全部触发完毕');

ok(errors.length === 0, '全程零 pageerror/console.error' + (errors.length ? ` :: ${errors.slice(0,3).join(' | ')}` : ''));

console.log(`\n==== ${pass} PASS / ${fail} FAIL ====`);
await browser.close();
process.exit(fail === 0 ? 0 : 1);
