# Security Fixes - Test Verification Guide

**Date**: 2026-01-20
**Commit**: `50a1d58`
**Purpose**: Verify implemented security fixes and new features

---

## Test Environment Setup

### Prerequisites
```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -e .

# Frontend
cd frontend
pnpm install
```

### Start Services
```bash
# Terminal 1: Backend (port 8002)
cd backend
python run_dev.py

# Terminal 2: Frontend (port 5173)
cd frontend
pnpm dev
```

---

## Test Case 1: Update Profile Endpoint Fix (Issue #9)

### Objective
Verify profile updates use correct API endpoint (`/auth/me`) instead of change password endpoint.

### Manual Test Steps

1. **Login as Admin**
   ```bash
   # Username: admin
   # Password: Admin123!@#
   ```

2. **Navigate to Profile Page**
   - Click user avatar → "个人资料" (Profile)

3. **Update Profile Information**
   - Change "Full Name" to "测试用户 Updated"
   - Change "Email" to "test@example.com"
   - Click "保存" (Save)

4. **Verify Request**
   - Open Browser DevTools (F12) → Network Tab
   - Filter by `me` or `auth`
   - Verify the request is:
     ```
     PUT /api/v1/auth/me
     NOT: PUT /api/v1/auth/change-password
     ```

5. **Expected Result**
   - ✅ Profile updates successfully
   - ✅ Request uses `/auth/me` endpoint
   - ✅ User information refreshed in UI

### Automated Test (Optional)
```bash
# Backend integration test
cd backend
pytest tests/integration/api/test_auth_endpoints.py::test_update_profile -v
```

---

## Test Case 2: Analytics Export Functionality (Issue #7)

### Objective
Verify analytics dashboard can export data to Excel and CSV formats.

### Manual Test Steps

#### 2.1 Excel Export

1. **Navigate to Analytics Dashboard**
   - Menu: "分析看板" (Analytics Dashboard)

2. **Wait for Data Load**
   - Verify charts and metrics display correctly
   - Check browser console for errors (should be none)

3. **Export to Excel**
   - Click "导出" (Export) button
   - Select "Excel" from dropdown
   - Wait for "正在导出..." message
   - Verify "导出成功" success message

4. **Verify Downloaded File**
   - File should be named: `analytics_YYYYMMDD_HHMMSS.xlsx`
     - Example: `analytics_20260120_143022.xlsx`
   - Open file in Excel or LibreOffice
   - Verify sheets contain:
     - Area summary (面积汇总)
     - Occupancy stats (出租统计)
     - Financial data (财务数据)
     - Distribution data (分布数据)

5. **Check Network Request**
   - DevTools → Network Tab
   - Look for: `POST /api/v1/analytics/export?export_format=excel`
   - Status: `200 OK`
   - Response Type: `blob` or `application/vnd.openxmlformats...`

#### 2.2 CSV Export

1. **Export to CSV**
   - Click "导出" button
   - Select "CSV" from dropdown
   - Wait for success message

2. **Verify Downloaded File**
   - File named: `analytics_YYYYMMDD_HHMMSS.csv`
   - Open in text editor
   - Verify JSON-formatted analytics data

3. **Network Request**
   - `POST /api/v1/analytics/export?export_format=csv`
   - Status: `200 OK`

#### 2.3 Filtered Data Export

1. **Apply Filters**
   - Set "Date From": 2024-01-01
   - Set "Date To": 2024-12-31
   - Click "应用筛选" (Apply Filters)

2. **Export Filtered Data**
   - Click "导出" → "Excel"
   - Open exported file
   - Verify data matches filtered date range

### Backend API Test (cURL)
```bash
# Test export endpoint directly
curl -X POST "http://localhost:8002/api/v1/analytics/export?export_format=excel" \
  -H "Authorization: Bearer <your_token>" \
  --output test_export.xlsx

# Verify file exists and has content
ls -lh test_export.xlsx
file test_export.xlsx
```

