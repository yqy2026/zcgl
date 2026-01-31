from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.enums import ContractStatus
from ...core.exception_handler import (
    BusinessValidationError,
    FileProcessingError,
    OperationNotAllowedError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from ...models.asset import Asset
from ...models.rent_contract import (
    DepositTransactionType,
    RentContract,
    RentDepositLedger,
    RentTerm,
)
from ...schemas.rent_contract import RentContractCreate, RentContractUpdate
from ...utils.model_utils import model_to_dict

from .helpers import RentContractHelperMixin


class RentContractLifecycleService(RentContractHelperMixin):
    """合同生命周期相关服务"""

    def create_contract(
        self, db: Session, *, obj_in: RentContractCreate
    ) -> RentContract:
        """创建合同（包含租金条款）- V2 支持多资产"""
        # 合同编号必须手工录入
        if not obj_in.contract_number or not obj_in.contract_number.strip():
            raise BusinessValidationError(
                "合同编号不能为空，请手工录入",
                field_errors={"contract_number": ["不能为空"]},
            )
        obj_in.contract_number = obj_in.contract_number.strip()

        # V2: 检查资产租金冲突
        if obj_in.asset_ids:
            conflicts = self._check_asset_rent_conflicts(
                db,
                asset_ids=obj_in.asset_ids,
                start_date=obj_in.start_date,
                end_date=obj_in.end_date,
                exclude_contract_id=None,
            )
            if conflicts:
                # 构造友好的错误消息
                conflict_details = [
                    f"资产 {c['asset_name']} 已被合同 {c['contract_number']} 覆盖 "
                    f"({c['contract_start_date']} 至 {c['contract_end_date']})"
                    for c in conflicts
                ]
                raise ResourceConflictError(
                    message=(
                        "资产租金冲突检测:\n"
                        + "\n".join(conflict_details)
                        + "\n\n是否仍要创建? 如果确认创建,请联系管理员或使用强制覆盖功能。"
                    ),
                    resource_type="asset",
                    details={"conflicts": conflicts},
                )

        # V2: 提取 asset_ids 单独处理
        asset_ids = obj_in.asset_ids or []
        contract_data = obj_in.model_dump(exclude={"rent_terms", "asset_ids"})
        db_contract = RentContract(**contract_data)

        # V2: 关联资产
        if asset_ids:
            assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
            sa_assets = [
                asset for asset in assets if hasattr(asset, "_sa_instance_state")
            ]
            if sa_assets:
                setattr(db_contract, "assets", sa_assets)

        db.add(db_contract)
        db.flush()  # 获取ID

        # 创建租金条款
        for term_data in obj_in.rent_terms:
            term_data_dict = term_data.model_dump()
            # 确保 total_monthly_amount 被正确计算
            if term_data_dict.get("total_monthly_amount") is None:
                monthly_rent = term_data_dict.get("monthly_rent", Decimal("0"))
                management_fee = term_data_dict.get("management_fee", Decimal("0"))
                other_fees = term_data_dict.get("other_fees", Decimal("0"))
                term_data_dict["total_monthly_amount"] = (
                    monthly_rent + management_fee + other_fees
                )

            term_data_dict["contract_id"] = db_contract.id
            db_term = RentTerm(**term_data_dict)
            db.add(db_term)

        db.commit()
        db.refresh(db_contract)

        # 记录历史
        self._create_history(
            db,
            contract_id=db_contract.id,
            change_type="创建",
            change_description="创建新合同",
            new_data=model_to_dict(db_contract),
        )

        return db_contract

    def update_contract(
        self, db: Session, *, db_obj: RentContract, obj_in: RentContractUpdate
    ) -> RentContract:
        """更新合同（包含租金条款）- V2 支持多资产"""
        old_data = model_to_dict(db_obj)

        # V2: 提取 asset_ids 单独处理
        update_data = obj_in.model_dump(
            exclude_unset=True, exclude={"rent_terms", "asset_ids"}
        )
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # V2: 更新资产关联
        if obj_in.asset_ids is not None:
            assets = db.query(Asset).filter(Asset.id.in_(obj_in.asset_ids)).all()
            sa_assets = [
                asset for asset in assets if hasattr(asset, "_sa_instance_state")
            ]
            if sa_assets:
                setattr(db_obj, "assets", sa_assets)

        # 更新租金条款
        if obj_in.rent_terms is not None:
            # 删除现有条款
            db.query(RentTerm).filter(RentTerm.contract_id == db_obj.id).delete()

            # 创建新条款
            for term_data in obj_in.rent_terms:
                term_data_dict = term_data.model_dump()
                term_data_dict["contract_id"] = db_obj.id
                db_term = RentTerm(**term_data_dict)
                db.add(db_term)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # 记录历史
        self._create_history(
            db,
            contract_id=db_obj.id,
            change_type="更新",
            change_description="更新合同信息",
            old_data=old_data,
            new_data=model_to_dict(db_obj),
        )

        return db_obj

    def renew_contract(
        self,
        db: Session,
        *,
        original_contract_id: str,
        new_contract_data: RentContractCreate,
        should_transfer_deposit: bool = True,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContract:
        """
        合同续签
        1. 创建新合同（预填数据）
        2. 结束原合同
        3. 转移押金（通过 DepositLedger 记录）
        """
        # 获取原合同
        original = (
            db.query(RentContract)
            .filter(RentContract.id == original_contract_id)
            .first()
        )
        if not original:
            raise ResourceNotFoundError("合同", original_contract_id)
        if original.contract_status != ContractStatus.ACTIVE:
            raise OperationNotAllowedError(
                f"原合同状态不可续签: {original.contract_status}",
                reason="contract_status_not_active",
            )

        # 创建新合同
        new_contract = self.create_contract(db, obj_in=new_contract_data)

        # 转移押金
        if should_transfer_deposit and original.total_deposit > 0:
            deposit_amount = original.total_deposit

            # 原合同押金转出
            transfer_out = RentDepositLedger()
            transfer_out.contract_id = original.id
            transfer_out.transaction_type = DepositTransactionType.TRANSFER_OUT
            transfer_out.amount = -deposit_amount
            transfer_out.transaction_date = date.today()
            transfer_out.related_contract_id = new_contract.id
            transfer_out.notes = f"续签转出至新合同 {new_contract.contract_number}"
            transfer_out.operator = operator
            transfer_out.operator_id = operator_id
            db.add(transfer_out)

            # 新合同押金转入
            transfer_in = RentDepositLedger()
            transfer_in.contract_id = new_contract.id
            transfer_in.transaction_type = DepositTransactionType.TRANSFER_IN
            transfer_in.amount = deposit_amount
            transfer_in.transaction_date = date.today()
            transfer_in.related_contract_id = original.id
            transfer_in.notes = f"从原合同 {original.contract_number} 续签转入"
            transfer_in.operator = operator
            transfer_in.operator_id = operator_id
            db.add(transfer_in)

        # 结束原合同
        setattr(original, "contract_status", ContractStatus.RENEWED)
        db.add(original)

        # 记录历史
        self._create_history(
            db,
            contract_id=original.id,
            change_type="续签",
            change_description=f"续签至新合同 {new_contract.contract_number}",
            operator=operator,
            operator_id=operator_id,
        )

        db.commit()
        db.refresh(new_contract)
        return new_contract

    def terminate_contract(
        self,
        db: Session,
        *,
        contract_id: str,
        termination_date: date,
        should_refund_deposit: bool = True,
        deduction_amount: Decimal = Decimal("0"),
        termination_reason: str | None = None,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContract:
        """
        合同提前终止
        1. 更新合同状态
        2. 处理押金（退还/抵扣）
        """
        contract = db.query(RentContract).filter(RentContract.id == contract_id).first()
        if not contract:
            raise ResourceNotFoundError("合同", contract_id)
        if contract.contract_status not in [ContractStatus.ACTIVE]:
            raise OperationNotAllowedError(
                f"合同状态不可终止: {contract.contract_status}",
                reason="contract_status_not_active",
            )

        deposit_balance = contract.total_deposit

        # 处理抵扣
        if deduction_amount > 0:
            if deduction_amount > deposit_balance:
                raise BusinessValidationError(
                    f"抵扣金额 {deduction_amount} 超过押金余额 {deposit_balance}",
                    field_errors={
                        "deduction_amount": ["超过押金余额"],
                    },
                )

            deduction = RentDepositLedger()
            deduction.contract_id = contract.id
            deduction.transaction_type = DepositTransactionType.DEDUCTION
            deduction.amount = -deduction_amount
            deduction.transaction_date = termination_date
            deduction.notes = f"终止抵扣: {termination_reason or '欠租等'}"
            deduction.operator = operator
            deduction.operator_id = operator_id
            db.add(deduction)
            deposit_balance -= deduction_amount

        # 退还剩余押金
        if should_refund_deposit and deposit_balance > 0:
            refund = RentDepositLedger()
            refund.contract_id = contract.id
            refund.transaction_type = DepositTransactionType.REFUND
            refund.amount = -deposit_balance
            refund.transaction_date = termination_date
            refund.notes = "终止退还押金"
            refund.operator = operator
            refund.operator_id = operator_id
            db.add(refund)

        # 更新合同状态
        setattr(contract, "contract_status", ContractStatus.TERMINATED)
        setattr(contract, "end_date", termination_date)
        db.add(contract)

        # 记录历史
        self._create_history(
            db,
            contract_id=contract.id,
            change_type="终止",
            change_description=f"提前终止: {termination_reason or '未说明'}",
            operator=operator,
            operator_id=operator_id,
        )

        db.commit()
        db.refresh(contract)
        return contract

    def upload_contract_attachment(
        self,
        db: Session,
        *,
        contract_id: str,
        file: UploadFile,
        file_type: str = "other",
        description: str | None = None,
        uploader_id: str,
        uploader_name: str,
    ) -> dict[str, Any]:
        """上传合同附件"""
        import uuid
        from pathlib import Path

        from ...crud.rent_contract import rent_contract
        from ...models.rent_contract import RentContractAttachment

        # 验证合同是否存在
        contract = rent_contract.get(db, id=contract_id)
        if not contract:
            raise ResourceNotFoundError("合同", contract_id)

        # 验证文件类型
        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ""

        if file_ext not in allowed_extensions:
            raise BusinessValidationError(
                f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_extensions)}"
            )

        # 创建上传目录
        upload_dir = (
            Path(settings.UPLOAD_DIR) / settings.RENT_CONTRACT_ATTACHMENT_SUBDIR
        )
        upload_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / unique_filename

        # 保存文件
        try:
            contents = file.file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
            file_size = len(contents)
            # 重置文件指针，以便其他地方可以再次读取
            file.file.seek(0)
        except Exception as e:
            raise FileProcessingError(
                message=f"文件保存失败: {str(e)}",
                file_name=file.filename,
                file_type=file.content_type,
            ) from e

        # 创建附件记录
        attachment = RentContractAttachment()
        attachment.contract_id = contract_id
        attachment.file_name = file.filename or "unnamed"
        attachment.file_path = str(file_path)
        attachment.file_size = file_size
        attachment.mime_type = file.content_type
        attachment.file_type = file_type
        attachment.description = description
        attachment.uploader = uploader_name
        attachment.uploader_id = uploader_id

        # 在一个事务中添加附件并提交
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        return {
            "id": attachment.id,
            "file_name": attachment.file_name,
            "file_size": attachment.file_size,
            "file_type": attachment.file_type,
            "description": attachment.description,
            "uploaded_at": attachment.created_at.isoformat(),
        }
