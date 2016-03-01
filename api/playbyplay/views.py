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
from player.models import CompiledPlayerGameStats, CompiledGoalieGameStats
from playbyplay.constants import gameTypes, gameStates


@permission_classes((IsAuthenticatedOrReadOnly, ))
class GoalieGameStatsViewSet(viewsets.ViewSet):
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
        if "player" in getValues and len(getValues["player"]) > 0:
            player = getValues["player"]
            kwargs['player_id__in'] = player
        if "date_start" in getValues and "date_end" in getValues:
            try:
                date_start = datetime.datetime.strptime(getValues["date_start"][0], "%m/%d/%Y").date()
                date_end =  datetime.datetime.strptime(getValues["date_end"][0], "%m/%d/%Y").date()

                kwargs['game__dateTime__gte'] = date_start
                kwargs['game__dateTime__lte'] = date_end
            except:
                date_start = None
                date_end = None
        if "period" in getValues:
            try:
                kwargs['period'] = int(getValues["period"][0])
            except:
                pass
        if "strength" in getValues:
            try:
                kwargs['strength'] = getValues["strength"][0]
            except Exception as e:
                pass
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
                toi = int(getValues["toi"][0]) * 60
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

        gameData = CompiledGoalieGameStats.objects.\
            values("player_id", "player__fullName", "game__season",
                "player__currentTeam__abbreviation", "game_id",
                "player__height", "player__weight", "player__birthDate", 
                "player__primaryPositionCode", "shotsLow",
                "savesLow", "shotsMedium", "savesMedium", "shotsHigh",
                "savesHigh", "toi").filter(*args, **kwargs)


        if "player" in getValues and len(getValues["player"]) > 0:  
            shotsKwargs = kwargs
            del shotsKwargs['player_id__in']  
            leaugeShots = CompiledGoalieGameStats.objects.\
                values("shotsLow", "savesLow", "shotsMedium", 
                    "savesMedium", "shotsHigh", "savesHigh", "toi").\
                filter(*args, **shotsKwargs)
        else:
            leaugeShots = CompiledGoalieGameStats.objects.\
                values("shotsLow", "savesLow", "shotsMedium", 
                    "savesMedium", "shotsHigh", "savesHigh").\
                filter(*args, **kwargs)


        players = {}
        compiled = []
        playergames = {}

        leaugeShotsLow = 0
        leaugeShotsMedium = 0
        leaugeShotsHigh = 0

        for data in leaugeShots:
            leaugeShotsLow += data['shotsLow']
            leaugeShotsMedium += data['shotsMedium']
            leaugeShotsHigh += data['shotsHigh']

       

        for data in gameData:
            data["leaugeShotsLow"] = leaugeShotsLow
            data["leaugeShotsMedium"] = leaugeShotsMedium
            data["leaugeShotsHigh"] = leaugeShotsHigh

            pname = data["player__fullName"]
            if pname not in players:
                player = setup_goalie(data)
                playergames[pname] = set()
                playergames[pname].add(data["game_id"])
                players[player["name"]] = player
            else:
                add_goalie(players[pname], data, playergames)
        if toi is not None:
            playerstoi = []
            for player in players:
                if players[player]["toi"] / players[player]["games"] >= toi:
                    playerstoi.append(players[player])
            return Response(playerstoi)
        print players
        return Response(players.values())


def add_goalie(existing, newdata, playergames):
    exclude = ["game", "player", "period", "strength",
        "player_id", "game_id", "_state", "toi", "timeOffIce",
        "player__currentTeam__abbreviation", "player__fullName",
        "game__season", "player__height", "player__weight",
        "player__birthDate", "player__primaryPositionCode"]
    for key in newdata:
        if key not in exclude:
            existing[key] += newdata[key]
    existing["toi"] += newdata["toi"].minute * 60 + newdata["toi"].second
    if newdata["game_id"] not in playergames[existing["name"]]:
        existing["games"] += 1
        playergames[existing["name"]].add(newdata["game_id"])


