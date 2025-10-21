"""
任务管理CRUD操作
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from datetime import datetime

from ..models.task import AsyncTask, TaskHistory, ExcelTaskConfig
from ..enums.task import TaskStatus, TaskType, ExcelConfigType
from ..schemas.task import TaskCreate, TaskUpdate, ExcelTaskConfigCreate
from ..exceptions import BusinessLogicError


class TaskCRUD:
    """任务CRUD操作类"""

    def create(self, db: Session, *, obj_in: TaskCreate, user_id: str = None) -> AsyncTask:
        """创建新任务"""
        db_obj = AsyncTask(
            task_type=obj_in.task_type,
            title=obj_in.title,
            description=obj_in.description,
            parameters=obj_in.parameters,
            config=obj_in.config,
            user_id=user_id,
            status=TaskStatus.PENDING,
            progress=0
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # 创建创建历史记录
        self.create_history(
            db=db,
            task_id=db_obj.id,
            action="created",
            message=f"任务 '{db_obj.title}' 已创建",
            user_id=user_id
        )

        return db_obj

    def get(self, db: Session, id: str) -> Optional[AsyncTask]:
        """获取单个任务"""
        return db.query(AsyncTask).filter(AsyncTask.id == id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        order_by: str = "created_at",
        order_dir: str = "desc"
    ) -> List[AsyncTask]:
        """获取任务列表"""
        query = db.query(AsyncTask).filter(AsyncTask.is_active == True)

        # 应用筛选条件
        if task_type:
            query = query.filter(AsyncTask.task_type == task_type)
        if status:
            query = query.filter(AsyncTask.status == status)
        if user_id:
            query = query.filter(AsyncTask.user_id == user_id)
        if created_after:
            query = query.filter(AsyncTask.created_at >= created_after)
        if created_before:
            query = query.filter(AsyncTask.created_at <= created_before)

        # 应用排序
        if hasattr(AsyncTask, order_by):
            order_column = getattr(AsyncTask, order_by)
            if order_dir.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))

        # 应用分页
        return query.offset(skip).limit(limit).all()

    def update(self, db: Session, *, db_obj: AsyncTask, obj_in: TaskUpdate) -> AsyncTask:
        """更新任务"""
        update_data = obj_in.dict(exclude_unset=True)

        # 状态变更特殊处理
        if "status" in update_data:
            old_status = db_obj.status
            new_status = update_data["status"]

            # 开始运行时设置开始时间
            if old_status == TaskStatus.PENDING and new_status == TaskStatus.RUNNING:
                update_data["started_at"] = datetime.utcnow()

            # 完成时设置完成时间
            if old_status in [TaskStatus.PENDING, TaskStatus.RUNNING] and new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                update_data["completed_at"] = datetime.utcnow()

                # 完成时设置进度为100%
                if new_status == TaskStatus.COMPLETED:
                    update_data["progress"] = 100

        # 更新字段
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # 创建历史记录
        if "status" in update_data:
            self.create_history(
                db=db,
                task_id=db_obj.id,
                action="status_changed",
                message=f"任务状态从 {old_status} 变更为 {new_status}",
                user_id=db_obj.user_id,
                details={"old_status": old_status, "new_status": new_status}
            )

        return db_obj

    def delete(self, db: Session, *, id: str) -> AsyncTask:
        """删除任务（软删除）"""
        db_obj = self.get(db, id=id)
        if not db_obj:
            raise BusinessLogicError("任务不存在")

        db_obj.is_active = False
        db.commit()
        db.refresh(db_obj)

        # 创建删除历史记录
        self.create_history(
            db=db,
            task_id=db_obj.id,
            action="deleted",
            message=f"任务 '{db_obj.title}' 已删除",
            user_id=db_obj.user_id
        )

        return db_obj

    def create_history(
        self,
        db: Session,
        *,
        task_id: str,
        action: str,
        message: str,
        user_id: str = None,
        details: Dict[str, Any] = None
    ) -> TaskHistory:
        """创建任务历史记录"""
        history = TaskHistory(
            task_id=task_id,
            action=action,
            message=message,
            user_id=user_id,
            details=details or {}
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        return history

    def get_history(self, db: Session, task_id: str) -> List[TaskHistory]:
        """获取任务历史记录"""
        return db.query(TaskHistory).filter(TaskHistory.task_id == task_id).order_by(desc(TaskHistory.created_at)).all()

    def count(self, db: Session, *, task_type: Optional[str] = None, status: Optional[str] = None) -> int:
        """统计任务数量"""
        query = db.query(AsyncTask).filter(AsyncTask.is_active == True)

        if task_type:
            query = query.filter(AsyncTask.task_type == task_type)
        if status:
            query = query.filter(AsyncTask.status == status)

        return query.count()

    def get_statistics(self, db: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取任务统计信息"""
        base_query = db.query(AsyncTask).filter(AsyncTask.is_active == True)

        if user_id:
            base_query = base_query.filter(AsyncTask.user_id == user_id)

        total_tasks = base_query.count()
        running_tasks = base_query.filter(AsyncTask.status == TaskStatus.RUNNING).count()
        completed_tasks = base_query.filter(AsyncTask.status == TaskStatus.COMPLETED).count()
        failed_tasks = base_query.filter(AsyncTask.status == TaskStatus.FAILED).count()

        # 按类型统计
        by_type = {}
        for task_type in TaskType:
            count = base_query.filter(AsyncTask.task_type == task_type).count()
            if count > 0:
                by_type[task_type.value] = count

        # 按状态统计
        by_status = {}
        for status in TaskStatus:
            count = base_query.filter(AsyncTask.status == status).count()
            if count > 0:
                by_status[status.value] = count

        # 平均持续时间
        completed_tasks_query = base_query.filter(
            and_(
                AsyncTask.status == TaskStatus.COMPLETED,
                AsyncTask.started_at.isnot(None),
                AsyncTask.completed_at.isnot(None)
            )
        )

        avg_duration = 0
        if completed_tasks_query.count() > 0:
            total_duration = sum(
                (task.completed_at - task.started_at).total_seconds()
                for task in completed_tasks_query.all()
            )
            avg_duration = total_duration / completed_tasks_query.count()

        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "by_type": by_type,
            "by_status": by_status,
            "avg_duration": avg_duration
        }


