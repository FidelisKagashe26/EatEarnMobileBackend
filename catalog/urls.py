from rest_framework.routers import DefaultRouter

from .views import MenuItemViewSet, VendorViewSet

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")
router.register("menu-items", MenuItemViewSet, basename="menuitem")

urlpatterns = router.urls
