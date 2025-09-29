"""
项目管理相关CRUD操作
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime

from ..models import Project, Asset
from ..schemas.project import ProjectCreate, ProjectUpdate, ProjectSearchRequest


class CRUDProject:
    """项目管理CRUD操作类"""

    def get(self, db: Session, id: str) -> Optional[Project]:
        """获取单个项目"""
        project_obj = db.query(Project).filter(Project.id == id).first()
        if project_obj:
            # 获取权属方关系
            from ..models import ProjectOwnershipRelation, Ownership
            ownership_relations = db.query(ProjectOwnershipRelation, Ownership).join(
                Ownership, ProjectOwnershipRelation.ownership_id == Ownership.id
            ).filter(
                ProjectOwnershipRelation.project_id == id,
                ProjectOwnershipRelation.is_active == True
            ).all()

            # 将关系数据存储为简单属性，而不是SQLAlchemy关系
            project_obj.ownership_relations_data = []
            for relation, ownership in ownership_relations:
                project_obj.ownership_relations_data.append({
                    'id': relation.id,
                    'ownership_id': ownership.id,
                    'ownership_name': ownership.name,
                    'is_active': relation.is_active
                })

        return project_obj

    def get_by_code(self, db: Session, code: str) -> Optional[Project]:
        """通过编码获取项目"""
        return db.query(Project).filter(Project.code == code).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Project]:
        """通过名称获取项目"""
        return db.query(Project).filter(Project.name == name).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> List[Project]:
        """获取多个项目"""
        query = db.query(Project)

        # 应用过滤条件
        if is_active is not None:
            query = query.filter(Project.is_active == is_active)

        if keyword:
            query = query.filter(
                or_(
                    Project.name.contains(keyword),
                    Project.code.contains(keyword),
                    Project.project_description.contains(keyword)
                )
            )

        # 获取项目列表
        projects = query.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()

        # 为每个项目添加权属方关系和资产计数
        from ..models import ProjectOwnershipRelation, Ownership
        for project in projects:
            # 获取权属方关系
            ownership_relations = db.query(ProjectOwnershipRelation, Ownership).join(
                Ownership, ProjectOwnershipRelation.ownership_id == Ownership.id
            ).filter(
                ProjectOwnershipRelation.project_id == project.id,
                ProjectOwnershipRelation.is_active == True
            ).all()

            # 将关系数据存储为简单属性，而不是SQLAlchemy关系
            project.ownership_relations_data = []
            for relation, ownership in ownership_relations:
                ownership_name = ownership.name if ownership else None
                project.ownership_relations_data.append({
                    'id': relation.id,
                    'ownership_id': ownership.id,
                    'ownership_name': ownership_name,
                    'is_active': relation.is_active
                })

            # 添加资产计数
            project.asset_count = self.get_asset_count(db, project.id)

        return projects

    def generate_project_code(self, db: Session, name: str = None) -> str:
        """生成简化的项目编码

        编码规则：[前缀][年月][序号]
        示例：PJ2501001（2025年1月第001个项目）

        Args:
            db: 数据库会话
            name: 项目名称（保留参数以兼容现有代码）

        Returns:
            str: 唯一的项目编码
        """
        from datetime import datetime

        # 固定前缀
        prefix = "PJ"

        # 获取当前年月
        current_date = datetime.now()
        year_month = current_date.strftime("%y%m")  # 如：2501

        # 构建基础编码格式
        base_format = f"{prefix}{year_month}"

        # 查询所有已存在的编码（包括新格式和旧格式）
        existing_codes = db.query(Project.code).filter(
            Project.code.like(f"{prefix}%")
        ).order_by(Project.code.desc()).all()

        # 找到新格式的最大序列号
        max_sequence = 0
        for existing_code in existing_codes:
            code_str = existing_code[0]
            # 新格式：PJ2509001 (9位)
            if len(code_str) == 9 and code_str[:2] == prefix and code_str[2:6].isdigit():
                try:
                    sequence = int(code_str[6:])
                    if sequence > max_sequence:
                        max_sequence = sequence
                except ValueError:
                    continue

        # 如果没有找到新格式编码，从1开始
        if max_sequence == 0:
            max_sequence = 0

        # 尝试生成唯一编码
        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            attempts += 1
            sequence_num = max_sequence + attempts
            sequence_str = f"{sequence_num:03d}"
            code = f"{base_format}{sequence_str}"

            # 检查编码是否已存在
            if not self.get_by_code(db, code):
                return code

        # 如果所有尝试都失败了，返回一个基于时间戳的编码
        import time
        timestamp = int(time.time())
        code = f"{base_format}{timestamp % 1000:03d}"
        return code

    def _generate_name_code(self, name: str) -> str:
        """从项目名称生成语义化编码

        使用增强的拼音映射表，提高编码的语义性
        """
        import re

        # 清理名称
        clean_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', name).strip()

        if not clean_name:
            return "XM"

        # 增强的中文拼音首字母映射
        enhanced_pinyin_map = {
            # 项目管理相关
            '项': 'X', '目': 'M', '工': 'G', '程': 'C', '建': 'J', '设': 'S',
            '开': 'K', '发': 'F', '规': 'G', '划': 'H', '管': 'G', '理': 'L',
            '施': 'S', '工': 'G', '监': 'J', '理': 'L', '运': 'Y', '营': 'Y',
            '维': 'W', '护': 'H', '验': 'Y', '收': 'S',

            # 地产相关
            '房': 'F', '地': 'D', '产': 'C', '园': 'Y', '小': 'X', '区': 'Q',
            '商': 'S', '住': 'Z', '宅': 'Z', '写': 'X', '字': 'Z', '楼': 'L',
            '中': 'Z', '心': 'X', '广': 'G', '场': 'C', '城': 'C', '市': 'S',
            '街': 'J', '道': 'D', '路': 'L', '巷': 'X', '里': 'L', '弄': 'N',

            # 建筑类型
            '大': 'D', '厦': 'S', '楼': 'L', '馆': 'G', '所': 'S', '站': 'Z',
            '堂': 'T', '厅': 'T', '室': 'S', '房': 'F', '间': 'J', '屋': 'W',
            '库': 'K', '棚': 'P', '场': 'C', '地': 'D', '基': 'J', '坑': 'K',

            # 商业用途
            '购': 'G', '物': 'W', '中': 'Z', '心': 'X', '办': 'B', '公': 'G',
            '酒': 'J', '店': 'D', '餐': 'C', '饮': 'Y', '娱': 'Y', '乐': 'L',
            '健': 'J', '身': 'S', '教': 'J', '育': 'Y', '医': 'Y', '疗': 'L',

            # 区域描述
            '新': 'X', '旧': 'J', '高': 'G', '低': 'D', '南': 'N', '北': 'B',
            '东': 'D', '西': 'X', '上': 'S', '下': 'X', '前': 'Q', '后': 'H',
            '左': 'Z', '右': 'Y', '内': 'N', '外': 'W', '中': 'Z', '央': 'Y',

            # 常用词汇
            '国': 'G', '家': 'J', '人': 'R', '民': 'M', '公': 'G', '司': 'S',
            '集': 'J', '团': 'T', '合': 'H', '作': 'Z', '联': 'L', '盟': 'M',
            '世': 'S', '界': 'J', '全': 'Q', '球': 'Q', '亚': 'Y', '洲': 'Z',
        }

        # 生成编码
        code = ''
        for char in clean_name[:6]:  # 最多取前6个字符
            if '\u4e00' <= char <= '\u9fa5':  # 中文字符
                code += enhanced_pinyin_map.get(char, 'X')
            else:
                code += char.upper()

        # 清理编码，只保留字母和数字
        code = re.sub(r'[^A-Z0-9]', '', code)

        # 如果编码为空或太短，使用默认
        if len(code) < 2:
            code = "XM"

        return code[:3]  # 返回最多3位

    def _calculate_checksum(self, code: str) -> str:
        """计算校验位

        使用简单的加权求和算法生成校验位
        """
        if not code:
            return 'A'

        # 权重分配
        weights = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

        # 计算加权和
        total = 0
        for i, char in enumerate(code):
            # 字符转数字（A=1, B=2...）
            if char.isalpha():
                char_value = ord(char.upper()) - ord('A') + 1
            else:
                char_value = int(char)

            # 应用权重（循环使用权重表）
            weight = weights[i % len(weights)]
            total += char_value * weight

        # 计算校验位（A-Z）
        checksum_value = (total % 26) + 1
        return chr(ord('A') + checksum_value - 1)

    def create(self, db: Session, *, obj_in: ProjectCreate, created_by: str = None) -> Project:
        """创建项目"""
        # 检查名称是否已存在
        if self.get_by_name(db, obj_in.name):
            raise ValueError(f"项目名称 {obj_in.name} 已存在")

        # 自动生成编码
        code = self.generate_project_code(db, obj_in.name)

        # 创建数据对象
        create_data = obj_in.dict()
        create_data['code'] = code

        # 提取权属方关系数据
        ownership_relations = create_data.pop('ownership_relations', [])
        ownership_ids = create_data.pop('ownership_ids', [])

        db_obj = Project(
            **create_data,
            created_by=created_by,
            updated_by=created_by
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # 创建权属方关系
        if ownership_relations:
            from ..models import ProjectOwnershipRelation
            for relation in ownership_relations:
                ownership_relation = ProjectOwnershipRelation(
                    project_id=db_obj.id,
                    ownership_id=relation['ownership_id'],
                    is_active=True
                )
                db.add(ownership_relation)
            db.commit()
            db.refresh(db_obj)

        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Project,
        obj_in: ProjectUpdate,
        updated_by: str = None
    ) -> Project:
        """更新项目"""
        # 检查名称是否已被其他项目使用
        if obj_in.name and obj_in.name != db_obj.name:
            existing = self.get_by_name(db, obj_in.name)
            if existing and existing.id != db_obj.id:
                raise ValueError(f"项目名称 {obj_in.name} 已存在")

        update_data = obj_in.dict(exclude_unset=True)
        update_data["updated_by"] = updated_by
        update_data["updated_at"] = datetime.utcnow()

        # 不允许更新编码
        if "code" in update_data:
            del update_data["code"]

        # 提取权属方关系数据
        ownership_relations = update_data.pop('ownership_relations', None)
        ownership_ids = update_data.pop('ownership_ids', None)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # 更新权属方关系
        if ownership_relations is not None:
            from ..models import ProjectOwnershipRelation

            # 删除现有关系
            db.query(ProjectOwnershipRelation).filter(
                ProjectOwnershipRelation.project_id == db_obj.id
            ).delete()

            # 创建新关系
            for relation in ownership_relations:
                ownership_relation = ProjectOwnershipRelation(
                    project_id=db_obj.id,
                    ownership_id=relation['ownership_id'],
                    is_active=True
                )
                db.add(ownership_relation)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: str) -> Project:
        """删除项目"""
        db_obj = self.get(db, id=id)
        if not db_obj:
            raise ValueError(f"项目ID {id} 不存在")

        # 检查是否有关联的资产
        asset_count = db.query(Asset).filter(Asset.project_id == id).count()

        if asset_count > 0:
            raise ValueError(f"该项目还有 {asset_count} 个关联资产，无法删除")

        db.delete(db_obj)
        db.commit()
        return db_obj

    def search(
        self,
        db: Session,
        search_params: ProjectSearchRequest
    ) -> Dict[str, Any]:
        """搜索项目"""
        query = db.query(Project)

        # 应用过滤条件
        if search_params.keyword:
            query = query.filter(
                or_(
                    Project.name.contains(search_params.keyword),
                    Project.code.contains(search_params.keyword),
                    Project.project_description.contains(search_params.keyword)
                )
            )

        if search_params.is_active is not None:
            query = query.filter(Project.is_active == search_params.is_active)

        if search_params.ownership_entity:
            query = query.filter(Project.ownership_entity.contains(search_params.ownership_entity))

        # 如果有ownership_id，需要查询项目-权属方关联表
        if search_params.ownership_id:
            from ..models import ProjectOwnershipRelation
            query = query.join(ProjectOwnershipRelation, Project.id == ProjectOwnershipRelation.project_id).filter(
                ProjectOwnershipRelation.ownership_id == search_params.ownership_id,
                ProjectOwnershipRelation.is_active == True
            )

        # 获取总数
        total = query.count()

        # 分页
        skip = (search_params.page - 1) * search_params.size
        items = query.order_by(desc(Project.created_at)).offset(skip).limit(search_params.size).all()

        # 为每个项目添加权属方关系和资产计数
        from ..models import ProjectOwnershipRelation, Ownership
        for project in items:
            # 获取权属方关系
            ownership_relations = db.query(ProjectOwnershipRelation, Ownership).join(
                Ownership, ProjectOwnershipRelation.ownership_id == Ownership.id
            ).filter(
                ProjectOwnershipRelation.project_id == project.id,
                ProjectOwnershipRelation.is_active == True
            ).all()

            # 将关系数据存储为简单属性，而不是SQLAlchemy关系
            project.ownership_relations_data = []
            for relation, ownership in ownership_relations:
                ownership_name = ownership.name if ownership else None
                project.ownership_relations_data.append({
                    'id': relation.id,
                    'ownership_id': ownership.id,
                    'ownership_name': ownership_name,
                    'is_active': relation.is_active
                })

            # 添加资产计数
            project.asset_count = self.get_asset_count(db, project.id)

        # 计算页数
        pages = (total + search_params.size - 1) // search_params.size

        return {
            "items": items,
            "total": total,
            "page": search_params.page,
            "size": search_params.size,
            "pages": pages
        }

    def get_statistics(self, db: Session) -> Dict[str, Any]:
        """获取项目统计信息"""
        # 基础统计
        total_count = db.query(Project).count()
        active_count = db.query(Project).filter(Project.is_active == True).count()
        inactive_count = total_count - active_count

        # 最近创建的项目
        recent_created = db.query(Project).order_by(desc(Project.created_at)).limit(5).all()

        # 项目类型分布
        type_distribution = {}
        project_types = db.query(Project.project_type).filter(Project.project_type.isnot(None)).all()
        for pt in project_types:
            type_distribution[pt.project_type] = type_distribution.get(pt.project_type, 0) + 1

        # 项目状态分布
        status_distribution = {}
        project_statuses = db.query(Project.project_status).filter(Project.project_status.isnot(None)).all()
        for ps in project_statuses:
            status_distribution[ps.project_status] = status_distribution.get(ps.project_status, 0) + 1

        # 城市分布
        city_distribution = {}
        project_cities = db.query(Project.city).filter(Project.city.isnot(None)).all()
        for pc in project_cities:
            city_distribution[pc.city] = city_distribution.get(pc.city, 0) + 1

        # 投资统计
        investment_stats = {
            "total_investment": sum(p.total_investment or 0 for p in db.query(Project).filter(Project.total_investment.isnot(None)).all()),
            "total_budget": sum(p.project_budget or 0 for p in db.query(Project).filter(Project.project_budget.isnot(None)).all()),
            "project_count": total_count
        }

        return {
            "total_count": total_count,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "recent_created": recent_created,
            "type_distribution": type_distribution,
            "status_distribution": status_distribution,
            "city_distribution": city_distribution,
            "investment_stats": investment_stats
        }

    def get_asset_count(self, db: Session, project_id: str) -> int:
        """获取项目关联的资产数量"""
        return db.query(Asset).filter(Asset.project_id == project_id).count()

    def toggle_status(self, db: Session, *, id: str, updated_by: str = None) -> Project:
        """切换项目状态"""
        db_obj = self.get(db, id=id)
        if not db_obj:
            raise ValueError(f"项目ID {id} 不存在")

        db_obj.is_active = not db_obj.is_active
        db_obj.updated_by = updated_by
        db_obj.updated_at = datetime.utcnow()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_dropdown_options(self, db: Session) -> List[Dict[str, Any]]:
        """获取下拉选项"""
        projects = db.query(Project).filter(Project.is_active == True).order_by(Project.name).all()
        return [
            {
                "id": project.id,
                "name": project.name,
                "code": project.code
            }
            for project in projects
        ]


# 创建CRUD实例
project = CRUDProject()