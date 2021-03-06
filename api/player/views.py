from django.db.models import Q
from django.shortcuts import render
from django.db.models import Count

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from playbyplay import models
from playbyplay.constants import gameTypes, gameStates

from helper import getPosition, setup_skater, add_player, get_client_ip, setup_goalie, add_goalie
from models import CompiledPlayerGameStats, CompiledGoalieGameStats, Player

import datetime


# Create your views here.
@permission_classes((IsAuthenticatedOrReadOnly, ))
class PlayerGameStatsViewSet(viewsets.ViewSet):
    def list(self, request):
        ip = get_client_ip(request)
        currentSeason = models.Game.objects.values_list("season").latest("endDateTime")[0]
        getValues = dict(request.GET)
        for key in getValues:
            val = getValues[key]
            if len(val) == 0:
                getValues.pop(key, None)
        args = ()
        kwargs = {
            'game__gameState__in': [5, 6, 7,],
            'game__season__in': [currentSeason, ]
        }
        if "player" in getValues and len(getValues["player"]) > 0:
            player = getValues["player"]
            kwargs['player_id__in'] = player
            playerKwargs['player_id__in'] = player
        if "date_start" in getValues and "date_end" in getValues:
            try:
                date_start = datetime.datetime.strptime(getValues["date_start"][0], "%m/%d/%Y").date()
                date_end =  datetime.datetime.strptime(getValues["date_end"][0], "%m/%d/%Y").date()
                print date_start, date_end
                kwargs['game__dateTime__gte'] = date_start - datetime.timedelta(hours=12)
                kwargs['game__dateTime__lte'] = date_end + datetime.timedelta(hours=24)
            except Exception as e:
                print e
                date_start = None
                date_end = None
        if "period" in getValues:
            try:
                kwargs['period'] = int(getValues["period"][0])
            except:
                kwargs['period__lte'] = 4
        else:
            kwargs['period__lte'] = 4
        args = Q(strength = "all")
        if "strength" in getValues:
            try:
                args = Q(strength=getValues["strength"][0])
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
            args = args & (Q(game__awayTeam__in = getValues['teams']) | Q(game__homeTeam__in = getValues['teams']))
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
            kwargs.pop("game__season", None)
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

        games = models.Game.objects.values("gamePk", "season").all()
        gameDict = {}
        for game in games:
            gameDict[game["gamePk"]] = game["season"]

        # Get players
        playersdata = Player.objects.values("currentTeam__abbreviation",
            "id", "fullName", "height", "weight", "birthDate", "primaryPositionCode")\
            .exclude(primaryPositionCode="G")
        players = {}

        # Get stats
        for player in playersdata:
            player = setup_skater(player)
            players[player["id"]] = player
        gameData = CompiledPlayerGameStats.objects.\
            values("player_id", "game_id", "goals", "assists", "assists2",
                   "gf", "ga", "pnDrawn", "pn", "sf", "msf", "bsf",
                   "ab", "onsf", "onmsf", "onbsf", "offgf", "offsf",
                   "offmsf", "offbsf", "offga", "offsa", "offmsa",
                   "offbsa", "sa", "msa", "bsa", "zso", "zsn", "zsd",
                   "toi", "timeOffIce", "ihsc", "isc", "sc", "hscf", "period",
                   "hsca", "sca", "fo_w", "fo_l", "hit", "hitt", "gv", "tk"
                ).filter(*(args, ), **kwargs).prefetch_related("game__season").iterator()

        compiled = []
        playergames = {}
        for data in gameData:
            pid = data["player_id"]
            if pid not in playergames:
                playergames[pid] = set()
            add_player(players[pid], data, playergames, gameDict)
        if toi is not None:
            playerstoi = []
            for player in players:
                if players[player]["toi"] / players[player]["games"] >= toi:
                    playerstoi.append(players[player])
            return Response(playerstoi)
        finalplayers = []
        for player in players:
            pdata = players[player]
            if pdata["games"] > 0:
                finalplayers.append(pdata)
        return Response(finalplayers)


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
        kwargs['period__in'] = [1,2,3,4] 
        if "period" in getValues:
            try:
                kwargs['period'] = int(getValues["period"][0])
            except:
                pass
        args = (Q(strength = "all"), )
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
            leagueShots = CompiledGoalieGameStats.objects.\
                values("shotsLow", "shotsMedium", "shotsHigh").\
                filter(*args, **shotsKwargs)
        else:
            leagueShots = CompiledGoalieGameStats.objects.\
                values("shotsLow", "shotsMedium", "shotsHigh").filter(*args, **kwargs)
                
        players = {}
        compiled = []
        playergames = {}

        leagueShotsLow = 0
        leagueShotsMedium = 0
        leagueShotsHigh = 0

        for data in leagueShots:
            leagueShotsLow += data['shotsLow']
            leagueShotsMedium += data['shotsMedium']
            leagueShotsHigh += data['shotsHigh']
       

        for data in gameData:
            data["leagueShotsLow"] = leagueShotsLow
            data["leagueShotsMedium"] = leagueShotsMedium
            data["leagueShotsHigh"] = leagueShotsHigh

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
        
        return Response(players.values())




