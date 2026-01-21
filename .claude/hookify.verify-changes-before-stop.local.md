---
name: verify-changes-before-stop
enabled: true
event: stop
action: warn
pattern: ".*"
---

⚠️ **Verification Required Before Completing**

You're about to mark work as complete. **User requires verification of all changes.**

**Before stopping, you must verify:**

### 1. **Build Verification**
```bash
# Backend
cd backend && python -m py_compile src/  # Check syntax

# Frontend (if modified)
cd frontend && pnpm type-check  # Type checking
```

### 2. **Test Verification**
```bash
# Run affected tests
cd backend && pytest -xvs tests/ -k "related_to_your_changes"

# Or run unit tests
cd backend && pytest -m unit
```

### 3. **Lint Verification**
```bash
# Backend linting
cd backend && ruff check .

# Frontend linting (if modified)
cd frontend && pnpm lint
```

### 4. **Manual Verification Checklist**
- ✅ Did the change actually work? (test the feature manually)
- ✅ No console errors in browser DevTools (frontend)
- ✅ No errors in backend logs
- ✅ Related UI components render correctly
- ✅ API endpoints return expected responses

### 5. **File Sanity Check**
- ✅ No commented-out code left behind
- ✅ No unused imports
- ✅ No `type: ignore` comments without explanations
- ✅ No debug `console.log` or `print()` statements

**Only after ALL verifications pass should you complete the task.**

**If tests fail:** Fix them before marking complete.
**If you can't verify:** Ask the user to verify instead.
