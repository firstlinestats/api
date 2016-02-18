from rest_framework import serializers

import models
import constants


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Venue
        fields = ("name", "city", "timeZone", "timeZoneOffset")


class TeamSerializer(serializers.ModelSerializer):
    conference = serializers.SerializerMethodField('GetConference')
    division = serializers.SerializerMethodField('GetDivision')
    venue = VenueSerializer(many=False, read_only=True)

    class Meta:
        model = models.Team
        fields = ("name", "shortName", "abbreviation", "venue",
            "teamName", "locationName", "firstYearOfPlay",
            "conference", "division", "officialSiteUrl")

    def GetConference(self, obj):
        for field in constants.conferences:
            if field[0] == obj.conference:
                return field[1]
        return obj.conference

    def GetDivision(self, obj):
        for field in constants.divisions:
            if field[0] == obj.division:
                return field[1]
        return obj.division


class SeasonStatsSerializer(serializers.ModelSerializer):
    team = TeamSerializer(many=False, read_only=True)

    class Meta:
        model = models.SeasonStats
        fields = ("date", "team", "season", "goalsAgainst",
            "goalsScored", "points", "gamesPlayed", "streakCode",
            "wins", "losses", "ot")
