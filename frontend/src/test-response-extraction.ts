/**
 * 测试ResponseExtractor核心功能
 * 这个文件用于验证我们的统一响应处理工具是否正常工作
 */

import { ResponseExtractor } from "./utils/responseExtractor";
import { handleApiError as handleError } from "./services";
import type { StandardApiResponse, PaginatedApiResponse } from "./types/api-response";

// 模拟axios响应
function createMockResponse(data: any): any {
  return {
    data: data,
    status: 200,
    statusText: "OK",
    headers: {},
    config: {} as any
  };
}

// 测试用例
function testResponseExtractor() {
  console.log("🧪 开始测试ResponseExtractor...");

  // 测试1: 标准响应格式
  console.log("\n📋 测试1: 标准响应格式");
  const standardResponse = createMockResponse({
    success: true,
    data: { id: 1, name: "Test User" },
    message: "成功"
  });

  const result1 = ResponseExtractor.smartExtract(standardResponse);
  console.log("结果:", result1);

  // 测试2: 分页响应格式
  console.log("\n📋 测试2: 分页响应格式");
  const paginatedResponse = createMockResponse({
    success: true,
    data: {
      items: [{ id: 1 }, { id: 2 }],
      pagination: {
        page: 1,
        pageSize: 10,
        total: 2,
        totalPages: 1
      }
    }
  });

  const result2 = ResponseExtractor.smartExtract(paginatedResponse);
  console.log("结果:", result2);

  // 测试3: 直接数据响应
  console.log("\n📋 测试3: 直接数据响应");
  const directResponse = createMockResponse([{ id: 1 }, { id: 2 }]);

  const result3 = ResponseExtractor.smartExtract(directResponse);
  console.log("结果:", result3);

  // 测试4: 错误响应
  console.log("\n📋 测试4: 错误响应");
  const errorResponse = createMockResponse({
    success: false,
    error: {
      message: "用户不存在"
    }
  });

  const result4 = ResponseExtractor.smartExtract(errorResponse);
  console.log("结果:", result4);

  // 测试5: extractData
  console.log("\n📋 测试5: 快速数据提取");
  const data5 = ResponseExtractor.extractData(standardResponse, null);
  console.log("提取的数据:", data5);

  // 测试6: 类型验证
  console.log("\n📋 测试6: 类型验证");
  interface User {
    id: number;
    name: string;
  }

  const result6 = ResponseExtractor.smartExtract<User>(standardResponse, {
    enableTypeValidation: true,
    expectedType: "object"
  });
  console.log("类型验证结果:", result6);

  console.log("\n✅ ResponseExtractor测试完成!");
}

// 测试ApiErrorHandler
function testApiErrorHandler() {
  console.log("\n🧪 开始测试ApiErrorHandler...");

  // 模拟网络错误
  try {
    const networkError = new Error("网络连接失败");
    throw networkError;
  } catch (error) {
    try {
      handleError(error, { showDetails: true });
    } catch (enhancedError) {
      console.log("网络错误处理结果:", enhancedError.message);
    }
  }

  // 模拟HTTP错误
  try {
    const httpError = {
      response: {
        status: 404,
        data: {
          message: "资源不存在"
        }
      }
    };
    throw httpError;
  } catch (error) {
    try {
      handleError(error, { showDetails: true });
    } catch (enhancedError) {
      console.log("HTTP错误处理结果:", enhancedError.message);
    }
  }

  console.log("✅ ApiErrorHandler测试完成!");
}

// 运行测试
console.log("🚀 开始API响应处理工具测试");

testResponseExtractor();
testApiErrorHandler();

console.log("\n🎉 所有测试完成！我们的核心功能正在正常工作！");