"""Asset CRUD shared helpers.

集中承载与 AssetCRUD 无直接业务耦合的类型别名、结果链调用辅助函数、
以及敏感字段加解密处理器，避免 `asset.py` 持续膨胀。
"""

import logging
from collections.abc import Awaitable, Iterable
from inspect import isawaitable
from typing import Any, Protocol, TypeVar, cast, overload

AssetMutationData = dict[str, Any]
AssetFilterData = dict[str, Any]
AssetIdentifier = str | int

TResultRow = TypeVar("TResultRow")
TScalar = TypeVar("TScalar")
TResultRow_co = TypeVar("TResultRow_co", covariant=True)
TScalar_co = TypeVar("TScalar_co", covariant=True)
TMaybeAwaitable = TypeVar("TMaybeAwaitable")

logger = logging.getLogger(__name__)


class SupportsAll(Protocol[TResultRow_co]):
    """Protocol for results supporting .all()."""

    def all(self) -> Iterable[TResultRow_co] | Awaitable[Iterable[TResultRow_co]]: ...


class SupportsFirst(Protocol[TResultRow_co]):
    """Protocol for results supporting .first()."""

    def first(self) -> TResultRow_co | None | Awaitable[TResultRow_co | None]: ...


class SupportsScalar(Protocol[TScalar_co]):
    """Protocol for results supporting .scalar()."""

    def scalar(self) -> TScalar_co | None | Awaitable[TScalar_co | None]: ...


class ScalarResultLike(
    SupportsAll[TScalar_co], SupportsFirst[TScalar_co], Protocol[TScalar_co]
):
    """Protocol for scalar result proxies from .scalars()."""


class SupportsScalars(Protocol[TScalar_co]):
    """Protocol for results supporting .scalars()."""

    def scalars(
        self,
    ) -> ScalarResultLike[TScalar_co] | Awaitable[ScalarResultLike[TScalar_co]]: ...


async def _resolve_maybe_awaitable(
    value: TMaybeAwaitable | Awaitable[TMaybeAwaitable],
) -> TMaybeAwaitable:
    if isawaitable(value):
        return await cast(Awaitable[TMaybeAwaitable], value)
    return value


async def _result_all(result: SupportsAll[Any]) -> list[TResultRow]:
    """兼容真实 AsyncSession 与测试 AsyncMock 的 result.all() 行为。"""
    all_result = await _resolve_maybe_awaitable(result.all())
    return list(cast(Iterable[TResultRow], all_result))


async def _scalars_all(result: SupportsScalars[Any]) -> list[TScalar]:
    """兼容真实 AsyncSession 与测试 AsyncMock 的 result.scalars().all() 行为。"""
    scalar_result = await _resolve_maybe_awaitable(result.scalars())
    all_result = await _resolve_maybe_awaitable(scalar_result.all())
    return list(cast(Iterable[TScalar], all_result))


async def _scalars_first(result: SupportsScalars[Any]) -> TScalar | None:
    """兼容真实 AsyncSession 与测试 AsyncMock 的 result.scalars().first() 行为。"""
    scalar_result = await _resolve_maybe_awaitable(result.scalars())
    return cast(TScalar | None, await _resolve_maybe_awaitable(scalar_result.first()))


async def _result_first(result: SupportsFirst[Any]) -> TResultRow | None:
    """兼容真实 AsyncSession 与测试 AsyncMock 的 result.first() 行为。"""
    return cast(TResultRow | None, await _resolve_maybe_awaitable(result.first()))


async def _result_scalar(result: SupportsScalar[Any]) -> TScalar | None:
    """兼容真实 AsyncSession 与测试 AsyncMock 的 result.scalar() 行为。"""
    return cast(TScalar | None, await _resolve_maybe_awaitable(result.scalar()))


