from django.conf.urls import url, include
from rest_framework import routers
import views

router = routers.DefaultRouter()
router.register(r'recent', views.RecentGameViewSet,
    base_name="RecentData")
router.register(r'game', views.GameDataViewSet,
    base_name="GameData")
router.register(r'games', views.GameListViewSet,
    base_name="GameList")
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^', include(router.urls)),
]
