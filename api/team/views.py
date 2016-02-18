from django.shortcuts import render

from rest_framework import viewsets

import models
import serializers


# Create your views here.
class TeamViewSet(viewsets.ModelViewSet):
    queryset = models.Team.objects.all().order_by("name")
    serializer_class = serializers.TeamSerializer


class VenueViewSet(viewsets.ModelViewSet):
    queryset = models.Venue.objects.all()
    serializer_class = serializers.VenueSerializer


class SeasonStatsViewSet(viewsets.ModelViewSet):
    queryset = models.SeasonStats.objects.filter(date=str(models.SeasonStats.objects.latest('date').date))
    serializer_class = serializers.SeasonStatsSerializer
