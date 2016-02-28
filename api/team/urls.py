from django.conf.urls import url, include
from rest_framework import routers
import views

router = routers.DefaultRouter()
router.register(r'teams', views.TeamsViewSet)
router.register(r'team', views.TeamViewSet,
    base_name='team')
router.register(r'venues', views.VenueViewSet)
router.register(r'stats', views.SeasonStatsViewSet)
router.register(r'dailystats', views.HistoricalStandingsView,
    base_name='dailystats')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^', include(router.urls)),
]