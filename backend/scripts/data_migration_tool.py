#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移工具
用于在不同版本之间迁移数据
"""

import sys
import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

class DataMigrationTool:
    def __init__(self):
        self.migration_history = []
    
    def backup_database(self, db_path, backup_dir='backups'):
        """备份数据库"""
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"backup_{timestamp}.db"
        
        # 复制数据库文件
        import shutil
        shutil.copy2(db_path, backup_file)
        
        print(f"数据库已备份到: {backup_file}")
        return backup_file
    
    def export_to_excel(self, db_path, output_file):
        """导出数据到Excel"""
        conn = sqlite3.connect(db_path)
        
        # 获取所有表名
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for table_name, in tables:
                if table_name.startswith('sqlite_'):
                    continue
                
                # 读取表数据
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                # 写入Excel工作表
                df.to_excel(writer, sheet_name=table_name, index=False)
                print(f"已导出表: {table_name} ({len(df)} 行)")
        
        conn.close()
        print(f"数据已导出到: {output_file}")
    
    def import_from_excel(self, excel_file, db_path, table_name='assets'):
        """从Excel导入数据"""
        # 备份原数据库
        self.backup_database(db_path)
        
        # 读取Excel文件
        df = pd.read_excel(excel_file, sheet_name=0)
        print(f"从Excel读取 {len(df)} 行数据")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        
        try:
            # 清空现有数据（可选）
            # conn.execute(f"DELETE FROM {table_name}")
            
            # 插入数据
            df.to_sql(table_name, conn, if_exists='append', index=False)
            conn.commit()
            
            print(f"数据已导入到表: {table_name}")
            
        except Exception as e:
            conn.rollback()
            print(f"导入失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def migrate_field_structure(self, db_path, migration_script):
        """执行字段结构迁移"""
        # 备份数据库
        backup_file = self.backup_database(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 读取迁移脚本
            with open(migration_script, 'r', encoding='utf-8') as f:
                sql_commands = f.read()
            
            # 执行迁移脚本
            cursor.executescript(sql_commands)
            conn.commit()
            
            print(f"字段结构迁移完成")
            
            # 记录迁移历史
            self.migration_history.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'field_migration',
                'script': migration_script,
                'backup': str(backup_file)
            })
            
        except Exception as e:
            conn.rollback()
            print(f"迁移失败: {str(e)}")
            print(f"可以从备份恢复: {backup_file}")
            raise
        finally:
            conn.close()
    
    def validate_data_integrity(self, db_path):
        """验证数据完整性"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        issues = []
        
        try:
            # 检查数据库完整性
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result[0] != 'ok':
                issues.append(f"数据库完整性检查失败: {result[0]}")
            
            # 检查必填字段
            cursor.execute("""
                SELECT COUNT(*) FROM assets 
                WHERE property_name IS NULL OR property_name = ''
            """)
            null_names = cursor.fetchone()[0]
            if null_names > 0:
                issues.append(f"发现 {null_names} 个资产缺少物业名称")
            
            # 检查数据一致性
            cursor.execute("""
                SELECT COUNT(*) FROM assets 
                WHERE rented_area > rentable_area AND rented_area IS NOT NULL AND rentable_area IS NOT NULL
            """)
            inconsistent_area = cursor.fetchone()[0]
            if inconsistent_area > 0:
                issues.append(f"发现 {inconsistent_area} 个资产的已租面积大于可租面积")
            
            # 检查出租率计算
            cursor.execute("""
                SELECT COUNT(*) FROM assets 
                WHERE rentable_area > 0 AND rented_area IS NOT NULL 
                AND ABS(occupancy_rate - (rented_area / rentable_area * 100)) > 0.01
            """)
            wrong_occupancy = cursor.fetchone()[0]
            if wrong_occupancy > 0:
                issues.append(f"发现 {wrong_occupancy} 个资产的出租率计算错误")
            
            if issues:
                print("数据完整性检查发现问题:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("✓ 数据完整性检查通过")
            
            return len(issues) == 0
            
        finally:
            conn.close()
    
    def fix_data_issues(self, db_path):
        """修复数据问题"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 修复出租率计算
            cursor.execute("""
                UPDATE assets 
                SET occupancy_rate = ROUND((rented_area / rentable_area) * 100, 2)
                WHERE rentable_area > 0 AND rented_area IS NOT NULL
            """)
            
            # 修复未出租面积
            cursor.execute("""
                UPDATE assets 
                SET unrented_area = rentable_area - COALESCE(rented_area, 0)
                WHERE rentable_area IS NOT NULL
            """)
            
            # 修复净收益
            cursor.execute("""
                UPDATE assets 
                SET net_income = COALESCE(annual_income, 0) - COALESCE(annual_expense, 0)
                WHERE annual_income IS NOT NULL OR annual_expense IS NOT NULL
            """)
            
            conn.commit()
            print("数据问题修复完成")
            
        except Exception as e:
            conn.rollback()
            print(f"数据修复失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def generate_migration_report(self, db_path, output_file):
        """生成迁移报告"""
        conn = sqlite3.connect(db_path)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_path': db_path,
            'migration_history': self.migration_history
        }
        
        # 获取表结构信息
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(assets)")
        columns = cursor.fetchall()
        
        report['table_structure'] = {
            'column_count': len(columns),
            'columns': [{'name': col[1], 'type': col[2], 'nullable': not col[3]} for col in columns]
        }
        
        # 获取数据统计
        cursor.execute("SELECT COUNT(*) FROM assets")
        total_assets = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assets WHERE rentable_area IS NOT NULL")
        rentable_assets = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(occupancy_rate) FROM assets WHERE occupancy_rate IS NOT NULL")
        avg_occupancy = cursor.fetchone()[0]
        
        report['data_statistics'] = {
            'total_assets': total_assets,
            'assets_with_rentable_area': rentable_assets,
            'average_occupancy_rate': round(avg_occupancy, 2) if avg_occupancy else 0
        }
        
        conn.close()
        
        # 保存报告
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"迁移报告已生成: {output_file}")
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据迁移工具')
    parser.add_argument('--db', default='../land_property.db', help='数据库文件路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='备份数据库')
    backup_parser.add_argument('--output-dir', default='backups', help='备份目录')
    
    # 导出命令
    export_parser = subparsers.add_parser('export', help='导出到Excel')
    export_parser.add_argument('--output', required=True, help='输出Excel文件')
    
    # 导入命令
    import_parser = subparsers.add_parser('import', help='从Excel导入')
    import_parser.add_argument('--input', required=True, help='输入Excel文件')
    import_parser.add_argument('--table', default='assets', help='目标表名')
    
    # 迁移命令
    migrate_parser = subparsers.add_parser('migrate', help='执行字段迁移')
    migrate_parser.add_parameter('--script', required=True, help='迁移脚本文件')
    
    # 验证命令
    validate_parser = subparsers.add_parser('validate', help='验证数据完整性')
    
    # 修复命令
    fix_parser = subparsers.add_parser('fix', help='修复数据问题')
    
    # 报告命令
    report_parser = subparsers.add_parser('report', help='生成迁移报告')
    report_parser.add_argument('--output', default='migration_report.json', help='报告文件')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tool = DataMigrationTool()
    
    try:
        if args.command == 'backup':
            tool.backup_database(args.db, args.output_dir)
        
        elif args.command == 'export':
            tool.export_to_excel(args.db, args.output)
        
        elif args.command == 'import':
            tool.import_from_excel(args.input, args.db, args.table)
        
        elif args.command == 'migrate':
            tool.migrate_field_structure(args.db, args.script)
        
        elif args.command == 'validate':
            success = tool.validate_data_integrity(args.db)
            sys.exit(0 if success else 1)
        
        elif args.command == 'fix':
            tool.fix_data_issues(args.db)
        
        elif args.command == 'report':
            tool.generate_migration_report(args.db, args.output)
        
    except Exception as e:
        print(f"操作失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()