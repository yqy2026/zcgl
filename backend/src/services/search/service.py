from __future__ import annotations

from collections import OrderedDict
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.asset import asset_crud
from ...crud.party import party_crud
from ...crud.query_builder import PartyFilter
from ...models.certificate_party_relation import CertificatePartyRelation
from ...models.contract_group import Contract, ContractGroup
from ...models.property_certificate import PropertyCertificate
from ...schemas.project import ProjectSearchRequest
from ..party import party_service
from ..project import project_service


class SearchService:
    DEFAULT_LIMIT_PER_TYPE = 5

    async def search_global(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        effective_party_ids: list[str] | None,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        if normalized_query == "":
            return {"query": "", "total": 0, "items": [], "groups": []}

        normalized_effective_party_ids = [
            str(item).strip()
            for item in (effective_party_ids or [])
            if str(item).strip() != ""
        ]
        if len(normalized_effective_party_ids) == 0:
            return {"query": normalized_query, "total": 0, "items": [], "groups": []}

        items = await self._collect_results(
            db=db,
            query=normalized_query,
            scope_mode=scope_mode,
            effective_party_ids=normalized_effective_party_ids,
        )
        ranked_items = sorted(
            items,
            key=lambda item: (
                int(item.get("business_rank", 0)),
                int(item.get("score", 0)),
                str(item.get("title", "")),
            ),
            reverse=True,
        )
        groups = self._build_groups(ranked_items)
        return {
            "query": normalized_query,
            "total": len(ranked_items),
            "items": ranked_items,
            "groups": groups,
        }

    async def _collect_results(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        effective_party_ids: list[str],
    ) -> list[dict[str, Any]]:
        party_filter = self._build_party_filter(
            scope_mode=scope_mode,
            effective_party_ids=effective_party_ids,
        )
        results: list[dict[str, Any]] = []
        results.extend(
            await self._search_assets(
                db=db, query=query, scope_mode=scope_mode, party_filter=party_filter
            )
        )
        results.extend(
            await self._search_projects(
                db=db, query=query, scope_mode=scope_mode, party_filter=party_filter
            )
        )
        results.extend(
            await self._search_contract_groups(
                db=db,
                query=query,
                scope_mode=scope_mode,
                effective_party_ids=effective_party_ids,
            )
        )
        results.extend(
            await self._search_contracts(
                db=db,
                query=query,
                scope_mode=scope_mode,
                effective_party_ids=effective_party_ids,
            )
        )
        results.extend(
            await self._search_customers(
                db=db,
                query=query,
                scope_mode=scope_mode,
                effective_party_ids=effective_party_ids,
            )
        )
        results.extend(
            await self._search_property_certificates(
                db=db, query=query, scope_mode=scope_mode, party_filter=party_filter
            )
        )
        return results

    @staticmethod
    def _build_party_filter(
        *, scope_mode: str, effective_party_ids: list[str]
    ) -> PartyFilter:
        if scope_mode == "owner":
            return PartyFilter(
                party_ids=effective_party_ids,
                filter_mode="owner",
                owner_party_ids=effective_party_ids,
                manager_party_ids=[],
            )
        if scope_mode == "all":
            return PartyFilter(
                party_ids=effective_party_ids,
                filter_mode="any",
                owner_party_ids=[],
                manager_party_ids=[],
            )
        return PartyFilter(
            party_ids=effective_party_ids,
            filter_mode="manager",
            owner_party_ids=[],
            manager_party_ids=effective_party_ids,
        )

    @staticmethod
    def _apply_contract_group_scope(
        stmt: Any, *, scope_mode: str, effective_party_ids: list[str]
    ) -> Any:
        if scope_mode == "owner":
            return stmt.where(ContractGroup.owner_party_id.in_(effective_party_ids))
        if scope_mode == "manager":
            return stmt.where(ContractGroup.operator_party_id.in_(effective_party_ids))
        return stmt.where(
            or_(
                ContractGroup.owner_party_id.in_(effective_party_ids),
                ContractGroup.operator_party_id.in_(effective_party_ids),
            )
        )

    async def _search_assets(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        party_filter: PartyFilter,
    ) -> list[dict[str, Any]]:
        _ = scope_mode
        assets, _ = await asset_crud.get_multi_with_search_async(
            db,
            search=query,
            skip=0,
            limit=self.DEFAULT_LIMIT_PER_TYPE,
            include_relations=True,
            include_contract_projection=False,
            party_filter=party_filter,
        )
        return [
            self._build_result_item(
                object_type="asset",
                object_id=str(asset.id),
                title=str(getattr(asset, "asset_name", "")),
                subtitle=str(getattr(asset, "asset_code", "")).strip() or None,
                summary=str(getattr(asset, "address", "")).strip() or None,
                keywords=["asset_name"],
                route_path=f"/assets/{asset.id}",
                score=self._score_text(
                    query,
                    [
                        getattr(asset, "asset_name", None),
                        getattr(asset, "asset_code", None),
                    ],
                ),
                business_rank=self._business_rank(
                    query, [getattr(asset, "asset_code", None)]
                ),
                group_label="资产",
            )
            for asset in assets
        ]

    async def _search_projects(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        party_filter: PartyFilter,
    ) -> list[dict[str, Any]]:
        _ = scope_mode
        result = await project_service.search_projects(
            db,
            search_params=ProjectSearchRequest(
                keyword=query,
                status=None,
                owner_party_id=None,
                page=1,
                page_size=5,
            ),
            party_filter=party_filter,
        )
        items = result.get("items", [])
        return [
            self._build_result_item(
                object_type="project",
                object_id=str(project.id),
                title=str(getattr(project, "project_name", "")),
                subtitle=str(getattr(project, "project_code", "")).strip() or None,
                summary=str(getattr(project, "status", "")).strip() or None,
                keywords=["project_name"],
                route_path=f"/project/{project.id}",
                score=self._score_text(
                    query,
                    [
                        getattr(project, "project_name", None),
                        getattr(project, "project_code", None),
                    ],
                ),
                business_rank=self._business_rank(
                    query, [getattr(project, "project_code", None)]
                ),
                group_label="项目",
            )
            for project in items
        ]

    async def _search_contract_groups(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        effective_party_ids: list[str],
    ) -> list[dict[str, Any]]:
        stmt = select(ContractGroup).where(
            ContractGroup.data_status == "正常",
            ContractGroup.group_code.ilike(f"%{query}%"),
        )
        stmt = self._apply_contract_group_scope(
            stmt,
            scope_mode=scope_mode,
            effective_party_ids=effective_party_ids,
        )

        groups = list(
            (await db.execute(stmt.limit(self.DEFAULT_LIMIT_PER_TYPE))).scalars().all()
        )
        return [
            self._build_result_item(
                object_type="contract_group",
                object_id=str(group.contract_group_id),
                title=str(group.group_code),
                subtitle=str(getattr(group.revenue_mode, "name", group.revenue_mode)),
                summary=str(getattr(group, "effective_from", "")),
                keywords=["group_code"],
                route_path=f"/contract-groups/{group.contract_group_id}",
                score=self._score_text(query, [group.group_code]),
                business_rank=self._business_rank(query, [group.group_code]),
                group_label="合同组",
            )
            for group in groups
        ]

    async def _search_contracts(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        effective_party_ids: list[str],
    ) -> list[dict[str, Any]]:
        stmt = (
            select(Contract)
            .join(
                ContractGroup,
                Contract.contract_group_id == ContractGroup.contract_group_id,
            )
            .where(
                Contract.data_status == "正常",
                Contract.contract_number.ilike(f"%{query}%"),
            )
        )
        stmt = self._apply_contract_group_scope(
            stmt,
            scope_mode=scope_mode,
            effective_party_ids=effective_party_ids,
        )

        contracts = list(
            (await db.execute(stmt.limit(self.DEFAULT_LIMIT_PER_TYPE))).scalars().all()
        )
        return [
            self._build_result_item(
                object_type="contract",
                object_id=str(contract.contract_id),
                title=str(contract.contract_number),
                subtitle=str(
                    getattr(
                        contract.group_relation_type,
                        "name",
                        contract.group_relation_type,
                    )
                ),
                summary=str(getattr(contract, "status", "")),
                keywords=["contract_number"],
                route_path=f"/contract-groups/{contract.contract_group_id}",
                score=self._score_text(query, [contract.contract_number]),
                business_rank=self._business_rank(query, [contract.contract_number]),
                group_label="合同",
            )
            for contract in contracts
        ]

    async def _search_customers(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        effective_party_ids: list[str],
    ) -> list[dict[str, Any]]:
        stmt = (
            select(Contract)
            .join(
                ContractGroup,
                Contract.contract_group_id == ContractGroup.contract_group_id,
            )
            .where(
                Contract.data_status == "正常",
                ContractGroup.data_status == "正常",
            )
        )
        stmt = self._apply_contract_group_scope(
            stmt,
            scope_mode=scope_mode,
            effective_party_ids=effective_party_ids,
        )

        contracts = list((await db.execute(stmt)).scalars().all())
        customer_ids: OrderedDict[str, None] = OrderedDict()
        for contract in contracts:
            binding_types = (
                ["owner", "manager"] if scope_mode == "all" else [scope_mode]
            )
            for binding_type in binding_types:
                customer_party_id = party_service._resolve_customer_party_id(
                    contract,
                    binding_type,
                )
                if customer_party_id is not None:
                    customer_ids.setdefault(customer_party_id, None)

        items: list[dict[str, Any]] = []
        for customer_party_id in list(customer_ids.keys())[
            : self.DEFAULT_LIMIT_PER_TYPE * 3
        ]:
            party = await party_crud.get_party(db, party_id=customer_party_id)
            if party is None:
                continue
            metadata = getattr(party, "metadata_json", None) or {}
            searchable_values = [
                getattr(party, "name", None),
                getattr(party, "code", None),
                metadata.get("unified_identifier"),
            ]
            score = self._score_text(query, searchable_values)
            if score <= 0:
                continue
            items.append(
                self._build_result_item(
                    object_type="customer",
                    object_id=str(party.id),
                    title=str(party.name),
                    subtitle=str(metadata.get("customer_type", "customer")),
                    summary=str(metadata.get("unified_identifier", "")).strip() or None,
                    keywords=["customer_name"],
                    route_path=f"/customers/{party.id}",
                    score=score,
                    business_rank=self._business_rank(
                        query,
                        [
                            metadata.get("unified_identifier"),
                            getattr(party, "code", None),
                        ],
                    ),
                    group_label="客户",
                )
            )
        return items[: self.DEFAULT_LIMIT_PER_TYPE]

    async def _search_property_certificates(
        self,
        *,
        db: AsyncSession,
        query: str,
        scope_mode: str,
        party_filter: PartyFilter,
    ) -> list[dict[str, Any]]:
        _ = scope_mode
        party_ids = [
            str(item).strip()
            for item in party_filter.party_ids
            if str(item).strip() != ""
        ]
        if len(party_ids) == 0:
            return []
        stmt = (
            select(PropertyCertificate)
            .join(
                CertificatePartyRelation,
                CertificatePartyRelation.certificate_id == PropertyCertificate.id,
            )
            .where(
                CertificatePartyRelation.party_id.in_(party_ids),
                or_(
                    PropertyCertificate.certificate_number.ilike(f"%{query}%"),
                    PropertyCertificate.property_address.ilike(f"%{query}%"),
                ),
            )
            .distinct()
            .limit(self.DEFAULT_LIMIT_PER_TYPE)
        )
        certificates = list((await db.execute(stmt)).scalars().all())
        return [
            self._build_result_item(
                object_type="property_certificate",
                object_id=str(certificate.id),
                title=str(certificate.certificate_number),
                subtitle=str(
                    getattr(
                        certificate.certificate_type,
                        "value",
                        certificate.certificate_type,
                    )
                ),
                summary=str(getattr(certificate, "property_address", "")).strip()
                or None,
                keywords=["certificate_number"],
                route_path=f"/property-certificates/{certificate.id}",
                score=self._score_text(
                    query,
                    [
                        getattr(certificate, "certificate_number", None),
                        getattr(certificate, "property_address", None),
                    ],
                ),
                business_rank=self._business_rank(
                    query, [getattr(certificate, "certificate_number", None)]
                ),
                group_label="产权证",
            )
            for certificate in certificates
        ]

    @staticmethod
    def _build_result_item(
        *,
        object_type: str,
        object_id: str,
        title: str,
        subtitle: str | None,
        summary: str | None,
        keywords: list[str],
        route_path: str,
        score: int,
        business_rank: int,
        group_label: str,
    ) -> dict[str, Any]:
        return {
            "object_type": object_type,
            "object_id": object_id,
            "title": title,
            "subtitle": subtitle,
            "summary": summary,
            "keywords": keywords,
            "route_path": route_path,
            "score": score,
            "business_rank": business_rank,
            "group_label": group_label,
        }

    @staticmethod
    def _build_groups(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
        for item in items:
            object_type = str(item.get("object_type", "")).strip()
            if object_type == "":
                continue
            if object_type not in grouped:
                grouped[object_type] = {
                    "object_type": object_type,
                    "label": item.get("group_label", object_type),
                    "count": 0,
                }
            grouped[object_type]["count"] += 1
        return list(grouped.values())

    @staticmethod
    def _score_text(query: str, values: list[Any]) -> int:
        normalized_query = query.strip().lower()
        if normalized_query == "":
            return 0
        best_score = 0
        for value in values:
            normalized_value = str(value).strip().lower() if value is not None else ""
            if normalized_value == "":
                continue
            if normalized_value == normalized_query:
                best_score = max(best_score, 100)
            elif normalized_value.startswith(normalized_query):
                best_score = max(best_score, 85)
            elif normalized_query in normalized_value:
                best_score = max(best_score, 65)
        return best_score

    @staticmethod
    def _business_rank(query: str, values: list[Any]) -> int:
        normalized_query = query.strip().lower()
        if normalized_query == "":
            return 0
        for value in values:
            normalized_value = str(value).strip().lower() if value is not None else ""
            if normalized_value == normalized_query:
                return 60
            if normalized_value.startswith(normalized_query):
                return 40
        return 0


search_service = SearchService()
