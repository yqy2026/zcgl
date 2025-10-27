"""
PDF处理监控API
提供性能监控、错误分析和系统健康状态查询
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.security import get_current_user
from ...database import get_db
from ...services.pdf_processing_monitor import pdf_processing_monitor
from ...services.pdf_session_service import pdf_session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf-import/monitoring", tags=["PDF监控"])


@router.get("/health")
async def get_system_health():
    """获取系统健康状态"""
    try:
        health = pdf_processing_monitor.get_system_health()
        return {
            "success": True,
            "data": {
                "timestamp": health.timestamp.isoformat(),
                "status": health.status,
                "metrics": {
                    "cpu_usage": health.cpu_usage,
                    "memory_usage": health.memory_usage,
                    "disk_usage": health.disk_usage,
                    "active_sessions": health.active_sessions,
                    "error_rate": health.error_rate,
                    "avg_processing_time": health.avg_processing_time,
                    "success_rate": health.success_rate,
                },
            },
        }
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统健康状态失败: {str(e)}")


@router.get("/performance")
async def get_performance_stats(
    hours: int = Query(default=24, ge=1, le=168),  # 1小时到7天
    current_user=Depends(get_current_user),
):
    """获取性能统计"""
    try:
        stats = pdf_processing_monitor.get_performance_stats(hours)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"获取性能统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取性能统计失败: {str(e)}")


@router.get("/errors")
async def get_error_stats(
    hours: int = Query(default=24, ge=1, le=168), current_user=Depends(get_current_user)
):
    """获取错误统计"""
    try:
        error_stats = pdf_processing_monitor.get_error_stats(hours)
        return {"success": True, "data": error_stats}
    except Exception as e:
        logger.error(f"获取错误统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取错误统计失败: {str(e)}")


@router.get("/recommendations")
async def get_optimization_recommendations(current_user=Depends(get_current_user)):
    """获取优化建议"""
    try:
        recommendations = pdf_processing_monitor.get_recommendations()

        # 获取系统建议
        performance_stats = pdf_processing_monitor.get_performance_stats(1)
        error_stats = pdf_processing_monitor.get_error_stats(1)
        health = pdf_processing_monitor.get_system_health()

        system_recommendations = []

        # 性能建议
        if performance_stats["avg_processing_time"] > 30:
            system_recommendations.append(
                {
                    "type": "performance",
                    "priority": "high",
                    "message": "平均处理时间超过30秒，建议优化算法或增加硬件资源",
                }
            )

        # 错误率建议
        if error_stats["error_rate"] > 0.1:
            system_recommendations.append(
                {
                    "type": "reliability",
                    "priority": "high",
                    "message": f"错误率过高({error_stats['error_rate']:.1%})，建议分析错误日志并改进系统稳定性",
                }
            )

        # 资源使用建议
        if health.cpu_usage > 80:
            system_recommendations.append(
                {
                    "type": "resource",
                    "priority": "medium",
                    "message": f"CPU使用率过高({health.cpu_usage:.1f}%)，建议优化算法或增加CPU资源",
                }
            )

        if health.memory_usage > 85:
            system_recommendations.append(
                {
                    "type": "resource",
                    "priority": "medium",
                    "message": f"内存使用率过高({health.memory_usage:.1f}%)，建议优化内存管理或增加内存",
                }
            )

        # 会话管理建议
        if health.active_sessions > 10:
            system_recommendations.append(
                {
                    "type": "capacity",
                    "priority": "medium",
                    "message": f"活跃会话数较多({health.active_sessions})，建议实施负载均衡或限流机制",
                }
            )

        return {
            "success": True,
            "data": {
                "automatic_recommendations": recommendations,
                "system_recommendations": system_recommendations,
                "overall_health": health.status,
                "priority_issues": [
                    r for r in system_recommendations if r["priority"] == "high"
                ],
            },
        }
    except Exception as e:
        logger.error(f"获取优化建议失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取优化建议失败: {str(e)}")


@router.get("/active-sessions")
async def get_active_sessions(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取活跃会话列表"""
    try:
        active_sessions = await pdf_session_service.get_active_sessions(db)

        session_details = []
        for session in active_sessions:
            # 获取监控信息
            operation_info = None
            if session.session_id in pdf_processing_monitor.active_operations:
                start_time = pdf_processing_monitor.active_operations[
                    session.session_id
                ]
                operation_info = {
                    "start_time": start_time.isoformat(),
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                }

            session_details.append(
                {
                    "session_id": session.session_id,
                    "file_name": session.file_name,
                    "status": session.status.value,
                    "progress": session.progress_percentage,
                    "current_step": session.current_step.value,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "operation_info": operation_info,
                }
            )

        return {
            "success": True,
            "data": {
                "total_active_sessions": len(session_details),
                "sessions": session_details,
            },
        }
    except Exception as e:
        logger.error(f"获取活跃会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取活跃会话失败: {str(e)}")


