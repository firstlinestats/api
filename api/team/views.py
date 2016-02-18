from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

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


@permission_classes((IsAuthenticatedOrReadOnly, ))
class HistoricalStandingsView(viewsets.ViewSet):
    def list(self, request, *args, **kwargs):
        standings = HistoricalCalculations()
        results = standings.do_work()
        response = Response(results)
        return response


class HistoricalCalculations(object):
    def __init__(self, *args, **kwargs):
        pass

    def do_work(self):
        season = models.SeasonStats.objects.values("season").latest("season")["season"]
        season_data = models.SeasonStats.objects.values("date", "team__teamName", "points").filter(season=season)
        teams = {}
        for s in season_data:
            teamName = s["team__teamName"]
            date = s["date"]
            points = s["points"]
            if s["team__teamName"] not in teams:
                teams[teamName] = []
            teams[teamName].append({"date": date, "points": points})
        return teams
