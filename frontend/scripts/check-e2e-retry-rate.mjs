// Q15（issue #92）：聚合 Playwright JSON 报告中的重试命中率，超阈值即失败。
// CI retries=2 会吃掉偶发 flaky；本脚本让「重试依赖」显性化——重试命中的
// 测试占比异常升高时，门禁失败并打印命中的用例清单，倒查不稳定根因。
import fs from 'node:fs';
import path from 'node:path';

const DEFAULT_THRESHOLD_PERCENT = 10;
// json reporter 在配置路径（playwright.config reportRoot）与 CLI
// --reporter=dot,json 的 cwd 输出之间都可能出现，按存在性取第一个。
const DEFAULT_REPORT_CANDIDATES = [
  path.join(
    process.cwd(),
    '..',
    'test-results',
    'frontend',
    'playwright',
    'reports',
    'test-results.json'
  ),
  path.join(process.cwd(), 'test-results.json'),
];

const readReportPath = () => {
  const raw = process.env.E2E_RETRY_REPORT_PATH?.trim();
  if (raw && raw !== '') {
    return raw;
  }
  const found = DEFAULT_REPORT_CANDIDATES.find(candidate =>
    fs.existsSync(candidate)
  );
  if (found != null) {
    return found;
  }
  return DEFAULT_REPORT_CANDIDATES[0];
};

const readThresholdPercent = () => {
  const raw = process.env.E2E_RETRY_THRESHOLD_PERCENT?.trim();
  if (raw == null || raw === '') {
    return DEFAULT_THRESHOLD_PERCENT;
  }
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0 || value > 100) {
    throw new Error(`E2E_RETRY_THRESHOLD_PERCENT must be 0-100, got: ${raw}`);
  }
  return value;
};

const collectRetriedTests = (suites, titles, retried) => {
  for (const suite of suites ?? []) {
    collectRetriedTests(
      suite.suites,
      [...titles, suite.title].filter(Boolean),
      retried
    );
    for (const spec of suite.specs ?? []) {
      for (const test of spec.tests ?? []) {
        const results = Array.isArray(test.results) ? test.results : [];
        if (results.length > 1) {
          retried.push({
            title: [...titles, spec.title].filter(Boolean).join(' › '),
            attempts: results.length,
            status: test.status,
          });
        }
      }
    }
  }
};

const countTotalTests = (suites) => {
  let total = 0;
  for (const suite of suites ?? []) {
    total += countTotalTests(suite.suites);
    for (const spec of suite.specs ?? []) {
      total += (spec.tests ?? []).length;
    }
  }
  return total;
};

const main = () => {
  const reportPath = readReportPath();
  const thresholdPercent = readThresholdPercent();

  if (!fs.existsSync(reportPath)) {
    throw new Error(`Playwright JSON report not found: ${reportPath}`);
  }

  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  const suites = Array.isArray(report.suites) ? report.suites : [];

  const retried = [];
  collectRetriedTests(suites, [], retried);
  const total = countTotalTests(suites);
  const ratePercent = total === 0 ? 0 : (retried.length / total) * 100;

  console.log(
    `[e2e-retry-rate] ${retried.length}/${total} tests retried (${ratePercent.toFixed(1)}%), threshold ${thresholdPercent}%`
  );

  for (const item of retried) {
    console.log(`  retried x${item.attempts - 1} [${item.status}] ${item.title}`);
  }

  if (ratePercent > thresholdPercent) {
    console.error(
      `[e2e-retry-rate] FAIL: retry rate ${ratePercent.toFixed(1)}% exceeds threshold ${thresholdPercent}% — flaky tests are being masked by retries; investigate the listed cases.`
    );
    process.exitCode = 1;
  }
};

main();
