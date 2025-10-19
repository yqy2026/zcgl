# PDF导入功能环境配置指南

## 概述

本文档详细说明了PDF智能导入功能所需的环境配置和依赖项。

## 当前环境状态

### ✅ 已安装的依赖

#### OCR依赖 (3/4)
- **pytesseract**: 0.3.13 - OCR引擎接口
- **pdf2image**: 可用 - PDF转图像工具
- **Pillow**: 10.4.0 - 图像处理库
- **opencv-python**: 未安装 - 图像预处理优化 (可选)

#### NLP依赖 (5/5)
- **spacy**: 3.8.6 - 自然语言处理引擎
- **jieba**: 0.42.1 - 中文分词工具
- **fuzzywuzzy**: 0.18.0 - 模糊字符串匹配
- **python-Levenshtein**: 0.27.1 - 字符串相似度计算
- **regex**: 2.5.147 - 高级正则表达式

#### PDF处理依赖 (2/2)
- **markitdown**: 0.1.3 - Microsoft PDF转Markdown工具
- **pdfplumber**: 0.11.7 - PDF内容提取工具

#### 异步处理依赖 (1/1)
- **aiofiles**: 23.0.0 - 异步文件操作

### ✅ 系统工具 (2/3)
- **Tesseract OCR**: C:\Program Files\Tesseract-OCR\tesseract.exe - OCR文字识别引擎
- **Poppler**: C:\Program Files\poppler\poppler-25.07.0\Library\bin\pdftoppm.exe - PDF渲染工具包
- **FFmpeg**: 未安装 - 多媒体处理 (可选)

## 功能完整性评估

### 核心功能状态: ✅ 完全可用

当前环境配置已经完全支持PDF智能导入的所有核心功能：

1. **PDF转换**: ✅
   - 支持标准PDF文件处理 (pdfplumber)
   - 支持扫描版PDF OCR处理 (Tesseract + pdf2image)
   - 支持高级PDF转换 (MarkItDown)

2. **智能信息提取**: ✅
   - 中文文本处理和分析
   - 58个关键字段提取
   - 阶梯租金智能识别
   - 模糊匹配和数据验证

3. **OCR功能**: ✅
   - 中文OCR识别 (chi_sim语言包)
   - 图像预处理优化
   - OCR fallback机制

4. **错误处理**: ✅
   - 详细的错误报告
   - 用户友好的错误提示
   - 智能建议系统

## 可选优化项目

### 1. OpenCV (可选)
- **用途**: 提升OCR前的图像预处理质量
- **安装**: `pip install opencv-python`
- **影响**: 对扫描质量较差的PDF有改善作用

### 2. FFmpeg (可选)
- **用途**: 多媒体文件处理
- **安装**: 从 https://ffmpeg.org/download.html 下载
- **影响**: 仅在处理包含音频/视频的PDF时需要

## 环境验证脚本

运行以下命令验证环境配置：

```bash
cd backend
python scripts/environment_setup.py check
```

## 故障排除

### 常见问题

1. **Tesseract找不到**
   ```
   解决方案:
   - 确认Tesseract已正确安装
   - 检查系统PATH环境变量
   - 或在代码中指定Tesseract路径
   ```

2. **Poppler找不到**
   ```
   解决方案:
   - 确认Poppler已正确安装
   - 检查bin目录是否在PATH中
   - 或在代码中指定Poppler路径
   ```

3. **中文OCR识别率低**
   ```
   解决方案:
   - 确认已下载chi_sim语言包
   - 检查PDF图像质量
   - 尝试调整OCR参数
   ```

## 性能优化建议

1. **系统资源**
   - 建议至少4GB内存
   - OCR处理时CPU使用率较高

2. **文件处理**
   - 大文件处理时间较长，请耐心等待
   - 建议单次处理文件不超过50MB

3. **并发处理**
   - 系统支持并发处理多个PDF文件
   - 建议同时处理的文件数不超过3个

## 更新和维护

### 依赖更新
定期更新关键依赖以获得更好的性能和稳定性：

```bash
pip install --upgrade pytesseract pdfplumber markitdown spacy
```

### 语言包更新
更新Tesseract中文语言包：

```bash
# 下载最新的chi_sim语言包
# 放置到Tesseract安装目录的tessdata文件夹
```

## 总结

当前环境配置已经完全满足PDF智能导入功能的需求。所有核心依赖都已正确安装和配置，系统可以处理各种类型的PDF文件，包括：

- ✅ 标准文本PDF
- ✅ 扫描版PDF (OCR支持)
- ✅ 混合内容PDF
- ✅ 复杂表格PDF
- ✅ 中文合同PDF

系统具备完整的错误处理机制和用户友好的提示，能够稳定可靠地进行PDF到结构化数据的转换。