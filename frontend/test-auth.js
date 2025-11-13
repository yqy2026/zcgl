/**
 * 认证功能测试脚本
 * 测试admin/admin123登录功能
 */

const axios = require('axios');

const API_BASE_URL = 'http://localhost:5173/api';

async function testAuth() {
  console.log('🧪 开始认证功能测试...\n');

  try {
    // 1. 测试登录API
    console.log('1. 测试登录API...');
    const loginResponse = await axios.post(`${API_BASE_URL}/auth/login`, {
      username: 'admin',
      password: 'admin123'
    }, {
      headers: {
        'Content-Type': 'application/json'
      }
    });

    console.log('✅ 登录API响应状态:', loginResponse.status);
    console.log('✅ 登录响应数据:', JSON.stringify(loginResponse.data, null, 2));

    if (loginResponse.data && loginResponse.data.access_token) {
      const token = loginResponse.data.access_token;
      console.log('✅ 获取到访问令牌');

      // 2. 测试使用令牌访问受保护的API
      console.log('\n2. 测试受保护的API访问...');
      const protectedResponse = await axios.get(`${API_BASE_URL}/auth/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('✅ 受保护API响应状态:', protectedResponse.status);
      console.log('✅ 用户数据获取成功');

      // 3. 测试用户资料API
      console.log('\n3. 测试用户资料API...');
      const profileResponse = await axios.get(`${API_BASE_URL}/auth/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('✅ 用户资料API响应状态:', profileResponse.status);
      console.log('✅ 用户资料:', JSON.stringify(profileResponse.data, null, 2));

    } else {
      console.log('❌ 登录响应中没有访问令牌');
    }

  } catch (error) {
    console.log('❌ 测试失败:', error.message);
    if (error.response) {
      console.log('❌ 错误状态码:', error.response.status);
      console.log('❌ 错误响应:', JSON.stringify(error.response.data, null, 2));
    }
  }
}

// 测试API可达性
async function testApiConnectivity() {
  console.log('🔍 测试API连接性...\n');

  const endpoints = [
    { path: '/auth/login', method: 'POST', description: '登录端点' },
    { path: '/analytics/comprehensive', method: 'GET', description: '分析数据端点' },
    { path: '/rental-contracts/statistics/overview', method: 'GET', description: '租赁统计端点' },
    { path: '/ownerships/statistics/summary', method: 'GET', description: '权属统计端点' }
  ];

  for (const endpoint of endpoints) {
    try {
      const config = {
        method: endpoint.method,
        url: `${API_BASE_URL}${endpoint.path}`,
        headers: { 'Content-Type': 'application/json' }
      };

      if (endpoint.method === 'POST') {
        config.data = { username: 'admin', password: 'admin123' };
      }

      const response = await axios(config);
      console.log(`✅ ${endpoint.description} (${endpoint.method} ${endpoint.path}): ${response.status}`);
    } catch (error) {
      if (error.response) {
        const status = error.response.status;
        const statusText = status === 401 ? '需要认证' :
                           status === 404 ? '端点不存在' :
                           status === 405 ? '方法不允许' : '错误';
        console.log(`⚠️  ${endpoint.description} (${endpoint.method} ${endpoint.path}): ${status} (${statusText})`);
      } else {
        console.log(`❌ ${endpoint.description} (${endpoint.method} ${endpoint.path}): 连接失败`);
      }
    }
  }
}

// 主测试函数
async function main() {
  console.log('🚀 开始完整的认证和API测试\n');
  console.log('=====================================\n');

  await testApiConnectivity();
  console.log('\n=====================================\n');
  await testAuth();

  console.log('\n=====================================');
  console.log('🎉 测试完成！');
  console.log('\n📝 测试总结:');
  console.log('1. API连接性测试完成');
  console.log('2. 认证功能测试完成');
  console.log('3. 请检查上述输出中的 ✅ 和 ⚠️ 标记');
  console.log('\n💡 如果看到大量 ⚠️ 401 错误，这是正常的，表示需要认证');
  console.log('💡 如果看到 ✅ 200 响应，说明对应端点正常工作');
}

// 运行测试
main().catch(console.error);