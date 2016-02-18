from __future__ import unicode_literals

from django.db import models

import constants


class Player(models.Model):
    id = models.IntegerField(primary_key=True)
    fullName = models.CharField(max_length=100)
    link = models.URLField()
    firstName = models.CharField(max_length=50)
    lastName = models.CharField(max_length=50)
    primaryNumber = models.IntegerField(null=True, blank=True)
    primaryPositionCode = models.CharField(max_length=1, choices=constants.playerPositions)
    birthDate = models.DateField()
    birthCity = models.CharField(max_length=100)
    birthStateProvince = models.CharField(max_length=100)
    birthCountry = models.CharField(max_length=100)
    height = models.CharField(max_length=10)
    weight = models.IntegerField()
    active = models.BooleanField(default=True)
    rookie = models.BooleanField(default=False)
    shootsCatches = models.CharField(max_length=1, blank=True, null=True)
    rosterStatus = models.CharField(max_length=1, choices=constants.rosterChoices)
    currentTeam = models.ForeignKey("team.Team", blank=True, null=True)

    def __unicode__(self):
        return self.fullName
