---
name: prevent-excessive-file-creation
enabled: true
event: file
action: block
conditions:
  - field: tool
    operator: equals
    pattern: "Write"
  - field: file_path
    operator: not_contains
    pattern: ".test."
  - field: file_path
    operator: not_contains
    pattern: ".spec."
---

⚠️ **New File Creation Blocked**

You're about to create a new file, but you should **EDIT an existing file instead**.

**Why this matters:**
- This codebase has a history of file duplication (50+ duplicate files documented)
- Git history shows excessive "refactor" commits removing duplicates
- Creating new files when editing would suffice creates technical debt

**Before creating a new file, verify:**
1. ✅ Does a similar file already exist? Search with `git ls-files` or `Glob`
2. ✅ Can the change be made to an existing file instead?
3. ✅ Is this file structure absolutely necessary, or over-engineering?

**Exceptions allowed:**
- Test files (*.test.ts, *.spec.ts, __tests__/)
- genuinely new features (not refactors/duplicates)
- documentation explicitly requested by user

**If you're sure this new file is needed:** Reconsider the file location and structure first.
