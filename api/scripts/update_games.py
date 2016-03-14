import os
import sys
import pytz
import json
import glob
import time
import django
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
import gzip

from StringIO import StringIO

from urllib2 import Request, urlopen, URLError

from compile_stats import compile_game

headers = {
    "User-Agent" : "Mozilla/5.0 (X11; U; Linux i686; " + \
        "en-US; rv:1.9.2.24) Gecko/20111107 " + \
        "Linux Mint/9 (Isadora) Firefox/3.6.24",
}

BASE = "http://www.nhl.com/scores/htmlreports/"  # Base URL for html reports
BASE_URL = "http://statsapi.web.nhl.com/api/"

TEAM_LIST = BASE_URL + "v1/teams/"

ROSTER_LIST = TEAM_LIST + "<teamId>/roster"

PLAYER_INFO = BASE_URL + "v1/people/"

SCHEDULE_INFO = BASE_URL + "v1/schedule/"

GAME_TIMESTAMPS = BASE_URL + "v1/game/<gamePk>/feed/live/timestamps/"

GAME_TIMESTAMP = BASE_URL + "v1/game/<gamePk>/feed/live/?timecode=<timeStamp>&fields=liveData,boxscore,teams,plays,currentPlay,about"
GAME_DIFF = BASE_URL + "v1/game/<gamePk>/feed/live/diffPatch?startTimecode=<startTime>&endTimecode=<endTime>"

GAME = BASE_URL + "v1/game/<gamePk>/feed/live/"

STANDINGS = BASE_URL + "v1/standings"

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


def get_game(id=None):
    url = GAME.replace("<gamePk>", str(id))
    return get_url(url)


def get_player(id=None, ids=None):
    if id is not None:
        url = PLAYER_INFO + str(id)
    elif ids is not None:
        url = PLAYER_INFO + "?personIds=" + ",".join(str(x) for x in ids)
    return get_url(url)


def getPlayer(playerDict, number2name, currnum, backup_names, away):
    currnum = str(currnum)
    if currnum in number2name:
        if number2name[currnum] in playerDict:
            return playerDict[number2name[currnum]]
        sn = number2name[currnum].split(" ").upper()
    else:
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
            sp = sn[0]
            if fp in sp or sp in fp and ps[1] == sn[1]:
                return playerDict[name]
    # check for last name? seriously NHL?
    for name in playerDict:
        ps = name.upper().split(" ")
        if len(ps) == len(sn):
            fp = ps[-1]
            sp = sn[-1]
            if fp == sp:
                return playerDict[name]
    # check for player who didn't even play in that game, really NHL???
    try:
        if currnum in number2name:
            player = pmodels.Player.objects.get(fullName__iexact=number2name[currnum])
        else:
            player = pmodels.Player.objects.get(fullName__iexact=" ".join(sn))
        return player.id
    except Exception as e:
        print e
    print number2name[currnum], currnum, playerDict
    raise Exception


def checkGoalies(players, gamePk, team, period):
    goalies = []
    for player in players:
        playerstats = players[player]["stats"]
        if "goalieStats" in playerstats:
            gs = playerstats["goalieStats"]
            goalie = pbpmodels.GoalieGameStats()
            try:
                goalie.player = pmodels.Player.objects.get(id=player.replace("ID", ""))
            except:
                gplayer = ingest_player(json.loads(api_calls.get_player(player.replace("ID", "")))["people"][0])
                goalie.player = gplayer
            goalie.game_id = gamePk
            goalie.team_id = team
            goalie.period = period
            if gs["timeOnIce"] < "60:00" or len(gs["timeOnIce"]) < 5:
                goalie.timeOnIce = "00:" + gs["timeOnIce"]
            elif len(gs["timeOnIce"]) >= 8:
                goalie.timeOnIce = gs["timeOnIce"]
            else:
                minutes = str(int(gs["timeOnIce"][:2]) - 60)
                if len(minutes) == 1:
                    minutes = "0" + minutes
                goalie.timeOnIce = "01:" + minutes + gs["timeOnIce"][2:]
            goalie.assists = gs["assists"]
            goalie.goals = gs["goals"]
            goalie.pim = gs["pim"]
            goalie.shots = gs["shots"]
            goalie.saves = gs["saves"]
            goalie.powerPlaySaves = gs["powerPlaySaves"]
            goalie.shortHandedSaves = gs["shortHandedSaves"]
            goalie.shortHandedShotsAgainst = gs["shortHandedShotsAgainst"]
            goalie.evenShotsAgainst = gs["evenShotsAgainst"]
            goalie.evenSaves = gs["evenSaves"]
            goalie.powerPlayShotsAgainst = gs["powerPlayShotsAgainst"]
            goalie.decision = gs["decision"]
            goalie.save()
            goalies.append(goalie)
    return goalies


