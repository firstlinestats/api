from rest_framework import serializers
from team.serializers import TeamSerializer
import constants
import models


class RecentGameSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField('GetDate')
    gameState = serializers.SerializerMethodField('GetGameState')
    gameType = serializers.SerializerMethodField('GetGameType')
    corsi = serializers.SerializerMethodField('GetCorsi')
    score = serializers.SerializerMethodField('GetScore')
    homeTeam = TeamSerializer()
    awayTeam = TeamSerializer()

    class Meta:
        model = models.Game
        fields = ("gameType", "homeTeam", "score",
            "awayTeam", "corsi", "gameState", "dateTime",
            "endDateTime", "date")

    def GetGameType(self, obj):
        for item in constants.gameTypes:
            if item[0] == obj.gameType:
                return item[1]
        return obj.gameType

    def GetGameState(self, obj):
        for item in constants.gameStates:
            if item[0] == obj.gameState:
                return item[1]
        return obj.gameState

    def GetDate(self, obj):
        return obj.dateTime.date()

    def GetScore(self, obj):
        return str(obj.homeScore) + "-" + str(obj.awayScore)

    def GetCorsi(self, obj):
        return str(self.GetHomeCorsi(obj)) + "/" + str(self.GetAwayCorsi(obj))

    def GetHomeCorsi(self, obj):
        shots = obj.homeShots or 0
        score = obj.homeScore or 0
        missed = obj.homeMissed or 0
        blocked = obj.awayBlocked or 0
        return shots + score + missed + blocked

    def GetAwayCorsi(self, obj):
        shots = obj.awayShots or 0
        score = obj.awayScore or 0
        missed = obj.awayMissed or 0
        blocked = obj.homeBlocked or 0
        return shots + score + missed + blocked