def setup_goalie(data):
    pdict = {"name": data["player__fullName"],
        "season": data["game__season"],
        "team": data["player__currentTeam__abbreviation"]}
    exclude = ["toi", "timeOffIce", "player__fullName",
        "player__currentTeam__abbreviation", "game__season",
        "player__birthDate", "player__primaryPositionCode"]
    for key in data:
        if key not in exclude:
            pdict[key] = data[key]
    pdict["games"] = 1
    if len(pdict["player__height"]) == 5:
        pdict["player__height"] = pdict["player__height"][:3] + "0" + pdict["player__height"][3:]
    pdict["currentTeamAbbr"] = pdict["team"]
    pdict["position"] = getPosition(data["player__primaryPositionCode"])
    pdict["age"] = helpers.calculate_age(data["player__birthDate"])
    pdict["toi"] = data["toi"].minute * 60 + data["toi"].second
    return pdict




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
        if "player" in getValues and len(getValues["player"]) > 0:
            player = getValues["player"]
            kwargs['player_id__in'] = player
        if "date_start" in getValues and "date_end" in getValues:
            try:
                date_start = datetime.datetime.strptime(getValues["date_start"][0], "%m/%d/%Y").date()
                date_end =  datetime.datetime.strptime(getValues["date_end"][0], "%m/%d/%Y").date()

                kwargs['game__dateTime__gte'] = date_start
                kwargs['game__dateTime__lte'] = date_end
            except:
                date_start = None
                date_end = None
        if "period" in getValues:
            try:
                kwargs['period'] = int(getValues["period"][0])
            except:
                pass
        if "strength" in getValues:
            try:
                kwargs['strength'] = getValues["strength"][0]
            except Exception as e:
                pass
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
                toi = int(getValues["toi"][0]) * 60
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

        gameData = CompiledPlayerGameStats.objects.\
            values("player_id", "player__fullName", "gv", "offbsf", "ab",
                "offmsa", "gf", "ga", "game__season",
                "player__currentTeam__abbreviation",
                "offbsa", "fo_l", "hscf", "onbsf", "onsf", "zsn",
                "timeOffIce", "toi", "tk", "msf", "pn", "msa",
                "hit", "assists2", "sca", "sc", "offga",
                "assists", "offgf", "bsf", "bsa", "onmsf",
                "hitt", "hsca", "offmsf", "fo_w", "sf", "zsd",
                "offsf", "offsa", "isc", "ihsc", "sa", "zso",
                "pnDrawn", "goals", "game_id",
                "player__height", "player__weight",
                "player__birthDate", "player__primaryPositionCode"
                ).filter(*args, **kwargs)
        players = {}
        compiled = []
        playergames = {}
        for data in gameData:
            pname = data["player__fullName"]
            if pname not in players:
                player = setup_skater(data)
                playergames[pname] = set()
                playergames[pname].add(data["game_id"])
                players[player["name"]] = player
            else:
                add_player(players[pname], data, playergames)
        if toi is not None:
            playerstoi = []
            for player in players:
                if players[player]["toi"] / players[player]["games"] >= toi:
                    playerstoi.append(players[player])
            return Response(playerstoi)
        return Response(players.values())


def add_player(existing, newdata, playergames):
    exclude = ["game", "player", "period", "strength",
        "player_id", "game_id", "_state", "toi", "timeOffIce",
        "player__currentTeam__abbreviation", "player__fullName",
        "game__season", "player__height", "player__weight",
        "player__birthDate", "player__primaryPositionCode"]
    for key in newdata:
        if key not in exclude:
            existing[key] += newdata[key]
    existing["toi"] += newdata["toi"].minute * 60 + newdata["toi"].second
    existing["timeOffIce"] += newdata["timeOffIce"].minute * 60 + newdata["timeOffIce"].second
    if newdata["game_id"] not in playergames[existing["name"]]:
        existing["games"] += 1
        playergames[existing["name"]].add(newdata["game_id"])



def setup_skater(data):
    pdict = {"name": data["player__fullName"],
        "season": data["game__season"],
        "team": data["player__currentTeam__abbreviation"]}
    exclude = ["toi", "timeOffIce", "player__fullName",
        "player__currentTeam__abbreviation", "game__season",
        "player__birthDate", "player__primaryPositionCode"]
    for key in data:
        if key not in exclude:
            pdict[key] = data[key]
    pdict["games"] = 1
    if len(pdict["player__height"]) == 5:
        pdict["player__height"] = pdict["player__height"][:3] + "0" + pdict["player__height"][3:]
    pdict["currentTeamAbbr"] = pdict["team"]
    pdict["position"] = getPosition(data["player__primaryPositionCode"])
    pdict["age"] = helpers.calculate_age(data["player__birthDate"])
    pdict["toi"] = data["toi"].minute * 60 + data["toi"].second
    pdict["timeOffIce"] = data["timeOffIce"].minute * 60 + data["timeOffIce"].second
    return pdict


