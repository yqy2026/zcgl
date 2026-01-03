from sqlalchemy.orm import Session
from ...models.auth import AuditLog, User

class AuditService:
    """审计日志服务"""
    
    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        api_endpoint: str | None = None,
        http_method: str | None = None,
        request_params: str | None = None,
        request_body: str | None = None,
        response_status: int | None = None,
        response_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> AuditLog | None:
        """创建审计日志"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        audit_log = AuditLog(
            user_id=user_id,
            username=user.username,
            user_role=user.role.value if hasattr(user.role, "value") else user.role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            api_endpoint=api_endpoint,
            http_method=http_method,
            request_params=request_params,
            request_body=request_body,
            response_status=response_status,
            response_message=response_message,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log