### Expected Issues & Solutions

| Issue | Solution |
|-------|----------|
| `export_analytics_to_excel` method missing | Add to `ExcelExportService` (see below) |
| CORS error during download | Verify backend CORS settings |
| 401 Unauthorized | Check token in httpOnly cookie |
| Empty file | Check analytics data exists in database |

---

## Test Case 3: SECRET_KEY Security (Issue #13)

### Objective
Verify SECRET_KEY meets security requirements and is not exposed in git.

### Automated Verification

```bash
# 1. Check SECRET_KEY length
cd backend
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('SECRET_KEY')
print(f'SECRET_KEY length: {len(key)} characters')
print(f'Meets requirement (≥32): {len(key) >= 32}')
"

# 2. Verify .env in .gitignore
git check-ignore -v backend/.env
# Expected output: .gitignore:198:.env    backend/.env

# 3. Check if .env was ever committed
git log --all --full-history -- "**/.env"
# Expected: No output (never committed)

# 4. Verify no SECRET_KEY in git history
git log --all -S "9Xg},^MOci_3Q%m2J33C*|5=4-kB%**P" --oneline
# Expected: No commits found
```

### Manual Verification

```bash
# View current SECRET_KEY (first 8 chars only)
grep "^SECRET_KEY=" backend/.env | cut -c1-20
# Should show: SECRET_KEY="9Xg},^MO...

# Verify it's not the example placeholder
grep 'placeholder\|<generate\|changeme\|REPLACE' backend/.env
# Should return: No results
```

---

## Regression Tests (Ensure Fixes Don't Break Existing Features)

### Test 4.1: User Authentication Flow

1. **Login**
   - Navigate to login page
   - Enter credentials
   - Click "登录"
   - ✅ Verify redirect to dashboard
   - ✅ Check localStorage contains `authData` with permissions

2. **Permission Check**
   - DevTools → Console
   - Type: `localStorage.getItem('authData')`
   - Parse JSON and verify:
     - `permissions` array exists
     - `user.role` is correct
     - `user.id` matches logged-in user

3. **Logout**
   - Click "退出登录"
   - ✅ Verify redirect to login page
   - ✅ Check localStorage cleared (no `authData`)
   - ✅ Check cookies cleared (no `access_token`)

### Test 4.2: Rate Limiting (Issue #1 - Already Fixed)

1. **Trigger Rate Limit**
   ```bash
   # Send rapid requests
   for i in {1..20}; do
     curl -X GET "http://localhost:8002/api/v1/assets" \
       -H "Authorization: Bearer <token>" &
   done
   ```

2. **Expected Result**
   - ✅ First 10-15 requests succeed
   - ✅ Subsequent requests return `429 Too Many Requests`
   - ✅ Backend logs show rate limit warnings

### Test 4.3: Admin Role Case Insensitivity (Issue #2 - Already Fixed)

1. **Create Test User**
   ```python
   # In backend Python shell
   from src.database import SessionLocal
   from src.crud.user import user_crud
   from src.models.auth import User

   db = SessionLocal()
   user = user_crud.create(db, obj_in={
       "username": "TestAdmin",
       "password": "Test123!@#",
       "role": "ADMIN"  # Uppercase
   })
   ```

2. **Login as TestAdmin**
   - Username: `TestAdmin`
   - Password: `Test123!@#`

3. **Verify Admin Access**
   - ✅ Can access admin-only pages
   - ✅ Has all permissions
   - ✅ Case-insensitive matching works

---

## Performance Tests

### Test 5.1: Large Dataset Export

1. **Prepare Data**
   - Ensure database has 1000+ asset records

2. **Export Large Dataset**
   - Analytics Dashboard → Export Excel
   - Measure time from click to download complete

3. **Acceptable Performance**
   - ✅ Excel export: < 10 seconds for 1000 records
   - ✅ CSV export: < 5 seconds for 1000 records
   - ✅ Memory usage: < 500MB spike during export

