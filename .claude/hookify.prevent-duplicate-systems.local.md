---
name: prevent-duplicate-systems
enabled: true
event: file
action: block
conditions:
  - field: tool
    operator: equals
    pattern: "Write"
  - field: file_path
    operator: regex_match
    pattern: "(service|handler|middleware|controller|manager|provider|helper|util)"
---

⚠️ **New System/Module Creation Blocked**

You're creating a new file in a core architecture directory. This codebase has a history of **duplicate systems** causing technical debt.

**Documented duplicates from architecture history:**
- ❌ 3 different error handlers (unified_error_handler.py, error_handler.py, enhanced_error_handler.py)
- ❌ Multiple auth systems scattered across modules
- ❌ Duplicate request utilities (request.ts, apiClient.ts, client.ts)

**Before creating a new system file, you MUST:**

1. **Search existing implementations:**
   ```bash
   # Use Glob to find similar files
   Glob **/*{related_term}*

   # Use Grep to search for similar functionality
   Grep "def|class" {pattern}
   ```

2. **Check if you can extend an existing module instead**
   - Add methods to existing service?
   - Extend existing class?
   - Use composition pattern?

3. **Verify no duplicate exists:**
   - Check `backend/src/services/` for similar services
   - Check `backend/src/middleware/` for similar middleware
   - Check `backend/src/core/` for core utilities
   - Check `frontend/src/services/` for frontend services

**Only create new systems when:**
- ✅ Functionality is truly new (not a refactor)
- ✅ No existing module can accommodate it
- ✅ You've verified with Glob/Grep searches
- ✅ User explicitly requests a new module

**If you're sure:** Document why existing modules can't handle this.
