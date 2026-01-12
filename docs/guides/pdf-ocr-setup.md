# PDF OCR 功能设置指南

本指南介绍如何配置和使用系统的 PDF OCR（光学字符识别）功能。

---

## 目录

- [快速开始](#快速开始)
- [安装方式](#安装方式)
- [系统要求](#系统要求)
- [环境配置](#环境配置)
- [功能验证](#功能验证)
- [故障排除](#故障排除)
- [GPU 加速（可选）](#gpu-加速可选)

---

## 快速开始

### 基础 PDF 处理（无需 OCR）

如果只需要处理文本型 PDF（非扫描件），使用基础安装即可：

```bash
cd backend
uv sync
```

**功能限制**：
- ✅ 支持文本型 PDF 解析
- ❌ 不支持扫描件/图片 PDF
- ❌ 不支持版面分析
- ❌ 不支持表格识别

### 完整 OCR 功能

如需处理扫描件、图片 PDF 或进行智能版面分析：

```bash
cd backend
uv sync --extra pdf-ocr
```

**完整功能**：
- ✅ 扫描件/图片 PDF 识别
- ✅ 智能版面分析
- ✅ 表格识别和解析
- ✅ 中英文混合识别

---

## 安装方式

### 开发环境

```bash
# 克隆项目
git clone <repository-url>
cd zcgl/backend

# 基础安装（推荐）
uv sync

# 如需 OCR 功能
uv sync --extra pdf-ocr
```

### 生产环境

```bash
# 使用 Docker（推荐）
docker build -t zcgl-backend .
# 默认包含 OCR 功能

# 或手动安装
uv sync --extra pdf-ocr --no-dev
```

### CI/CD 环境

```yaml
# .github/workflows/ci.yml 示例
- name: Install dependencies
  run: |
    cd backend
    uv sync --extra pdf-ocr
```

---

## 系统要求

### 最低配置

| 组件 | 要求 |
|------|------|
| **Python** | 3.12+ |
| **RAM** | 4GB（CPU 模式） |
| **磁盘** | 2GB 可用空间 |
| **操作系统** | Linux/macOS/Windows |

### 推荐配置

| 组件 | 要求 |
|------|------|
| **RAM** | 8GB+ |
| **CPU** | 4核心+ |
| **GPU** | NVIDIA GPU（可选，CUDA 11.2+） |

### 依赖大小

| 依赖组 | 大小 |
|--------|------|
| **基础** | ~500MB |
| **PDF-OCR** | +350MB |
| **总计** | ~850MB |

---

## 环境配置

### 环境变量

在 `backend/.env` 文件中配置：

```bash
# OCR 引擎选择
# 可选值: optimized, paddle
OCR_ENGINE_PROVIDER=paddle

# 语言设置
# ch: 中文, en: 英文
OCR_LANG=ch

# GPU 加速（需要 CUDA）
OCR_USE_GPU=false

# CPU 优化选项
OCR_ENABLE_MKLDNN=true

# 文本方向检测
OCR_USE_TEXTLINE_ORIENTATION=true

# 检测阈值（0-1，默认 0.3）
OCR_DET_DB_THRESH=0.3

# 置信度阈值（0-1，默认 0.5）
OCR_DROP_SCORE=0.5
```

### 依赖策略

系统支持三种依赖策略，通过 `DEPENDENCY_POLICY` 设置：

```bash
# 严格模式：关键依赖缺失时报错
DEPENDENCY_POLICY=strict

# 优雅模式：依赖缺失时警告并降级
DEPENDENCY_POLICY=graceful

# 可选模式：依赖缺失时静默降级
DEPENDENCY_POLICY=optional
```

**推荐**：
- 生产环境: `strict`
- 开发环境: `strict`
- 测试环境: `graceful`

---

## 功能验证

### 1. 检查安装

```bash
cd backend
python -c "import paddleocr; print('PaddleOCR 安装成功')"
```

预期输出：
```
PaddleOCR 安装成功
```

### 2. 检查服务状态

```python
# 在 Python 中运行
from src.services.providers.ocr_provider import is_ocr_available, get_ocr_service_type

if is_ocr_available():
    print(f"OCR 服务可用: {get_ocr_service_type()}")
else:
    print("OCR 服务不可用")
```

### 3. 运行测试

```bash
# 单元测试
pytest tests/unit/services/document/test_paddleocr_service.py -v

# 集成测试
pytest tests/integration/test_pdf_ocr_workflow.py -v
```

### 4. 测试 PDF 处理

```python
from src.services.document.paddleocr_service import get_paddleocr_service

service = get_paddleocr_service()
result = service.to_markdown("test.pdf")

if result["success"]:
    print("PDF 处理成功")
    print(result["markdown"][:500])  # 打印前 500 字符
else:
    print(f"处理失败: {result['error']}")
```

---

## 故障排除

### 问题 1: 导入错误

**症状**：
```
ImportError: cannot import name 'PPStructureV3' from 'paddleocr'
```

**解决方案**：
```bash
# 安装额外的 paddlex 依赖
pip install paddlex[ocr]

# 或重新安装
uv sync --extra pdf-ocr --reinstall
```

### 问题 2: 内存不足

**症状**：
```
MemoryError: Unable to allocate array
```

**解决方案**：

1. 减少并发处理数
```bash
# .env
OCR_MAX_CONCURRENT=1
```

2. 增加系统交换空间
```bash
# Linux
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

3. 处理较小的文件

### 问题 3: CUDA 错误

**症状**：
```
RuntimeError: (External) CUDA error(3), initialization error.
```

**解决方案**：

```bash
# 禁用 GPU，使用 CPU 模式
# .env
OCR_USE_GPU=false
```

### 问题 4: 识别准确率低

**解决方案**：

1. 提高扫描质量（300 DPI+）
2. 调整检测阈值
```bash
# .env
OCR_DET_DB_THRESH=0.2  # 降低阈值
OCR_DROP_SCORE=0.3     # 降低置信度
```
3. 尝试不同的语言模式

### 问题 5: 服务初始化失败

**检查日志**：
```bash
# 查看详细错误
tail -f backend/logs/app.log | grep -i ocr
```

**重新初始化服务**：
```python
from src.services.providers.ocr_provider import reinitialize_ocr_service

if reinitialize_ocr_service():
    print("服务重新初始化成功")
```

---

## GPU 加速（可选）

### CUDA 安装

1. **检查 NVIDIA 驱动**
```bash
nvidia-smi
```

2. **安装 CUDA Toolkit**（11.2 或更高）
```bash
# Ubuntu/Debian
wget https://developer.download.nvidia.com/compute/cuda/11.2.0/local_installers/cuda_11.2.0_460.27.03_linux.run
sudo sh cuda_11.2.0_460.27.03_linux.run

# Windows
# 从 NVIDIA 官网下载安装程序
```

3. **安装 GPU 版本 PaddlePaddle**
```bash
# CUDA 11.2
pip install paddlepaddle-gpu==3.2.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

# CUDA 12.x
pip install paddlepaddle-gpu==3.2.0.post12 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 启用 GPU

```bash
# .env
OCR_USE_GPU=true
```

### 验证 GPU

```python
import paddle
print(f"GPU 可用: {paddle.is_compiled_with_cuda()}")

# 使用 paddle 检查
from paddle import device
print(f"设备: {device.get_device()}")
```

### 性能对比

| 操作 | CPU | GPU |
|------|-----|-----|
| 单页 OCR | ~5秒 | ~0.5秒 |
| 10页 PDF | ~50秒 | ~5秒 |
| 批量处理（10个） | ~500秒 | ~50秒 |

---

## 最佳实践

### 1. 选择合适的模式

| PDF 类型 | 推荐方法 | 原因 |
|----------|----------|------|
| 文本型 PDF | `extract()` | 快速、准确 |
| 扫描件 | `extract_from_pdf_vision()` | 图像理解 |
| 混合型 | `extract_smart()` | 自动检测 |

### 2. 错误处理

```python
from src.services.providers.ocr_provider import is_ocr_available

if not is_ocr_available():
    # 降级到其他方法
    result = await extractor.extract_from_pdf_vision(pdf_path)
else:
    # 使用 OCR
    result = await extractor.extract(markdown_content)
```

### 3. 性能优化

```python
# 限制并发处理
import asyncio

semaphore = asyncio.Semaphore(3)  # 最多3个并发

async def process_with_limit(pdf_path):
    async with semaphore:
        return await process_pdf(pdf_path)
```

### 4. 缓存结果

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_pdf_analysis(pdf_hash: str):
    return analyze_pdf(pdf_path)
```

---

## 常见问题 (FAQ)

### Q: OCR 功能是否必需？

A: 不是。如果只处理文本型 PDF（非扫描件），基础安装即可。

### Q: 如何卸载 OCR 依赖？

A:
```bash
uv pip uninstall paddleocr paddlepaddle opencv-python
```

### Q: 支持 GPU 加速吗？

A: 支持，需要 NVIDIA GPU 和 CUDA 11.2+。

### Q: 处理速度如何？

A: CPU 模式约 5 秒/页，GPU 模式约 0.5 秒/页。

### Q: 支持哪些语言？

A: 主要支持中文和英文，可配置其他语言。

### Q: 能处理手写文字吗？

A: 效果有限，建议使用印刷体文档。

---

## 参考资源

- [PaddleOCR 官方文档](https://github.com/PaddlePaddle/PaddleOCR)
- [项目后端开发指南](../guides/backend.md)
- [环境配置指南](../guides/environment-setup.md)
- [CLAUDE.md](../../CLAUDE.md)

---

**更新日期**: 2026-01-10
**维护者**: 开发团队
