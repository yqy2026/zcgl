# Tesseract OCR 手动安装详细指导

## 🎯 目标
安装Tesseract OCR引擎以支持PDF扫描件的文本识别，从而实现PDF智能导入功能。

## 📋 当前状态
- ✅ Python依赖已安装 (pytesseract, pdf2image, pillow)
- ✅ 后端服务正常运行
- ❌ Tesseract OCR引擎未安装
- ❌ spaCy中文NLP模型未安装

## 🔧 手动安装步骤

### 第一步：下载Tesseract OCR

1. **访问官方下载页面**：
   - 打开浏览器，访问：https://github.com/UB-Mannheim/tesseract/wiki
   - 找到 "Tesseract installer for Windows" 部分

2. **直接下载链接**：
   - 64位系统：https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3/tesseract-ocr-w64-setup-5.3.3.exe
   - 32位系统：https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3/tesseract-ocr-w32-setup-5.3.3.exe

3. **备用下载源**：
   - 官方网站：https://tesseract-ocr.github.io/tessdoc/Installation.html
   - 如果GitHub访问困难，可以尝试其他下载源

### 第二步：安装Tesseract OCR

1. **运行安装程序**：
   - 右键点击下载的 `.exe` 文件
   - 选择"以管理员身份运行"

2. **重要配置选项**：
   ```
   ✓ 同意许可协议
   ✓ 选择安装路径（建议默认）：C:\Program Files\Tesseract-OCR
   ✓ 选择组件：
        - Tesseract OCR（必选）
        - Training Tools（可选）
   ✓ 选择语言包（重要！）：
        - English (已默认选择)
        - ⭐ Chinese (Simplified) - 必须勾选
        - Chinese (Traditional) - 可选
        - 其他语言包按需选择
   ```

3. **完成安装**：
   - 点击"Install"开始安装
   - 等待安装完成
   - 可选择是否查看README

### 第三步：配置环境变量

1. **打开系统环境变量设置**：
   - 按 `Win + R`，输入 `sysdm.cpl`
   - 点击"高级"选项卡
   - 点击"环境变量"

2. **编辑系统PATH**：
   - 在"系统变量"中找到 `Path`
   - 点击"编辑"
   - 点击"新建"
   - 添加：`C:\Program Files\Tesseract-OCR`

3. **验证环境变量**：
   - 打开新的命令提示符（CMD）
   - 输入：`tesseract --version`
   - 应该显示版本信息

### 第四步：验证语言包

1. **检查可用语言**：
   ```cmd
   tesseract --list-langs
   ```

2. **预期输出**：
   ```
   List of available languages (3):
   chi_sim
   chi_tra
   eng
   ```

3. **确认中文支持**：
   - `chi_sim` = 简体中文 ✅ 必须存在
   - `chi_tra` = 繁体中文（可选）
   - `eng` = 英文 ✅ 应该存在

### 第五步：测试OCR功能

1. **安装验证后，重启PDF导入服务**：
   ```cmd
   # 停止当前服务
   # 在后端服务窗口按 Ctrl+C

   # 重新启动
   start_uv.bat
   ```

2. **测试您的PDF文件**：
   - 使用您的租赁合同PDF重新测试
   - 系统现在应该能够识别扫描件中的文本

## 🔍 故障排除

### 问题1：tesseract命令不存在
**原因**：环境变量配置错误
**解决**：
1. 确认安装路径是否正确
2. 重新添加到系统PATH
3. 重启命令提示符或计算机

### 问题2：中文识别为乱码
**原因**：未安装中文语言包
**解决**：
1. 重新运行Tesseract安装程序
2. 确保勾选 "Chinese (Simplified)"
3. 使用 `tesseract --list-langs` 验证

### 问题3：识别精度低
**原因**：扫描质量或语言设置问题
**解决**：
1. 确保PDF扫描清晰（300DPI以上）
2. 在代码中尝试不同语言组合
3. 考虑预处理图像（增强对比度）

### 问题4：权限错误
**原因**：未使用管理员权限安装
**解决**：
1. 右键安装程序，选择"以管理员身份运行"
2. 确保安装目录有写入权限

## 📞 获取帮助

如果遇到困难：
1. **查看Tesseract官方文档**：https://tesseract-ocr.github.io/tessdoc/
2. **检查GitHub Issues**：https://github.com/tesseract-ocr/tesseract/issues
3. **重新运行验证脚本**：完成后运行 `python verify_tesseract.py`

## ✅ 完成检查清单

安装完成后，请确认以下项目：

- [ ] Tesseract OCR程序已安装
- [ ] 安装路径已添加到系统PATH
- [ ] `tesseract --version` 命令正常工作
- [ ] `tesseract --list-langs` 包含 `chi_sim`
- [ ] 重新启动了PDF导入服务
- [ ] 测试PDF能够正常处理

## 🎉 预期结果

安装成功后，您的PDF智能导入功能将能够：

1. **识别扫描件PDF中的文本**
2. **提取58个关键字段**
3. **自动匹配资产和所有权信息**
4. **提供智能数据验证**

这样您就可以成功导入您的租赁合同PDF了！