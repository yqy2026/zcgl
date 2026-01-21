# Architecture Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up single-file directories and AI-generated naming prefixes to improve codebase organization and maintainability.

**Architecture:** This plan addresses the remaining architecture issues by consolidating single-file directories into their proper locations and removing AI-generated naming prefixes. The approach is incremental with testing at each step to ensure no functionality is broken.

**Tech Stack:** Python 3.12 (Backend), React 19 + TypeScript (Frontend), pytest, vitest

---

## Task 1: Move validators.py to validation/ directory

**Rationale:** The `validation/` directory exists but is empty (only contains `__pycache__`). Moving `validators.py` from `core/` to `validation/` makes the codebase more logical.

**Files:**
- Move: `backend/src/core/validators.py` → `backend/src/validation/validators.py`
- Modify: All files importing `from src.core.validators` (need to identify)
- Test: `backend/tests/unit/core/` (check for validator tests)

### Step 1: Find all imports of validators module

```bash
cd backend
grep -r "from src.core.validators" --include="*.py" .
grep -r "from src.core import validators" --include="*.py" .
```

Expected output: List of files importing the validators module

### Step 2: Create the validation directory structure (if needed)

```bash
cd backend/src
ls -la validation/
```

If `__init__.py` doesn't exist:
```bash
touch validation/__init__.py
```

### Step 3: Move the validators.py file

```bash
cd backend/src
mv core/validators.py validation/validators.py
```

### Step 4: Update all import references

For each file found in Step 1, update the import:

**Before:**
```python
from src.core.validators import ValidatorClass
# or
from src.core import validators
```

**After:**
```python
from src.validation.validators import ValidatorClass
# or
from src.validation import validators
```

### Step 5: Update test imports (if any)

```bash
cd backend
grep -r "from src.core.validators" tests/
```

Update any test imports to use `src.validation.validators`

### Step 6: Verify the changes with tests

```bash
cd backend
pytest tests/unit/ -v -k "validator"
pytest tests/integration/ -v -k "validator"
```

Expected: All tests PASS

### Step 7: Run backend type checking

```bash
cd backend
mypy src/
```

Expected: No type errors related to validators import

### Step 8: Commit

```bash
git add backend/src/core/validators.py backend/src/validation/validators.py
git add backend/tests/  # any test updates
git commit -m "refactor(backend): move validators.py from core/ to validation/

- Move core/validators.py → validation/validators.py for better organization
- Update all import references across codebase
- Validation directory now properly contains validation logic

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Move permission.py to core/ directory

**Rationale:** The `decorators/` directory contains only one file (`permission.py`). Moving it to `core/` as `permissions.py` eliminates the single-file directory.

**Files:**
- Move: `backend/src/decorators/permission.py` → `backend/src/core/permissions.py`
- Modify: All files importing `from src.decorators.permission`
- Test: `backend/tests/unit/decorators/` (check for permission tests)

### Step 1: Find all imports of permission module

```bash
cd backend
grep -r "from src.decorators.permission" --include="*.py" .
grep -r "from src.decorators import permission" --include="*.py" .
```

Expected output: List of files importing the permission module

### Step 2: Read the permission.py file to understand its structure

```bash
cat backend/src/decorators/permission.py
```

### Step 3: Copy (not move yet) the file to core/ with new name

```bash
cd backend/src
cp decorators/permission.py core/permissions.py
```

### Step 4: Update the module name in the new file

Open `backend/src/core/permissions.py` and update:

**Check if the file has:**
```python
# File-level docstring or module name references
```

If it references decorators.permission, update to core.permissions

### Step 5: Update all import references

For each file found in Step 1, update the import:

**Before:**
```python
from src.decorators.permission import some_decorator
# or
from src.decorators import permission
```

**After:**
```python
from src.core.permissions import some_decorator
# or
from src.core import permissions
```

### Step 6: Update test imports (if any)

```bash
cd backend
grep -r "from src.decorators.permission" tests/
```

Update any test imports

### Step 7: Verify the changes with tests

```bash
cd backend
pytest tests/unit/decorators/ -v 2>/dev/null || echo "No tests in decorators/"
pytest tests/unit/core/ -v -k "permission"
```

Expected: All tests PASS

### Step 8: Run the full test suite

```bash
cd backend
pytest tests/unit/ -v
```

Expected: All tests PASS

### Step 9: Remove the old decorators directory

```bash
cd backend/src
rm -rf decorators/
```

### Step 10: Commit

```bash
git add backend/src/decorators/ backend/src/core/permissions.py
git add backend/tests/  # any test updates
git commit -m "refactor(backend): move permission.py from decorators/ to core/

