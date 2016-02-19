from django.conf.urls import url, include
from rest_framework import routers
import views

router = routers.DefaultRouter()
router.register(r'recent', views.RecentGameViewSet)
router.register(r'playerstats', views.PlayerGameStatsViewSet,
    base_name="PlayerStats")
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^', include(router.urls)),
]
