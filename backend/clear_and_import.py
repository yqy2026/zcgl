#!/usr/bin/env python3
"""
清理系统测试数据并导入新的Excel文件
"""

import os
import sys
import pandas as pd
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import SessionLocal, drop_tables, create_tables
from models.asset import Asset
from schemas.asset import AssetCreate
from crud.asset import asset_crud


def clear_all_data():
    """清理所有数据"""
    print("正在清理数据库...")
    
    # 删除所有表
    drop_tables()
    print("✓ 已删除所有数据表")
    
    # 重新创建表
    create_tables()
    print("✓ 已重新创建数据表")


def import_excel_data(excel_file_path: str):
    """导入Excel数据"""
    if not os.path.exists(excel_file_path):
        print(f"❌ Excel文件不存在: {excel_file_path}")
        return False
    
    print(f"正在导入Excel文件: {excel_file_path}")
    
    try:
        # 读取Excel文件
        df = pd.read_excel(excel_file_path)
        print(f"✓ 成功读取Excel文件，共 {len(df)} 行数据")
        
        # 显示列名
        print(f"Excel列名: {list(df.columns)}")
        
        # 字段映射 - 根据实际Excel文件的列名进行映射
        field_mapping = {
            # 根据实际Excel文件的列名映射
            "物业名称": "property_name",
            "权属方": "ownership_entity", 
            "经营管理方": "management_entity",
            "所在地址": "address",
            "土地面积\n(平方米)": "land_area",
            " 实际房产面积\n(平方米) ": "actual_property_area",
            " 经营性物业可出租面积\n(平方米\n) ": "rentable_area",
            " 经营性物业已出租面积\n(平方米) ": "rented_area",
            "经营性物业未出租面积\n(平方米)": "unrented_area",
            "非经营物业面积\n(平方米)": "non_commercial_area",
            "是否确权\n（已确权、未确权、部分确权）": "ownership_status",
            "证载用途\n（商业、住宅、办公、厂房、车位..）": "certificated_usage",
            "实际用途\n（商业、住宅、办公、厂房、车位..）": "actual_usage",
            "业态类别": "business_category",
            "物业使用状态\n（出租、闲置、自用、公房、其他）": "usage_status",
            "是否涉诉": "is_litigated",
            "物业性质（经营类、非经营类）": "property_nature",
            "经营模式": "business_model",
            "是否计入出租率": "include_in_occupancy_rate",
            "出租率": "occupancy_rate",
            "现租赁合同": "lease_contract",
            "租户名称": "tenant_name",
            "说明": "description"
        }
        
        # 重命名列
        available_mappings = {k: v for k, v in field_mapping.items() if k in df.columns}
        df = df.rename(columns=available_mappings)
        print(f"✓ 已映射 {len(available_mappings)} 个字段")
        
        # 创建数据库会话
        db = SessionLocal()
        
        try:
            success_count = 0
            error_count = 0
            errors = []
            
            # 逐行处理数据
            for index, row in df.iterrows():
                try:
                    # 清理数据，移除NaN值
                    cleaned_data = {}
                    for key, value in row.items():
                        if pd.notna(value) and str(value).strip():
                            # 处理数值类型
                            if key in ['land_area', 'actual_property_area', 'rentable_area', 
                                     'rented_area', 'unrented_area', 'non_commercial_area']:
                                try:
                                    cleaned_data[key] = float(value)
                                except (ValueError, TypeError):
                                    cleaned_data[key] = 0.0
                            else:
                                cleaned_data[key] = str(value).strip()
                    
                    # 数据转换和标准化
                    if 'ownership_status' in cleaned_data:
                        # 转换确权状态
                        status_mapping = {
                            '已确权': '已确权',
                            '未确权': '未确权', 
                            '部分确权': '部分确权'
                        }
                        cleaned_data['ownership_status'] = status_mapping.get(cleaned_data['ownership_status'], '未确权')
                    
                    if 'usage_status' in cleaned_data:
                        # 转换使用状态
                        usage_mapping = {
                            '出租': '出租',
                            '自用': '自用',
                            '闲置': '空置',
                            '空置': '空置',
                            '公房': '自用',
                            '其他': '空置'
                        }
                        cleaned_data['usage_status'] = usage_mapping.get(cleaned_data['usage_status'], '空置')
                    
                    if 'property_nature' in cleaned_data:
                        # 转换物业性质
                        nature_mapping = {
                            '经营类': '经营性',
                            '经营性': '经营性',
                            '非经营类': '非经营性',
                            '非经营性': '非经营性'
                        }
                        cleaned_data['property_nature'] = nature_mapping.get(cleaned_data['property_nature'], '经营性')
                    
                    if 'is_litigated' in cleaned_data:
                        # 转换是否涉诉
                        litigation_mapping = {
                            '是': '是',
                            '否': '否',
                            '无': '否',
                            '': '否'
                        }
                        cleaned_data['is_litigated'] = litigation_mapping.get(cleaned_data['is_litigated'], '否')
                    
                    # 确保必填字段存在，并处理重复名称
                    if 'property_name' not in cleaned_data or not cleaned_data['property_name']:
                        cleaned_data['property_name'] = f"物业_{index + 1}"
                    else:
                        # 为了避免重复，在物业名称后添加行号
                        original_name = cleaned_data['property_name']
                        cleaned_data['property_name'] = f"{original_name}_{index + 1}"
                    
                    if 'address' not in cleaned_data or not cleaned_data['address']:
                        cleaned_data['address'] = "地址待完善"
                    
                    # 设置默认值 - 使用正确的枚举值
                    defaults = {
                        'ownership_status': '未确权',  # 使用正确的枚举值
                        'property_nature': '经营性',
                        'usage_status': '空置',  # 使用正确的枚举值
                        'is_litigated': '否'
                    }
                    
                    for key, default_value in defaults.items():
                        if key not in cleaned_data:
                            cleaned_data[key] = default_value
                    
                    # 创建资产对象
                    asset_create = AssetCreate(**cleaned_data)
                    
                    # 保存到数据库
                    try:
                        created_asset = asset_crud.create(db=db, obj_in=asset_create)
                        
                        if created_asset:
                            success_count += 1
                            if success_count % 50 == 0:
                                print(f"已导入 {success_count} 条记录...")
                                # 定期提交事务
                                db.commit()
                        else:
                            raise ValueError("创建资产记录失败")
                    except Exception as create_error:
                        # 回滚当前事务
                        db.rollback()
                        raise create_error
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"第{index + 1}行: {str(e)}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            # 提交事务
            db.commit()
            
            print(f"\n导入完成:")
            print(f"✓ 成功导入: {success_count} 条记录")
            if error_count > 0:
                print(f"❌ 失败记录: {error_count} 条")
                print("错误详情:")
                for error in errors[:5]:  # 只显示前5个错误
                    print(f"  - {error}")
                if len(errors) > 5:
                    print(f"  ... 还有 {len(errors) - 5} 个错误")
            
            return success_count > 0
            
        except Exception as e:
            db.rollback()
            print(f"❌ 导入过程中发生错误: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")
        return False


def main():
    """主函数"""
    print("=== 清理系统数据并导入新数据 ===\n")
    
    # 1. 清理现有数据
    clear_all_data()
    
    # 2. 导入新数据
    excel_file_path = r"D:\code\zcgl\wylist20250731.xlsx"
    
    # 检查文件是否存在
    if not os.path.exists(excel_file_path):
        # 尝试在当前目录查找
        current_dir_file = "wylist20250731.xlsx"
        if os.path.exists(current_dir_file):
            excel_file_path = current_dir_file
            print(f"在当前目录找到文件: {excel_file_path}")
        else:
            print(f"❌ 找不到Excel文件: {excel_file_path}")
            print("请确认文件路径是否正确")
            return
    
    success = import_excel_data(excel_file_path)
    
    if success:
        print("\n🎉 数据清理和导入完成!")
    else:
        print("\n❌ 数据导入失败，请检查错误信息")


if __name__ == "__main__":
    main()