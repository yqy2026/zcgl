"""
操作日志模型
记录系统中所有重要操作的审计跟踪
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from ..database import Base


class OperationLog(Base):  # type: ignore[valid-type, misc]
    """操作日志模型"""

    __tablename__ = "operation_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 用户信息
    user_id = Column(String, nullable=False, comment="操作用户ID")
    username = Column(String(100), comment="操作用户名")

    # 操作信息
    action = Column(String(50), nullable=False, comment="操作类型")
    action_name = Column(String(200), comment="操作名称")
    module = Column(String(50), nullable=False, comment="操作模块")
    module_name = Column(String(200), comment="模块名称")

    # 资源信息
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(String(100), comment="资源ID")
    resource_name = Column(String(200), comment="资源名称")

    # 请求信息
    request_method = Column(String(10), comment="HTTP方法")
    request_url = Column(Text, comment="请求URL")
    request_params = Column(Text, comment="请求参数(JSON)")
    request_body = Column(Text, comment="请求体(JSON)")

    # 响应信息
    response_status = Column(Integer, comment="响应状态码")
    response_time = Column(Integer, comment="响应时间(毫秒)")
    error_message = Column(Text, comment="错误消息")

    # 环境信息
    ip_address = Column(String(45), comment="客户端IP")
    user_agent = Column(Text, comment="用户代理")

    # 详情信息
    details = Column(Text, comment="详细信息(JSON)")

    # 时间信息
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<OperationLog(user={self.username}, action={self.action}, resource={self.resource_type}:{self.resource_id})>"
