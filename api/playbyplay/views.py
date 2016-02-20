from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from rest_framework import viewsets
from rest_framework import filters
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

import pytz
import datetime
import serializers

import models
import helper
import helpers
from player.helper import getPosition
from playbyplay.constants import gameTypes


# Create your views here.
@permission_classes((IsAuthenticatedOrReadOnly, ))
class GameDataViewSet(viewsets.ViewSet):
    def list(self, request):
        getValues = dict(request.GET)
        gamePk = getValues.get("gamePk", None)
        if gamePk is not None:
            gamePk = int(gamePk[0])
        else:
            return Response({"details": "Game not found."})
        gameData = {"details": {}, "teamData": [], "goalies": [],
            "homeSkaters": [], "awaySkaters": []}


        game = models.Game.objects.get(gamePk=gamePk)
        details = {}
        details["homeTeamName"] = game.homeTeam.teamName
        details["awayTeamName"] = game.awayTeam.teamName
        details["homeTeamAbbr"] = game.homeTeam.abbreviation
        details["awayTeamAbbr"] = game.awayTeam.abbreviation
        details["homeScore"] = game.homeScore
        details["awayScore"] = game.awayScore
        details["venue"] = str(game.venue)
        details["date"] = game.dateTime.astimezone(pytz.timezone('US/Eastern')).strftime("%B %d, %Y %r")
        gameData["details"] = details
        if game.gameState in ['3', '4', '5', '6', '7']:
            pbp = models.PlayByPlay.objects.filter(gamePk=gamePk)
            playerStats = models.PlayerGameStats.objects.filter(game=gamePk).order_by('team', 'player__lastName')
            goalieStats = models.GoalieGameStats.objects.filter(game=gamePk)

            homeTeam = helper.init_team()
            homeTeam["teamName"] = game.homeTeam.teamName
            homeTeam["teamAbbr"] = game.homeTeam.abbreviation
            awayTeam = helper.init_team()
            awayTeam["teamName"] = game.awayTeam.teamName
            awayTeam["teamAbbr"] = game.awayTeam.abbreviation

            """players = {}
            for playerdata in playerStats:
                player = helper.init_player()
                player["name"] = playerdata.player.fullName
                player["position"] = playerdata.player.primaryPositionCode
                player["team"] = playerdata.team
                players[playerdata.player_id] = player
            for goaliedata in goalieStats:
                player = helper.init_player()
                player["name"] = goaliedata.player.fullName
                player["position"] = goaliedata.player.primaryPositionCode
                player["team"] = goaliedata.team
                players[goaliedata.player_id] = player

            poi_data = models.PlayerOnIce.objects\
                .values("player_id", "play_id").filter(play__in=pbp)
            onice = {}
            for p in poi_data:
                player_id = p["player_id"]
                play_id = p["play_id"]
                if play_id not in onice:
                    onice[play_id] = set()
                onice[play_id].add(player_id)

            pip_data = models.PlayerInPlay.objects.values("play_id",
                "player_id", "player_type").filter(play__in=pbp)

            pos = 0
            neg = 0
            for play in pbp:
                play_id = play.id
                team = play.team
                if play_id in onice:
                    poi = onice[play_id]
                    play_type = play.playType
                    if play_type == "SHOT":
                        if team == homeTeam["team"]:
                            homeTeam["sf"] += 1
                        else:
                            awayTeam["sf"] += 1
                        for pid in poi:
                            if players[pid]["team"] == team:
                                players[pid]["sf"] += 1
                            else:
                                players[pid]["sa"] += 1
                    elif play_type == "GOAL":
                        if team == homeTeam["team"]:
                            homeTeam["gf"] += 1
                            homeTeam["sf"] += 1
                        else:
                            awayTeam["gf"] += 1
                            awayTeam["sf"] += 1
                        for pid in poi:
                            if players[pid]["team"] == team:
                                players[pid]["gf"] += 1
                            else:
                                players[pid]["ga"] += 1
                    elif play_type == "MISSED_SHOT":
                        if team == homeTeam["team"]:
                            homeTeam["msf"] += 1
                        else:
                            awayTeam["msf"] += 1
                        for pid in poi:
                            if players[pid]["team"] == team:
                                players[pid]["msf"] += 1
                            else:
                                players[pid]["msa"] += 1
                    elif play_type == "BLOCKED_SHOT":
                        if team == homeTeam["team"]:
                            homeTeam["bsf"] += 1
                        else:
                            awayTeam["bsf"] += 1
                        for pid in poi:
                            if players[pid]["team"] == team:
                                players[pid]["bsf"] += 1
                            else:
                                players[pid]["bsa"] += 1

            for pid in players:
                player = players[pid]
                player["cf"] = player["sf"] + player["msf"] + player["bsa"]
                player["ca"] = player["sa"] + player["msa"] + player["bsf"]
                player["ff"] = player["cf"] - player["bsa"]
                player["fa"] = player["ca"] - player["bsf"]
                player["g+-"] = player["gf"] - player["ga"]
                player["p"] = player["g"] + player["a1"] + player["a2"]
            homeTeam["cf"] = homeTeam["sf"] + homeTeam["gf"] + awayTeam["bsf"]
            awayTeam["cf"] = awayTeam["sf"] + awayTeam["gf"] + homeTeam["bsf"]

            # Get individual actions
            type_sum = {1: "fo_w", 2: "fo_l", 3: "hit+", 4: "hit-",
                5: "g", 6: "a1", 7: "icf", 8: "save", 9: "ab",
                10: "pn-", 11: "pn+", 16: "a2"}
            for pip in pip_data:
                player = players[pip["player_id"]]
                player_type = pip["player_type"]
                if player_type == 1:
                    if player["team"] == homeTeam["team"]:
                        homeTeam["fo_w"] += 1
                    else:
                        awayTeam["fo_w"] += 1
                elif player_type == 3:
                    if player["team"] == homeTeam["team"]:
                        homeTeam["hit+"] += 1
                    else:
                        awayTeam["hit+"] += 1
                if player_type in type_sum:
                    player[type_sum[player_type]] += 1"""

            gameData["teamData"].append(homeTeam)
            gameData["teamData"].append(awayTeam)


        return Response(gameData)


class RecentGameViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Game.objects.filter(dateTime__date__lte=datetime.date.today()).order_by('-dateTime', '-gamePk')[:30]
    serializer_class = serializers.RecentGameSerializer


@permission_classes((IsAuthenticatedOrReadOnly, ))
class PlayerGameStatsViewSet(viewsets.ViewSet):
    def list(self, request):
        currentSeason = models.Game.objects.latest("endDateTime").season
        getValues = dict(request.GET)
        for key in getValues:
            val = getValues[key]
            if len(val) == 0:
                getValues.pop(key, None)
        args = ()
        kwargs = {
            'game__gameState__in': [6, 7, 8],
            'game__season__in': [currentSeason, ]
        }
        if "date_start" in getValues and "date_end" in getValues:
            try:
                date_start = datetime.datetime.strptime(getValues["date_start"][0], "%m/%d/%Y").date()
                date_end =  datetime.datetime.strptime(getValues["date_end"][0], "%m/%d/%Y").date()

                kwargs['game__dateTime__gte'] = date_start
                kwargs['game__dateTime__lte'] = date_end
            except:
                date_start = None
                date_end = None
        bySeason = False
        if "divide_by_season" in getValues:
            if "on" == getValues["divide_by_season"][0]:
                bySeason = True
        game_types = gameTypes
        if "game_type" in getValues and len(getValues["game_type"]) > 0:
            game_types = getValues["game_type"]
            kwargs['game__gameType__in'] = game_types
        venues = None
        if "venues" in getValues and len(getValues["venues"]) > 0:
            venues = getValues["venues"]
            kwargs['game__venue__name__in'] = venues
        teams = None
        if "teams" in getValues and len(getValues["teams"]) > 0:
            teams = getValues["teams"]
            args = ( Q(game__awayTeam__in = getValues['teams']) | Q(game__homeTeam__in = getValues['teams']), )
        toi = None
        if "toi" in getValues and len(getValues["toi"]) > 0:
            try:
                toi = int(getValues["toi"][0])
                if toi > 60:
                    h, m = divmod(toi, 60)
                    kwargs['timeOnIce__gte'] = "%02d:%02d:00" % (h, m)
                else:
                    kwargs['timeOnIce__gte'] = "00:%02d:00" % (toi, )
            except:
                pass
        seasons = currentSeason
        if "seasons" in getValues and len(getValues["seasons"]) > 0:
            seasons = getValues["seasons"]
            kwargs['game__season__in'] = seasons
        home_or_away = None
        if "home_or_away" in getValues and len(getValues["home_or_away"]) > 0:
            try:
                home_or_away = int(getValues["home_or_away"][0])
                if home_or_away == 1:
                    home_or_away = False
                elif home_or_away == 2:
                    home_or_away = None
                else:
                    home_or_away = True
            except:
                pass
        positions = None
        if "position" in getValues and len(getValues["position"]) > 0:
            positions = getValues["position"]
            kwargs['player__primaryPositionCode__in'] = positions

        today = datetime.date.today()
        start = datetime.datetime.now()
        tgameStats = models.PlayerGameStats.objects\
            .values("player__fullName", "player__currentTeam__shortName",
                "player__currentTeam", "player__primaryPositionCode",
                "player__birthDate", "player__weight", "player__height",
                "player__currentTeam__abbreviation", "hits",
                "player__id", "timeOnIce", "assists", "goals", "shots",
                "powerPlayGoals", "powerPlayAssists", "penaltyMinutes",
                "faceOffWins", "faceoffTaken", "takeaways", "giveaways",
                "shortHandedGoals", "shortHandedAssists", "blocked",
                "plusMinus", "evenTimeOnIce", "powerPlayTimeOnIce",
                "shortHandedTimeOnIce", "player__id", "team",
                "game__homeTeam", "game__season")\
            .filter(*args, **kwargs).iterator()
        if bySeason is False:
            gameStats = {}
        else:
            seasonStats = {}
        pid = "player__id"
        exclude = [pid, "player__birthDate", "player__primaryPositionCode",
            "player__fullName", "player__currentTeam", "team",
            "player__currentTeam__abbreviation", "player__id",
            "player__currentTeam__shortName", "player__height",
            "player__weight", "game__season", "game__homeTeam"]

        for t in tgameStats:
            counts = True
            if home_or_away is not None:
                counts = False
                if home_or_away is True and t["team"] == t["game__homeTeam"]:
                    counts = True
                elif home_or_away is False and t["team"] != t["game__homeTeam"]:
                    counts = True
            if counts is True:
                if bySeason is True:
                    if t["game__season"] not in seasonStats:
                        seasonStats[t["game__season"]] = {}
                    gameStats = seasonStats[t["game__season"]]
                if t[pid] not in gameStats:
                    gameStats[t[pid]] = t
                    gameStats[t[pid]]["games"] = 1
                    gameStats[t[pid]]["age"] = helpers.calculate_age(t["player__birthDate"], today=today)
                    gameStats[t[pid]]["player__primaryPositionCode"] = getPosition(t["player__primaryPositionCode"])
                    d1 = gameStats[t[pid]]["timeOnIce"]
                    gameStats[t[pid]]["timeOnIce"] = datetime.timedelta(minutes=d1.minute, seconds=d1.second)
                else:
                    gameStats[t[pid]]["games"] += 1
                    for key in t:
                        if key not in exclude:
                            if isinstance(gameStats[t[pid]][key], datetime.time):
                                gameStats[t[pid]][key] = helpers.combine_time(gameStats[t[pid]][key], t[key])
                            elif isinstance(gameStats[t[pid]][key], datetime.timedelta):
                                gameStats[t[pid]][key] += datetime.timedelta(minutes=t[key].minute, seconds=t[key].second)
                            else:
                                if gameStats[t[pid]][key] is not None:
                                    gameStats[t[pid]][key] += t[key]
                                else:
                                    gameStats[t[pid]][key] = t[key]
        if bySeason is True:
            gameStats = {}
            for key in seasonStats:
                for pid in seasonStats[key]:
                    gameStats[str(key)+"|"+str(pid)] = seasonStats[key][pid]
        remove = ["game__season", "game__homeTeam", "player__id",
            "team", "player__currentTeam"]
        replace = {"player__fullName": "name",
            "player__primaryPositionCode": "position",
            "player__currentTeam__shortName": "currentTeam",
            "player__birthDate": "birthDate",
            "player__currentTeam__abbreviation": "currentTeamAbbr",
            "player__height": "height", "player__weight": "weight"}
        for t in gameStats:
            games = gameStats[t]["games"]
            pdict = gameStats[t]
            for r in remove:
                pdict.pop(r, None)
            for r in replace:
                pdict[replace[r]] = pdict[r]
                pdict.pop(r, None)
            if len(gameStats[t]["height"]) == 5:
                gameStats[t]["height"] = gameStats[t]["height"][:3] + "0" + gameStats[t]["height"][3:]
            if games != 0:
                gameStats[t]["points"] = gameStats[t]["goals"] + gameStats[t]["assists"]
                gameStats[t]["G60"] = round(gameStats[t]["goals"] / gameStats[t]["timeOnIce"].total_seconds() * 60 * 60, 2)
                gameStats[t]["A60"] = round(gameStats[t]["assists"] / gameStats[t]["timeOnIce"].total_seconds() * 60 * 60, 2)
                gameStats[t]["P60"] = round(gameStats[t]["G60"] + gameStats[t]["A60"], 2)
                m, s = divmod(round(gameStats[t]["timeOnIce"].total_seconds() / games, 2), 60)
                gameStats[t]["TOIGm"] = "%02d:%02d" % (m, s)
                if gameStats[t]["faceoffTaken"] > 0:
                    gameStats[t]["facPercent"] = round((float(gameStats[t]["faceOffWins"]) / float(gameStats[t]["faceoffTaken"])) * 100, 2)
                else:
                    gameStats[t]["facPercent"] = 0
            else:
                gameStats[t]["points"] = 0
                gameStats[t]["G60"] = 0
                gameStats[t]["A60"] = 0
                gameStats[t]["P60"] = 0
                gameStats[t]["TOIGm"] = 0
                gameStats[t]["facPercent"] = 0
        return Response(gameStats.values())
