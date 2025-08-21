"""
简化版后端API - 用于快速启动和测试
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
from datetime import datetime
import uuid

# 创建FastAPI应用
app = FastAPI(
    title="土地物业资产管理系统 API",
    description="简化版API，用于快速启动和演示",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class Asset(BaseModel):
    id: Optional[str] = None
    property_name: str
    ownership_entity: str
    management_entity: Optional[str] = None
    address: str
    land_area: Optional[float] = None
    actual_property_area: Optional[float] = None
    rentable_area: Optional[float] = None
    rented_area: Optional[float] = None
    unrented_area: Optional[float] = None
    non_commercial_area: Optional[float] = None
    ownership_status: str = "未确权"
    certificated_usage: Optional[str] = None
    actual_usage: Optional[str] = None
    business_category: Optional[str] = None
    usage_status: str = "闲置"
    is_litigated: Optional[str] = "否"
    property_nature: str = "经营类"
    business_model: Optional[str] = None
    include_in_occupancy_rate: Optional[str] = "是"
    occupancy_rate: Optional[str] = "0%"
    lease_contract: Optional[str] = None
    current_contract_start_date: Optional[str] = None
    current_contract_end_date: Optional[str] = None
    tenant_name: Optional[str] = None
    ownership_category: Optional[str] = None
    current_lease_contract: Optional[str] = None
    wuyang_project_name: Optional[str] = None
    agreement_start_date: Optional[str] = None
    agreement_end_date: Optional[str] = None
    current_terminal_contract: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# 初始化SQLite数据库
def init_db():
    conn = sqlite3.connect('assets.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY,
            property_name TEXT NOT NULL,
            ownership_entity TEXT NOT NULL,
            management_entity TEXT,
            address TEXT NOT NULL,
            land_area REAL,
            actual_property_area REAL,
            rentable_area REAL,
            rented_area REAL,
            unrented_area REAL,
            non_commercial_area REAL,
            ownership_status TEXT DEFAULT '未确权',
            certificated_usage TEXT,
            actual_usage TEXT,
            business_category TEXT,
            usage_status TEXT DEFAULT '闲置',
            is_litigated TEXT DEFAULT '否',
            property_nature TEXT DEFAULT '经营类',
            business_model TEXT,
            include_in_occupancy_rate TEXT DEFAULT '是',
            occupancy_rate TEXT DEFAULT '0%',
            lease_contract TEXT,
            current_contract_start_date TEXT,
            current_contract_end_date TEXT,
            tenant_name TEXT,
            ownership_category TEXT,
            current_lease_contract TEXT,
            wuyang_project_name TEXT,
            agreement_start_date TEXT,
            agreement_end_date TEXT,
            current_terminal_contract TEXT,
            description TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # 插入演示数据
    cursor.execute('SELECT COUNT(*) FROM assets')
    if cursor.fetchone()[0] == 0:
        demo_assets = [
            {
                'id': str(uuid.uuid4()),
                'property_name': '示例商业大厦A座',
                'ownership_entity': '示例集团有限公司',
                'management_entity': '示例物业管理公司',
                'address': '广东省广州市天河区珠江新城示例路123号',
                'land_area': 5000.0,
                'actual_property_area': 12000.0,
                'rentable_area': 10000.0,
                'rented_area': 8000.0,
                'unrented_area': 2000.0,
                'non_commercial_area': 2000.0,
                'ownership_status': '已确权',
                'certificated_usage': '商业',
                'actual_usage': '办公、商业',
                'business_category': '写字楼',
                'usage_status': '出租',
                'is_litigated': '否',
                'property_nature': '经营类',
                'business_model': '整体出租',
                'include_in_occupancy_rate': '是',
                'occupancy_rate': '80.00%',
                'lease_contract': 'HT-2024-001',
                'tenant_name': '示例科技有限公司',
                'description': '位于珠江新城核心区域的高端商业大厦',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'property_name': '示例工业园B区',
                'ownership_entity': '示例实业有限公司',
                'address': '广东省深圳市宝安区示例工业园区',
                'land_area': 15000.0,
                'actual_property_area': 8000.0,
                'rentable_area': 7000.0,
                'rented_area': 5000.0,
                'unrented_area': 2000.0,
                'non_commercial_area': 1000.0,
                'ownership_status': '已确权',
                'certificated_usage': '工业',
                'actual_usage': '生产制造',
                'business_category': '制造业',
                'usage_status': '出租',
                'is_litigated': '否',
                'property_nature': '经营类',
                'occupancy_rate': '71.43%',
                'description': '现代化工业园区，配套设施完善',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'property_name': '示例住宅小区',
                'ownership_entity': '示例房地产开发有限公司',
                'address': '广东省广州市番禺区示例住宅区',
                'land_area': 20000.0,
                'actual_property_area': 50000.0,
                'rentable_area': 0.0,
                'rented_area': 0.0,
                'unrented_area': 0.0,
                'non_commercial_area': 50000.0,
                'ownership_status': '部分确权',
                'certificated_usage': '住宅',
                'actual_usage': '住宅',
                'business_category': '住宅',
                'usage_status': '自用',
                'is_litigated': '否',
                'property_nature': '非经营类',
                'occupancy_rate': '0%',
                'description': '高品质住宅小区，环境优美',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        for asset in demo_assets:
            placeholders = ', '.join(['?' for _ in asset.keys()])
            columns = ', '.join(asset.keys())
            cursor.execute(f'INSERT INTO assets ({columns}) VALUES ({placeholders})', list(asset.values()))
    
    conn.commit()
    conn.close()

# 启动时初始化数据库
init_db()

# API路由
@app.get("/")
def root():
    return {"message": "土地物业资产管理系统 API 正在运行", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/assets", response_model=dict)
def get_assets(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    ownership_status: Optional[str] = None,
    property_nature: Optional[str] = None,
    usage_status: Optional[str] = None
):
    """获取资产列表"""
    conn = sqlite3.connect('assets.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 构建查询条件
    where_conditions = []
    params = []
    
    if search:
        where_conditions.append("(property_name LIKE ? OR ownership_entity LIKE ? OR address LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    if ownership_status:
        where_conditions.append("ownership_status = ?")
        params.append(ownership_status)
    
    if property_nature:
        where_conditions.append("property_nature = ?")
        params.append(property_nature)
    
    if usage_status:
        where_conditions.append("usage_status = ?")
        params.append(usage_status)
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # 获取总数
    cursor.execute(f"SELECT COUNT(*) FROM assets WHERE {where_clause}", params)
    total = cursor.fetchone()[0]
    
    # 获取分页数据
    offset = (page - 1) * limit
    cursor.execute(f"""
        SELECT * FROM assets 
        WHERE {where_clause} 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    
    assets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "data": assets,
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": (page * limit) < total,
        "has_prev": page > 1
    }

