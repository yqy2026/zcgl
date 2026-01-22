# Constants Migration Guide | 常量迁移指南

**Last Updated**: 2026-01-21
**Status**: Optional - Old imports still work

---

## Overview | 概述

As part of the architecture refactoring, 12 constants subdirectories have been consolidated into 6 organized files. This guide shows how to migrate to the new import style.

作为架构重构的一部分，12个常量子目录已合并为6个有组织的文件。本指南展示如何迁移到新的导入方式。

---

## New Import Style (Recommended) | 新导入方式（推荐）

### API & HTTP Constants

```python
# NEW (Recommended)
from src.constants.api_constants import (
    HTTPMethods,
    PaginationLimits,
    BasePaths,
    AssetPaths,
    API_PATHS,
    dynamic_path,
)

# OLD (Still works)
from src.constants.http.methods import HTTPMethods
from src.constants.pagination.limits import PaginationLimits
from src.constants.api_paths import BasePaths, AssetPaths
```

### Validation Constants

```python
# NEW (Recommended)
from src.constants.validation_constants import (
    FieldLengthLimits,
    ValueRanges,
    FileSizeLimits,
    AuthFields,
)

# OLD (Still works)
from src.constants.validation.lengths import FieldLengthLimits
from src.constants.validation.ranges import ValueRanges
from src.constants.validation.sizes import FileSizeLimits
from src.constants.auth.fields import AuthFields
```

### Business Constants

```python
# NEW (Recommended)
from src.constants.business_constants import (
    CommonStatusValues,
    DataStatusValues,
    DateTimeFields,
)

# OLD (Still works)
from src.constants.status.common import CommonStatusValues
from src.constants.status.data import DataStatusValues
from src.constants.datetime.fields import DateTimeFields
```

### Storage Constants

```python
# NEW (Recommended)
from src.constants.storage_constants import (
    FileTypes,
    FileLimits,
    DatabasePoolConfig,
)

# OLD (Still works)
from src.constants.file.types import FileTypes
from src.constants.file.limits import FileLimits
from src.constants.database.pool import DatabasePoolConfig
```

### Message Constants

```python
# NEW (Recommended)
from src.constants.message_constants import (
    ErrorIDs,
    ErrorMessages,
    EMPTY_STRING,
)

# OLD (Still works)
from src.constants.errors.error_ids import ErrorIDs
from src.constants.errors.messages import ErrorMessages
from src.constants.strings.empty import EMPTY_STRING
```

### Performance Constants

```python
# NEW (Recommended)
from src.constants.performance_constants import (
    CacheLimits,
    CacheTTL,
    PerformanceThresholds,
)

# OLD (Still works)
from src.constants.performance.cache import CacheLimits, CacheTTL
from src.constants.performance.monitoring import PerformanceThresholds
```

---

## Migration Strategy | 迁移策略

### Phase 1: New Code (Immediate)
✅ Use new import style for all new code

### Phase 2: Updated Code (Opportunistic)
✅ When editing a file, update its imports to new style

### Phase 3: Bulk Migration (Optional)
⚠️ Can be done in a future PR using automated refactoring

```python
# Automated migration script example
import re
import os

def migrate_imports(file_path):
    """Migrate imports from old to new style."""
    replacements = [
        (r'from src\.constants\.http\.methods import', 'from src.constants.api_constants import'),
        (r'from src\.constants\.pagination\.limits import', 'from src.constants.api_constants import'),
        (r'from src\.constants\.auth\.fields import', 'from src.constants.validation_constants import'),
        (r'from src\.constants\.validation\.lengths import', 'from src.constants.validation_constants import'),
        # Add more patterns...
    ]

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for old, new in replacements:
        content = re.sub(old, new, content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
```

---

## Benefits | 优势

1. **Simpler Imports** (更简单的导入)
   - Fewer directory levels
   - More intuitive organization

2. **Better Discoverability** (更好的可发现性)
   - Related constants grouped together
   - Clearer semantic organization

3. **Reduced Complexity** (降低复杂度)
   - 12 subdirectories → 6 files (50% reduction)
   - Easier to navigate and maintain

---

## Backward Compatibility | 向后兼容性

✅ **OLD IMPORTS WILL CONTINUE TO WORK**
- No breaking changes
- Gradual migration possible
- No immediate action required

⚠️ **Deprecation Timeline** (Future consideration)
- v1.x: Old imports still supported
- v2.0: May add deprecation warnings
- v3.0: May remove old subdirectories

---

## Quick Reference | 快速参考

| Old Import Path | New Import Path |
|----------------|-----------------|
| `http/methods.py` | `api_constants.py` |
| `pagination/limits.py` | `api_constants.py` |
| `api_paths.py` | `api_constants.py` |
| `auth/fields.py` | `validation_constants.py` |
| `validation/lengths.py` | `validation_constants.py` |
| `validation/ranges.py` | `validation_constants.py` |
| `validation/sizes.py` | `validation_constants.py` |
| `status/common.py` | `business_constants.py` |
| `status/data.py` | `business_constants.py` |
| `datetime/fields.py` | `business_constants.py` |
| `file/types.py` | `storage_constants.py` |
| `file/limits.py` | `storage_constants.py` |
| `database/pool.py` | `storage_constants.py` |
| `strings/empty.py` | `message_constants.py` |
| `errors/error_ids.py` | `message_constants.py` |
| `errors/messages.py` | `message_constants.py` |
| `performance/cache.py` | `performance_constants.py` |
| `performance/monitoring.py` | `performance_constants.py` |

---

**Questions?** Refer to `docs/architecture-refactoring.md` for detailed information.
