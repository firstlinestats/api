import os
import sys
import json
import glob
import time
import django

import gzip

from StringIO import StringIO

from urllib2 import Request, urlopen, URLError

from bs4 import BeautifulSoup

import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "api"))
sys.path.append("../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
from django.conf import settings

django.setup()


import team.models as tmodels
import player.models as pmodels
import playbyplay.models as pbpmodels
import playbyplay.helper as pbphelper
from django.db import transaction
from django.db.models import Count
from django.db.utils import IntegrityError

LIVE_BASE = "http://live.nhl.com/GameData/"  # Base URL for the live data reports

BASE = "http://www.nhl.com/scores/htmlreports/"  # Base URL for html reports

headers = {
    "User-Agent" : "Mozilla/5.0 (X11; U; Linux i686; " + \
        "en-US; rv:1.9.2.24) Gecko/20111107 " + \
        "Linux Mint/9 (Isadora) Firefox/3.6.24",
}


def main():
    event_dict = {
        "FACEOFF": "FAC",
        "HIT": "HIT",
        "GIVEAWAY": "GIVE",
        "GOAL": "GOAL",
        "SHOT": "SHOT",
        "MISSED_SHOT": "MISS",
        "PENALTY": "PENL",
        "STOP": "STOP",
        "SUB": "SUB",
        "FIGHT": "PENL",
        "TAKEAWAY": "TAKE",
        "BLOCKED_SHOT": "BLOCK",
        "PERIOD_START": "PSTR",
        "PERIOD_END": "PEND",
        "GAME_END": "GEND",
        "GAME_SCHEDULED": "GAME_SCHEDULED",
        "PERIOD_READY": "PERIOD_START",
        "PERIOD_OFFICIAL": "PERIOD_OFFICIAL",
        "SHOOTOUT_COMPLETE": "SOC",
        "EARLY_INT_START": "EISTR",
        "EARLY_INT_END": "EIEND",
        "GAME_OFFICIAL": "GOFF",
        "CHALLENGE": "CHL",
        "EMERGENCY_GOALTENDER": "EMERGENCY_GOALTENDER"
    }
    startingDateTime = datetime.date(2016, 2, 6)
    tpgs = pbpmodels.PlayerGameStats.objects.values("player_id", "game_id").filter(game__season=20122013)
    pgs = {}
    print "checking pgs"
    for t in tpgs:
        if t["player_id"] not in pgs:
            pgs[t["player_id"]] = set()
        pgs[t["player_id"]].add(t["game_id"])
    missing = {}
    total = 0
    print "finding missing..."

    total = 0
    poi = pbpmodels.PlayerOnIce.objects.values("game_id", "player_id").filter(game__season=20122013)
    pigs = {}
    for p in poi:
        if p["game_id"] not in pigs:
            pigs[p["game_id"]] = set()
        pigs[p["game_id"]].add(p["player_id"])
    for p in pgs:
        for game in pgs[p]:
            if game not in pigs:
                missing[game] = set()
            elif p not in pigs[game]:
                if game not in missing:
                    missing[game] = set()
                missing[game].add(p)
                total += 1
    for game_id in missing:
        print game_id, missing[game_id]
        game = pbpmodels.Game.objects.get(gamePk=game_id)
        playerstats = pbpmodels.PlayerGameStats.objects.values("team_id", "player__fullName", "player_id").filter(game=game)
        hp = {}
        ap = {}
        eventIdxs = {}
        pbps = pbpmodels.PlayByPlay.objects.values("period", "periodTime", "playType", "id").filter(gamePk=game)
        for pbp in pbps:
            periodTime = pbp["periodTime"].strftime("%-H:%M")
            if pbp["period"] not in eventIdxs:
                eventIdxs[pbp["period"]] = {}
            if periodTime not in eventIdxs[pbp["period"]]:
                eventIdxs[pbp["period"]][periodTime] = {}
            if event_dict[pbp["playType"]] not in eventIdxs[pbp["period"]][periodTime]:
                eventIdxs[pbp["period"]][periodTime][event_dict[pbp["playType"]]] = [pbp["id"], ]
            else:
                eventIdxs[pbp["period"]][periodTime][event_dict[pbp["playType"]]].append(pbp["id"])
        for ps in playerstats:
            if ps["team_id"] == game.homeTeam_id:
                hp[ps["player__fullName"].upper()] = ps["player_id"]
            else:
                ap[ps["player__fullName"].upper()] = ps["player_id"]
        goaliestats = pbpmodels.GoalieGameStats.objects.values("team_id", "player__fullName", "player_id").filter(game=game)
        for gs in goaliestats:
            if gs["team_id"] == game.homeTeam_id:
                hp[gs["player__fullName"].upper()] = gs["player_id"]
            else:
                ap[gs["player__fullName"].upper()] = gs["player_id"]
        url = BASE + "20122013" + "/PL0" + str(game.gamePk)[5:] + ".HTM"
        data = get_url(url)
        soup = BeautifulSoup(data, 'html.parser')
        evens = soup.find_all('tr', attrs={'class': 'evenColor'})
        count = 0
        saved = []
        with transaction.atomic():
            pbpmodels.PlayerOnIce.objects.filter(game_id=game_id).delete()
            for row in evens:
                backup_names = {}
                cols = row.find_all('td', recursive=False)
                fonts = row.find_all('font')
                if len(list(cols[3].strings)) >= 1:
                    time = list(cols[3].strings)[0]
                    for ele in fonts:
                        if ele.has_attr("title"):
                            title = ele.attrs["title"].split(" - ")[1]
                            number = ele.text
                            if number in backup_names:
                                backup_names[number + "H"] = title
                            else:
                                backup_names[number] = title
                    fcols = [ele.text.strip().replace("\n", "") for ele in cols]
                    eventIdx = int(fcols[1])
                    playType = fcols[4]
                    if eventIdx in eventIdxs and time in eventIdxs[eventIdx] and playType in eventIdxs[eventIdx][time]:
                        players = fcols[6:]
                        away = players[0]
                        home = players[1]
                        away = [x[0:-1] for x in away.replace(u'\xa0', " ").split(" ")]
                        home = [x[0:-1] for x in home.replace(u'\xa0', " ").split(" ")]
                        awayNames = {}
                        homeNames = {}
                        for f in fonts:
                            if "title" in f:
                                title = f["title"].split(" - ")[-1]
                                number = f.text
                                if number in away and number not in awayNames:
                                    awayNames[number] = title
                                else:
                                    homeNames[number] = title
                        acount = 1
                        players = set()
                        for anum in away:
                            if len(anum) > 0:
                                for play_id in eventIdxs[eventIdx][time][playType]:
                                    pbpdict = {}
                                    pbpdict["play_id"] = play_id
                                    pbpdict["game_id"] = game.gamePk
                                    anum = int(anum)
                                    player = getPlayer(ap, awayNames, anum, backup_names, True) #ap[awayNames[str(anum)]]
                                    if player not in players:
                                        players.add(player)
                                        pbpdict["player_id"] = player
                                        acount += 1
                                        try:
                                            pbpp = pbpmodels.PlayerOnIce(**pbpdict)
                                            #pbpp.save()
                                            saved.append(pbpp)
                                        except TypeError:
                                            pass
                        hcount = 1
                        for hnum in home:
                            if len(hnum) > 0:
                                for play_id in eventIdxs[eventIdx][time][playType]:
                                    pbpdict = {}
                                    pbpdict["play_id"] = play_id
                                    pbpdict["game_id"] = game.gamePk
                                    # fix yo formatting nhl dot com
                                    hnum = int(str(hnum).replace("=\"center\">", "").replace("C", ""))
                                    player = getPlayer(hp, homeNames, hnum, backup_names, False)
                                    if player not in players:
                                        players.add(player)
                                        pbpdict["player_id"] = player
                                        hcount += 1
                                        try:
                                            pbpp = pbpmodels.PlayerOnIce(**pbpdict)
                                            #pbpp.save()
                                            saved.append(pbpp)
                                        except TypeError:
                                            pass
                        # Remove so there are no duplicates, first entry will have the most data
                        eventIdxs[eventIdx][time].pop(playType, None)

            pbpmodels.PlayerOnIce.objects.bulk_create(saved)


def getPlayer(playerDict, number2name, currnum, backup_names, away):
    currnum = str(currnum)
    #if currnum in number2name:
    #    if number2name[currnum] in playerDict:
    #        return playerDict[number2name[currnum]]
    #    sn = number2name[currnum].split(" ").upper()
    #else:
    if away is False:
        if str(currnum) + "H" in backup_names:
            sn = backup_names[str(currnum) + "H"].upper().split(" ")
        else:
            sn = backup_names[str(currnum)].upper().split(" ")
    else:
        sn = backup_names[str(currnum)].upper().split(" ")

    # check for first name?
    for name in playerDict:
        ps = name.upper().split(" ")
        if len(ps) == len(sn):
            fp = ps[0]
            fl = ps[-1]
            sp = sn[0]
            sl = sn[-1]
            if (fp in sp or sp in fp and ps[1] == sn[1]) and fl == sl:
                return playerDict[name]
    # check for player who didn't even play in that game, really NHL???
    try:
        if currnum in number2name:
            player = pmodels.Player.objects.get(fullName__iexact=number2name[currnum])
        else:
            player = pmodels.Player.objects.get(fullName__iexact=" ".join(sn))
        return player.id
    except:
        try:
            player = pmodels.Player.objects.get(lastName__iexact=sn[-1])
            return player.id
        except Exception as e:
            print sn
            print e
    print number2name[currnum], currnum, playerDict
    raise Exception


def get_url(url):
    request = Request(url, headers=headers)
    request.add_header('Accept-encoding', 'gzip')
    try:
        response = urlopen(request)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO( response.read())
            f = gzip.GzipFile(fileobj=buf)
            html = f.read()
        else:
            html = response.read()
    except URLError, e:
        print e
        return "{}"
    return html



if __name__ == "__main__":
    main()