@app.get("/api/assets/{asset_id}", response_model=Asset)
def get_asset(asset_id: str):
    """获取单个资产"""
    conn = sqlite3.connect('assets.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
    asset = cursor.fetchone()
    conn.close()
    
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    return dict(asset)

@app.post("/api/assets", response_model=Asset)
def create_asset(asset: Asset):
    """创建资产"""
    conn = sqlite3.connect('assets.db')
    cursor = conn.cursor()
    
    asset_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    asset_dict = asset.dict()
    asset_dict['id'] = asset_id
    asset_dict['created_at'] = now
    asset_dict['updated_at'] = now
    
    # 自动计算出租率
    if asset_dict.get('rentable_area') and asset_dict.get('rented_area'):
        occupancy_rate = (asset_dict['rented_area'] / asset_dict['rentable_area']) * 100
        asset_dict['occupancy_rate'] = f"{occupancy_rate:.2f}%"
    
    # 自动计算未出租面积
    if asset_dict.get('rentable_area') and asset_dict.get('rented_area'):
        asset_dict['unrented_area'] = asset_dict['rentable_area'] - asset_dict['rented_area']
    
    placeholders = ', '.join(['?' for _ in asset_dict.keys()])
    columns = ', '.join(asset_dict.keys())
    cursor.execute(f'INSERT INTO assets ({columns}) VALUES ({placeholders})', list(asset_dict.values()))
    
    conn.commit()
    conn.close()
    
    return asset_dict

@app.put("/api/assets/{asset_id}", response_model=Asset)
def update_asset(asset_id: str, asset: Asset):
    """更新资产"""
    conn = sqlite3.connect('assets.db')
    cursor = conn.cursor()
    
    # 检查资产是否存在
    cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="资产不存在")
    
    asset_dict = asset.dict()
    asset_dict['updated_at'] = datetime.now().isoformat()
    
    # 自动计算出租率
    if asset_dict.get('rentable_area') and asset_dict.get('rented_area'):
        occupancy_rate = (asset_dict['rented_area'] / asset_dict['rentable_area']) * 100
        asset_dict['occupancy_rate'] = f"{occupancy_rate:.2f}%"
    
    # 自动计算未出租面积
    if asset_dict.get('rentable_area') and asset_dict.get('rented_area'):
        asset_dict['unrented_area'] = asset_dict['rentable_area'] - asset_dict['rented_area']
    
    # 构建更新语句
    set_clause = ', '.join([f"{key} = ?" for key in asset_dict.keys() if key != 'id'])
    values = [value for key, value in asset_dict.items() if key != 'id']
    values.append(asset_id)
    
    cursor.execute(f"UPDATE assets SET {set_clause} WHERE id = ?", values)
    conn.commit()
    
    # 返回更新后的数据
    cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
    conn.row_factory = sqlite3.Row
    updated_asset = dict(cursor.fetchone())
    conn.close()
    
    return updated_asset

