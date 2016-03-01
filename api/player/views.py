from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from playbyplay import models
from playbyplay.constants import gameTypes, gameStates

from helper import getPosition, setup_skater, add_player, get_client_ip
from models import CompiledPlayerGameStats, Player


# Create your views here.
@permission_classes((IsAuthenticatedOrReadOnly, ))
class PlayerGameStatsViewSet(viewsets.ViewSet):
    def list(self, request):
        ip = get_client_ip(request)
        print ip
        currentSeason = models.Game.objects.values_list("season").latest("endDateTime")[0]
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