def ingest_player(jinfo, team=None):
    try:
        player = pmodels.Player()
        player.id = jinfo["id"]
        player.fullName = jinfo["fullName"]
        player.link = jinfo["link"]
        player.firstName = jinfo["firstName"]
        player.lastName = jinfo["lastName"]
        if "primaryNumber" in jinfo:
            player.primaryNumber = jinfo["primaryNumber"]
        player.primaryPositionCode = jinfo["primaryPosition"]["code"]
        player.birthDate = jinfo["birthDate"]
        player.birthCity = jinfo["birthCity"]
        player.birthCountry = jinfo["birthCountry"]
        player.height = jinfo["height"]
        player.weight = jinfo["weight"]
        player.active = jinfo["active"]
        player.rookie = jinfo["rookie"]
        if "shootsCatches" in jinfo:
            player.shootsCatches = jinfo["shootsCatches"]
        if team is not None:
            player.currentTeam_id = team
        else:
            player.currentTeam = tmodels.Team.objects.get(id=jinfo["currentTeam"]["id"])
        player.rosterStatus = jinfo["rosterStatus"]
        player.save()
        return player
    except Exception as e:
        print e
        print jinfo
        

def set_player_stats(pd, team, game, players, period):
    pgss = []
    for sid in pd: # I swear that's not a Crosby reference
        iid = int(sid.replace("ID", ""))
        if "skaterStats" in pd[sid]["stats"]:
            jp = pd[sid]["stats"]["skaterStats"]
            if iid not in players:
                player = ingest_player(json.loads(get_player(sid.replace("ID", "")))["people"][0])
                players[player.id] = player
            else:
                player = players[iid]
            pgs = pbpmodels.PlayerGameStats()
            pgs.player = player
            pgs.game = game
            pgs.timeOnIce = "00:" + jp["timeOnIce"]
            pgs.assists = jp["assists"]
            pgs.goals = jp["goals"]
            pgs.shots = jp["shots"]
            pgs.hits = jp["hits"]
            pgs.powerPlayGoals = jp["powerPlayGoals"]
            pgs.powerPlayAssists = jp["powerPlayAssists"]
            pgs.penaltyMinutes = jp["penaltyMinutes"]
            pgs.faceOffWins = jp["faceOffWins"]
            pgs.faceoffTaken = jp["faceoffTaken"]
            pgs.takeaways = jp["takeaways"]
            pgs.giveaways = jp["giveaways"]
            pgs.shortHandedGoals = jp["shortHandedGoals"]
            pgs.shortHandedAssists = jp["shortHandedAssists"]
            pgs.blocked = jp["blocked"]
            pgs.plusMinus = jp["plusMinus"]
            pgs.evenTimeOnIce = "00:" + jp["evenTimeOnIce"]
            pgs.powerPlayTimeOnIce = "00:" + jp["powerPlayTimeOnIce"]
            pgs.shortHandedTimeOnIce = "00:" + jp["shortHandedTimeOnIce"]
            pgs.period = period
            pgs.team = team
            pgss.append(pgs)
    return pgss


def find_current_games():
    today = datetime.datetime.now(tz=pytz.UTC)
    current_games = pbpmodels.Game.objects.exclude(gameState__in=[6,7,8]).filter(dateTime__lte=today)
    return current_games


