/**
 * 批量修复React组件测试文件，使其使用正确的测试工具
 */

const fs = require('fs')
const path = require('path')

// 需要修复的测试文件列表
const testFilesToFix = [
  'src/components/Asset/__tests__/AssetForm.basic.test.tsx',
  'src/components/Asset/__tests__/AssetForm.test.tsx',
  'src/components/Asset/__tests__/AssetSearch.test.tsx',
  'src/components/Asset/__tests__/AssetImport.test.tsx',
  'src/components/Asset/__tests__/AssetExport.test.tsx',
  'src/components/Asset/__tests__/AssetDetailInfo.test.tsx',
  'src/components/Contract/__tests__/EnhancedPDFImportUploader.test.tsx',
  'src/components/ErrorHandling/__tests__/GlobalErrorBoundary.test.tsx',
  'src/components/ErrorHandling/__tests__/UXComponents.test.tsx',
  'src/components/Router/__tests__/DynamicRouteLoader.test.tsx',
  'src/components/Router/__tests__/RoutePerformanceMonitor.test.tsx',
  'src/hooks/__tests__/useErrorHandler.test.ts',
]

// 修复单个测试文件
function fixTestFile(filePath) {
  const fullPath = path.resolve(__dirname, '..', filePath)

  if (!fs.existsSync(fullPath)) {
    console.log(`文件不存在，跳过: ${filePath}`)
    return false
  }

  try {
    let content = fs.readFileSync(fullPath, 'utf8')
    const originalContent = content

    // 修复导入语句
    content = content.replace(
      /import\s*{\s*render[^}]*}\s*from\s*['"]@testing-library\/react['"];?\s*\n?/g,
      ''
    )

    // 添加测试工具导入
    const testUtilsImport = "import { render, screen } from '../../../__tests__/utils/testUtils'\n"

    // 查找React导入并在其后添加测试工具导入
    if (content.includes("import React from 'react'")) {
      content = content.replace(
        /import React from 'react'\n/,
        "import React from 'react'\n" + testUtilsImport
      )
    } else {
      // 如果没有React导入，在文件开头添加
      content = testUtilsImport + content
    }

    // 修复vitest导入
    content = content.replace(
      /import\s*{\s*vi[^}]*}\s*from\s*['"]vitest['"];?\s*\n?/g,
      '// Jest imports - no explicit import needed for describe, it, expect\n'
    )

    // 修复vi.使用
    content = content.replace(/vi\./g, 'jest.')

    // 如果内容有变化，写回文件
    if (content !== originalContent) {
      fs.writeFileSync(fullPath, content, 'utf8')
      console.log(`✅ 修复完成: ${filePath}`)
      return true
    } else {
      console.log(`⚪ 无需修复: ${filePath}`)
      return false
    }
  } catch (error) {
    console.error(`❌ 修复失败: ${filePath}`, error.message)
    return false
  }
}

// 批量修复所有文件
function fixAllTestFiles() {
  console.log('🔧 开始批量修复React组件测试文件...\n')

  let fixedCount = 0
  let totalCount = testFilesToFix.length

  testFilesToFix.forEach(filePath => {
    if (fixTestFile(filePath)) {
      fixedCount++
    }
  })

  console.log(`\n✨ 修复完成! 总计 ${totalCount} 个文件，修复了 ${fixedCount} 个文件`)
}

// 运行修复
if (require.main === module) {
  fixAllTestFiles()
}

module.exports = { fixTestFile, fixAllTestFiles }