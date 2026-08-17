"""静态路径遮蔽回归测试（2026-08-17 点检缺陷 2.1/2.2/2.3）。

FastAPI 按声明顺序匹配路由：单段动态路由 ``/{id}`` 若先于静态路径声明，
会把 ``/types``、``/statistics`` 等静态段吸收成 id 参数（查无此记录 → 404），
表现为「OpenAPI 可见、运行时不可达」。历史缺陷：

- asset-custom-fields：``GET /types`` 被 ``/{field_id}`` 遮蔽，
  同时存在 ``/types/list[Any]`` 垃圾路径与前端 ``/types/list`` 三方错位；
- tasks：``/statistics``、``/running``、``/recent``、``/cleanup``
  被 ``/{task_id}`` 遮蔽；
- enum-fields：``/types/categories/list[Any]`` 字面量路径污染 OpenAPI。

本文件钉住「静态路径前置 + 全仓无 ``[Any]`` 路径残留」。
"""

import pytest

pytestmark = pytest.mark.api


def _paths(router) -> list[str]:
    return [route.path for route in router.routes]


def test_custom_field_types_route_should_precede_field_id() -> None:
    """GET /types 必须先于 /{field_id} 声明，否则被吸收为 field_id="types"。"""
    from src.api.v1.assets.custom_fields import router

    paths = _paths(router)
    assert "/types" in paths
    assert paths.index("/types") < paths.index("/{field_id}")


def test_custom_fields_should_not_contain_any_literal_paths() -> None:
    from src.api.v1.assets.custom_fields import router

    assert not any("[Any]" in path for path in _paths(router))


def test_tasks_static_routes_should_precede_task_id() -> None:
    """/statistics、/running、/recent、/cleanup 均须先于 /{task_id} 声明。"""
    from src.api.v1.system.tasks import router

    paths = _paths(router)
    detail_index = paths.index("/tasks/{task_id}")
    for static_path in (
        "/tasks/statistics",
        "/tasks/running",
        "/tasks/recent",
        "/tasks/cleanup",
    ):
        assert static_path in paths, static_path
        assert paths.index(static_path) < detail_index, static_path


def test_enum_field_categories_route_should_be_plain() -> None:
    """枚举类别列表路径应为 /types/categories/list，不得残留 [Any] 字面量。"""
    from src.api.v1.system.enum_field import router

    paths = _paths(router)
    assert "/enum-fields/types/categories/list" in paths
    assert not any("[Any]" in path for path in paths)


def test_api_router_should_have_no_any_literal_paths() -> None:
    """全仓守卫：任何已挂载路由路径不得包含 [Any] 类型注解残留。"""
    from src.api.v1 import api_router

    polluted = [
        route.path
        for route in api_router.routes
        if "[Any]" in getattr(route, "path", "")
    ]
    assert polluted == []
