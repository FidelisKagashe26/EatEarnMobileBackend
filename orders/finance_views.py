"""Money settlement endpoints.

Flow per DELIVERED order (percentages set by the admin on each vendor):
  - vendor owes platform:   commission_amount = commission% × subtotal
  - platform owes the agent: delivery_earning = delivery_share% × commission

Payments recorded here settle those balances:
  - delivery_payout:    admin → delivery agent
  - vendor_settlement:  vendor → admin
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.views import is_admin
from catalog.models import Vendor

from .models import Order, Payment

DELIVERED = "DELIVERED"


def _sum(queryset, field):
    return queryset.aggregate(total=Sum(field))["total"] or 0


class MyEarningsView(APIView):
    """A delivery agent's ledger: earned, paid, and the outstanding balance."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.DELIVERY and not is_admin(request.user):
            return Response({"detail": "Delivery agents only."}, status=status.HTTP_403_FORBIDDEN)

        delivered = Order.objects.filter(delivery_agent=request.user, status=DELIVERED)
        earned = _sum(delivered, "delivery_earning")
        payments = Payment.objects.filter(agent=request.user, kind=Payment.Kind.DELIVERY_PAYOUT)
        paid = _sum(payments, "amount")

        return Response({
            "earned": earned,
            "paid": paid,
            "balance": earned - paid,
            "deliveredTrips": delivered.count(),
            "payments": [
                {
                    "id": str(p.id),
                    "amount": p.amount,
                    "note": p.note,
                    "createdAt": p.created_at.isoformat(),
                }
                for p in payments[:20]
            ],
        })