@app.delete("/api/assets/{asset_id}")
def delete_asset(asset_id: str):
    """删除资产"""
    conn = sqlite3.connect('assets.db')
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="资产不存在")
    
    conn.commit()
    conn.close()
    
    return {"message": "资产删除成功"}

@app.get("/api/assets/stats/overview")
def get_assets_stats():
    """获取资产统计概览"""
    conn = sqlite3.connect('assets.db')
    cursor = conn.cursor()
    
    # 总体统计
    cursor.execute("""
        SELECT 
            COUNT(*) as total_count,
            SUM(actual_property_area) as total_area,
            AVG(actual_property_area) as avg_area,
            SUM(rentable_area) as total_rentable_area,
            SUM(rented_area) as total_rented_area
        FROM assets
    """)
    
    stats = cursor.fetchone()
    
    # 按性质分组统计
    cursor.execute("""
        SELECT property_nature, COUNT(*) as count, SUM(actual_property_area) as total_area
        FROM assets 
        GROUP BY property_nature
    """)
    nature_stats = cursor.fetchall()
    
    # 按状态分组统计
    cursor.execute("""
        SELECT usage_status, COUNT(*) as count
        FROM assets 
        GROUP BY usage_status
    """)
    status_stats = cursor.fetchall()
    
    # 按确权状态分组统计
    cursor.execute("""
        SELECT ownership_status, COUNT(*) as count
        FROM assets 
        GROUP BY ownership_status
    """)
    ownership_stats = cursor.fetchall()
    
    conn.close()
    
    total_rentable = stats[3] or 0
    total_rented = stats[4] or 0
    occupancy_rate = (total_rented / total_rentable * 100) if total_rentable > 0 else 0
    
    return {
        "total_count": stats[0] or 0,
        "total_area": stats[1] or 0,
        "avg_area": stats[2] or 0,
        "total_rentable_area": total_rentable,
        "total_rented_area": total_rented,
        "occupancy_rate": occupancy_rate,
        "by_nature": [
            {"nature": row[0], "count": row[1], "total_area": row[2] or 0}
            for row in nature_stats
        ],
        "by_status": [
            {"status": row[0], "count": row[1]}
            for row in status_stats
        ],
        "by_ownership": [
            {"ownership_status": row[0], "count": row[1]}
            for row in ownership_stats
        ]
    }

if __name__ == "__main__":
    print("🚀 启动土地物业资产管理系统 - 简化版API")
    print("📱 访问地址:")
    print("   API: http://localhost:8001")
    print("   文档: http://localhost:8001/docs")
    print("   健康检查: http://localhost:8001/health")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)