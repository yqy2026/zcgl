"""
PDF导入核心服务
整合PDF处理、会话管理、验证匹配和数据库导入的完整流程
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .pdf_processing_service import pdf_processing_service
from .pdf_session_service import pdf_session_service
from .pdf_validation_matching_service import PDFValidationMatchingService
from .contract_extractor import extract_contract_info
from ..models.pdf_import_session import SessionStatus, ProcessingStep

logger = logging.getLogger(__name__)

class PDFImportService:
    """PDF导入核心服务"""

    def __init__(self):
        self.processing_service = pdf_processing_service

    async def process_pdf_file(
        self,
        db: Session,
        session_id: str,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """异步处理PDF文件的完整流程"""

        try:
            # 获取会话信息
            session = await pdf_session_service.get_session(db, session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 开始异步处理
            task = asyncio.create_task(
                self._process_pdf_async(db, session, user_id, organization_id)
            )

            # 注册任务以便取消
            pdf_session_service.register_background_task(session_id, task)

            return {
                'success': True,
                'message': 'PDF处理已开始',
                'session_id': session_id,
                'status': 'processing'
            }

        except Exception as e:
            logger.error(f"启动PDF处理失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }

    async def _process_pdf_async(
        self,
        db: Session,
        session,
        user_id: Optional[int],
        organization_id: Optional[int]
    ):
        """异步处理PDF的核心逻辑"""
        session_id = session.session_id

        try:
            # 步骤1: PDF文本提取
            await self._extract_text_step(db, session)

            # 步骤2: 信息提取
            await self._extract_info_step(db, session)

            # 步骤3: 数据验证
            await self._validate_data_step(db, session)

            # 步骤4: 数据匹配
            await self._match_data_step(db, session)

            # 完成处理
            await pdf_session_service.update_session_progress(
                db, session_id, SessionStatus.READY_FOR_REVIEW,
                ProcessingStep.FINAL_REVIEW, 95.0
            )

            logger.info(f"PDF处理完成: {session_id}")

        except Exception as e:
            logger.error(f"PDF处理失败: {session_id}, 错误: {str(e)}")
            await pdf_session_service.update_session_progress(
                db, session_id, SessionStatus.FAILED,
                session.current_step, session.progress_percentage,
                str(e)
            )
        finally:
            # 清理任务
            pdf_session_service.unregister_background_task(session_id)

    async def _extract_text_step(self, db: Session, session):
        """步骤1: PDF文本提取"""
        session_id = session.session_id

        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.PROCESSING,
            ProcessingStep.PDF_CONVERSION, 20.0
        )

        # 获取处理配置
        processing_options = session.processing_options or {}
        prefer_ocr = processing_options.get('prefer_ocr', False)

        # 执行文本提取
        # 从processing_options中排除prefer_ocr，避免重复参数
        filtered_options = {k: v for k, v in processing_options.items() if k != 'prefer_ocr'}

        extraction_result = await self.processing_service.extract_text_from_pdf(
            session.file_path,
            prefer_ocr=prefer_ocr,
            **filtered_options
        )

        if not extraction_result['success']:
            raise Exception(f"PDF文本提取失败: {extraction_result['error']}")

        # 更新会话
        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.TEXT_EXTRACTED,
            ProcessingStep.TEXT_EXTRACTION, 40.0,
            extracted_text=extraction_result['text'],
            processing_method=extraction_result['processing_method'],
            ocr_used=extraction_result.get('ocr_used', False),
            confidence_score=extraction_result.get('overall_confidence_score', 0.8)
        )

        logger.info(f"文本提取完成: {session_id}, 方法: {extraction_result['processing_method']}")

    async def _extract_info_step(self, db: Session, session):
        """步骤2: 信息提取"""
        session_id = session.session_id

        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.INFO_EXTRACTED,
            ProcessingStep.INFO_EXTRACTION, 60.0
        )

        # 使用合同提取器
        extracted_info = extract_contract_info(session.extracted_text)

        if not extracted_info.get('success'):
            raise Exception(f"合同信息提取失败: {extracted_info.get('error', '未知错误')}")

        # 更新会话
        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.INFO_EXTRACTED,
            ProcessingStep.INFO_EXTRACTION, 60.0,
            extracted_data=extracted_info.get('extracted_fields', {}),
            confidence_score=extracted_info.get('overall_confidence', 0.0)
        )

        logger.info(f"信息提取完成: {session_id}, 字段数: {len(extracted_info.get('extracted_fields', {}))}")

    async def _validate_data_step(self, db: Session, session):
        """步骤3: 数据验证"""
        session_id = session.session_id

        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.VALIDATING,
            ProcessingStep.DATA_VALIDATION, 75.0
        )

        # 创建验证服务
        validation_service = PDFValidationMatchingService(db)

        # 执行验证
        validation_result = await validation_service.validate_extracted_data(
            session.extracted_data
        )

        # 更新会话
        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.VALIDATING,
            ProcessingStep.DATA_VALIDATION, 75.0,
            validation_results=validation_result
        )

        logger.info(f"数据验证完成: {session_id}, 验证分数: {validation_result['validation_score']:.2f}")

    async def _match_data_step(self, db: Session, session):
        """步骤4: 数据匹配"""
        session_id = session.session_id

        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.MATCHING,
            ProcessingStep.ASSET_MATCHING, 90.0
        )

        # 创建验证匹配服务
        validation_service = PDFValidationMatchingService(db)

        # 执行匹配
        matching_result = await validation_service.perform_data_matching(
            session.extracted_data
        )

        # 更新会话
        await pdf_session_service.update_session_progress(
            db, session_id, SessionStatus.MATCHING,
            ProcessingStep.DUPLICATE_CHECK, 90.0,
            matching_results=matching_result
        )

        logger.info(f"数据匹配完成: {session_id}, 匹配度: {matching_result['overall_match_confidence']:.2f}")

    async def confirm_import(
        self,
        db: Session,
        session_id: str,
        confirmed_data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """确认导入数据到数据库"""

        try:
            # 获取会话
            session = await pdf_session_service.get_session(db, session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            if session.status != SessionStatus.READY_FOR_REVIEW:
                raise ValueError(f"会话状态不正确: {session.status}")

            await pdf_session_service.update_session_progress(
                db, session_id, SessionStatus.CONFIRMED,
                ProcessingStep.FINAL_REVIEW, 100.0
            )

            # 创建数据库记录
            contract_id = await self._create_contract_records(
                db, confirmed_data, session, user_id
            )

            # 更新会话状态
            await pdf_session_service.update_session_progress(
                db, session_id, SessionStatus.COMPLETED,
                ProcessingStep.FINAL_REVIEW, 100.0
            )

            logger.info(f"合同导入成功: {session_id}, 合同ID: {contract_id}")

            return {
                'success': True,
                'message': '合同数据导入成功',
                'contract_id': contract_id,
                'session_id': session_id
            }

        except Exception as e:
            logger.error(f"合同导入失败: {session_id}, 错误: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }

    async def _create_contract_records(
        self,
        db: Session,
        confirmed_data: Dict[str, Any],
        session,
        user_id: Optional[int]
    ) -> int:
        """创建合同相关数据库记录"""
        from ..models.rent_contract import RentContract, RentTerm
        from ..models.asset import Asset
        from ..models.ownership import Ownership

        try:
            # 创建租赁合同记录
            contract = RentContract(
                contract_number=confirmed_data.get('contract_number', f"HT-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                tenant_name=confirmed_data.get('tenant_name'),
                tenant_contact=confirmed_data.get('tenant_contact'),
                tenant_phone=confirmed_data.get('tenant_phone'),
                tenant_address=confirmed_data.get('tenant_address'),
                property_address=confirmed_data.get('property_address'),
                monthly_rent_base=confirmed_data.get('monthly_rent_base'),
                total_deposit=confirmed_data.get('total_deposit'),
                contract_status='active',
                payment_terms=confirmed_data.get('payment_terms'),
                contract_notes=confirmed_data.get('contract_notes'),
                sign_date=self._parse_date(confirmed_data.get('sign_date')),
                start_date=self._parse_date(confirmed_data.get('start_date')),
                end_date=self._parse_date(confirmed_data.get('end_date')),
                asset_id=confirmed_data.get('asset_id'),
                ownership_id=confirmed_data.get('ownership_id'),
                organization_id=session.organization_id,
                created_by=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                source_session_id=session.session_id  # 记录来源会话
            )

            db.add(contract)
            db.flush()  # 获取ID

            # 创建租金条款记录
            rent_terms = confirmed_data.get('rent_terms', [])
            if not rent_terms and confirmed_data.get('monthly_rent_base'):
                # 如果没有详细条款，创建一个默认条款
                rent_terms = [{
                    'start_date': confirmed_data.get('start_date'),
                    'end_date': confirmed_data.get('end_date'),
                    'monthly_rent': confirmed_data.get('monthly_rent_base'),
                    'rent_description': '基础租金'
                }]

            for term_data in rent_terms:
                rent_term = RentTerm(
                    contract_id=contract.id,
                    start_date=self._parse_date(term_data.get('start_date')),
                    end_date=self._parse_date(term_data.get('end_date')),
                    monthly_rent=term_data.get('monthly_rent'),
                    rent_description=term_data.get('rent_description'),
                    management_fee=term_data.get('management_fee'),
                    other_fees=term_data.get('other_fees'),
                    total_monthly_amount=term_data.get('total_monthly_amount'),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(rent_term)

            db.commit()

            return contract.id

        except Exception as e:
            db.rollback()
            raise Exception(f"创建合同记录失败: {str(e)}")

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None

        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y年%m月%d日',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    async def get_session_status(
        self,
        db: Session,
        session_id: str
    ) -> Dict[str, Any]:
        """获取会话状态"""

        session = await pdf_session_service.get_session(db, session_id)
        if not session:
            return {
                'success': False,
                'error': '会话不存在'
            }

        return {
            'success': True,
            'session_status': {
                'session_id': session.session_id,
                'status': session.status.value,
                'progress': session.progress_percentage,
                'current_step': session.current_step.value if session.current_step else None,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'error_message': session.error_message,
                'extracted_data': session.extracted_data,
                'validation_results': session.validation_results,
                'matching_results': session.matching_results,
                'confidence_score': session.confidence_score
            }
        }

    async def cancel_processing(
        self,
        db: Session,
        session_id: str,
        reason: str = "用户取消"
    ) -> Dict[str, Any]:
        """取消PDF处理"""

        success = await pdf_session_service.cancel_session(db, session_id, reason)

        return {
            'success': success,
            'message': '处理已取消' if success else '取消失败，会话可能已完成或不存在',
            'session_id': session_id
        }

# 创建全局实例
pdf_import_service = PDFImportService()