class FinanceSummaryView(APIView):
    """Admin overview: what the platform owes agents and is owed by vendors."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin(request.user):
            return Response({"detail": "Admins only."}, status=status.HTTP_403_FORBIDDEN)

        # --- Delivery agents (platform pays them) ---
        agents = []
        for agent in User.objects.filter(role=User.Role.DELIVERY):
            earned = _sum(Order.objects.filter(delivery_agent=agent, status=DELIVERED), "delivery_earning")
            paid = _sum(Payment.objects.filter(agent=agent, kind=Payment.Kind.DELIVERY_PAYOUT), "amount")
            if earned or paid:
                agents.append({
                    "id": str(agent.id),
                    "name": agent.full_name,
                    "phone": agent.phone,
                    "earned": earned,
                    "paid": paid,
                    "balance": earned - paid,
                })
        agents.sort(key=lambda row: row["balance"], reverse=True)

        # --- Vendors (they pay the platform) ---
        vendors = []
        for vendor in Vendor.objects.all():
            commission = _sum(Order.objects.filter(vendor=vendor, status=DELIVERED), "commission_amount")
            received = _sum(Payment.objects.filter(vendor=vendor, kind=Payment.Kind.VENDOR_SETTLEMENT), "amount")
            if commission or received:
                vendors.append({
                    "id": str(vendor.id),
                    "name": vendor.name,
                    "commission": commission,
                    "received": received,
                    "balance": commission - received,
                })
        vendors.sort(key=lambda row: row["balance"], reverse=True)

        return Response({
            "delivery": {
                "totalEarned": sum(a["earned"] for a in agents),
                "totalPaid": sum(a["paid"] for a in agents),
                "totalOutstanding": sum(a["balance"] for a in agents),
                "agents": agents,
            },
            "vendors": {
                "totalCommission": sum(v["commission"] for v in vendors),
                "totalReceived": sum(v["received"] for v in vendors),
                "totalOutstanding": sum(v["balance"] for v in vendors),
                "vendors": vendors,
            },
        })


class ReportStatsView(APIView):
    """Period statistics for reports: today / week / month / year.

    Returns totals plus a breakdown (per day for short periods, per month for
    a year) and per-vendor / per-agent tables for the same window — enough to
    render and print a complete report.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin(request.user):
            return Response({"detail": "Admins only."}, status=status.HTTP_403_FORBIDDEN)

        period = request.query_params.get("period", "week")
        now = timezone.localtime()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "today":
            start = start_of_day
        elif period == "month":
            start = start_of_day - timedelta(days=29)
        elif period == "year":
            start = start_of_day.replace(month=1, day=1)
        else:  # week (default)
            period = "week"
            start = start_of_day - timedelta(days=6)

        delivered = (
            Order.objects.filter(status=DELIVERED, placed_at__gte=start)
            .select_related("vendor", "delivery_agent")
            .prefetch_related("items")
        )

        buckets: dict[str, dict] = {}
        vendor_rows: dict[str, dict] = {}
        agent_rows: dict[str, dict] = {}
        totals = {"orders": 0, "revenue": 0, "commission": 0, "deliveryEarnings": 0}

        for order in delivered:
            local = timezone.localtime(order.placed_at)
            key = local.strftime("%b %Y") if period == "year" else local.strftime("%d %b")
            row = buckets.setdefault(
                key,
                {"label": key, "sort": local.strftime("%Y-%m-%d"), "orders": 0, "revenue": 0,
                 "commission": 0, "deliveryEarnings": 0},
            )
            commission = order.commission_amount or 0
            earning = order.delivery_earning or 0

            row["orders"] += 1
            row["revenue"] += order.total
            row["commission"] += commission
            row["deliveryEarnings"] += earning

            totals["orders"] += 1
            totals["revenue"] += order.total
            totals["commission"] += commission
            totals["deliveryEarnings"] += earning

            v = vendor_rows.setdefault(
                order.vendor.name, {"name": order.vendor.name, "orders": 0, "revenue": 0, "commission": 0}
            )
            v["orders"] += 1
            v["revenue"] += order.total
            v["commission"] += commission

            if order.delivery_agent_id:
                a = agent_rows.setdefault(
                    order.delivery_agent.full_name,
                    {"name": order.delivery_agent.full_name, "trips": 0, "earnings": 0},
                )
                a["trips"] += 1
                a["earnings"] += earning

        rows = sorted(buckets.values(), key=lambda r: r["sort"])
        for row in rows:
            row.pop("sort", None)

        return Response({
            "period": period,
            "from": start.isoformat(),
            "generatedAt": now.isoformat(),
            "totals": totals,
            "rows": rows,
            "vendors": sorted(vendor_rows.values(), key=lambda r: r["revenue"], reverse=True),
            "agents": sorted(agent_rows.values(), key=lambda r: r["earnings"], reverse=True),
        })


class RecordPaymentView(APIView):
    """Admin records a settlement: a payout to an agent or cash in from a vendor."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_admin(request.user):
            return Response({"detail": "Admins only."}, status=status.HTTP_403_FORBIDDEN)

        kind = request.data.get("kind")
        try:
            amount = int(request.data.get("amount"))
        except (TypeError, ValueError):
            return Response({"detail": "amount must be a number."}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"detail": "amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        note = (request.data.get("note") or "").strip()

        if kind == "delivery_payout":
            agent = User.objects.filter(pk=request.data.get("agentId"), role=User.Role.DELIVERY).first()
            if not agent:
                return Response({"detail": "Delivery agent not found."}, status=status.HTTP_404_NOT_FOUND)
            Payment.objects.create(
                kind=Payment.Kind.DELIVERY_PAYOUT, agent=agent, amount=amount,
                note=note, recorded_by=request.user,
            )
        elif kind == "vendor_settlement":
            vendor = Vendor.objects.filter(pk=request.data.get("vendorId")).first()
            if not vendor:
                return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)
            Payment.objects.create(
                kind=Payment.Kind.VENDOR_SETTLEMENT, vendor=vendor, amount=amount,
                note=note, recorded_by=request.user,
            )
        else:
            return Response(
                {"detail": "kind must be 'delivery_payout' or 'vendor_settlement'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": "Payment recorded."}, status=status.HTTP_201_CREATED)
