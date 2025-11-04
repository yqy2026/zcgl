const fs = require('fs');
const path = require('path');

// 读取API一致性报告
const reportPath = path.join(__dirname, '../frontend-api-consistency-report.json');
const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));

// 按文件分组问题
const issuesByFile = {};
report.issues.forEach(issue => {
    const normalizedPath = issue.file.replace(/\\/g, '/');
    if (!issuesByFile[normalizedPath]) {
        issuesByFile[normalizedPath] = [];
    }
    issuesByFile[normalizedPath].push(issue);
});

// 修复错误处理问题
function fixErrorHandling(content, issues) {
    let modified = content;
    const errorHandlingIssues = issues.filter(issue => issue.type === 'error_handling');

    errorHandlingIssues.forEach(issue => {
        const lines = modified.split('\n');
        const lineNumber = issue.lineNumber - 1; // 转换为0基索引

        if (lineNumber >= 0 && lineNumber < lines.length) {
            const line = lines[lineNumber];

            // 查找异步API调用模式
            if (line.includes('await apiClient.') || line.includes('await this.')) {
                // 检查是否已经有try-catch
                let hasTryCatch = false;
                let braceCount = 0;
                let inTryBlock = false;

                // 向上查找try块
                for (let i = lineNumber; i >= 0; i--) {
                    if (lines[i].includes('try {')) {
                        inTryBlock = true;
                        break;
                    }
                    if (lines[i].includes('}') && inTryBlock) {
                        braceCount--;
                        if (braceCount === 0) {
                            break;
                        }
                    }
                    if (lines[i].includes('{') && inTryBlock) {
                        braceCount++;
                    }
                }

                if (!inTryBlock) {
                    // 需要添加错误处理
                    const indentMatch = line.match(/^(\s*)/);
                    const indent = indentMatch ? indentMatch[1] : '';

                    // 查找方法开始
                    let methodStart = lineNumber;
                    for (let i = lineNumber; i >= 0; i--) {
                        if (lines[i].includes('async ') || lines[i].includes('function')) {
                            methodStart = i;
                            break;
                        }
                    }

                    // 在方法开始添加try-catch
                    const methodLine = lines[methodStart];
                    const methodIndent = methodLine.match(/^(\s*)/)[1];

                    // 重构方法
                    let methodBody = [];
                    let methodEnd = lineNumber;
                    let foundEnd = false;

                    for (let i = methodStart + 1; i < lines.length; i++) {
                        if (lines[i].includes('}') && !lines[i].includes('catch')) {
                            // 检查是否是方法结束
                            let methodBraceCount = 0;
                            for (let j = methodStart; j <= i; j++) {
                                if (lines[j].includes('{')) methodBraceCount++;
                                if (lines[j].includes('}')) methodBraceCount--;
                            }
                            if (methodBraceCount === 0) {
                                methodEnd = i;
                                foundEnd = true;
                                break;
                            }
                        }
                        methodBody.push(lines[i]);
                    }

                    if (foundEnd) {
                        // 重构方法，添加错误处理
                        const newMethodBody = [
                            `${methodIndent}try {`,
                            ...methodBody.map(l => l.replace(/^/, '  ')),
                            `${methodIndent}} catch (error) {`,
                            `${methodIndent}  console.error('操作失败:', error)`,
                            `${methodIndent}  throw new Error(error instanceof Error ? error.message : '操作失败')`,
                            `${methodIndent}}`
                        ];

                        // 替换原方法内容
                        lines.splice(methodStart + 1, methodEnd - methodStart, ...newMethodBody);
                        modified = lines.join('\n');
                    }
                }
            }
        }
    });

    return modified;
}

// 修复响应处理问题
function fixResponseHandling(content) {
    // 替换兼容性代码为统一的response.data格式
    return content
        .replace(/if\s*\(\s*response\s*\)\s*{\s*return\s*response\s*;\s*}/g, 'return response.data;')
        .replace(/return\s+response\s*;\s*\/\/ 兼容旧格式/g, 'return response.data;')
        .replace(/response\s*\|\|\s*\{\}\s*;\s*\/\/ 兼容性处理/g, 'response.data;')
        .replace(/response\s*\?\s*response\s*:\s*\{\}\s*;\s*\/\/ 兼容处理/g, 'response.data;');
}

// 修复路径格式问题
function fixPathFormat(content, issues) {
    let modified = content;
    const pathFormatIssues = issues.filter(issue => issue.type === 'path_format');

    pathFormatIssues.forEach(issue => {
        if (issue.message.includes('API路径应该以/开头')) {
            // 修复动态路径格式
            modified = modified.replace(/\$\{this\.baseUrl\}\/([^`]+)/g, '/api/v1$1');
            modified = modified.replace(/\$\{([^}]+)\}/g, '${$1}');
        }
    });

    return modified;
}

// 修复文件
Object.entries(issuesByFile).forEach(([filePath, issues]) => {
    if (fs.existsSync(filePath)) {
        console.log(`正在修复文件: ${filePath}`);
        let content = fs.readFileSync(filePath, 'utf8');

        // 应用各种修复
        content = fixErrorHandling(content, issues);
        content = fixResponseHandling(content);
        content = fixPathFormat(content, issues);

        fs.writeFileSync(filePath, content);
        console.log(`已修复文件: ${filePath} (${issues.length}个问题)`);
    } else {
        console.log(`文件不存在: ${filePath}`);
    }
});

console.log('API一致性修复完成！');