- Move decorators/permission.py → core/permissions.py
- Eliminate single-file decorators/ directory
- Update all import references across codebase

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Rename AdvancedFiltersSection.tsx

**Rationale:** Remove AI-generated "Advanced" prefix for clearer, more maintainable naming.

**Files:**
- Rename: `frontend/src/components/Analytics/Filters/AdvancedFiltersSection.tsx` → `frontend/src/components/Analytics/Filters/FiltersSection.tsx`
- Modify: All files importing/using AdvancedFiltersSection

### Step 1: Find all usages of AdvancedFiltersSection

```bash
cd frontend
grep -r "AdvancedFiltersSection" --include="*.tsx" --include="*.ts" src/
```

Expected output: List of files using this component

### Step 2: Read the component file

```bash
cat frontend/src/components/Analytics/Filters/AdvancedFiltersSection.tsx
```

Note: Check the component name, export type, and any internal references

### Step 3: Rename the file

```bash
cd frontend/src/components/Analytics/Filters/
mv AdvancedFiltersSection.tsx FiltersSection.tsx
```

### Step 4: Update component name in the file

Open `frontend/src/components/Analytics/Filters/FiltersSection.tsx` and update:

**Before:**
```tsx
export const AdvancedFiltersSection: React.FC<Props> = ({ ... }) => {
  // ...
}
```

**After:**
```tsx
export const FiltersSection: React.FC<Props> = ({ ... }) => {
  // ...
}
```

**Also update the display name if present:**
```tsx
FiltersSection.displayName = 'FiltersSection';
```

### Step 5: Update all imports and usages

For each file found in Step 1, update:

**Before:**
```tsx
import { AdvancedFiltersSection } from './Filters/AdvancedFiltersSection';
// or
import { AdvancedFiltersSection } from '@/components/Analytics/Filters/AdvancedFiltersSection';

// usage
<AdvancedFiltersSection ... />
```

**After:**
```tsx
import { FiltersSection } from './Filters/FiltersSection';
// or
import { FiltersSection } from '@/components/Analytics/Filters/FiltersSection';

// usage
<FiltersSection ... />
```

### Step 6: Run frontend type checking

```bash
cd frontend
pnpm type-check
```

Expected: No type errors related to FiltersSection

### Step 7: Run frontend tests

```bash
cd frontend
pnpm test -- FiltersSection
```

Expected: All tests PASS

### Step 8: Commit

```bash
git add frontend/src/components/Analytics/Filters/AdvancedFiltersSection.tsx
git add frontend/src/components/Analytics/Filters/FiltersSection.tsx
git add frontend/src/  # files with updated imports
git commit -m "refactor(frontend): rename AdvancedFiltersSection to FiltersSection

- Remove AI-generated 'Advanced' prefix for clearer naming
- Update all import references across codebase
- Component functionality unchanged

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Rename AssetAdvancedSection.tsx

**Rationale:** Remove AI-generated "Advanced" prefix. This component represents detailed asset information, so "Detailed" is more appropriate.

**Files:**
- Rename: `frontend/src/components/Forms/Asset/AssetAdvancedSection.tsx` → `frontend/src/components/Forms/Asset/AssetDetailedSection.tsx`
- Modify: All files importing/using AssetAdvancedSection

### Step 1: Find all usages of AssetAdvancedSection

```bash
cd frontend
grep -r "AssetAdvancedSection" --include="*.tsx" --include="*.ts" src/
```

Expected output: List of files using this component

### Step 2: Read the component file

```bash
cat frontend/src/components/Forms/Asset/AssetAdvancedSection.tsx
```

Note: Component structure, props, and usage patterns

### Step 3: Rename the file

```bash
cd frontend/src/components/Forms/Asset/
mv AssetAdvancedSection.tsx AssetDetailedSection.tsx
```

### Step 4: Update component name in the file

Open `frontend/src/components/Forms/Asset/AssetDetailedSection.tsx` and update:

**Before:**
```tsx
export const AssetAdvancedSection: React.FC<Props> = ({ ... }) => {
  // ...
}
```

**After:**
```tsx
export const AssetDetailedSection: React.FC<Props> = ({ ... }) => {
  // ...
}
```

**Update display name if present:**
```tsx
AssetDetailedSection.displayName = 'AssetDetailedSection';
```

### Step 5: Update all imports and usages

For each file found in Step 1, update:

**Before:**
```tsx
import { AssetAdvancedSection } from './AssetAdvancedSection';
// or
import { AssetAdvancedSection } from '@/components/Forms/Asset/AssetAdvancedSection';

// usage
<AssetAdvancedSection ... />
```

**After:**
```tsx
import { AssetDetailedSection } from './AssetDetailedSection';
// or
import { AssetDetailedSection } from '@/components/Forms/Asset/AssetDetailedSection';

