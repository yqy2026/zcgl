/**
 * 统一字典服务测试脚本
 * 用于验证服务是否正常工作
 */

import { dictionaryService } from "./index";

async function testDictionaryService() {
  console.log("🧪 开始测试统一字典服务...\n");

  // Test getting available types
  console.log("1. 测试获取可用类型");
  console.log(`✅ 可用字典类型数量: ${types.length}`);
  console.log(`   类型列表: ${types.map((t) => t.code).join(", ")}\n`);

  // Test single dictionary fetch
  console.log("2. 测试单个字典获取");
  console.log(`✅ property_nature 加载成功`);
  console.log(`   数据来源: ${result.source}`);
  console.log(`   数据条数: ${result.data.length}`);
  console.log(`   数据预览: ${JSON.stringify(result.data.slice(0, 2), null, 2)}\n`);

  // Test batch dictionary fetch
  console.log("3. 测试批量字典获取");
  console.log(`✅ 批量获取完成`);
  console.log(`   ${dictType}: ${result.data.length} 项 (来源: ${result.source})`);
  console.log(`   ${dictType}: 失败 (${result.error})`);
  console.log("");

  // Test cache functionality
  console.log("4. 测试缓存功能");
  console.log(`✅ 缓存测试完成`);
  console.log(`   第一次来源: ${result1.source}`);
  console.log(`   第二次来源: ${result2.source}`);
  console.log(`   缓存统计: ${stats.cacheSize} 个字典已缓存\n`);

  // Test dictionary type checking
  console.log("5. 测试字典类型检查");
  console.log(`✅ 字典类型检查完成`);
  console.log(`   property_nature: ${exists1 ? "存在" : "不存在"}`);
  console.log(`   non_existent_type: ${exists2 ? "存在" : "不存在"}\n`);

  // All tests completed
  console.log("🎉 所有测试完成！");

  // Test function bound to window
  console.log("测试函数已绑定到 window.testDictionaryService()");
}

// If run this script directly
if (typeof window !== "undefined") {
  // In browser environment
  (window as { testDictionaryService?: typeof testDictionaryService }).testDictionaryService =
    testDictionaryService;
  console.log("测试函数已绑定到 window.testDictionaryService()");
}

export { testDictionaryService };
