from sqlalchemy.orm import Session

from ..models.rent_contract import RentContractAttachment


class RentContractAttachmentCRUD:
    """合同附件 CRUD 操作"""

    def get_by_contract(
        self, db: Session, *, contract_id: str
    ) -> list[RentContractAttachment]:
        return (
            db.query(RentContractAttachment)
            .filter(RentContractAttachment.contract_id == contract_id)
            .order_by(RentContractAttachment.created_at.desc())
            .all()
        )

    def get(
        self,
        db: Session,
        *,
        attachment_id: str,
        contract_id: str | None = None,
    ) -> RentContractAttachment | None:
        query = db.query(RentContractAttachment).filter(
            RentContractAttachment.id == attachment_id
        )
        if contract_id:
            query = query.filter(RentContractAttachment.contract_id == contract_id)
        return query.first()


rent_contract_attachment_crud = RentContractAttachmentCRUD()
