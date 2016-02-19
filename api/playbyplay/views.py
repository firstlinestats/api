from django.shortcuts import render

from rest_framework import viewsets

import datetime
import models
import serializers

# Create your views here.
class RecentGameViewSet(viewsets.ModelViewSet):
    queryset = models.Game.objects.filter(dateTime__date__lte=datetime.date.today()).order_by('-dateTime', '-gamePk')[:30]
    serializer_class = serializers.RecentGameSerializer
