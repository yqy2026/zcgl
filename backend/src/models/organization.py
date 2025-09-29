"""
组织架构相关数据库模型
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..database import Base


class Organization(Base):
    """组织架构模型"""
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 基本信息
    name = Column(String(200), nullable=False, comment="组织名称")
    level = Column(Integer, nullable=False, default=1, comment="组织层级")
    sort_order = Column(Integer, default=0, comment="排序")
    
    # 层级关系
    parent_id = Column(String, ForeignKey("organizations.id"), comment="上级组织ID")
    path = Column(String(1000), comment="组织路径，用/分隔")
    
    # 描述信息
    description = Column(Text, comment="组织描述")
    functions = Column(Text, comment="主要职能")
    
    # 系统信息
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")
    
    # 关系定义
    parent = relationship("Organization", remote_side=[id], back_populates="children")
    children = relationship("Organization", back_populates="parent", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="organization", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="organization")
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name})>"


class Position(Base):
    """职位模型"""
    __tablename__ = "positions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 基本信息
    name = Column(String(100), nullable=False, comment="职位名称")
    level = Column(Integer, nullable=False, default=1, comment="职位级别")
    category = Column(String(50), comment="职位类别")
    
    # 所属组织
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, comment="所属组织ID")
    
    # 职位描述
    description = Column(Text, comment="职位描述")
    responsibilities = Column(Text, comment="岗位职责")
    requirements = Column(Text, comment="任职要求")
    
    # 薪资范围
    salary_min = Column(Integer, comment="最低薪资")
    salary_max = Column(Integer, comment="最高薪资")
    
    # 状态信息
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")
    
    # 关系定义
    organization = relationship("Organization", back_populates="positions")
    employees = relationship("Employee", back_populates="position")
    
    def __repr__(self):
        return f"<Position(id={self.id}, name={self.name})>"


class Employee(Base):
    """员工模型"""
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 基本信息
    employee_no = Column(String(50), unique=True, nullable=False, comment="员工编号")
    name = Column(String(100), nullable=False, comment="姓名")
    gender = Column(String(10), comment="性别")
    birth_date = Column(DateTime, comment="出生日期")
    id_card = Column(String(20), comment="身份证号")
    
    # 联系信息
    emergency_contact = Column(String(100), comment="紧急联系人")
    emergency_phone = Column(String(20), comment="紧急联系电话")
    
    # 组织关系
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, comment="所属组织ID")
    position_id = Column(String, ForeignKey("positions.id"), comment="职位ID")
    direct_supervisor_id = Column(String, ForeignKey("employees.id"), comment="直接上级ID")
    
    # 工作信息
    hire_date = Column(DateTime, comment="入职日期")
    probation_end_date = Column(DateTime, comment="试用期结束日期")
    employment_type = Column(String(20), comment="用工类型(full_time/part_time/contract/intern)")
    work_location = Column(String(200), comment="工作地点")
    
    # 薪资信息
    base_salary = Column(Integer, comment="基本工资")
    performance_salary = Column(Integer, comment="绩效工资")
    total_salary = Column(Integer, comment="总薪资")
    
    # 状态信息
    resignation_date = Column(DateTime, comment="离职日期")
    resignation_reason = Column(Text, comment="离职原因")
    
    # 其他信息
    education = Column(String(50), comment="学历")
    major = Column(String(100), comment="专业")
    skills = Column(Text, comment="技能")
    notes = Column(Text, comment="备注")
    
    # 系统信息
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")
    
    # 关系定义
    organization = relationship("Organization", back_populates="employees")
    position = relationship("Position", back_populates="employees")
    direct_supervisor = relationship("Employee", remote_side=[id], back_populates="subordinates")
    subordinates = relationship("Employee", back_populates="direct_supervisor")
    
    def __repr__(self):
        return f"<Employee(id={self.id}, name={self.name}, employee_no={self.employee_no})>"


class OrganizationHistory(Base):
    """组织架构变更历史"""
    __tablename__ = "organization_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, comment="组织ID")
    
    # 变更信息
    action = Column(String(20), nullable=False, comment="操作类型(create/update/delete)")
    field_name = Column(String(100), comment="变更字段")
    old_value = Column(Text, comment="原值")
    new_value = Column(Text, comment="新值")
    change_reason = Column(String(500), comment="变更原因")
    
    # 操作信息
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="操作时间")
    created_by = Column(String(100), comment="操作人")
    
    # 关系
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<OrganizationHistory(id={self.id}, action={self.action})>"