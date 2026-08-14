"""
产权证端点（list/get/create/update/delete）的业务错误传播测试。

验收修复（2026-08-14）：create_certificate 曾用 `except Exception -> 500` 吞掉服务层
`BaseBusinessError`（BusinessValidationError 应为 422、DuplicateResourceError 应为 409、
ResourceNotFoundError 应为 404），导致产权证创建对所有输入一律 500，阻断 ACC-010~014。
五个端点处理器统一补 `except BaseBusinessError: raise` 后，本文件锁定业务异常必须原样
透传给全局异常处理器——除 create 外，list/get/update/delete 四个端点的映射同样钉住
（2026-08-14 两轴复核 D2 补全）。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)


def _build_app() -> FastAPI:
    from src.api.v1.assets import property_certificate as module
    from src.core.exception_handler import setup_exception_handlers

    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(module.router, prefix="/property-certificates")
    app.dependency_overrides[module.get_async_db] = lambda: MagicMock()
    app.dependency_overrides[module.get_current_active_user] = lambda: MagicMock(
        id="user-1"
    )
    # 五个端点（list/get/create/update/delete）均声明 `_authz_ctx` 授权依赖，逐一覆盖，
    # 使业务错误传播测试直达服务层。
    for route in module.router.routes:
        if route.dependant is None:
            continue
        for dependency in route.dependant.dependencies:
            if dependency.name == "_authz_ctx":
                app.dependency_overrides[dependency.call] = lambda: MagicMock()
    return app


def _create_payload() -> dict[str, str]:
    return {
        "certificate_number": "QC-CERT-001",
        "certificate_type": "real_estate",
    }


def test_create_propagates_business_validation_error_as_422() -> None:
    """保存硬门槛校验失败（如缺资产关联）必须返回 422，而不是 500。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.create_certificate = AsyncMock(
        side_effect=BusinessValidationError(
            "property certificate save gate failed",
            field_errors={
                "asset_ids": ["at least one linked asset is required"],
                "holder_party_ids": ["at least one approved holder party is required"],
            },
        )
    )
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.post("/property-certificates", json=_create_payload())

    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["details"]["field_errors"]["asset_ids"] == [
        "at least one linked asset is required"
    ]


def test_create_propagates_duplicate_certificate_number_as_409() -> None:
    """证号全局唯一冲突（REQ-AST-005 硬门槛）必须返回 409，而不是 500。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.create_certificate = AsyncMock(
        side_effect=DuplicateResourceError(
            "产权证", "certificate_number", "QC-CERT-001"
        )
    )
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.post("/property-certificates", json=_create_payload())

    assert response.status_code == 409
    assert response.json()["success"] is False


def test_create_propagates_missing_linked_asset_as_404() -> None:
    """关联资产不存在必须返回 404，而不是 500。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.create_certificate = AsyncMock(
        side_effect=ResourceNotFoundError("资产", "asset-999")
    )
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.post("/property-certificates", json=_create_payload())

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_create_success_still_returns_200() -> None:
    """合法输入仍正常返回 200（修复不得破坏成功路径）。"""
    from datetime import datetime

    from src.api.v1.assets import property_certificate as module
    from src.schemas.property_certificate import PropertyCertificateResponse

    certificate = MagicMock()
    certificate.id = "cert-1"
    certificate.certificate_number = "QC-CERT-001"
    certificate.certificate_type = "real_estate"
    service = MagicMock()
    service.create_certificate = AsyncMock(return_value=certificate)
    app = _build_app()

    response_payload = PropertyCertificateResponse(
        id="cert-1",
        certificate_number="QC-CERT-001",
        certificate_type="real_estate",
        created_at=datetime(2026, 8, 14),
        updated_at=datetime(2026, 8, 14),
    )

    with (
        patch.object(module, "PropertyCertificateService", return_value=service),
        patch.object(
            module, "map_property_certificate_response", return_value=response_payload
        ),
    ):
        with TestClient(app) as client:
            response = client.post("/property-certificates", json=_create_payload())

    assert response.status_code == 200
    service.create_certificate.assert_awaited_once()


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (BusinessValidationError("列表查询参数无效"), 422),
        (DuplicateResourceError("产权证", "certificate_number", "QC-CERT-001"), 409),
        (ResourceNotFoundError("产权证", "cert-999"), 404),
    ],
)
def test_list_propagates_business_errors(error, expected_status) -> None:
    """列表端点的业务异常必须透传（422/409/404），不得被吞成 500。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.list_certificates = AsyncMock(side_effect=error)
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.get("/property-certificates")

    assert response.status_code == expected_status
    assert response.json()["success"] is False


def test_list_unknown_errors_still_return_500() -> None:
    """未知异常仍返回 500（失败要响亮），业务错误修复不得把未知错误一起吞掉。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.list_certificates = AsyncMock(side_effect=RuntimeError("boom"))
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.get("/property-certificates")

    assert response.status_code == 500
    assert response.json()["success"] is False


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (BusinessValidationError("详情查询参数无效"), 422),
        (ResourceNotFoundError("产权证", "cert-999"), 404),
    ],
)
def test_get_propagates_business_errors(error, expected_status) -> None:
    """详情端点的业务异常必须透传，不得被吞成 500。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.get_certificate = AsyncMock(side_effect=error)
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.get("/property-certificates/cert-1")

    assert response.status_code == expected_status
    assert response.json()["success"] is False


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (BusinessValidationError("更新数据校验失败"), 422),
        (DuplicateResourceError("产权证", "certificate_number", "QC-CERT-001"), 409),
        (ResourceNotFoundError("产权证", "cert-999"), 404),
    ],
)
def test_update_propagates_business_errors(error, expected_status) -> None:
    """更新端点的业务异常必须透传，不得被吞成 500。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.get_certificate = AsyncMock(return_value=MagicMock())
    service.update_certificate = AsyncMock(side_effect=error)
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.put("/property-certificates/cert-1", json={})

    assert response.status_code == expected_status
    assert response.json()["success"] is False


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (BusinessValidationError("删除校验失败"), 422),
        (ResourceNotFoundError("产权证", "cert-999"), 404),
    ],
)
def test_delete_propagates_business_errors(error, expected_status) -> None:
    """删除端点的业务异常必须透传，不得被吞成 500。"""
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.get_certificate = AsyncMock(return_value=MagicMock())
    service.delete_certificate = AsyncMock(side_effect=error)
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.delete("/property-certificates/cert-1")

    assert response.status_code == expected_status
    assert response.json()["success"] is False
