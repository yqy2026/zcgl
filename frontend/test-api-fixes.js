/**
 * 问题修复验证脚本
 *
 * 使用方法：
 * 1. 在浏览器控制台运行此脚本
 * 2. 查看验证结果
 *
 * 注意：需要在已登录状态下运行
 */

(async function testAPIFixes() {
  console.log('🧪 开始API修复验证测试...\n');

  const results = {
    passed: 0,
    failed: 0,
    tests: []
  };

  // 获取认证token
  const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
  if (!token) {
    console.error('❌ 未找到认证token，请先登录');
    return;
  }
  console.log('✅ 认证token已找到');

  // 基础配置
  const baseURL = '/api';
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };

  // 测试函数
  async function testAPI(name, url, expectedStatus = 200) {
    try {
      console.log(`\n📡 测试: ${name}`);
      console.log(`   URL: ${url}`);

      const response = await fetch(`${baseURL}${url}`, { headers });

      const status = response.status;
      console.log(`   状态码: ${status}`);

      if (status === expectedStatus || (status >= 200 && status < 300)) {
        console.log(`   ✅ 通过`);
        results.passed++;
        results.tests.push({ name, url, status, success: true });
        return true;
      } else {
        console.log(`   ❌ 失败 (期望: ${expectedStatus}, 实际: ${status})`);
        results.failed++;
        results.tests.push({ name, url, status, success: false, error: `Unexpected status: ${status}` });
        return false;
      }
    } catch (error) {
      console.log(`   ❌ 异常: ${error.message}`);
      results.failed++;
      results.tests.push({ name, url, success: false, error: error.message });
      return false;
    }
  }

  // ==================== 执行测试 ====================

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 1: 通知API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试1.1: 通知列表 (无斜杠)
  await testAPI('通知列表 (无斜杠)', '/v1/notifications?limit=10');

  // 测试1.2: 通知未读数
  await testAPI('通知未读数', '/v1/notifications/unread-count');

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 2: 权属管理API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试2.1: 权属方列表 (无斜杠)
  await testAPI('权属方列表 (无斜杠)', '/v1/ownerships?page=1&size=10');

  // 测试2.2: 权属方下拉选项
  await testAPI('权属方下拉选项', '/v1/ownerships/dropdown-options');

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 3: 组织架构API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试3.1: 组织列表 (无斜杠)
  await testAPI('组织列表 (无斜杠)', '/v1/organizations?limit=10');

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 4: 项目管理API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试4.1: 项目列表 (无斜杠)
  await testAPI('项目列表 (无斜杠)', '/v1/projects?page=1&limit=10');

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 5: 任务管理API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试5.1: 任务列表 (无斜杠)
  await testAPI('任务列表 (无斜杠)', '/v1/tasks?limit=10');

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 6: 综合分析API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试6.1: 综合分析
  await testAPI('综合统计分析', '/v1/analytics/comprehensive');

  // 测试6.2: 缓存统计
  await testAPI('缓存统计信息', '/v1/analytics/cache/stats');

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 7: 缺陷追踪API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试7.1: 缺陷列表 (无斜杠)
  await testAPI('缺陷列表 (无斜杠)', '/v1/defects?limit=10');

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('测试组 8: 用户认证API修复验证');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  // 测试8.1: 当前用户信息
  await testAPI('当前用户信息', '/v1/auth/me');

  // 测试8.2: 用户统计
  await testAPI('用户统计', '/v1/auth/users/statistics/summary');

  // ==================== 测试结果汇总 ====================

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('📊 测试结果汇总');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`✅ 通过: ${results.passed}`);
  console.log(`❌ 失败: ${results.failed}`);
  console.log(`📈 总计: ${results.passed + results.failed}`);
  console.log(`成功率: ${((results.passed / (results.passed + results.failed)) * 100).toFixed(1)}%`);

  // 显示失败的测试
  if (results.failed > 0) {
    console.log('\n❌ 失败的测试:');
    results.tests.filter(t => !t.success).forEach(test => {
      console.log(`   - ${test.name}`);
      console.log(`     URL: ${test.url}`);
      console.log(`     错误: ${test.error || 'Unknown error'}`);
    });
  }

  // 生成测试报告
  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      total: results.passed + results.failed,
      passed: results.passed,
      failed: results.failed,
      successRate: ((results.passed / (results.passed + results.failed)) * 100).toFixed(1) + '%'
    },
    tests: results.tests
  };

  console.log('\n📋 详细测试报告:', JSON.stringify(report, null, 2));

  // 返回结果供外部使用
  return report;
})();