def main():
    # Find games that are current
    current_games = find_current_games()
    # set a test for an instance where we don't want to keep running?
    keep_running = True
    players = {}
    tplayers = pmodels.Player.objects.all()
    for t in tplayers:
        players[t.id] = t
    # Loop through current games
    while keep_running:
        # Loop through current_games
        for game in current_games:
            print game.gamePk
            # Call function that will handle most of the work, return True if the game has finished
            finished = update_game(game, players)
            # If the game has finished, compile the final stats
            if finished:
                fgame = {"gamePk": game.gamePk, "homeTeam_id": game.homeTeam_id,
                    "awayTeam_id": game.awayTeam_id}
                # Delete any existing
                with transaction.atomic():
                    pmodels.CompiledPlayerGameStats.objects.filter(game=game).delete()
                    pmodels.CompiledGoalieGameStats.objects.filter(game=game).delete()
                    compile_game(fgame)
        
        # Find active games and loop back up, repeating
        current_games = find_current_games()
        if len(current_games) == 0:
            gameTime = pbpmodels.Game.objects.filter(gameState=1).earliest("dateTime").dateTime
            today = datetime.datetime.now(tz=pytz.UTC)
            diff = gameTime - today
            seconds = diff.total_seconds() - 60
            time.sleep(seconds)
        else:
            # sleep for one minute
            time.sleep(60)


