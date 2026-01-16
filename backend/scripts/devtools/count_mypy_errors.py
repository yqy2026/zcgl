#!/usr/bin/env python3
"""Count mypy errors from output"""
from collections import defaultdict

# 从任务输出复制的错误列表
errors = r"""
src\utils\cache_manager.py:54: error: Unused "type: ignore" comment  [unused-ignore]
src\database.py:28: error: Name "enhance_database_security" already defined (possibly by an import)  [no-redef]
src\database.py:29: error: Unused "type: ignore" comment  [unused-ignore]
src\middleware\request_logging.py:22: error: Unused "type: ignore" comment  [unused-ignore]
src\middleware\request_logging.py:24: error: Unused "type: ignore" comment  [unused-ignore]
src\services\core\password_service.py:115: error: Unused "type: ignore" comment  [unused-ignore]
src\middleware\security_middleware.py:506: error: Unused "type: ignore" comment  [unused-ignore]
src\crud\base.py:84: error: Returning Any from function declared to return "_ModelType | None"  [no-any-return]
src\crud\base.py:105: error: Unused "type: ignore" comment  [unused-ignore]
src\crud\base.py:105: error: Returning Any from function declared to return "list[_ModelType]"  [no-any-return]
src\crud\base.py:105: note: Error code "no-any-return" not covered by "type: ignore" comment
src\crud\base.py:199: error: Returning Any from function declared to return "_ModelType"  [no-any-return]
src\crud\base.py:245: error: Unused "type: ignore" comment  [unused-ignore]
src\crud\base.py:259: error: Unused "type: ignore" comment  [unused-ignore]
src\main.py:170: error: "None" not callable  [misc]
src\main.py:264: error: Argument 1 to "add_middleware" of "Starlette" has incompatible type "type[Any]"; expected "_MiddlewareFactory[[]]"  [arg-type]
src\services\permission\rbac_service.py:82: error: Redundant cast to "str"  [redundant-cast]
src\services\permission\rbac_service.py:93: error: Redundant cast to "bool"  [redundant-cast]
src\services\permission\rbac_service.py:115: error: Unused "type: ignore" comment  [unused-ignore]
src\services\permission\rbac_service.py:116: error: Unused "type: ignore" comment  [unused-ignore]
src\services\permission\rbac_service.py:121: error: Redundant cast to "str"  [redundant-cast]
src\services\permission\rbac_service.py:135: error: Redundant cast to "bool"  [redundant-cast]
src\services\permission\rbac_service.py:379: error: Unused "type: ignore" comment  [unused-ignore]
src\services\permission\rbac_service.py:380: error: Unused "type: ignore" comment  [unused-ignore]
src\services\permission\rbac_service.py:574: error: Redundant cast to "str"  [redundant-cast]
src\services\permission\rbac_service.py:607: error: Argument 1 to "loads" has incompatible type "dict[str, Any]"; expected "str | bytes | bytearray"  [arg-type]
src\services\asset\occupancy_calculator.py:125: error: Item "None" of "Row[...] | None" has no attribute "total_rentable"  [union-attr]
src\services\asset\occupancy_calculator.py:126: error: Item "None" of "Row[...] | None" has no attribute "total_rented"  [union-attr]
src\services\asset\occupancy_calculator.py:128: error: Item "None" of "Row[...] | None" has no attribute "total_count"  [union-attr]
src\services\asset\occupancy_calculator.py:129: error:Item "None" of "Row[...] | None" has no attribute "rentable_count"  [union-attr]
src\crud\task.py:12: error: Missing type parameters for generic type "CRUDBase"  [type-arg]
src\crud\task.py:138: error: Missing type parameters for generic type "CRUDBase"  [type-arg]
src\crud\system_dictionary.py:10: error: Missing type parameters for generic type "CRUDBase"  [type-arg]
src\crud\rbac.py:51: error: Incompatible types in assignment (expression has type "bool", target has type "str")  [assignment]
src\crud\rbac.py:56: error: Unexpected keyword argument "db_session" for "build_query" of "QueryBuilder"  [call-arg]
src\crud\rbac.py:56: error: Unexpected keyword argument "model" for "build_query" of "QueryBuilder"  [call-arg]
src\crud\rbac.py:56: error: "Select[Any]" has no attribute "all"  [attr-defined]
src\crud\rbac.py:55: error: Returning Any from function declared to return "list[Role]"  [no-any-return]
src\crud\rbac.py:60: error: Argument "base_query" to "build_query" of "QueryBuilder" has incompatible type "Query[Role]"; expected "Select[Any] | None"  [arg-type]
src\crud\rbac.py:111: error: Incompatible types in assignment (expression has type "bool", target has type "str")  [assignment]
src\crud\rbac.py:114: error: Unexpected keyword argument "db_session" for "build_query" of "QueryBuilder"  [call-arg]
src\crud\rbac.py:114: error: Unexpected keyword argument "model" for "build_query" of "QueryBuilder"  [call-arg]
src\crud\rbac.py:114: error: "Select[Any]" has no attribute "all"  [attr-defined]
src\crud\rbac.py:113: error: Returning Any from function declared to return "list[Permission]"  [no-any-return]
src\crud\rbac.py:118: error: Argument "base_query" to "build_query" of "QueryBuilder" has incompatible type "Query[Permission]"; expected "Select[Any] | None"  [arg-type]
src\crud\project.py:11: error: Missing type parameters for generic type "CRUDBase"  [type-arg]
"""

def main():
    errors_by_file = defaultdict(list)

    for line in errors.strip().split('\n'):
        if ':' not in line or 'error:' not in line:
            continue

        parts = line.split(':', 2)
        if len(parts) >= 3:
            file_path = parts[0].strip()
            error_info = parts[2].strip() if len(parts) > 2 else ""

            if 'error:' in error_info:
                # Extract error code
                error_code = 'unknown'
                if '[' in error_info and ']' in error_info:
                    error_code = error_info[error_info.rfind('[')+1:error_info.rfind(']')]

                errors_by_file[file_path].append({
                    'code': error_code,
                    'message': error_info
                })

    print("="*70)
    print("MYPY ERROR ANALYSIS")
    print("="*70)

    total_errors = sum(len(errs) for errs in errors_by_file.values())
    print(f"\nTotal errors: {total_errors}")
    print(f"Files with errors: {len(errors_by_file)}")

    # Group by error code
    error_codes = defaultdict(int)
    for errs in errors_by_file.values():
        for err in errs:
            error_codes[err['code']] += 1

    print("\nError code distribution:")
    for code, count in sorted(error_codes.items(), key=lambda x: -x[1]):
        print(f"  {code:20s}: {count:3d}")

    # Sort files by error count
    sorted_files = sorted(
        errors_by_file.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    print("\nTop 20 files with most errors:")
    for i, (file_path, errs) in enumerate(sorted_files[:20], 1):
        file_name = file_path.split('\\')[-1]
        print(f"{i:2d}. {file_name:40s} ({len(errs):2d} errors)")

    print("\n" + "="*70)
    print(f"REMAINING: {total_errors} errors")
    print("TARGET: <50 errors")
    print(f"NEED TO FIX: {max(0, total_errors - 50)} errors")
    print("="*70)

if __name__ == "__main__":
    main()
