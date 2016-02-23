from django.conf.urls import url, include
from rest_framework import routers
import views

router = routers.DefaultRouter()
router.register(r'recent', views.RecentGameViewSet)
router.register(r'playerstats', views.PlayerGameStatsViewSet,
    base_name="PlayerStats")
router.register(r'goaliestats', views.GoalieGameStatsViewSet,
    base_name="GoalieStats")
router.register(r'game', views.GameDataViewSet,
    base_name="GameData")
router.register(r'games', views.GameListViewSet,
    base_name="GameList")
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^', include(router.urls)),
]
