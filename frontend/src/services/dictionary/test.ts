/**
 * 统一字典服务测试脚本
 * 用于验证服务是否正常工作
 */

import { dictionaryService } from './index'

async function testDictionaryService() {
  console.log('🧪 开始测试统一字典服务...\n')

  // 测试1: 获取可用类型
  console.log('1. 测试获取可用类型')
  try {
    const types = dictionaryService.getAvailableTypes()
    console.log(`✅ 可用字典类型数量: ${types.length}`)
    console.log(`   类型列表: ${types.map(t => t.code).join(', ')}\n`)
  } catch (error) {
    console.error('❌ 获取可用类型失败:', error)
    return
  }

  // 测试2: 单个字典获取
  console.log('2. 测试单个字典获取')
  try {
    const result = await dictionaryService.getOptions('property_nature')
    if (result.success) {
      console.log(`✅ property_nature 加载成功`)
      console.log(`   数据来源: ${result.source}`)
      console.log(`   数据条数: ${result.data.length}`)
      console.log(`   数据预览: ${JSON.stringify(result.data.slice(0, 2), null, 2)}\n`)
    } else {
      console.error(`❌ property_nature 加载失败: ${result.error}\n`)
    }
  } catch (error) {
    console.error('❌ 单个字典获取异常:', error)
    return
  }

  // 测试3: 批量字典获取
  console.log('3. 测试批量字典获取')
  try {
    const dictTypes = ['property_nature', 'usage_status', 'ownership_status']
    const results = await dictionaryService.getBatchOptions(dictTypes)

    console.log(`✅ 批量获取完成`)
    Object.entries(results).forEach(([dictType, result]) => {
      if (result.success) {
        console.log(`   ${dictType}: ${result.data.length} 项 (来源: ${result.source})`)
      } else {
        console.log(`   ${dictType}: 失败 (${result.error})`)
      }
    })
    console.log('')
  } catch (error) {
    console.error('❌ 批量字典获取异常:', error)
    return
  }

  // 测试4: 缓存功能
  console.log('4. 测试缓存功能')
  try {
    // 第一次获取
    const result1 = await dictionaryService.getOptions('property_nature', {
      useCache: true,
      useFallback: true
    })

    // 第二次获取（应该使用缓存）
    const result2 = await dictionaryService.getOptions('property_nature', {
      useCache: true,
      useFallback: true
    })

    const stats = dictionaryService.getStats()
    console.log(`✅ 缓存测试完成`)
    console.log(`   第一次来源: ${result1.source}`)
    console.log(`   第二次来源: ${result2.source}`)
    console.log(`   缓存统计: ${stats.cacheSize} 个字典已缓存\n`)
  } catch (error) {
    console.error('❌ 缓存测试异常:', error)
    return
  }

  // 测试5: 字典类型检查
  console.log('5. 测试字典类型检查')
  try {
    const exists1 = dictionaryService.isTypeAvailable('property_nature')
    const exists2 = dictionaryService.isTypeAvailable('non_existent_type')

    console.log(`✅ 字典类型检查完成`)
    console.log(`   property_nature: ${exists1 ? '存在' : '不存在'}`)
    console.log(`   non_existent_type: ${exists2 ? '存在' : '不存在'}\n`)
  } catch (error) {
    console.error('❌ 字典类型检查异常:', error)
    return
  }

  console.log('🎉 所有测试完成！')
}

// 如果直接运行此脚本
if (typeof window !== 'undefined') {
  // 在浏览器环境中运行
  (window as any).testDictionaryService = testDictionaryService
  console.log('测试函数已绑定到 window.testDictionaryService()')
}

export { testDictionaryService }