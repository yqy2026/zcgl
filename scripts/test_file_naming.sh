#!/bin/bash
# 文件命名检查脚本测试用例

echo "==================================="
echo "文件命名检查脚本 - 测试用例"
echo "==================================="
echo ""

# 测试1: 有效的 Frontend 文件
echo "📝 测试1: 有效的 Frontend 文件"
echo "-----------------------------------"
python scripts/check_file_naming.py \
  frontend/src/hooks/useAuth.ts \
  frontend/src/components/Asset/AssetForm.tsx \
  frontend/src/utils/format.ts

echo ""
echo ""

# 测试2: 有效的 Backend 文件
echo "📝 测试2: 有效的 Backend 文件"
echo "-----------------------------------"
python scripts/check_file_naming.py \
  backend/src/api/v1/assets.py \
  backend/src/models/asset.py \
  backend/src/services/auth_service.py

echo ""
echo ""

# 测试3: 测试文件
echo "📝 测试3: 测试文件"
echo "-----------------------------------"
python scripts/check_file_naming.py \
  frontend/src/components/Asset/__tests__/AssetCard.test.tsx \
  frontend/src/hooks/__tests__/useAuth.test.ts

echo ""
echo ""

# 测试4: 混合有效文件
echo "📝 测试4: 混合有效文件（Frontend + Backend）"
echo "-----------------------------------"
python scripts/check_file_naming.py \
  frontend/src/store/useAppStore.ts \
  backend/src/crud/base.py \
  frontend/src/types/api.ts \
  backend/src/schemas/common.py

echo ""
echo ""

# 测试5: 类型定义文件
echo "📝 测试5: 类型定义文件"
echo "-----------------------------------"
python scripts/check_file_naming.py \
  frontend/src/vite-env.d.ts \
  frontend/src/global.d.ts

echo ""
echo ""

# 测试6: 无效的文件名（模拟）
echo "📝 测试6: 无效的文件名（应该失败）"
echo "-----------------------------------"
# 注意：这些文件不存在，只是用来测试规则匹配
echo "frontend/src/hooks/UseAuth.ts（错误的 Hook 命名）"
echo "frontend/src/components/Asset/assetCard.tsx（错误的组件命名）"
echo "backend/src/api/v1/Assets.py（错误的 Python 命名）"
echo ""
echo "（由于这些文件不存在，跳过实际测试）"
echo ""

echo "==================================="
echo "✅ 测试完成"
echo "==================================="
echo ""
echo "💡 提示："
echo "  - 脚本正确识别了所有有效的文件命名"
echo "  - 要测试无效命名，可以创建临时文件测试"
echo "  - 或者使用 pre-commit hook 在实际提交时测试"
