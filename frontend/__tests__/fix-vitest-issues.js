/**
 * 修复Vitest到Jest的转换问题
 */

const fs = require('fs')
const path = require('path')

// 需要修复的文件列表
const filesToFix = [
  'src/utils/__tests__/dataConversion.test.ts',
  'src/utils/__tests__/enumHelpers.test.ts',
  'src/services/__tests__/assetService.test.ts',
  'src/components/Asset/__tests__/AssetForm.basic.test.tsx',
  'src/components/Asset/__tests__/AssetDetailInfo.test.tsx',
  'src/components/Asset/__tests__/AssetForm.test.tsx',
  'src/components/Asset/__tests__/AssetSearch.test.tsx',
  'src/components/ErrorHandling/__tests__/GlobalErrorBoundary.test.tsx',
  'src/components/ErrorHandling/__tests__/UXComponents.test.tsx',
]

// 修复单个文件
function fixFile(filePath) {
  const fullPath = path.resolve(__dirname, '..', filePath)

  if (!fs.existsSync(fullPath)) {
    console.log(`文件不存在，跳过: ${filePath}`)
    return false
  }

  try {
    let content = fs.readFileSync(fullPath, 'utf8')
    const originalContent = content

    // 修复Vitest导入
    content = content.replace(
      /import\s*{\s*vi[^}]*}\s*from\s*['"]vitest['"];?\s*\n?/g,
      ''
    )

    // 修复vi.使用
    content = content.replace(/vi\./g, 'jest.')

    // 修复其他Vitest相关导入
    content = content.replace(
      /import\s*{\s*([^}]*vi[^}]*)}\s*from\s*['"]vitest['"];?\s*\n?/g,
      (match, imports) => {
        const filteredImports = imports
          .split(',')
          .map(imp => imp.trim())
          .filter(imp => !imp.startsWith('vi'))
          .join(', ')

        return filteredImports ? `import { ${filteredImports} } from 'vitest';\n` : ''
      }
    )

    // 如果有vitest导入但被清空了，添加Jest注释
    if (content.includes('from \'vitest\'') || content.includes('from "vitest"')) {
      content = content.replace(
        /import\s*{\s*[^}]*}\s*from\s*['"]vitest['"];?\s*\n?/g,
        '// Jest imports - no explicit import needed for describe, it, expect\n'
      )
    }

    // 确保有Jest注释
    if (!content.includes('// Jest imports') && (content.includes('describe(') || content.includes('it('))) {
      // 在第一个describe或import之前添加注释
      const firstDescribeIndex = content.indexOf('describe(')
      const firstImportIndex = content.indexOf('import')
      const insertIndex = Math.min(
        firstDescribeIndex !== -1 ? firstDescribeIndex : Infinity,
        firstImportIndex !== -1 ? firstImportIndex : Infinity
      )

      if (insertIndex !== Infinity) {
        content = content.slice(0, insertIndex) +
                 '// Jest imports - no explicit import needed for describe, it, expect\n' +
                 content.slice(insertIndex)
      }
    }

    // 写回文件
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

// 批量修复
function fixAllFiles() {
  console.log('🔧 开始修复Vitest到Jest转换问题...\n')

  let fixedCount = 0
  let totalCount = filesToFix.length

  filesToFix.forEach(filePath => {
    if (fixFile(filePath)) {
      fixedCount++
    }
  })

  console.log(`\n✨ 修复完成! 总计 ${totalCount} 个文件，修复了 ${fixedCount} 个文件`)
}

// 运行修复
if (require.main === module) {
  fixAllFiles()
}

module.exports = { fixFile, fixAllFiles }