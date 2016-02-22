from __future__ import division

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
from playbyplay.constants import gameTypes, gameStates


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
            "homeSkaters": [], "awaySkaters": [], "shotData": {"home": [], "away": []}}


        game = models.Game.objects.get(gamePk=gamePk)
        details = {}
        details["homeTeamName"] = game.homeTeam.teamName
        details["awayTeamName"] = game.awayTeam.teamName
        details["homeTeamAbbr"] = game.homeTeam.abbreviation
        details["awayTeamAbbr"] = game.awayTeam.abbreviation
        details["homeScore"] = game.homeScore
        details["awayScore"] = game.awayScore
        details["venue"] = str(game.venue)
        details["date"] = game.dateTime.astimezone(pytz.timezone('US/Eastern')).strftime("%B %d, %Y %I:%M %p EST")
        gameData["details"] = details

        if game.gameState in ['3', '4', '5', '6', '7']:
            pbp = models.PlayByPlay.objects.filter(gamePk=gamePk).order_by("period", "periodTime")
            playerStats = models.PlayerGameStats.objects.filter(game=gamePk).order_by('team', 'player__lastName')
            goalieStats = models.GoalieGameStats.objects.filter(game=gamePk)

            homeTeam = helper.init_team()
            homeTeam["teamName"] = game.homeTeam.teamName
            homeTeam["teamAbbr"] = game.homeTeam.abbreviation
            awayTeam = helper.init_team()
            awayTeam["teamName"] = game.awayTeam.teamName
            awayTeam["teamAbbr"] = game.awayTeam.abbreviation

            players = {}
            for playerdata in playerStats:
                player = helper.init_player()
                player["name"] = playerdata.player.fullName
                player["position"] = playerdata.player.primaryPositionCode
                player["team"] = playerdata.team.teamName
                #player["toi"] = playerdata.timeOnIce
                #player["pptoi"] = playerdata.powerPlayTimeOnIce
                #player["shtoi"] = playerdata.shortHandedTimeOnIce
                player["toi"] = 0
                players[playerdata.player_id] = player
            for goaliedata in goalieStats:
                player = helper.init_goalie()
                player["name"] = goaliedata.player.fullName
                player["position"] = goaliedata.player.primaryPositionCode
                player["team"] = goaliedata.team.teamName
                #player["toi"] = playerdata.timeOnIce
                #player["pptoi"] = playerdata.powerPlayTimeOnIce
                #player["shtoi"] = playerdata.shortHandedTimeOnIce
                player["toi"] = 0
                player["teamAbbr"] = goaliedata.team.abbreviation
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
                "player_id", "player_type", "play__playType").filter(play__in=pbp)

            found = set()
            previous_play = None
            previous_period = 1
            previous_shot = None
            previous_danger = None
            for play in pbp:
                add_play = False
                if previous_play is not None and previous_period == play.period:
                    addedTime = self.diff_times_in_seconds(previous_play, play.periodTime)
                    add_play = True
                elif previous_period != play.period:
                    previous_period = play.period
                previous_play = play.periodTime
                play_id = play.id
                if play.team is not None:
                    team = play.team.teamName
                if play_id in onice:
                    poi = onice[play_id]
                    play_type = play.playType
                    for pid in poi:
                        if add_play:
                            players[pid]["toi"] += addedTime
                    if play_type in ["SHOT", "GOAL", "MISSED_SHOT", "BLOCKED_SHOT"]:
                        danger = self.calculate_danger(play, previous_shot, previous_danger)
                        previous_shot = play
                        previous_danger = danger
                        if team == homeTeam["teamName"]:
                            xcoord = abs(play.xcoord)
                            ycoord = play.ycoord
                            gameData["shotData"]["home"].append({"x": xcoord,
                                "y": ycoord, "type": play_type})
                    if play_type == "SHOT":
                        if team == homeTeam["teamName"]:
                            homeTeam["sf"] += 1
                        else:
                            awayTeam["sf"] += 1
                        for pid in poi:
                            if players[pid]["position"] != "G":
                                if players[pid]["team"] == team:
                                    players[pid]["sf"] += 1
                                else:
                                    players[pid]["sa"] += 1
                    elif play_type == "GOAL":
                        found.add(play.id)
                        if team == homeTeam["teamName"]:
                            homeTeam["gf"] += 1
                            homeTeam["sf"] += 1
                        else:
                            awayTeam["gf"] += 1
                            awayTeam["sf"] += 1
                        for pid in poi:
                            if players[pid]["position"] != "G":
                                if players[pid]["team"] == team:
                                    players[pid]["gf"] += 1
                                    players[pid]["sf"] += 1
                                else:
                                    players[pid]["ga"] += 1
                                    players[pid]["sa"] += 1
                            else:
                                if players[pid]["team"] != team:
                                    # calculate goal danger
                                    players[pid]["gu"] += 1
                    elif play_type == "MISSED_SHOT":
                        if team == homeTeam["teamName"]:
                            homeTeam["msf"] += 1
                        else:
                            awayTeam["msf"] += 1
                        for pid in poi:
                            if players[pid]["position"] != "G":
                                if players[pid]["team"] == team:
                                    players[pid]["msf"] += 1
                                else:
                                    players[pid]["msa"] += 1
                    elif play_type == "BLOCKED_SHOT":
                        if team == homeTeam["teamName"]:
                            awayTeam["bsf"] += 1
                        else:
                            homeTeam["bsf"] += 1
                        for pid in poi:
                            if players[pid]["position"] != "G":
                                if players[pid]["team"] == team:
                                    players[pid]["bsf"] += 1
                                else:
                                    players[pid]["bsa"] += 1
                    elif play_type == "FACEOFF":
                        if play.period == 2 or play.period == 4:
                            play.xcoord = -play.xcoord
                        if play.xcoord < -25.00:
                            awayTeam["zso"] += 1
                            for pid in poi:
                                if players[pid]["position"] != "G":
                                    if players[pid]["team"] == awayTeam["teamName"]:
                                        players[pid]["zso"] += 1
                                    else:
                                        players[pid]["zsd"] += 1
                        elif play.xcoord > 25.00:
                            homeTeam["zso"] += 1
                            for pid in poi:
                                if players[pid]["position"] != "G":
                                    if players[pid]["team"] == homeTeam["teamName"]:
                                        players[pid]["zso"] += 1
                                    else:
                                        players[pid]["zsd"] += 1

            for pid in players:
                player = players[pid]
                timeOnIceSeconds = player["toi"]
                if player["position"] != "G":
                    player["cf"] = player["sf"] + player["msf"] + player["bsa"]
                    player["ca"] = player["sa"] + player["msa"] + player["bsf"]
                    player["ff"] = player["cf"] - player["bsa"]
                    player["fa"] = player["ca"] - player["bsf"]
                    player["g+-"] = player["gf"] - player["ga"]
                    player["sf60"] = round(player["sf"] / timeOnIceSeconds * 3600, 2)
                    player["sa60"] = round(player["sa"] / timeOnIceSeconds * 3600, 2)
                    player["cf60"] = round(player["cf"] / timeOnIceSeconds * 3600, 2)
                    player["ca60"] = round(player["ca"] / timeOnIceSeconds * 3600, 2)
                    player["ff60"] = round(player["ff"] / timeOnIceSeconds * 3600, 2)
                    player["fa60"] = round(player["fa"] / timeOnIceSeconds * 3600, 2)
                player["toi"] = self.seconds_to_hms(timeOnIceSeconds)

            homeTeam["cf"] = homeTeam["msf"] + homeTeam["sf"] + homeTeam["gf"] + homeTeam["bsf"]
            awayTeam["cf"] = awayTeam["msf"] + awayTeam["sf"] + awayTeam["gf"] + awayTeam["bsf"]

            # Get individual actions
            type_sum = {
                1: "fo_w",
                2: "fo_l",
                3: "hit+",
                4: "hit-",
                5: "g",
                6: "a1",
                7: "icf",
                8: "su",
                9: "ab",
                10: "pn+",
                11: "pn-",
                16: "a2"
            }
            for pip in pip_data:
                player = players[pip["player_id"]]
                player_type = pip["player_type"]
                if player_type == 1:
                    if player["team"] == homeTeam["teamName"]:
                        homeTeam["fo_w"] += 1
                    else:
                        awayTeam["fo_w"] += 1
                elif player_type == 3:
                    if player["team"] == homeTeam["teamName"]:
                        homeTeam["hit+"] += 1
                    else:
                        awayTeam["hit+"] += 1
                elif player_type == 10:
                    if player["team"] == homeTeam["teamName"]:
                        homeTeam["pn"] += 1
                    else:
                        awayTeam["pn"] += 1
                if player_type in type_sum:
                    if player_type == 5:
                        player["icf"] += 1
                    elif player_type == 7:
                        if pip["play__playType"] == "BLOCKED_SHOT":
                            player["bk"] += 1
                        elif pip["play__playType"] == "MISSED_SHOT":
                            player["ms"] += 1
                        elif pip["play__playType"] == "SHOT":
                            player["sh"] += 1
                    player[type_sum[player_type]] += 1

            for playerid in players:
                player = players[playerid]
                player["id"] = playerid
                if player["position"] != "G":
                    if player["team"] == homeTeam["teamName"]:
                        gameData["homeSkaters"].append(player)
                    else:
                        gameData["awaySkaters"].append(player)
                else:
                    gameData["goalies"].append(player)

            gameData["teamData"].append(homeTeam)
            gameData["teamData"].append(awayTeam)


        return Response(gameData)

    def calculate_danger(self, shot, pshot, pdanger):
        #print shot.xcoord, shot.ycoord, shot.period, shot.periodTime
        # TODO: Normalize
        xcoord = shot.xcoord
        ycoord = shot.ycoord
        # Calculate Location

        # Depending on location, determine chance
        #if abs(xcoord) <= 20 and abs(ycoord) >=
        return "LOW"

    def seconds_to_hms(self, seconds):
        m, s = divmod(seconds, 60)
        return "%02d:%02d" % (m, s)

    def hms_to_seconds(self, t):
        if t is not None:
            h, m, s = [int(i) for i in str(t).split(':')]
            return 3600*h + 60*m + s
        return None

    def diff_times_in_seconds(self, t1, t2):
        # assumes t1 & t2 are python times, on the same day and t2 is after t1
        m1, s1, _ = t1.hour, t1.minute, t1.second
        m2, s2, _ = t2.hour, t2.minute, t2.second
        t1_secs = s1 + 60 * m1
        t2_secs = s2 + 60 * m2
        return( t2_secs - t1_secs)


class RecentGameViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Game.objects.filter(dateTime__date__lte=datetime.date.today()).order_by('-dateTime', '-gamePk')[:30]
    serializer_class = serializers.RecentGameSerializer

@permission_classes((IsAuthenticatedOrReadOnly, ))
class GameListViewSet(viewsets.ViewSet):
    def list(self, request):
        currentSeason = models.Game.objects.latest("endDateTime").season
        getValues = dict(request.GET)
        for key in getValues:
            val = getValues[key]
            if len(val) == 0:
                getValues.pop(key, None)
        kwargs = {
            'gameState__in' : [6,7,8],
            'season' : currentSeason
        }
        args = ()
        teams = None
        if "teams" in getValues and len(getValues["teams"]) > 0:
            teams = getValues["teams"]
            args = ( Q(awayTeam__in = getValues['teams']) | Q(homeTeam__in = getValues['teams']), )
        seasons = currentSeason
        if "seasons" in getValues and len(getValues["seasons"]) > 0:
            seasons = getValues["seasons"]
            kwargs['season__in'] = seasons
        venues = None
        if 'venues' in getValues:
            if getValues['venues'][0]:
                kwargs['venue__name'] = getValues['venues'][0]
        game_types = gameTypes
        if "game_type" in getValues and len(getValues["game_type"]) > 0:
            game_types = getValues["game_type"]
            kwargs['gameType__in'] = game_types
        if "date_start" in getValues and "date_end" in getValues:
            try:
                date_start = datetime.datetime.strptime(getValues["date_start"][0], "%m/%d/%Y").date()
                date_end =  datetime.datetime.strptime(getValues["date_end"][0], "%m/%d/%Y").date()
                print date_start
                print date_end
                kwargs['dateTime__gte'] = date_start
                kwargs['dateTime__lte'] = date_end
            except:
                date_start = None
                date_end = None
        games = models.Game.objects\
            .values('gamePk', 'dateTime', 'gameType', 'gameState', 'awayTeam', 'homeTeam', 'awayTeam__abbreviation', 
                'homeTeam__abbreviation', 'homeTeam__id', 
                'awayTeam__id', 'homeTeam__teamName', 'awayTeam__teamName', 'homeScore', 'awayScore', 'awayShots', 
                'homeShots', 'awayBlocked', 'homeBlocked', 'awayMissed',
                'homeMissed', 'gameState', 'endDateTime')\
            .filter(*args, **kwargs).order_by('-gamePk')
        gameList = []
        for game in games:
            g = {}

            for item in gameTypes:
                if item[0] == game['gameType']:
                    g['gameType'] = item[1]
            g['homeTeam'] = {"id" : game['homeTeam__id'], "name" :  game['homeTeam__teamName'], "abbreviation" : game['homeTeam__abbreviation']}
            g['awayTeam'] = {"id" : game['awayTeam__id'], "name" : game['awayTeam__teamName'], "abbreviation" : game['awayTeam__abbreviation']}
            g['score'] = str(game['homeScore']) + "-" + str(game['awayScore'])
            for item in gameStates:
                if item[0] == game['gameState']:
                    g['gameState'] = item[1]
            g['dateTime'] = game['dateTime'].astimezone(pytz.timezone('US/Eastern')).strftime("%I:%M %p EST")
            g['endDateTime'] = ''
            if game['endDateTime'] is not None:
                g['endDateTime'] = game['endDateTime'].astimezone(pytz.timezone('US/Eastern')).strftime("%I:%M %p EST")
            g['date'] = game['dateTime'].date()
            g['gamePk'] = game['gamePk']
            hShots = game['homeShots'] or 0
            hScore = game['homeScore'] or 0
            hMissed = game['homeMissed'] or 0
            aBlocked = game['awayBlocked'] or 0
            homeCorsi = hShots +hScore + hMissed + aBlocked
            aShots = game['awayShots'] or 0
            aScore = game['awayScore'] or 0
            aMissed = game['awayMissed'] or 0
            hBlocked = game['homeBlocked'] or 0
            awayCorsi = aShots + aScore + aMissed + hBlocked
            g['corsi'] = str(homeCorsi) + "/" + str(awayCorsi)
            gameList.append(g)          
        return Response(gameList)

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