# Create your views here.
@permission_classes((IsAuthenticatedOrReadOnly, ))
class GameDataViewSet(viewsets.ViewSet):
    def list(self, request):
        getValues = dict(request.GET)
        gamePk = getValues.get("gamePk", None)
        period = getValues.get("periodOption", None)
        teamStrengths = getValues.get("teamStrengths", None)
        scoreSituation = getValues.get("scoreSituation", None)
        if scoreSituation is not None:
            scoreSituation = scoreSituation[0]
        if teamStrengths is not None:
            teamStrengths = teamStrengths[0]
        args = ()
        if gamePk is not None:
            gamePk = int(gamePk[0])
        else:
            return Response({"details": "Game not found."})
        kwargs = {"gamePk": gamePk}
        if period is not None:
            try:
                kwargs["period"] = int(period[0])
            except:
                pass
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
            pbp = models.PlayByPlay.objects.filter(*args, **kwargs).order_by("period", "periodTime")
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
                .values("player_id", "play_id", "play__homeScore", "play__awayScore").filter(play__in=pbp)
            onice = {}
            home = {}
            away = {}
            for p in poi_data:
                player_id = p["player_id"]
                play_id = p["play_id"]
                homeScore = p["play__homeScore"]
                awayScore = p["play__awayScore"]
                if play_id not in onice:
                    onice[play_id] = set()
                if play_id not in home:
                    home[play_id] = {"count": 0, "goalie": True, "score": homeScore}
                    away[play_id] = {"count": 0, "goalie": True, "score": awayScore}
                if players[player_id]["team"] == homeTeam["teamName"]:
                    if players[player_id]["position"] == "G":
                        home[play_id]["goalie"] = False
                    home[play_id]["count"] += 1
                else:
                    if players[player_id]["position"] == "G":
                        away[play_id]["goalie"] = False
                    away[play_id]["count"] += 1
                onice[play_id].add(player_id)

            pip_data = models.PlayerInPlay.objects.values("play_id",
                "player_id", "player_type", "play__playType", "play__team__teamName").filter(play__in=pbp).order_by("play__period", "play__periodTime")

            found = set()
            previous_play = None
            previous_period = 1
            previous_shot = None
            previous_danger = None
            previous = None
            scs = {}
            count = 0
            hsc = 0
            asc = 0
            for play in pbp:
                add_play = False
                if previous_play is not None and previous_period == play.period:
                    addedTime = self.diff_times_in_seconds(previous_play, play.periodTime)
                    add_play = True
                elif previous_period != play.period:
                    previous_period = play.period
                previous_play = play.periodTime
                play_id = play.id
                homeinclude, awayinclude = self.check_play(home, away, play_id, teamStrengths, scoreSituation, hsc, asc)
                if play.playType == "GOAL":
                    if play.team.teamName == homeTeam["teamName"]:
                        hsc += 1
                    else:
                        asc += 1
                if play.team is not None:
                    team = play.team.teamName
                if play_id in onice:
                    poi = onice[play_id]
                    play_type = play.playType
                    if add_play:
                        if homeinclude:
                            homeTeam["toi"] += addedTime
                        if awayinclude:
                            awayTeam["toi"] += addedTime
                    for pid in poi:
                        if add_play:
                            if (players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                    (players[pid]["team"] == awayTeam["teamName"] and awayinclude):
                                players[pid]["toi"] += addedTime
                    if play_type in ["SHOT", "GOAL", "MISSED_SHOT", "BLOCKED_SHOT"]:
                        danger, sc = self.calculate_scoring_chance(play, previous_shot, previous_danger, previous)
                        previous_shot = play
                        previous_danger = danger
                        scs[play_id] = {"sc": sc, "danger": danger}
                        for pid in poi:
                            player = players[pid]
                            if player["position"] != "G" and ((players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                    (players[pid]["team"] == awayTeam["teamName"] and awayinclude)):
                                if player["team"] == team:
                                    player["scf"] += 1
                                else:
                                    player["sca"] += 1
                        if team == homeTeam["teamName"]:
                            if sc == 1 and homeinclude:
                                homeTeam["scf"] += 1
                            elif sc == 2 and homeinclude:
                                homeTeam["hscf"] += 1
                        else:
                            if sc == 1 and awayinclude:
                                awayTeam["scf"] += 1
                            elif sc == 2 and awayinclude:
                                awayTeam["hscf"] += 1
                        if team == homeTeam["teamName"] and homeinclude:
                            xcoord = play.xcoord
                            ycoord = play.ycoord
                            if xcoord < 0:
                                xcoord = abs(xcoord)
                                ycoord = -ycoord
                            gameData["shotData"]["home"].append({"x": xcoord,
                                "y": ycoord, "type": play_type, "danger": danger,
                                "scoring_chance": sc})
                        elif team == awayTeam["teamName"] and awayinclude:
                            xcoord = play.xcoord
                            ycoord = play.ycoord
                            if xcoord > 0:
                                xcoord = -xcoord
                                ycoord = -ycoord
                            gameData["shotData"]["away"].append({"x": xcoord,
                                "y": ycoord, "type": play_type, "danger": danger,
                                "scoring_chance": sc})
                    if play_type == "SHOT":
                        if team == homeTeam["teamName"] and homeinclude:
                            homeTeam["sf"] += 1
                        elif team == awayTeam["teamName"] and awayinclude:
                            awayTeam["sf"] += 1
                        for pid in poi:
                            include = (players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                (players[pid]["team"] == awayTeam["teamName"] and awayinclude)
                            if players[pid]["position"] != "G" and include:
                                if players[pid]["team"] == team:
                                    players[pid]["sf"] += 1
                                else:
                                    players[pid]["sa"] += 1
                    elif play_type == "GOAL":
                        found.add(play.id)
                        if team == homeTeam["teamName"] and homeinclude:
                            homeTeam["gf"] += 1
                            homeTeam["sf"] += 1
                        elif team == awayTeam["teamName"] and awayinclude:
                            awayTeam["gf"] += 1
                            awayTeam["sf"] += 1
                        for pid in poi:
                            include = (players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                (players[pid]["team"] == awayTeam["teamName"] and awayinclude)
                            if include:
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
                                        if danger == "LOW":
                                            players[pid]["gl"] += 1
                                        elif danger == "MEDIUM":
                                            players[pid]["gm"] += 1
                                        elif danger == "HIGH":
                                            players[pid]["gh"] += 1
                                        else:
                                            players[pid]["gu"] += 1
                    elif play_type == "MISSED_SHOT":
                        if team == homeTeam["teamName"] and homeinclude:
                            homeTeam["msf"] += 1
                        elif team == awayTeam["teamName"] and awayinclude:
                            awayTeam["msf"] += 1
                        for pid in poi:
                            include = (players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                (players[pid]["team"] == awayTeam["teamName"] and awayinclude)
                            if players[pid]["position"] != "G" and include:
                                if players[pid]["team"] == team:
                                    players[pid]["msf"] += 1
                                else:
                                    players[pid]["msa"] += 1
                    elif play_type == "BLOCKED_SHOT":
                        if team == homeTeam["teamName"] and awayinclude:
                            awayTeam["bsf"] += 1
                        elif team == awayTeam["teamName"] and homeinclude:
                            homeTeam["bsf"] += 1
                        for pid in poi:
                            include = (players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                (players[pid]["team"] == awayTeam["teamName"] and awayinclude)
                            if players[pid]["position"] != "G" and include:
                                if players[pid]["team"] == team:
                                    players[pid]["bsf"] += 1
                                else:
                                    players[pid]["bsa"] += 1
                    elif play_type == "FACEOFF":
                        if play.period == 2 or play.period == 4:
                            play.xcoord = -play.xcoord
                        if play.xcoord < -25.00 and awayinclude:
                            awayTeam["zso"] += 1
                            for pid in poi:
                                include = (players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                    (players[pid]["team"] == awayTeam["teamName"] and awayinclude)
                                if players[pid]["position"] != "G" and include:
                                    if players[pid]["team"] == awayTeam["teamName"]:
                                        players[pid]["zso"] += 1
                                    else:
                                        players[pid]["zsd"] += 1
                        elif play.xcoord > 25.00 and homeinclude:
                            homeTeam["zso"] += 1
                            for pid in poi:
                                include = (players[pid]["team"] == homeTeam["teamName"] and homeinclude) or\
                                    (players[pid]["team"] == awayTeam["teamName"] and awayinclude)
                                if players[pid]["position"] != "G" and include:
                                    if players[pid]["team"] == homeTeam["teamName"]:
                                        players[pid]["zso"] += 1
                                    else:
                                        players[pid]["zsd"] += 1
                previous = play

            for pid in players:
                player = players[pid]
                timeOnIceSeconds = player["toi"]
                if player["position"] != "G":
                    player["cf"] = player["sf"] + player["msf"] + player["bsa"]
                    player["ca"] = player["sa"] + player["msa"] + player["bsf"]
                    player["ff"] = player["cf"] - player["bsa"]
                    player["fa"] = player["ca"] - player["bsf"]
                    player["g+-"] = player["gf"] - player["ga"]
                    try:
                        player["sf60"] = round(player["sf"] / timeOnIceSeconds * 3600, 2)
                        player["sa60"] = round(player["sa"] / timeOnIceSeconds * 3600, 2)
                        player["cf60"] = round(player["cf"] / timeOnIceSeconds * 3600, 2)
                        player["ca60"] = round(player["ca"] / timeOnIceSeconds * 3600, 2)
                        player["ff60"] = round(player["ff"] / timeOnIceSeconds * 3600, 2)
                        player["fa60"] = round(player["fa"] / timeOnIceSeconds * 3600, 2)
                    except:
                        zeroes = ["sf60", "sa60", "cf60", "ca60", "ff60", "fa60"]
                        for z in zeroes:
                            player[z] = 0
                player["toi"] = self.seconds_to_hms(timeOnIceSeconds)
            homeTeam["toi"] = self.seconds_to_hms(homeTeam["toi"])
            awayTeam["toi"] = self.seconds_to_hms(awayTeam["toi"])
            homeTeam["cf"] = homeTeam["msf"] + homeTeam["sf"] + homeTeam["bsf"]
            awayTeam["cf"] = awayTeam["msf"] + awayTeam["sf"] + awayTeam["bsf"]

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
            hsc = 0
            asc = 0
            for pip in pip_data:
                play_id = pip["play_id"]
                homeinclude, awayinclude = self.check_play(home, away, play_id, teamStrengths, scoreSituation, hsc, asc)
                if pip["play__playType"] == "GOAL" and pip["player_type"] == 5:
                    if pip["play__team__teamName"] == homeTeam["teamName"]:
                        hsc += 1
                    else:
                        asc += 1
                player = players[pip["player_id"]]
                player_type = pip["player_type"]

                if player_type == 1:
                    if player["team"] == homeTeam["teamName"] and homeinclude:
                        homeTeam["fo_w"] += 1
                    elif player["team"] == awayTeam["teamName"] and awayinclude:
                        awayTeam["fo_w"] += 1
                elif player_type == 3:
                    if player["team"] == homeTeam["teamName"] and homeinclude:
                        homeTeam["hit+"] += 1
                    elif player["team"] == awayTeam["teamName"] and awayinclude:
                        awayTeam["hit+"] += 1
                elif player_type == 10:
                    if player["team"] == homeTeam["teamName"] and homeinclude:
                        homeTeam["pn"] += 1
                    elif player["team"] == awayTeam["teamName"] and awayinclude:
                        awayTeam["pn"] += 1
                if player_type in type_sum:
                    if (player["team"] == homeTeam["teamName"] and homeinclude) or \
                        (player["team"] == awayTeam["teamName"] and awayinclude):
                        if player_type == 5:
                            player["icf"] += 1
                        elif player_type == 7:
                            sc = scs[pip["play_id"]]["sc"]
                            if sc == 1:
                                player["isc"] += 1
                            elif sc == 2:
                                player["ihsc"] += 1
                            if pip["play__playType"] == "BLOCKED_SHOT":
                                player["bk"] += 1
                            elif pip["play__playType"] == "MISSED_SHOT":
                                player["ms"] += 1
                            elif pip["play__playType"] == "SHOT":
                                player["sh"] += 1
                        elif player_type == 8:
                            if scs[pip["play_id"]]["danger"] == "LOW":
                                player["sl"] += 1
                                player["su"] -= 1
                            elif scs[pip["play_id"]]["danger"] == "MEDIUM":
                                player["sm"] += 1
                                player["su"] -= 1
                            elif scs[pip["play_id"]]["danger"] == "HIGH":
                                player["sh"] += 1
                                player["su"] -= 1
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

    def check_play(self, home, away, play_id, teamStrengths, scoreSituation, hsc, asc):
        hb = False
        ab = False
        if play_id in home:
            hp = home[play_id]["count"]
            ap = away[play_id]["count"]
            hg = home[play_id]["goalie"]
            ag = away[play_id]["goalie"]
            if teamStrengths is None or teamStrengths == "all":
                hb, ab = True, True
            elif teamStrengths == "4v4" and hp == 5 and ap == 5:
                hb, ab = True, True
            elif teamStrengths == "even" and hp == ap and hp == 6:
                hb, ab = True, True
            elif teamStrengths == "pp":
                if hp == ap + 1:
                    hb, ab = True, False
                elif hp + 1 == ap:
                    hb, ab = False, True
            elif teamStrengths == "pk":
                if hp == ap + 1:
                    hb, ab = False, True
                elif hp + 1 == ap:
                    hb, ab = True, False
            elif teamStrengths == "3v3" and hp == 4 and ap == 4:
                hb, ab = True, True
            elif teamStrengths == "og":
                if hg is True and ag is False:
                    hb, ab = False, True
                elif hg is False and ag is True:
                    hb, ab = True, False
                elif hg is True and ag is True:
                    hb, ab = True, True
            elif teamStrengths == "tg":
                if hg is True and ag is False:
                    hb, ab = True, False
                elif hg is False and ag is True:
                    hb, ab = False, True
                elif hg is True and ag is True:
                    hb, ab = True, True
            if scoreSituation is not None and scoreSituation != "all":
                # Only account for removing the play!
                if scoreSituation == "t3+":
                    if hsc <= asc + 3:
                        hb = False
                    if asc <= hsc + 3:
                        ab = False
                elif scoreSituation == "t2":
                    if hsc != asc - 2:
                        hb = False
                    if asc != hsc - 2:
                        ab = False
                elif scoreSituation == "t1":
                    if hsc != asc - 1:
                        hb = False
                    if asc != hsc - 1:
                        ab = False
                elif scoreSituation == "t":
                    if hsc != asc:
                        hb, ab = False, False
                elif scoreSituation == "l3+":
                    if hsc < asc + 3:
                        hb = False
                    if asc < hsc + 3:
                        ab = False
                elif scoreSituation == "l2":
                    if hsc != asc + 2:
                        hb = False
                    if asc != hsc + 2:
                        ab = False
                elif scoreSituation == "l1":
                    if hsc != asc + 1:
                        hb = False
                    if asc != hsc + 1:
                        ab = False
                elif scoreSituation == "w1":
                    if hsc > asc + 1 or hsc < asc - 1:
                        hb, ab = False, False
        return hb, ab

    def calculate_rebound(self, shot, pshot):
        if pshot is not None and shot.period == pshot.period:
            if shot.team == pshot.team and pshot.shotType != "GOAL":
                diff = self.diff_times_in_seconds(shot.periodTime,
                    pshot.periodTime)
                if diff >= -3:
                    return True
        return False

    def calculate_rush(self, shot, pplay):
        if pplay is not None and shot.period == pplay.period:
            diff = self.diff_times_in_seconds(shot.periodTime,
                pplay.periodTime)
            sx = shot.xcoord
            px = pplay.xcoord
            if sx > 0:
                if px > 0:
                    return True
            else:
                if px < 0:
                    return True
        return False

    def calculate_scoring_chance(self, shot, pshot, pdanger, pplay):
        rebound = self.calculate_rebound(shot, pshot)
        rush = self.calculate_rush(shot, pplay)
        # if rebound, scoring_chance
        zone = self.calculate_danger_zone(shot, pshot, pdanger)
        # "prevcurrtime" "cblockreb2", "cmissreb2", "shotreb2", "cblockreb3",
        # "cmissreb3", "shotreb3", "rushn4", "rusho4"
        if rebound:
            return zone, 2
        elif rush and self.diff_times_in_seconds(shot.periodTime,
                pplay.periodTime) >= -4:
            return zone, 2
        if zone == "LOW":
            if rebound and shot.playType != "BLOCKED_SHOT":
                return zone, 1
            elif rush is True:
                return zone, 1
        elif zone == "MEDIUM":
            if shot.playType != "BLOCKED_SHOT":
                return zone, 1
        else:
            return zone, 1
        return zone, 0

    def calculate_danger_zone(self, shot, pshot, pdanger):
        # TODO: Normalize
        xcoord = shot.xcoord
        ycoord = shot.ycoord
        # Calculate Location
        poly =  [(89, -9),
        (69, -22), (54, -22),
        (54, -9), (44, -9),
        (44, 9), (54, 9),
        (54, 22), (69, 22),
        (89, 9), (89, -9)]
        highpoly = [(89, -9),
        (69, -9), (69, 9),
        (89, 9), (89, -9)]
        if self.point_inside_polygon(xcoord, ycoord, highpoly) is True:
            return "HIGH"
        elif self.point_inside_polygon(xcoord, ycoord, poly) is True:
            return "MEDIUM"
        return "LOW"

    def point_inside_polygon(self, x, y, poly):
        # check if point is a vertex
        x = float(x)
        y = float(y)
        if x < 0:
            x = abs(x)
            y = -y
        if (x,y) in poly: return True

        # check if point is on a boundary
        for i in range(len(poly)):
            p1 = None
            p2 = None
            if i==0:
                p1 = poly[0]
                p2 = poly[1]
            else:
                p1 = poly[i-1]
                p2 = poly[i]
            if p1[1] == p2[1] and p1[1] == y and x > min(p1[0], p2[0]) and x < max(p1[0], p2[0]):
                return True
          
        n = len(poly)
        inside = False

        p1x,p1y = poly[0]
        for i in range(n+1):
            p2x,p2y = poly[i % n]
            if y > min(p1y,p2y):
                if y <= max(p1y,p2y):
                    if x <= max(p1x,p2x):
                        if p1y != p2y:
                            xints = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                        if p1x == p2x or x <= xints:
                            inside = not inside
            p1x,p1y = p2x,p2y

        if inside:
            return True
        else:
            return False

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
        if "game_state" in getValues and len(getValues["game_state"]) > 0:
            states = getValues["game_state"]
            kwargs['gameState__in'] = states
        if "teams" in getValues and len(getValues["teams"]) > 0:
            teams = getValues["teams"]
            args = ( Q(awayTeam__in = getValues['teams']) | Q(homeTeam__in = getValues['teams']), )
        seasons = currentSeason
        if "seasons" in getValues and len(getValues["seasons"]) > 0:
            seasons = getValues["seasons"]
            kwargs['season__in'] = seasons
        venues = None
        if "venues" in getValues and len(getValues["venues"]) > 0:
            venues = getValues["venues"]
            kwargs['game__venue__name__in'] = venues
        game_types = gameTypes
        if "game_type" in getValues and len(getValues["game_type"]) > 0:
            game_types = getValues["game_type"]
            kwargs['gameType__in'] = game_types
        if "date_start" in getValues and "date_end" in getValues:
            try:
                date_start = datetime.datetime.strptime(getValues["date_start"][0], "%m/%d/%Y").date()
                date_end =  datetime.datetime.strptime(getValues["date_end"][0], "%m/%d/%Y").date()
                kwargs['dateTime__gte'] = date_start
                kwargs['dateTime__lte'] = date_end
            except:
                date_start = None
                date_end = None
        games = models.Game.objects\
            .values('gamePk', 'dateTime', 'gameType', 'gameState', 'awayTeam', 'homeTeam', 'awayTeam__abbreviation', 
                'homeTeam__abbreviation', 'homeTeam__id', 
                'awayTeam__id', 'homeTeam__shortName', 'awayTeam__shortName', 'homeScore', 'awayScore', 'awayShots', 
                'homeShots', 'awayBlocked', 'homeBlocked', 'awayMissed',
                'homeMissed', 'gameState', 'endDateTime')\
            .filter(*args, **kwargs).order_by('-gamePk')
        gameList = []
        for game in games:
            g = {}
            for item in gameTypes:
                if item[0] == game['gameType']:
                    g['gameType'] = item[1]
            g['homeTeam'] = {"id" : game['homeTeam__id'], "name" :  game['homeTeam__shortName'], "abbreviation" : game['homeTeam__abbreviation']}
            g['awayTeam'] = {"id" : game['awayTeam__id'], "name" : game['awayTeam__shortName'], "abbreviation" : game['awayTeam__abbreviation']}
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

