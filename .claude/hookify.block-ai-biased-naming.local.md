---
name: block-ai-biased-naming
enabled: true
event: file
action: block
pattern: "(Enhanced|Unified|Advanced|Smart|Intelligent|Auto|Magic|Dynamic|Flexible|Generic|Universal|Multi|Meta|Super|Ultra|Hyper|Pro|Master|Elite|Premium|Optimized|Robust|Secure|Safe)[A-Z]"
---

⚠️ **AI-Biased Naming Blocked**

You're using a generic, non-descriptive prefix that obscures the business logic purpose.

**Why this matters:**
- Names like "EnhancedContractReview" don't say WHAT it enhances
- "UnifiedProjectSelect" doesn't explain what's being unified
- These prefixes create confusion about actual functionality
- Git history shows multiple "Enhanced" files being later refactored

**Use domain-specific naming instead:**

❌ **Bad:** `EnhancedContractReview`
✅ **Good:** `ContractReviewWithValidation` (describes the feature)

❌ **Bad:** `UnifiedProjectSelect`
✅ **Good:** `ProjectSelectWithOrgFilter` (describes the behavior)

❌ **Bad:** `AdvancedAnalyticsCard`
✅ **Good:** `TrendAnalysisCard` (describes the data)

**Choose names that describe:**
- The business domain (Contract, Asset, User)
- The specific feature (Validation, Filter, Trend)
- The component type (Card, Modal, List)

**Rule of thumb:** If you can swap "Enhanced" for "Improved" and the name still makes sense, it's not descriptive enough.