@transaction.atomic()
def update_game(game, players):
    allpgss = []
    allperiods = []
    allplaybyplay = []
    allplayers = []
    homeMissed = 0
    awayMissed = 0
    # Delete old data
    if pbpmodels.GamePeriod.objects.filter(game=game).count() > 0:
        pbpmodels.GamePeriod.objects.filter(game=game).delete()
    if pbpmodels.PlayerInPlay.objects.filter(game=game).count() > 0:
        pbpmodels.PlayerInPlay.objects.filter(game=game).delete()
    if pbpmodels.PlayByPlay.objects.filter(gamePk=game).count() > 0:
        pbpmodels.PlayByPlay.objects.filter(gamePk=game).delete()
    if pbpmodels.PlayerGameStats.objects.filter(game=game).count() > 0:
        pbpmodels.PlayerGameStats.objects.filter(game=game).delete()
    # Get live game data
    j = json.loads(get_game(game.gamePk))
    gd = j["gameData"]
    ld = j["liveData"]
    boxScore = ld["boxscore"]
    lineScore = ld["linescore"]
    # Update gameData
    game.dateTime = gd["datetime"]["dateTime"]
    if "endDateTime" in gd["datetime"]:
        game.endDateTime = gd["datetime"]["endDateTime"]
    else:
        print gd["datetime"]
    game.gameState = gd["status"]["codedGameState"]
    # Get linescore information
    game.homeScore = lineScore["teams"]["home"]["goals"]
    game.awayScore = lineScore["teams"]["away"]["goals"]
    game.homeShots = lineScore["teams"]["home"]["shotsOnGoal"]
    game.awayShots = lineScore["teams"]["away"]["shotsOnGoal"]
    # Get boxscore information
    home = boxScore["teams"]["home"]["teamStats"]["teamSkaterStats"]
    away = boxScore["teams"]["away"]["teamStats"]["teamSkaterStats"]
    game.homePIM = home["pim"]
    game.awayPIM = away["pim"]
    game.homePPGoals = home["powerPlayGoals"]
    game.awayPPGoals = away["powerPlayGoals"]
    game.homePPOpportunities = home["powerPlayOpportunities"]
    game.awayPPOpportunities = away["powerPlayOpportunities"]
    game.homeFaceoffPercentage = home["faceOffWinPercentage"]
    game.awayFaceoffPercentage = away["faceOffWinPercentage"]
    game.homeBlocked = home["blocked"]
    game.awayBlocked = away["blocked"]
    game.homeTakeaways = home["takeaways"]
    game.awayTakeaways = away["takeaways"]
    game.homeGiveaways = home["giveaways"]
    game.awayGiveaways = away["giveaways"]
    game.homeHits = home["hits"]
    game.awayHits = away["hits"]
    cperiod = 1
    for period in lineScore["periods"]:
        p = pbpmodels.GamePeriod()
        p.game = game
        p.period = period["num"]
        if period["num"] > cperiod:
            cperiod = period["num"]
        if "startTime" in period:
            p.startTime = period["startTime"]
        if "endTime" in period:
            p.endTime = period["endTime"]
        p.homeScore = period["home"]["goals"]
        p.homeShots = period["home"]["shotsOnGoal"]
        p.awayScore = period["away"]["goals"]
        p.awayShots = period["away"]["shotsOnGoal"]
        allperiods.append(p)
    if lineScore["hasShootout"]:
        sinfo = lineScore["shootoutInfo"]
        try:
            s = pbpmodels.Shootout.objects.get(game=game)
        except:
            s = pbpmodels.Shootout()
            s.game = game
        s.awayScores = sinfo["away"]["scores"]
        s.awayAttempts = sinfo["away"]["attempts"]
        s.homeScores = sinfo["home"]["scores"]
        s.homeAttempts = sinfo["home"]["attempts"]
        s.save()
    homeSkaters = j["liveData"]["boxscore"]["teams"]["home"]["skaters"]
    homeGoalies = j["liveData"]["boxscore"]["teams"]["home"]["goalies"]
    homeOnIce = j["liveData"]["boxscore"]["teams"]["home"]["onIce"]
    homeScratches = j["liveData"]["boxscore"]["teams"]["home"]["scratches"]
    awaySkaters = j["liveData"]["boxscore"]["teams"]["away"]["skaters"]
    awayGoalies = j["liveData"]["boxscore"]["teams"]["away"]["goalies"]
    awayOnIce = j["liveData"]["boxscore"]["teams"]["away"]["onIce"]
    awayScratches = j["liveData"]["boxscore"]["teams"]["away"]["scratches"]
    homeIds = set(homeSkaters + homeGoalies + homeOnIce + homeScratches)
    awayIds = set(awaySkaters + awayGoalies + awayOnIce + awayScratches)
    gd = j["gameData"]
    # Player Info
    pinfo = gd["players"]
    for sid in pinfo: # I swear that's not a Crosby reference
        iid = int(sid.replace("ID", ""))
        if iid not in players:
            if iid in homeIds:
                team = game.homeTeam
            elif iid in awayIds:
                team = game.awayTeam
            else:
                print iid, homeIds, awayIds
                raise Exception
            player = ingest_player(pinfo[sid], team.id)
            players[player.id] = player
    # liveData
    ld = j["liveData"]
    lineScore = ld["linescore"]
    # Plays
    playid = pbpmodels.PlayByPlay.objects.values('id').latest('id')['id'] + 1
    for play in ld["plays"]["allPlays"]:
        about = play["about"]
        pplayers = play["players"]
        result = play["result"]
        coordinates = play["coordinates"]
        p = pbpmodels.PlayByPlay()
        p.id = playid
        p.gamePk = game
        p.eventId = about["eventId"]
        p.eventIdx = about["eventIdx"]
        p.period = about["period"]
        p.periodTime = about["periodTime"]
        p.dateTime = about["dateTime"]
        p.playType = result["eventTypeId"]
        p.playDescription = result["description"]
        if "team" in play:
            p.team_id = play["team"]["id"]
        if result["eventTypeId"] == "MISSED_SHOT":
            if play["team"]["id"] == game.homeTeam_id:
                homeMissed += 1
            else:
                awayMissed += 1
        if "secondaryType" in result:
            if p.playType == "PENALTY":
                p.penaltyType = result["secondaryType"]
            else:
                p.shotType = result["secondaryType"]
        if p.playType == "PENALTY":
            p.penaltySeverity = result["penaltySeverity"]
            p.penaltyMinutes = result["penaltyMinutes"]
        if "strength" in result:
            p.strength = result["strength"]["code"]
        if "x" in coordinates and "y" in coordinates:
            p.xcoord = coordinates["x"]
            p.ycoord = coordinates["y"]
        allplaybyplay.append(p)
        assist_found = False
        for pp in pplayers:
            poi = pbpmodels.PlayerInPlay()
            poi.play_id = playid
            poi.game = game
            poi.player_id = pp["player"]["id"]
            if assist_found is True and pbphelper.get_player_type(pp["playerType"]) == 6:
                poi.player_type = 16
                poi.eventId = about["eventId"]
                poi.game_id = game.gamePk
            else:
                poi.player_type = pbphelper.get_player_type(pp["playerType"])
                if poi.player_type == 6:
                    assist_found = True
            allplayers.append(poi)
        playid += 1
    game.homeMissed = homeMissed
    game.awayMissed = awayMissed
    game.save()
    pbpmodels.GamePeriod.objects.bulk_create(allperiods)
    pbpmodels.PlayByPlay.objects.bulk_create(allplaybyplay)
    pbpmodels.PlayerInPlay.objects.bulk_create(allplayers)
    hp = boxScore["teams"]["home"]["players"]
    ap = boxScore["teams"]["away"]["players"]
    homegoalies = ld["boxscore"]["teams"]["home"]["players"]
    awaygoalies = ld["boxscore"]["teams"]["away"]["players"]
    hometeam = ld["boxscore"]["teams"]["home"]["team"]["id"]
    awayteam = ld["boxscore"]["teams"]["away"]["team"]["id"]
    goaliestats = []
    goaliestats.extend(checkGoalies(homegoalies, game.gamePk, hometeam, cperiod))
    goaliestats.extend(checkGoalies(awaygoalies, game.gamePk, awayteam, cperiod))
    allpgss.extend(set_player_stats(hp, game.homeTeam, game, players, cperiod))
    allpgss.extend(set_player_stats(ap, game.awayTeam, game, players, cperiod))
    pbpmodels.PlayerGameStats.objects.bulk_create(allpgss)

    # Find any existing POI data and delete
    pbpmodels.PlayerOnIce.objects.filter(game=game).delete()
    # Get player on ice data
    eventIdxs = {}
    for pbp in allplaybyplay:
        periodTime = str(pbp.periodTime)
        if pbp.period not in eventIdxs:
            eventIdxs[pbp.period] = {}
        if periodTime not in eventIdxs[pbp.period]:
            eventIdxs[pbp.period][periodTime] = {}
        if event_dict[pbp.playType] not in eventIdxs[pbp.period][periodTime]:
            eventIdxs[pbp.period][periodTime][event_dict[pbp.playType]] = [pbp.id, ]
        else:
            eventIdxs[pbp.period][periodTime][event_dict[pbp.playType]].append(pbp.id)
    hp = {}
    ap = {}
    for ps in allpgss:
        if ps.team_id == game.homeTeam_id:
            hp[ps.player.fullName.upper()] = ps.player_id
        else:
            ap[ps.player.fullName.upper()] = ps.player_id
    for gs in goaliestats:
        if gs.team_id == game.homeTeam_id:
            hp[gs.player.fullName.upper()] = gs.player_id
        else:
            ap[gs.player.fullName.upper()] = gs.player_id
    url = BASE + str(game.season) + "/PL0" + str(game.gamePk)[5:] + ".HTM"
    data = get_url(url)
    soup = BeautifulSoup(data, 'html.parser')
    evens = soup.find_all('tr', attrs={'class': 'evenColor'})
    count = 0
    saved = []
    for row in evens:
        backup_names = {}
        cols = row.find_all('td', recursive=False)
        fonts = row.find_all('font')
        if len(list(cols[3].strings)) >= 1:
            time = list(cols[3].strings)[0]
            if len(time) < 5:
                time = "0" + time
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
                                pbpp = pbpmodels.PlayerOnIce(**pbpdict)
                                #pbpp.save()
                                saved.append(pbpp)
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
                                pbpp = pbpmodels.PlayerOnIce(**pbpdict)
                                #pbpp.save()
                                saved.append(pbpp)
                # Remove so there are no duplicates, first entry will have the most data
                eventIdxs[eventIdx][time].pop(playType, None)
    pbpmodels.PlayerOnIce.objects.bulk_create(saved)
    if game.gameState in [6,7,8,"6","7","8"]:
        return True
    return False



if __name__ == "__main__":
    main()