class ExcelTaskConfigCRUD:
    """Excel任务配置CRUD操作类"""

    def create(self, db: Session, *, obj_in: ExcelTaskConfigCreate, user_id: str = None) -> ExcelTaskConfig:
        """创建Excel任务配置"""
        # 如果设置为默认配置，取消其他默认配置
        if obj_in.is_default:
            db.query(ExcelTaskConfig).filter(
                and_(
                    ExcelTaskConfig.config_type == obj_in.config_type,
                    ExcelTaskConfig.task_type == obj_in.task_type,
                    ExcelTaskConfig.is_default == True
                )
            ).update({"is_default": False})

        db_obj = ExcelTaskConfig(
            config_name=obj_in.config_name,
            config_type=obj_in.config_type,
            task_type=obj_in.task_type,
            field_mapping=obj_in.field_mapping,
            validation_rules=obj_in.validation_rules,
            format_config=obj_in.format_config,
            is_default=obj_in.is_default,
            created_by=user_id
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def get(self, db: Session, id: str) -> Optional[ExcelTaskConfig]:
        """获取单个配置"""
        return db.query(ExcelTaskConfig).filter(ExcelTaskConfig.id == id).first()

    def get_default(self, db: Session, config_type: str, task_type: str) -> Optional[ExcelTaskConfig]:
        """获取默认配置"""
        return db.query(ExcelTaskConfig).filter(
            and_(
                ExcelTaskConfig.config_type == config_type,
                ExcelTaskConfig.task_type == task_type,
                ExcelTaskConfig.is_default == True,
                ExcelTaskConfig.is_active == True
            )
        ).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        config_type: Optional[str] = None,
        task_type: Optional[str] = None,
        is_active: bool = True
    ) -> List[ExcelTaskConfig]:
        """获取配置列表"""
        query = db.query(ExcelTaskConfig).filter(ExcelTaskConfig.is_active == is_active)

        if config_type:
            query = query.filter(ExcelTaskConfig.config_type == config_type)
        if task_type:
            query = query.filter(ExcelTaskConfig.task_type == task_type)

        return query.order_by(ExcelTaskConfig.is_default.desc(), ExcelTaskConfig.created_at.desc()).offset(skip).limit(limit).all()

    def update(self, db: Session, *, db_obj: ExcelTaskConfig, obj_in: Dict[str, Any]) -> ExcelTaskConfig:
        """更新配置"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def delete(self, db: Session, *, id: str) -> ExcelTaskConfig:
        """删除配置（软删除）"""
        db_obj = self.get(db, id=id)
        if not db_obj:
            raise BusinessLogicError("配置不存在")

        db_obj.is_active = False
        db.commit()
        db.refresh(db_obj)

        return db_obj


# 创建CRUD实例
task_crud = TaskCRUD()
excel_task_config_crud = ExcelTaskConfigCRUD()