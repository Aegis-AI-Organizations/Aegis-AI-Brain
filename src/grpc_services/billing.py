import logging
import asyncio
import grpc

import aegis.v2.billing_pb2 as billing_pb2
import aegis.v2.billing_pb2_grpc as billing_pb2_grpc
from config.db import get_session_factory
from models.company import Company
from models.token_ledger import TokenLedger
from grpc_services.utils import with_identity

logger = logging.getLogger(__name__)

# Pricing Matrix as per Step 3 requirements
PRICING_MATRIX = {"IP": 1, "API": 3, "WEBAPP": 5}
TOKEN_ADJUSTMENT_ROLES = {"superadmin", "billing_aegis"}
TOKEN_CONSUMPTION_ROLES = {"superadmin", "admin", "owner", "operateur", "billing_aegis"}


class BillingService(billing_pb2_grpc.BillingServiceServicer):
    """BillingService handles token balance and ledger management."""

    def __init__(self):
        self._session_factory = None

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = get_session_factory()
        return self._session_factory

    def _get_balance_db_sync(self, company_id: str):
        with self.session_factory() as db:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return None
            return company.token_balance

    @with_identity(verified_only=True)
    async def GetBalance(
        self, request: billing_pb2.GetBalanceRequest, context, identity
    ) -> billing_pb2.GetBalanceResponse:
        # RBAC: Owners/Viewers can only see their own balance, admins can see any
        if identity["role"] not in ["superadmin", "admin", "commercial"]:
            if str(identity.get("company_id")) != request.company_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                return billing_pb2.GetBalanceResponse()

        balance = await asyncio.to_thread(self._get_balance_db_sync, request.company_id)
        if balance is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Company not found")
            return billing_pb2.GetBalanceResponse()

        return billing_pb2.GetBalanceResponse(
            company_id=request.company_id, balance=balance
        )

    def _get_ledger_db_sync(self, company_id: str, limit: int, offset: int):
        with self.session_factory() as db:
            query = db.query(TokenLedger).filter(TokenLedger.company_id == company_id)
            total = query.count()
            entries = (
                query.order_by(TokenLedger.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return entries, total

    @with_identity(verified_only=True)
    async def GetLedger(
        self, request: billing_pb2.GetLedgerRequest, context, identity
    ) -> billing_pb2.GetLedgerResponse:
        # RBAC: Owners/Viewers can only see their own ledger, admins can see any
        if identity["role"] not in ["superadmin", "admin", "commercial"]:
            if str(identity.get("company_id")) != request.company_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                return billing_pb2.GetLedgerResponse()

        limit = request.limit if request.limit > 0 else 50
        offset = request.offset if request.offset >= 0 else 0

        entries, total = await asyncio.to_thread(
            self._get_ledger_db_sync, request.company_id, limit, offset
        )

        proto_entries = []
        for e in entries:
            entry = billing_pb2.LedgerEntry(
                id=str(e.id),
                company_id=str(e.company_id),
                amount=e.amount,
                reason=e.reason,
                scan_id=str(e.scan_id) if e.scan_id else "",
            )
            if e.created_at:
                entry.created_at.FromDatetime(e.created_at)
            proto_entries.append(entry)

        return billing_pb2.GetLedgerResponse(entries=proto_entries, total=total)

    def _adjust_tokens_db_sync(self, company_id: str, amount: int, reason: str):
        with self.session_factory() as db:
            try:
                # Use FOR UPDATE to prevent race conditions on balance
                company = (
                    db.query(Company)
                    .filter(Company.id == company_id)
                    .with_for_update()
                    .first()
                )
                if not company:
                    return None, "Company not found"

                # Check for negative balance if subtracting
                if amount < 0 and company.token_balance + amount < 0:
                    return None, "Insufficient token balance"

                # ACID Transaction: Update balance and create ledger entry
                company.token_balance += amount

                ledger_entry = TokenLedger(
                    company_id=company.id, amount=amount, reason=reason
                )
                db.add(ledger_entry)

                db.commit()
                return company.token_balance, None
            except Exception as e:
                db.rollback()
                logger.exception("Failed to adjust tokens")
                return None, str(e)

    @with_identity(verified_only=True)
    async def AdjustTokens(
        self, request: billing_pb2.AdjustTokensRequest, context, identity
    ) -> billing_pb2.AdjustTokensResponse:
        if not can_adjust_tokens(identity, request.company_id, request.amount):
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return billing_pb2.AdjustTokensResponse()

        balance, error = await asyncio.to_thread(
            self._adjust_tokens_db_sync,
            request.company_id,
            request.amount,
            request.reason,
        )

        if error:
            status_code = (
                grpc.StatusCode.FAILED_PRECONDITION
                if "Insufficient" in error
                else grpc.StatusCode.INTERNAL
            )
            context.set_code(status_code)
            context.set_details(error)
            return billing_pb2.AdjustTokensResponse()

        return billing_pb2.AdjustTokensResponse(
            company_id=request.company_id, balance=balance
        )

    @with_identity(verified_only=True)
    async def PreFlightCheck(
        self, request: billing_pb2.PreFlightCheckRequest, context, identity
    ) -> billing_pb2.PreFlightCheckResponse:
        # RBAC check
        if (
            identity["role"] == "owner"
            and str(identity.get("company_id")) != request.company_id
        ):
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return billing_pb2.PreFlightCheckResponse()

        # 1. Calculate estimated cost based on Pricing Matrix
        estimated_cost = (
            request.target_config.ip_count * PRICING_MATRIX["IP"]
            + request.target_config.api_count * PRICING_MATRIX["API"]
            + request.target_config.webapp_count * PRICING_MATRIX["WEBAPP"]
        )

        # 2. Get current balance
        balance = await asyncio.to_thread(self._get_balance_db_sync, request.company_id)
        if balance is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return billing_pb2.PreFlightCheckResponse()
        return billing_pb2.PreFlightCheckResponse(
            sufficient_balance=(balance >= estimated_cost),
            estimated_cost=estimated_cost,
            current_balance=balance,
        )

    def _get_usage_stats_db_sync(self, company_id: str, days: int):
        from sqlalchemy import func, cast, Date
        from datetime import datetime, timedelta, timezone

        with self.session_factory() as db:
            since = datetime.now(timezone.utc) - timedelta(days=days)

            # Query: Aggregate daily negative amounts (consumption)
            # We filter for amount < 0 to only count "spending"
            stats = (
                db.query(
                    cast(TokenLedger.created_at, Date).label("day"),
                    func.abs(func.sum(TokenLedger.amount)).label("total"),
                )
                .filter(TokenLedger.company_id == company_id)
                .filter(TokenLedger.created_at >= since)
                .filter(TokenLedger.amount < 0)
                .group_by(cast(TokenLedger.created_at, Date))
                .order_by("day")
                .all()
            )

            total_period = sum(s.total for s in stats)
            usage_days = [
                billing_pb2.UsageDay(date=s.day.isoformat(), total_consumed=s.total)
                for s in stats
            ]

            return usage_days, total_period

    @with_identity(verified_only=True)
    async def GetUsageStats(
        self, request: billing_pb2.GetUsageStatsRequest, context, identity
    ) -> billing_pb2.GetUsageStatsResponse:
        # RBAC check
        if (
            identity["role"] == "owner"
            and str(identity.get("company_id")) != request.company_id
        ):
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return billing_pb2.GetUsageStatsResponse()

        days = request.days if request.days > 0 else 30

        usage_days, total_period = await asyncio.to_thread(
            self._get_usage_stats_db_sync, request.company_id, days
        )

        return billing_pb2.GetUsageStatsResponse(
            days=usage_days, total_period=total_period
        )


def can_adjust_tokens(identity, company_id: str, amount: int) -> bool:
    role = identity.get("role")
    if role in TOKEN_ADJUSTMENT_ROLES:
        return True

    if amount >= 0 or role not in TOKEN_CONSUMPTION_ROLES:
        return False

    return str(identity.get("company_id") or "") == company_id
