"""Property Certificate Models - 产权证管理数据模型"""

from enum import Enum


class CertificateType(str, Enum):
    """产权证类型"""

    REAL_ESTATE = "real_estate"  # 不动产权证（新版）
    HOUSE_OWNERSHIP = "house_ownership"  # 房屋所有权证（旧版）
    LAND_USE = "land_use"  # 土地使用证
    OTHER = "other"  # 其他权属证明


class OwnerType(str, Enum):
    """权利人类型"""

    INDIVIDUAL = "individual"  # 个人
    ORGANIZATION = "organization"  # 组织/企业
    JOINT = "joint"  # 共有