### Test 5.2: Concurrent Exports

```bash
# Terminal 1: Start backend with monitoring
cd backend
python run_dev.py

# Terminal 2: Send 5 concurrent export requests
for i in {1..5}; do
  curl -X POST "http://localhost:8002/api/v1/analytics/export?export_format=excel" \
    -H "Authorization: Bearer <token>" \
    --output "export_$i.xlsx" &
done

wait

# Verify all files downloaded successfully
ls -lh export_*.xlsx
```

---

## Known Issues & Workarounds

### Issue 1: ExcelExportService Missing Method

**Error**: `AttributeError: 'ExcelExportService' object has no attribute 'export_analytics_to_excel'`

**Temporary Workaround**:
```python
# Add to backend/src/services/excel/excel_export_service.py

def export_analytics_to_excel(self, analytics_data: dict) -> BytesIO:
    """Export analytics data to Excel format"""
    import openpyxl
    from openpyxl.styles import Font, Alignment

    buffer = BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Analytics"

    # Add summary section
    ws['A1'] = "资产分析报告"
    ws['A1'].font = Font(bold=True, size=16)
    ws['A2'] = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Add metrics
    row = 4
    for key, value in analytics_data.get('area_summary', {}).items():
        ws[f'A{row}'] = str(key)
        ws[f'B{row}'] = str(value)
        row += 1

    wb.save(buffer)
    buffer.seek(0)
    return buffer
```

### Issue 2: CORS During File Download

**Error**: `CORS policy: No 'Access-Control-Allow-Origin' header`

**Solution**: Verify backend CORS configuration includes frontend URL:
```python
# backend/src/core/config.py
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    # Add your frontend URL if different
]
```

---

## Test Results Checklist

Copy and paste this checklist to track your testing progress:

```markdown
- [ ] Test 1.1: Profile update uses correct endpoint (/auth/me)
- [ ] Test 1.2: Profile data saves successfully
- [ ] Test 2.1: Excel export downloads correctly
- [ ] Test 2.2: CSV export downloads correctly
- [ ] Test 2.3: Filtered data export works
- [ ] Test 3.1: SECRET_KEY length ≥ 32 characters
- [ ] Test 3.2: .env file not in git history
- [ ] Test 4.1: Authentication flow works
- [ ] Test 4.2: Rate limiting activates
- [ ] Test 4.3: Case-insensitive admin role works
- [ ] Test 5.1: Large dataset export performance OK
- [ ] Test 5.2: Concurrent exports handled correctly
```

---

## Quick Smoke Test (5 Minutes)

If you're short on time, run this minimal test:

```bash
# 1. Start services
cd backend && python run_dev.py &
cd frontend && pnpm dev &

# 2. Test login
curl -X POST "http://localhost:8002/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!@#"}'

# 3. Test export
curl -X POST "http://localhost:8002/api/v1/analytics/export?export_format=excel" \
  -H "Authorization: Bearer <token_from_step_2>" \
  --output quick_test.xlsx

# 4. Verify file
ls -lh quick_test.xlsx
file quick_test.xlsx

# Expected: File size > 0, type: Excel 2007+
```

---

## Next Steps After Testing

### If Tests Pass ✅
1. Deploy to staging environment
2. Run full E2E test suite
3. Monitor for 24 hours before production deployment

### If Tests Fail ❌
1. Check backend logs: `tail -f backend/logs/app.log`
2. Check browser console for errors
3. Review failed test output
4. Create GitHub issue with error details

---

## Questions or Issues?

- **Backend Issues**: Check `backend/logs/app.log`
- **Frontend Issues**: Check browser DevTools Console
- **Database Issues**: Verify `backend/database/data/*.db` exists
- **Environment Issues**: Verify `backend/.env` configured correctly

---

**Additional Resources**:
- Design Document: `docs/plans/2026-01-20-security-issues-analysis.md`
- Backend Tests: `backend/tests/`
- Frontend Tests: `frontend/src/**/__tests__/`
