from __future__ import unicode_literals

from django.db import models

import constants


class Venue(models.Model):
    name = models.CharField(max_length=50)
    city = models.CharField(max_length=50, null=True, blank=True)
    timeZone = models.CharField(max_length=50, null=True, blank=True)
    timeZoneOffset = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("name", "city")

    def __unicode__(self):
        if self.city is not None:
            return self.name + ", " + self.city
        return self.name



class Team(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    shortName = models.CharField(max_length=50)
    link = models.URLField()
    venue = models.ForeignKey(Venue)
    abbreviation = models.CharField(max_length=3)
    teamName = models.CharField(max_length=50)
    locationName = models.CharField(max_length=50)
    firstYearOfPlay = models.IntegerField()
    conference = models.CharField(max_length=1, choices=constants.conferences)
    division = models.CharField(max_length=1, choices=constants.divisions)
    officialSiteUrl = models.URLField()
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name


class SeasonStats(models.Model):
    date = models.DateField()
    team = models.ForeignKey(Team)
    season = models.IntegerField()
    goalsAgainst = models.IntegerField(null=True, blank=True)
    goalsScored = models.IntegerField(null=True, blank=True)
    points = models.IntegerField()
    gamesPlayed = models.IntegerField()
    streakCode = models.CharField(max_length=3, null=True, blank=True)
    wins = models.IntegerField()
    losses = models.IntegerField()
    ot = models.IntegerField()

    class Meta:
        unique_together = ("date", "team")
