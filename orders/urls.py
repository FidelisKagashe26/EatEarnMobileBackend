from django.urls import path
from rest_framework.routers import DefaultRouter

from .finance_views import FinanceSummaryView, MyEarningsView, RecordPaymentView, ReportStatsView
from .views import OrderViewSet

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("finance/my-earnings/", MyEarningsView.as_view(), name="finance-my-earnings"),
    path("finance/summary/", FinanceSummaryView.as_view(), name="finance-summary"),
    path("finance/payments/", RecordPaymentView.as_view(), name="finance-payments"),
    path("finance/stats/", ReportStatsView.as_view(), name="finance-stats"),
    *router.urls,
]