// usage
<AssetDetailedSection ... />
```

### Step 6: Run frontend type checking

```bash
cd frontend
pnpm type-check
```

Expected: No type errors related to AssetDetailedSection

### Step 7: Run frontend tests

```bash
cd frontend
pnpm test -- AssetDetailedSection
```

Expected: All tests PASS

### Step 8: Commit

```bash
git add frontend/src/components/Forms/Asset/AssetAdvancedSection.tsx
git add frontend/src/components/Forms/Asset/AssetDetailedSection.tsx
git add frontend/src/  # files with updated imports
git commit -m "refactor(frontend): rename AssetAdvancedSection to AssetDetailedSection

- Remove AI-generated 'Advanced' prefix
- Use 'Detailed' to better describe component's purpose (detailed asset info)
- Update all import references across codebase
- Component functionality unchanged

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Final verification and cleanup

**Rationale:** Ensure all changes work together and no issues remain.

### Step 1: Run full backend test suite

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected: All tests PASS

### Step 2: Run full frontend test suite

```bash
cd frontend
pnpm test
```

Expected: All tests PASS

### Step 3: Run frontend type checking

```bash
cd frontend
pnpm type-check
```

Expected: No type errors

### Step 4: Run backend type checking

```bash
cd backend
mypy src/
```

Expected: No type errors

### Step 5: Verify no broken imports

```bash
# Backend
cd backend
python -c "from src.validation import validators; print('✓ validators import OK')"
python -c "from src.core.permissions import permission; print('✓ permissions import OK')"

# Frontend
cd frontend
pnpm exec tsc --noEmit 2>&1 | grep -i "error" || echo "✓ No TypeScript errors"
```

Expected: All imports successful, no errors

### Step 6: Verify directory structure

```bash
# Verify decorators/ is deleted
ls backend/src/decorators/ 2>&1 | grep "No such file" && echo "✓ decorators/ deleted"

# Verify validation/ has validators.py
ls backend/src/validation/validators.py && echo "✓ validators.py in validation/"

# Verify Advanced files are renamed
ls frontend/src/components/Analytics/Filters/FiltersSection.tsx && echo "✓ FiltersSection renamed"
ls frontend/src/components/Forms/Asset/AssetDetailedSection.tsx && echo "✓ AssetDetailedSection renamed"
```

Expected: All checks pass

### Step 7: Create summary commit if needed

If any additional files were modified during verification:

```bash
git add backend/ frontend/
git commit -m "chore: final cleanup and verification after architecture refactoring

- All tests passing
- No type errors
- Directory structure verified
- Import references updated

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Testing Strategy

### Backend Testing
- **Unit Tests**: Run `pytest tests/unit/ -v` after each file move
- **Integration Tests**: Run `pytest tests/integration/ -v` after all moves
- **Type Checking**: Run `mypy src/` to ensure no type errors
- **Import Verification**: Use Python to import moved modules

### Frontend Testing
- **Unit Tests**: Run `pnpm test` for each renamed component
- **Type Checking**: Run `pnpm type-check` after each rename
- **Build Verification**: Run `pnpm build` to ensure no build errors

### Rollback Strategy
If any step fails:
1. Revert the last commit: `git reset --hard HEAD~1`
2. Investigate the failure
3. Fix the issue
4. Retry the step

---

## Expected Outcomes

### Before:
- `backend/src/core/validators.py` (in wrong location)
- `backend/src/decorators/permission.py` (single-file directory)
- `backend/src/validation/` (empty directory)
- `frontend/src/.../AdvancedFiltersSection.tsx`
- `frontend/src/.../AssetAdvancedSection.tsx`

### After:
- `backend/src/validation/validators.py` (proper location)
- `backend/src/core/permissions.py` (consolidated in core/)
- `backend/src/decorators/` (deleted)
- `frontend/src/.../FiltersSection.tsx`
- `frontend/src/.../AssetDetailedSection.tsx`

### Metrics:
- **Single-file directories eliminated**: 2 (decorators/, validation/)
- **AI-generated prefixes removed**: 2
- **Files moved**: 2
- **Files renamed**: 2

---

## Notes

- This plan addresses the **actual current state** of the codebase (verified via exploration)
- The verification report contained some inaccuracies (e.g., 20+ Advanced files, but only 2 exist)
- Focus is on **high-impact, low-risk** changes
- Each task is independent and can be executed separately
- All changes maintain backward compatibility in functionality (better organization only)

---

**Plan created:** 2026-01-21
**Estimated effort:** 2-3 hours
**Risk level:** Low (file moves/renames with import updates)