@router.get("/dashboard")
async def get_monitoring_dashboard(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取监控仪表板数据"""
    try:
        # 获取各种统计数据
        health = pdf_processing_monitor.get_system_health()
        performance_stats = pdf_processing_monitor.get_performance_stats(hours)
        error_stats = pdf_processing_monitor.get_error_stats(hours)
        recommendations = pdf_processing_monitor.get_recommendations()
        active_sessions = await pdf_session_service.get_active_sessions(db)

        # 构建仪表板数据
        dashboard_data = {
            "system_health": {
                "status": health.status,
                "status_color": {
                    "healthy": "green",
                    "warning": "orange",
                    "critical": "red",
                }.get(health.status, "gray"),
                "metrics": {
                    "cpu_usage": health.cpu_usage,
                    "memory_usage": health.memory_usage,
                    "disk_usage": health.disk_usage,
                    "active_sessions": health.active_sessions,
                    "error_rate": health.error_rate,
                    "avg_processing_time": health.avg_processing_time,
                    "success_rate": health.success_rate,
                },
            },
            "performance_summary": {
                "total_operations": performance_stats["total_operations"],
                "success_rate": performance_stats["success_rate"],
                "avg_processing_time": performance_stats["avg_processing_time"],
                "performance_level": performance_stats["performance_level"],
                "period_hours": performance_stats["period_hours"],
            },
            "error_summary": {
                "total_errors": error_stats["total_errors"],
                "resolved_errors": error_stats["resolved_errors"],
                "error_rate": error_stats["error_rate"],
                "top_error_types": dict(
                    sorted(
                        error_stats["errors_by_type"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:5]
                ),
            },
            "activity_summary": {
                "active_sessions": len(active_sessions),
                "session_status_breakdown": {},
            },
            "recommendations": {
                "total_count": len(recommendations),
                "priority_issues": len([r for r in recommendations if "高" in r]),
                "items": recommendations[:5],  # 只返回前5个建议
            },
            "timestamp": datetime.now().isoformat(),
        }

        # 会话状态分布
        for session in active_sessions:
            status = session.status.value
            if (
                status
                not in dashboard_data["activity_summary"]["session_status_breakdown"]
            ):
                dashboard_data["activity_summary"]["session_status_breakdown"][
                    status
                ] = 0
            dashboard_data["activity_summary"]["session_status_breakdown"][status] += 1

        return {"success": True, "data": dashboard_data}
    except Exception as e:
        logger.error(f"获取监控仪表板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取监控仪表板失败: {str(e)}")


@router.post("/start-monitoring")
async def start_monitoring(current_user=Depends(get_current_user)):
    """启动监控"""
    try:
        pdf_processing_monitor.start_monitoring()
        return {"success": True, "message": "PDF处理监控已启动"}
    except Exception as e:
        logger.error(f"启动监控失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动监控失败: {str(e)}")


@router.post("/stop-monitoring")
async def stop_monitoring(current_user=Depends(get_current_user)):
    """停止监控"""
    try:
        pdf_processing_monitor.stop_monitoring()
        return {"success": True, "message": "PDF处理监控已停止"}
    except Exception as e:
        logger.error(f"停止监控失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"停止监控失败: {str(e)}")


@router.get("/status")
async def get_monitoring_status(current_user=Depends(get_current_user)):
    """获取监控状态"""
    try:
        return {
            "success": True,
            "data": {
                "monitoring_active": pdf_processing_monitor._monitoring_active,
                "total_error_records": len(pdf_processing_monitor.error_records),
                "total_performance_metrics": len(
                    pdf_processing_monitor.performance_metrics
                ),
                "active_operations": len(pdf_processing_monitor.active_operations),
                "max_records": pdf_processing_monitor.max_records,
            },
        }
    except Exception as e:
        logger.error(f"获取监控状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取监控状态失败: {str(e)}")