class SensitiveDataHandler:
    """
    敏感数据处理器 - PII字段加密

    支持两种加密模式：
    - 确定性加密 (AES-256-CBC with derived IV): 用于可搜索字段（手机号等）
    - 标准加密 (AES-256-GCM): 用于非搜索字段

    使用方法：
    # 在子类中定义敏感字段
    class MySensitiveDataHandler(SensitiveDataHandler):
        SEARCHABLE_FIELDS = {"phone", "id_card"}
        NON_SEARCHABLE_FIELDS = {"note"}
    """

    # 默认无敏感字段（子类应覆盖）
    SEARCHABLE_FIELDS: set[str] = set()
    NON_SEARCHABLE_FIELDS: set[str] = set()
    ALL_PII_FIELDS = SEARCHABLE_FIELDS | NON_SEARCHABLE_FIELDS

    def __init__(
        self,
        searchable_fields: set[str] | None = None,
        non_searchable_fields: set[str] | None = None,
    ) -> None:
        """
        初始化敏感数据处理器

        Args:
            searchable_fields: 需要加密且可搜索的字段（如手机号）
            non_searchable_fields: 需要加密但不需要搜索的字段（如备注）
        """
        # 如果提供了参数，使用参数；否则使用类属性
        if searchable_fields is not None:
            self.SEARCHABLE_FIELDS = searchable_fields
        if non_searchable_fields is not None:
            self.NON_SEARCHABLE_FIELDS = non_searchable_fields
        self.ALL_PII_FIELDS = self.SEARCHABLE_FIELDS | self.NON_SEARCHABLE_FIELDS

        from ..core.encryption import EncryptionKeyManager, FieldEncryptor

        key_manager = EncryptionKeyManager()
        self.encryptor = FieldEncryptor(key_manager)
        self.encryption_enabled = key_manager.is_available()

        if not self.encryption_enabled:
            logger.warning(
                "Encryption disabled: DATA_ENCRYPTION_KEY not set or invalid. "
                "PII data will be stored in plaintext."
            )

    def encrypt_field(self, field_name: str, value: object) -> object:
        """
        加密单个字段

        Args:
            field_name: 字段名称
            value: 字段值

        Returns:
            加密后的值，如果不是PII字段或加密失败则返回原值
        """
        if not self.encryption_enabled or value is None:
            return value

        # 使用确定性加密（可搜索）
        if field_name in self.SEARCHABLE_FIELDS:
            encrypted = self.encryptor.encrypt_deterministic(str(value))
            return value if encrypted is None else encrypted

        # 使用标准加密（不可搜索）
        if field_name in self.NON_SEARCHABLE_FIELDS:
            encrypted = self.encryptor.encrypt_standard(str(value))
            return value if encrypted is None else encrypted

        # 非PII字段，返回原值
        return value

    def decrypt_field(self, field_name: str, value: object) -> object:
        """
        解密单个字段

        Args:
            field_name: 字段名称
            value: 字段值（可能已加密）

        Returns:
            解密后的值，如果不是加密格式则返回原值
            注意：真正的解密错误（如密钥错误）会返回 None
        """
        if not self.encryption_enabled or value is None:
            return value

        # 使用确定性解密
        if field_name in self.SEARCHABLE_FIELDS:
            return self.encryptor.decrypt_deterministic(str(value))

        # 使用标准解密
        if field_name in self.NON_SEARCHABLE_FIELDS:
            return self.encryptor.decrypt_standard(str(value))

        # 非PII字段，返回原值
        return value

    @overload
    def encrypt_data(self, data: AssetMutationData) -> AssetMutationData: ...

    @overload
    def encrypt_data(
        self, data: list[AssetMutationData]
    ) -> list[AssetMutationData]: ...

    def encrypt_data(
        self, data: AssetMutationData | list[AssetMutationData]
    ) -> AssetMutationData | list[AssetMutationData]:
        """
        批量加密数据中的PII字段

        Args:
            data: 字典或字典列表

        Returns:
            加密后的数据（原地修改）
        """
        if isinstance(data, dict):
            for field_name in self.ALL_PII_FIELDS:
                if field_name in data:
                    data[field_name] = self.encrypt_field(field_name, data[field_name])
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field_name in self.ALL_PII_FIELDS:
                        if field_name in item:
                            item[field_name] = self.encrypt_field(
                                field_name, item[field_name]
                            )
        return data

    @overload
    def decrypt_data(self, data: AssetMutationData) -> AssetMutationData: ...

    @overload
    def decrypt_data(
        self, data: list[AssetMutationData]
    ) -> list[AssetMutationData]: ...

    def decrypt_data(
        self, data: AssetMutationData | list[AssetMutationData]
    ) -> AssetMutationData | list[AssetMutationData]:
        """
        批量解密数据中的PII字段

        Args:
            data: 字典或字典列表

        Returns:
            解密后的数据（原地修改）
        """
        if isinstance(data, dict):
            for field_name in self.ALL_PII_FIELDS:
                if field_name in data and data[field_name] is not None:
                    data[field_name] = self.decrypt_field(field_name, data[field_name])
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field_name in self.ALL_PII_FIELDS:
                        if field_name in item and item[field_name] is not None:
                            item[field_name] = self.decrypt_field(
                                field_name, item[field_name]
                            )
        return data
