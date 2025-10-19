# Tesseract OCR 安装指南

## 概述
Tesseract OCR是一个开源的光学字符识别引擎，可以识别扫描件PDF中的文本内容。

## 安装步骤

### 步骤1：下载Tesseract OCR

1. **访问官方下载页面**：
   - 打开浏览器，访问：https://github.com/UB-Mannheim/tesseract/wiki
   - 或者直接访问：https://github.com/UB-Mannheim/tesseract/wiki#tesseract-installer-for-windows

2. **下载Windows安装包**：
   - 查找 "Tesseract installer for Windows"
   - 下载最新版本的安装包（通常是 `.exe` 文件）
   - 推荐版本：tesseract-ocr-w64-setup-5.x.x.exe

### 步骤2：安装Tesseract OCR

1. **运行安装程序**：
   - 右键点击下载的 `.exe` 文件，选择"以管理员身份运行"
   - 按照安装向导进行安装

2. **重要配置**：
   - **选择安装路径**：建议使用默认路径 `C:\Program Files\Tesseract-OCR`
   - **选择语言包**：⚠️ **必须勾选中文语言包**
     - `Chinese (Simplified)` - 简体中文
     - `Chinese (Traditional)` - 繁体中文（可选）
     - `English` - 英文（默认已选）

3. **完成安装**：
   - 点击"Install"开始安装
   - 等待安装完成

### 步骤3：配置环境变量

1. **添加Tesseract到系统PATH**：
   - 打开"系统属性" → "高级" → "环境变量"
   - 在"系统变量"中找到"Path"，点击"编辑"
   - 点击"新建"，添加以下路径：
     ```
     C:\Program Files\Tesseract-OCR
     ```

2. **验证环境变量**：
   - 打开新的命令提示符（CMD）
   - 输入以下命令：
     ```cmd
     tesseract --version
     ```
   - 如果显示版本信息，说明安装成功

### 步骤4：验证中文语言包

1. **检查语言包**：
   ```cmd
   tesseract --list-langs
   ```

2. **确认包含中文**：
   输出应该包含：
   ```
   List of available languages (3):
   chi_sim
   chi_tra
   eng
   ```

### 步骤5：测试OCR功能

安装完成后，您可以使用以下命令测试OCR功能：

```cmd
# 测试英文OCR
tesseract image.png output -l eng

# 测试中文OCR
tesseract image.png output -l chi_sim+eng
```

## 安装完成后

1. **重启PDF导入服务**：
   - 停止当前运行的后端服务
   - 重新启动：`start_uv.bat` 或 `start.bat`

2. **测试PDF智能导入**：
   - 使用您的租赁合同PDF重新测试导入功能
   - 系统现在应该能够识别扫描件中的文本

## 故障排除

### 问题1：tesseract命令不存在
**解决方案**：
- 确认环境变量配置正确
- 重启命令提示符或计算机
- 检查安装路径是否存在

### 问题2：中文识别失败
**解决方案**：
- 确认安装时选择了中文语言包
- 使用 `tesseract --list-langs` 检查可用语言
- 重新安装Tesseract并确保选择中文语言包

### 问题3：识别精度低
**解决方案**：
- 确保PDF扫描质量较高（300DPI以上）
- 尝试使用不同的语言组合（如：chi_sim+eng）
- 考虑预处理PDF图像（提高对比度等）

## 联系支持

如果遇到安装问题，请：
1. 检查Tesseract官方文档
2. 确认系统满足最低要求
3. 查看错误日志获取详细信息