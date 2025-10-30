"""
依赖注入容器
提供统一的服务注册和管理
"""

import inspect
from abc import ABC
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class ServiceLifetime:
    """服务生命周期"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDescriptor:
    """服务描述符"""

    def __init__(
        self,
        service_type: type,
        implementation: type | Callable,
        lifetime: str = ServiceLifetime.TRANSIENT,
        factory: Callable | None = None,
        dependencies: List[type] | None = None
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.lifetime = lifetime
        self.factory = factory
        self.dependencies = dependencies or []
        self.instance = None


class DIContainer:
    """依赖注入容器"""

    def __init__(self):
        self._services: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}
        self._scoped: dict[str, dict[type, Any]] = {}

    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[[], T] = None,
        factory: Callable[[], T] | None = None
    ) -> "DIContainer":
        """
        注册单例服务

        Args:
            service_type: 服务类型
            implementation: 实现类
            factory: 工厂函数

        Returns:
            容器实例
        """
        if implementation is None and factory is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.SINGLETON,
            factory=factory
        )

        self._services[service_type] = descriptor
        return self

    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[[], T] = None,
        factory: Callable[[], T] | None = None
    ) -> "DIContainer":
        """
        注册瞬态服务

        Args:
            service_type: 服务类型
            implementation: 实现类
            factory: 工厂函数

        Returns:
            容器实例
        """
        if implementation is None and factory is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.TRANSIENT,
            factory=factory
        )

        self._services[service_type] = descriptor
        return self

    def register_scoped(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[[], T] = None,
        factory: Callable[[], T] | None = None
    ) -> "DIContainer":
        """
        注册作用域服务

        Args:
            service_type: 服务类型
            implementation: 实现类
            factory: 工厂函数

        Returns:
            容器实例
        """
        if implementation is None and factory is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.SCOPED,
            factory=factory
        )

        self._services[service_type] = descriptor
        return self

    def register_instance(self, service_type: type[T], instance: T) -> "DIContainer":
        """
        注册服务实例

        Args:
            service_type: 服务类型
            instance: 服务实例

        Returns:
            容器实例
        """
        self._singletons[service_type] = instance
        return self

    def resolve(self, service_type: type[T]) -> T:
        """
        解析服务

        Args:
            service_type: 服务类型

        Returns:
            服务实例

        Raises:
            ValueError: 服务未注册
        """
        # 检查是否已注册
        if service_type not in self._services and service_type not in self._singletons:
            # 尝试自动注册
            self._auto_register(service_type)

        # 检查单例
        if service_type in self._singletons:
            return self._singletons[service_type]

        # 获取服务描述符
        if service_type not in self._services:
            raise ValueError(f"服务 {service_type.__name__} 未注册")

        descriptor = self._services[service_type]

        # 根据生命周期创建实例
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type not in self._singletons:
                instance = self._create_instance(descriptor)
                self._singletons[service_type] = instance
            return self._singletons[service_type]

        elif descriptor.lifetime == ServiceLifetime.TRANSIENT:
            return self._create_instance(descriptor)

        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            # 简化实现，这里返回瞬态实例
            # 在实际项目中，应该使用请求上下文来管理作用域
            return self._create_instance(descriptor)

        else:
            raise ValueError(f"不支持的生命周期: {descriptor.lifetime}")

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建服务实例"""
        # 使用工厂函数
        if descriptor.factory:
            return descriptor.factory()

        # 使用实现类
        if inspect.isclass(descriptor.implementation):
            # 检查是否需要依赖注入
            sig = inspect.signature(descriptor.implementation.__init__)
            kwargs = {}

            for param_name, param in sig.parameters.items():
                if param_name != 'self' and param.annotation != inspect.Parameter.empty:
                    try:
                        dependency = self.resolve(param.annotation)
                        kwargs[param_name] = dependency
                    except ValueError:
                        # 依赖未注册，跳过
                        if param.default == inspect.Parameter.empty:
                            # 必需参数缺失，抛出异常
                            raise ValueError(f"无法解析依赖: {param.annotation.__name__}")
                        # 使用默认值

            return descriptor.implementation(**kwargs)

        # 使用可调用对象
        elif callable(descriptor.implementation):
            return descriptor.implementation()

        else:
            raise ValueError(f"无法创建服务实例: {descriptor.service_type.__name__}")

    def _auto_register(self, service_type: type):
        """自动注册服务"""
        if not inspect.isclass(service_type):
            return

        # 检查是否有无参构造函数
        sig = inspect.signature(service_type.__init__)
        if len(sig.parameters) == 1:  # 只有 self参数
            self.register_transient(service_type, service_type)

    def clear_scoped(self, scope_id: str):
        """清理作用域缓存"""
        if scope_id in self._scoped:
            del self._scoped[scope_id]

    def get_registered_services(self) -> dict[type, ServiceDescriptor]:
        """获取已注册的服务"""
        return self._services.copy()

    def is_registered(self, service_type: type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services or service_type in self._singletons


class ServiceLocator:
    """服务定位器"""

    def __init__(self, container: DIContainer):
        self.container = container

    def get(self, service_type: type[T]) -> T:
        """获取服务实例"""
        return self.container.resolve(service_type)

    def try_get(self, service_type: type[T]) -> T | None:
        """尝试获取服务实例"""
        try:
            return self.container.resolve(service_type)
        except ValueError:
            return None


# 全局依赖注入容器
di_container = DIContainer()
service_locator = ServiceLocator(di_container)


# 装饰器
def injectable[T](service_type: type[T], lifetime: str = ServiceLifetime.TRANSIENT):
    """
    可注入服务装饰器

    Args:
        service_type: 服务类型
        lifetime: 生命周期
    """
    def decorator(cls):
        if lifetime == ServiceLifetime.SINGLETON:
            di_container.register_singleton(service_type, cls)
        elif lifetime == ServiceLifetime.TRANSIENT:
            di_container.register_transient(service_type, cls)
        elif lifetime == ServiceLifetime.SCOPED:
            di_container.register_scoped(service_type, cls)
        else:
            raise ValueError(f"不支持的生命周期: {lifetime}")
        return cls
    return decorator


def depends[T](service_type: type[T]) -> T:
    """
    依赖注入便捷函数

    Args:
        service_type: 服务类型

    Returns:
        服务实例
    """
    return service_locator.get(service_type)


def try_depends[T](service_type: type[T]) -> T | None:
    """
    尝试依赖注入便捷函数

    Args:
        service_type: 服务类型

    Returns:
        服务实例或None
    """
    return service_locator.try_get(service_type)


# 服务基类
class BaseService(ABC):
    """服务基类"""

    def __init__(self):
        self._validate_dependencies()

    def _validate_dependencies(self):
        """验证依赖注入"""
        # 子类可以重写此方法来验证依赖
        pass


# 便捷函数
def register_service(
    service_type: type[T],
    implementation: type[T] | Callable[[], T] = None,
    lifetime: str = ServiceLifetime.TRANSIENT
) -> None:
    """注册服务便捷函数"""
    if lifetime == ServiceLifetime.SINGLETON:
        di_container.register_singleton(service_type, implementation)
    elif lifetime == ServiceLifetime.TRANSIENT:
        di_container.register_transient(service_type, implementation)
    elif lifetime == ServiceLifetime.SCOPED:
        di_container.register_scoped(service_type, implementation)
    else:
        raise ValueError(f"不支持的生命周期: {lifetime}")


def get_service[T](service_type: type[T]) -> T:
    """获取服务便捷函数"""
    return service_locator.get(service_type)
