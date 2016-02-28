import os
import sys
import json
import glob
import time
import django

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

headers = {
    "User-Agent" : "Mozilla/5.0 (X11; U; Linux i686; " + \
        "en-US; rv:1.9.2.24) Gecko/20111107 " + \
        "Linux Mint/9 (Isadora) Firefox/3.6.24",
}


def get_values(ptype):
    if ptype == "skater":
        return ["goals", "assists", "assists2", "gf",
                "ga", "pnDrawn", "pn", "sf", "msf",
                "bsf", "onsf", "onmsf", "onbsf", "offgf", "offsf",
                "offmsf", "offbsf", "offga", "offsa",
                "offmsa", "offbsa", "sa", "msa", "bsa", "zso",
                "zsn", "zsd", "toi", "ihsc", "isc", "sc",
                "hscf", "hsca", "sca", "fo_w", "fo_l", "hit",
                "hitt", "gv", "tk", "toi", "timeOffIce", "ab"]
    elif ptype == "goalie":
        values = ["toi"]
        for s in ["shots", "saves"]:
            for l in ["Low", "Medium", "High"]:
                values.append(s+l)
        return values
    else:
        raise Exception


def setup_player_dict(player_id, gamePk, ptype):
    values = {1: {}, 2: {}, 3: {}, 4: {}, 5: {}}
    for period in values:
        strengths = {"all": {}, "even": {}, "pp": {}, "3v3": {},
            "pk": {}, "4v4": {}, "og": {}, "tg": {}, "oth": {}}
        values[period] = strengths
        for strength in values[period]:
            data = {"player_id": player_id, "game_id": gamePk,
                "period": period, "strength": strength}
            pvalues = get_values(ptype)
            for v in pvalues:
                data[v] = 0
            values[period][strength] = data
    return values


def setup_skater(player_id, gamePk):
    return setup_player_dict(player_id, gamePk, "skater")


def setup_goalie(player_id, gamePk):
    return setup_player_dict(player_id, gamePk, "goalie")


def convert_time(seconds):
    return datetime.timedelta(seconds=seconds)


def get_strengths(onice, players, awayTeam, homeTeam, goalies):
    away = 0
    home = 0
    missingHome = True
    missingAway = True
    homeStrength = ["all", ]
    awayStrength = ["all", ]
    for player in onice:
        if player in players:
            if player in goalies:
                if goalies[player] == homeTeam:
                    missingHome = False
                elif goalies[player] == awayTeam:
                    missingAway = False
            if players[player] == homeTeam:
                home += 1
            elif players[player] == awayTeam:
                away += 1
            else:
                pass
    if missingHome:
        homeStrength.append("tg")
        awayStrength.append("og")
    if missingAway:
        homeStrength.append("og")
        awayStrength.append("tg")
    if home == 6 and away == 6:
        homeStrength.append("even")
        awayStrength.append("even")
    elif home <= 5:
        if away == 5 and home == 5:
            homeStrength.append("4v4")
            awayStrength.append("4v4")
        elif away == 6:
            homeStrength.append("pk")
            awayStrength.append("pp")
        elif home == 4 and away == 4:
            homeStrength.append("3v3")
            awayStrength.append("3v3")
        elif home == 0 and away == 0:
            # pass for beginning of game
            pass
        else:
            homeStrength.append("oth")
            awayStrength.append("oth")
    elif away <= 5:
        if home == 6:
            homeStrength.append("pk")
            awayStrength.append("pp")
        else:
            homeStrength.append("oth")
            awayStrength.append("oth")
    else:
        homeStrength.append("oth")
        awayStrength.append("oth")
    return homeStrength, awayStrength


def point_inside_polygon( x, y, poly):
    # check if point is a vertex
    try:
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
    except:
        return False


def diff_times_in_seconds(t1, t2):
    # assumes t1 & t2 are python times, on the same day and t2 is after t1
    m1, s1, _ = t1.hour, t1.minute, t1.second
    m2, s2, _ = t2.hour, t2.minute, t2.second
    t1_secs = s1 + 60 * m1
    t2_secs = s2 + 60 * m2
    return (t1_secs - t2_secs)


def calculate_rebound(shot, pshot):
    if pshot is not None and shot.period == pshot.period:
        if shot.team == pshot.team and pshot.shotType != "GOAL":
            diff = diff_times_in_seconds(shot.periodTime,
                pshot.periodTime)
            if diff >= -3:
                return True
    return False


def calculate_rush(shot, pplay):
    if pplay is not None and shot.period == pplay.period:
        diff = diff_times_in_seconds(shot.periodTime,
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


def calculate_danger_zone(shot, pshot, pdanger):
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
    if point_inside_polygon(xcoord, ycoord, highpoly) is True:
        return "High"
    elif point_inside_polygon(xcoord, ycoord, poly) is True:
        return "Medium"
    return "Low"


def calculate_scoring_chance(shot, pshot, pdanger, pplay):
    rebound = calculate_rebound(shot, pshot)
    rush = calculate_rush(shot, pplay)
    # if rebound, scoring_chance
    zone = calculate_danger_zone(shot, pshot, pdanger)
    # "prevcurrtime" "cblockreb2", "cmissreb2", "shotreb2", "cblockreb3",
    # "cmissreb3", "shotreb3", "rushn4", "rusho4"
    if rebound:
        return zone, 2
    elif rush and diff_times_in_seconds(shot.periodTime,
            pplay.periodTime) >= -4:
        return zone, 2
    if zone == "Low":
        if rebound and shot.playType != "BLOCKED_SHOT":
            return zone, 1
        elif rush is True:
            return zone, 1
    elif zone == "Medium":
        if shot.playType != "BLOCKED_SHOT":
            return zone, 1
    else:
        return zone, 1
    return zone, 0


def find_players_team_strength(pteam, homeTeam, awayTeam, homeStrength,
        awayStrength):
    if pteam == homeTeam:
        return homeStrength
    elif pteam == awayTeam:
        return awayStrength
    else:
        print pteam
        raise Exception


def handle_goal(pbp, gameDict, inplay, onice, homeStrength, awayStrength,
        players, homeTeam, awayTeam, zone, sc, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        team = players[pid]
        strength = find_players_team_strength(players[pid], homeTeam,
            awayTeam, homeStrength, awayStrength)
        if ptype == 5:
            # Find goalie who was scored on
            for g in onice:
                if g in gameDict["goalies"] and players[g] != team:
                    gstrength = find_players_team_strength(players[g],
                        homeTeam, awayTeam, homeStrength, awayStrength)
                    for s in gstrength:
                        shotType = "shots" + zone
                        data = gameDict["goalies"][g][period][s]
                        data[shotType] += 1
            # Add stats for shooter
            if pid in gameDict["skaters"]:
                for s in strength:
                    data = gameDict["skaters"][pid][period][s]
                    gf = team
                    data["goals"] += 1
                    data["sf"] += 1
                    if sc == 2:
                        data["ihsc"] += 1
                    elif sc == 1:
                        data["isc"] += 1
        elif ptype == 6:
            # Add stats for primary assist
            if pid in gameDict["skaters"]:
                for s in strength:
                    data = gameDict["skaters"][pid][period][s]
                    data["assists"] += 1
        elif ptype == 16:
            # Add stats for secondary assist
            if pid in gameDict["skaters"]:
                for s in strength:
                    data = gameDict["skaters"][pid][period][s]
                    data["assists2"] += 1
    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        pteam = players[player]
        if player in gameDict["skaters"]:
            data = gameDict["skaters"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            if pteam == gf:
                for s in strength:
                    data[s]["gf"] += 1
                    data[s]["onsf"] += 1
                    if sc == 2:
                        data[s]["hscf"] += 1
                    elif sc == 1:
                        data[s]["sc"] += 1
                    data[s]["toi"] += seconds
            else:
                for s in strength:
                    data[s]["ga"] += 1
                    data[s]["sa"] += 1
                    if sc == 2:
                        data[s]["hsca"] += 1
                    elif sc == 1:
                        data[s]["sca"] += 1
                    data[s]["toi"] += seconds
        else:
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["goalies"][player][period]
            for s in strength:
                data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            if pteam == gf:
                for s in strength:
                    data[s]["offsf"] += 1
                    data[s]["offgf"] += 1
            else:
                for s in strength:
                    data[s]["offsa"] += 1
                    data[s]["offga"] += 1
            data[s]["timeOffIce"] += seconds


def handle_shot(pbp, gameDict, inplay, onice, homeStrength, awayStrength,
        players, homeTeam, awayTeam, zone, sc, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        team = players[pid]
        strength = find_players_team_strength(players[pid], homeTeam,
            awayTeam, homeStrength, awayStrength)
        if ptype == 7:
            # Add stats for shooter
            for s in strength:
                data = gameDict["skaters"][pid][period][s]
                gf = team
                data["sf"] += 1
                if sc == 2:
                    data["ihsc"] += 1
                elif sc == 1:
                    data["isc"] += 1
        elif ptype == 8:
            # Add stats for goalie
            shotType = "shots" + zone
            saveType = "saves" + zone
            for s in strength:
                data = gameDict["goalies"][pid][period][s]
                data[shotType] += 1
                data[saveType] += 1


    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        pteam = players[player]
        if player in gameDict["skaters"]:
            data = gameDict["skaters"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            if pteam == gf:
                for s in strength:
                    data[s]["onsf"] += 1
                    if sc == 2:
                        data[s]["hscf"] += 1
                    elif sc == 1:
                        data[s]["sc"] += 1
                    data[s]["toi"] += seconds
            else:
                for s in strength:
                    data[s]["sa"] += 1
                    if sc == 2:
                        data[s]["hsca"] += 1
                    elif sc == 1:
                        data[s]["sca"] += 1
                    data[s]["toi"] += seconds
        if player in gameDict["goalies"]:
            data = gameDict["goalies"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            for s in strength:
                data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            if pteam == gf:
                for s in strength:
                    data[s]["offsf"] += 1
                    data[s]["timeOffIce"] += seconds
            else:
                for s in strength:
                    data[s]["offsa"] += 1
                    data[s]["timeOffIce"] += seconds


def handle_blocked_shot(pbp, gameDict, inplay, onice, homeStrength,
        awayStrength, players, homeTeam, awayTeam, zone, sc, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        team = players[pid]
        strength = find_players_team_strength(players[pid], homeTeam,
            awayTeam, homeStrength, awayStrength)
        if ptype == 7:
            # Add stats for shooter
            for s in strength:
                data = gameDict["skaters"][pid][period][s]
                gf = team
                data["bsf"] += 1
                if sc == 2:
                    data["ihsc"] += 1
                elif sc == 1:
                    data["isc"] += 1
        elif ptype == 9:
            # Add stats for shooter
            for s in strength:
                data = gameDict["skaters"][pid][period][s]
                gf = team
                data["ab"] += 1



    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        pteam = players[player]
        if player in gameDict["skaters"]:
            data = gameDict["skaters"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            if pteam == gf:
                for s in strength:
                    data[s]["onbsf"] += 1
                    if sc == 2:
                        data[s]["hscf"] += 1
                    elif sc == 1:
                        data[s]["sc"] += 1
                    data[s]["toi"] += seconds
            else:
                for s in strength:
                    data[s]["bsa"] += 1
                    if sc == 2:
                        data[s]["hsca"] += 1
                    elif sc == 1:
                        data[s]["sca"] += 1
                    data[s]["toi"] += seconds
        if player in gameDict["goalies"]:
            data = gameDict["goalies"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            for s in strength:
                data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            if pteam == gf:
                for s in strength:
                    data[s]["offbsf"] += 1
                    data[s]["timeOffIce"] += seconds
            else:
                for s in strength:
                    data[s]["offbsa"] += 1
                    data[s]["timeOffIce"] += seconds


def handle_missed_shot(pbp, gameDict, inplay, onice, homeStrength,
        awayStrength, players, homeTeam, awayTeam, zone, sc, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        if pid in players:
            team = players[pid]
            strength = find_players_team_strength(players[pid], homeTeam,
                awayTeam, homeStrength, awayStrength)
            if ptype == 7:
                # Add stats for shooter
                for s in strength:
                    data = gameDict["skaters"][pid][period][s]
                    gf = team
                    data["msf"] += 1
                    if sc == 2:
                        data["ihsc"] += 1
                    elif sc == 1:
                        data["isc"] += 1

    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        if player in players:
            pteam = players[player]
            if player in gameDict["skaters"]:
                data = gameDict["skaters"][player][period]
                strength = find_players_team_strength(players[pid], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                if pteam == gf:
                    for s in strength:
                        data[s]["onmsf"] += 1
                        if sc == 2:
                            data[s]["hscf"] += 1
                        elif sc == 1:
                            data[s]["sc"] += 1
                        data[s]["toi"] += seconds
                else:
                    for s in strength:
                        data[s]["msa"] += 1
                        if sc == 2:
                            data[s]["hsca"] += 1
                        elif sc == 1:
                            data[s]["sca"] += 1
                        data[s]["toi"] += seconds
        if player in gameDict["goalies"]:
            data = gameDict["goalies"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            for s in strength:
                data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            if pteam == gf:
                for s in strength:
                    data[s]["offmsf"] += 1
                    data[s]["timeOffIce"] += seconds
            else:
                for s in strength:
                    data[s]["offmsa"] += 1
                    data[s]["timeOffIce"] += seconds


def handle_penalty(pbp, gameDict, inplay, onice, homeStrength,
        awayStrength, players, homeTeam, awayTeam, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        team = players[pid]
        strength = find_players_team_strength(players[pid], homeTeam,
            awayTeam, homeStrength, awayStrength)
        if ptype == 10 and pid in gameDict["skaters"]:
            # Add stats for shooter
            for s in strength:
                data = gameDict["skaters"][pid][period][s]
                gf = team
                data["pn"] += 1
        elif ptype == 11 and pid in gameDict["skaters"]:
            for s in strength:
                data = gameDict["skaters"][pid][period][s]
                data["pnDrawn"] += 1

    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        pteam = players[player]
        if player in gameDict["skaters"]:
            data = gameDict["skaters"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            for s in strength:
                data[s]["toi"] += seconds
        if player in gameDict["goalies"]:
            data = gameDict["goalies"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            for s in strength:
                data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            for s in strength:
                data[s]["timeOffIce"] += seconds


def handle_takeaway(pbp, gameDict, inplay, onice, homeStrength,
        awayStrength, players, homeTeam, awayTeam, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        team = players[pid]
        strength = find_players_team_strength(players[pid], homeTeam,
            awayTeam, homeStrength, awayStrength)
        if ptype == 13:
            # Add stats for shooter
            if pid in gameDict["skaters"]:
                for s in strength:
                    data = gameDict["skaters"][pid][period][s]
                    gf = team
                    data["tk"] += 1

    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        if player in players:
            pteam = players[player]
            if player in gameDict["skaters"]:
                data = gameDict["skaters"][player][period]
                strength = find_players_team_strength(players[player], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                for s in strength:
                    data[s]["toi"] += seconds
            if player in gameDict["goalies"]:
                data = gameDict["goalies"][player][period]
                strength = find_players_team_strength(players[player], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                for s in strength:
                    data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            for s in strength:
                data[s]["timeOffIce"] += seconds


def handle_giveaway(pbp, gameDict, inplay, onice, homeStrength,
        awayStrength, players, homeTeam, awayTeam, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        if pid in players:
            team = players[pid]
            strength = find_players_team_strength(players[pid], homeTeam,
                awayTeam, homeStrength, awayStrength)
            if ptype == 13:
                # Add stats for shooter
                if pid in gameDict["skaters"]:
                    for s in strength:
                        data = gameDict["skaters"][pid][period][s]
                        gf = team
                        data["gv"] += 1

    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        if player in players:
            pteam = players[player]
            if player in gameDict["skaters"]:
                data = gameDict["skaters"][player][period]
                strength = find_players_team_strength(players[player], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                for s in strength:
                    data[s]["toi"] += seconds
            if player in gameDict["goalies"]:
                data = gameDict["goalies"][player][period]
                strength = find_players_team_strength(players[player], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                for s in strength:
                    data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            for s in strength:
                data[s]["timeOffIce"] += seconds


def handle_faceoff(pbp, gameDict, inplay, onice, homeStrength,
        awayStrength, players, homeTeam, awayTeam, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    xcoord = pbp.xcoord
    ycoord = pbp.ycoord
    if pbp.period == 2 or pbp.period == 4:
        xcoord = -xcoord
    if xcoord < -25.00:
        awayZone = "zso"
        homeZone = "zsd"
    elif xcoord > 25.00:
        homeZone = "zso"
        awayZone = "zsd"
    else:
        homeZone = "zsn"
        awayZone = "zsn"
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        if pid in players:
            team = players[pid]
            strength = find_players_team_strength(players[pid], homeTeam,
                awayTeam, homeStrength, awayStrength)
            if ptype == 1:
                # Add stats for shooter
                for s in strength:
                    data = gameDict["skaters"][pid][period][s]
                    gf = team
                    data["fo_w"] += 1
            elif ptype == 2:
                # Add stats for shooter
                for s in strength:
                    data = gameDict["skaters"][pid][period][s]
                    gf = team
                    data["fo_l"] += 1

    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        if player in players:
            pteam = players[player]
            if player in gameDict["skaters"]:
                data = gameDict["skaters"][player][period]
                strength = find_players_team_strength(players[player], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                for s in strength:
                    data[s]["toi"] += seconds
                    if players[player] == awayTeam:
                        data[s][awayZone] += 1
                    else:
                        data[s][homeZone] += 1
            if player in gameDict["goalies"]:
                data = gameDict["goalies"][player][period]
                strength = find_players_team_strength(players[player], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                for s in strength:
                    data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            data = gameDict["skaters"][player][period]
            for s in strength:
                data[s]["timeOffIce"] += seconds


def handle_hit(pbp, gameDict, inplay, onice, homeStrength,
        awayStrength, players, homeTeam, awayTeam, previous_play):
    exclude = set()
    period = pbp.period
    gf = None
    # Get values for those involved in play
    for p in inplay:
        pid = p["player_id"]
        ptype = p["player_type"]
        if pid in players:
            team = players[pid]
            strength = find_players_team_strength(players[pid], homeTeam,
                awayTeam, homeStrength, awayStrength)
            if ptype == 3:
                # Add stats for hitter
                if pid in gameDict["skaters"]:
                    for s in strength:
                        data = gameDict["skaters"][pid][period][s]
                        gf = team
                        data["hit"] += 1
            elif ptype == 4:
                # Add stats for hitter
                if pid in gameDict["skaters"]:
                    for s in strength:
                        data = gameDict["skaters"][pid][period][s]
                        gf = team
                        data["hitt"] += 1

    # Get values for those on the ice
    if previous_play is not None:
        seconds = diff_times_in_seconds(pbp.periodTime, previous_play.periodTime)
        if seconds < 0:
            seconds = 0
    else:
        seconds = 0
    for player in onice:
        exclude.add(player)
        if player in players:
            pteam = players[player]
            if player in gameDict["skaters"]:
                data = gameDict["skaters"][player][period]
                strength = find_players_team_strength(players[player], homeTeam,
                    awayTeam, homeStrength, awayStrength)
                for s in strength:
                    data[s]["toi"] += seconds
        if player in gameDict["goalies"]:
            data = gameDict["goalies"][player][period]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            for s in strength:
                data[s]["toi"] += seconds
    # Get values for those not on the ice
    for player in players:
        if player in gameDict["skaters"] and player not in exclude:
            pteam = players[player]
            strength = find_players_team_strength(players[player], homeTeam,
                awayTeam, homeStrength, awayStrength)
            data = gameDict["skaters"][player][period]
            for s in strength:
                data[s]["timeOffIce"] += seconds


def main():
    # For each completed Game
    existing = set(pmodels.CompiledPlayerGameStats.objects.values_list("game_id", flat=True).all())
    for game in pbpmodels.Game.objects.values("gamePk", "homeTeam_id", "awayTeam_id").filter(gameState__in=[5, 6, 7]).exclude(gamePk__in=existing):
        # For every player, every game, every period, define dict
        # Each dict should contain every strength as a key
        # That will hold another dict with the information
        print game["gamePk"]
        homeTeam = game["homeTeam_id"]
        awayTeam = game["awayTeam_id"]
        gameDict = {"skaters": {}, "goalies": {}}
        players = {}
        goalies = {}
        tskaters = pbpmodels.PlayerGameStats.objects.filter(game=game["gamePk"])
        tgoalies = pbpmodels.GoalieGameStats.objects.filter(game=game["gamePk"])
        for skater in tskaters:
            gameDict["skaters"][skater.player.id] = setup_skater(skater.player.id,
                game["gamePk"])
            if skater.team is not None:
                players[skater.player.id] = skater.team.id
        for goalie in tgoalies:
            gameDict["goalies"][goalie.player.id] = setup_goalie(goalie.player.id,
                game["gamePk"])
            players[goalie.player.id] = goalie.team.id
            goalies[goalie.player.id] = goalie.team.id
        # For every play in that game
        previous_play = None
        previous_shot = None
        previous_danger = None
        if len(gameDict["skaters"]) > 0:
            for pbp in pbpmodels.PlayByPlay.objects.filter(gamePk_id=game["gamePk"]).order_by("period", "periodTime"):
                # Add the relevant stats for that play to the respective players
                inplay = pbpmodels.PlayerInPlay.objects.values("player_id", "player_type").filter(play_id=pbp.id)
                onice = pbpmodels.PlayerOnIce.objects.values_list("player_id", flat=True).filter(play_id=pbp.id)
                for player in onice:
                    if player not in players:
                        gameDict["skaters"][player] = setup_skater(player, game["gamePk"])
                homeStrength, awayStrength = get_strengths(onice, players, homeTeam, awayTeam, goalies)
                playType = pbp.playType
                if playType == "FACEOFF":
                    handle_faceoff(pbp, gameDict, inplay, onice, homeStrength,
                        awayStrength, players, homeTeam, awayTeam,
                        previous_play)
                elif playType == "HIT":
                    handle_hit(pbp, gameDict, inplay, onice, homeStrength,
                        awayStrength, players, homeTeam, awayTeam,
                        previous_play)
                elif playType == "GIVEAWAY":
                    handle_giveaway(pbp, gameDict, inplay, onice, homeStrength,
                        awayStrength, players, homeTeam, awayTeam,
                        previous_play)
                elif playType == "GOAL":
                    shotZone, shotSC = calculate_scoring_chance(pbp,
                        previous_shot, previous_danger, previous_play)
                    handle_goal(pbp, gameDict, inplay, onice, homeStrength,
                        awayStrength, players, homeTeam, awayTeam,
                        shotZone, shotSC, previous_play)
                    previous_shot = pbp
                    previous_danger = shotZone
                elif playType == "SHOT":
                    shotZone, shotSC = calculate_scoring_chance(pbp,
                        previous_shot, previous_danger, previous_play)
                    handle_shot(pbp, gameDict, inplay, onice, homeStrength,
                        awayStrength, players, homeTeam, awayTeam,
                        shotZone, shotSC, previous_play)
                    previous_shot = pbp
                    previous_danger = shotZone
                elif playType == "MISSED_SHOT":
                    shotZone, shotSC = calculate_scoring_chance(pbp,
                        previous_shot, previous_danger, previous_play)
                    handle_missed_shot(pbp, gameDict, inplay, onice,
                        homeStrength, awayStrength, players, homeTeam,
                        awayTeam, shotZone, shotSC, previous_play)
                    previous_shot = pbp
                    previous_danger = shotZone
                elif playType == "PENALTY":
                    handle_penalty(pbp, gameDict, inplay, onice,
                        homeStrength, awayStrength, players, homeTeam,
                        awayTeam, previous_play)
                elif playType == "PENALTY_END":
                    pass
                elif playType == "STOP":
                    pass
                elif playType == "SUBSTITUTION":
                    pass
                elif playType == "FIGHT":
                    pass
                elif playType == "TAKEAWAY":
                    handle_takeaway(pbp, gameDict, inplay, onice, homeStrength,
                        awayStrength, players, homeTeam, awayTeam,
                        previous_play)
                elif playType == "BLOCKED_SHOT":
                    shotZone, shotSC = calculate_scoring_chance(pbp,
                        previous_shot, previous_danger, previous_play)
                    handle_blocked_shot(pbp, gameDict, inplay, onice,
                        homeStrength, awayStrength, players, homeTeam,
                        awayTeam, shotZone, shotSC, previous_play)
                    previous_shot = pbp
                    previous_danger = shotZone
                elif playType == "PERIOD_START":
                    pass
                elif playType == "PERIOD_END":
                    pass
                elif playType == "GAME_END":
                    pass
                elif playType == "GAME_SCHEDULED":
                    pass
                elif playType == "PERIOD_READY":
                    pass
                elif playType == "PERIOD_OFFICIAL":
                    pass
                elif playType == "SHOOTOUT_COMPLETE":
                    pass
                elif playType == "EARLY_INT_START":
                    pass
                elif playType == "EARLY_INT_END":
                    pass
                elif playType == "GAME_OFFICIAL":
                    pass
                elif playType == "CHALLENGE":
                    pass
                elif playType == "EMERGENCY_GOALTENDER":
                    pass
                # Update those who were on the ice for the play as well
                previous_play = pbp
            sAddData = []
            gAddData = []
            for pid in gameDict["skaters"]:
                skater = gameDict["skaters"][pid]
                for p in skater:
                    period = skater[p]
                    for strength in period:
                        relevant = ["goals", "assists", "assists2", "gf",
                            "ga", "pnDrawn", "pn", "sf", "msf",
                            "bsf", "onsf", "onmsf", "onbsf", "offgf", "offsf",
                            "offmsf", "offbsf", "offga", "offsa",
                            "offmsa", "offbsa", "sa", "msa", "bsa", "zso",
                            "zsn", "zsd", "toi", "ihsc", "isc", "sc",
                            "hscf", "hsca", "sca", "fo_w", "fo_l", "hit",
                            "hitt", "gv", "tk", "toi", "timeOffIce", "ab"]
                        add = False
                        for key in relevant:
                            if period[strength][key] > 0:
                                add = True
                                break
                        if add:
                            m, s = divmod(period[strength]["toi"], 60)
                            h, m = divmod(m, 60)
                            toi = "%d:%02d:%02d" % (h, m, s)
                            period[strength]["toi"] = toi
                            m, s = divmod(period[strength]["timeOffIce"], 60)
                            h, m = divmod(m, 60)
                            toi = "%d:%02d:%02d" % (h, m, s)
                            period[strength]["timeOffIce"] = toi
                            cpgs = pmodels.CompiledPlayerGameStats(**period[strength])
                            sAddData.append(cpgs)
            for pid in gameDict["goalies"]:
                skater = gameDict["goalies"][pid]
                for p in skater:
                    period = skater[p]
                    for strength in period:
                        relevant = ["shotsLow", "savesLow", "shotsMedium",
                            "savesMedium", "shotsHigh", "savesHigh", "toi"]
                        add = False
                        for key in relevant:
                            if period[strength][key] > 0:
                                add = True
                                break
                        if add:
                            m, s = divmod(period[strength]["toi"], 60)
                            h, m = divmod(m, 60)
                            toi = "%d:%02d:%02d" % (h, m, s)
                            period[strength]["toi"] = toi
                            cggs = pmodels.CompiledGoalieGameStats(**period[strength])
                            gAddData.append(cggs)
            with transaction.atomic():
                pmodels.CompiledPlayerGameStats.objects.bulk_create(sAddData)
                pmodels.CompiledGoalieGameStats.objects.bulk_create(gAddData)


def update_player_stats(pd, team, game, players, period):
    for sid in pd: # I swear that's not a Crosby reference
        iid = int(sid.replace("ID", ""))
        if "skaterStats" in pd[sid]["stats"]:
            jp = pd[sid]["stats"]["skaterStats"]
            if iid not in players:
                player = ingest_player(jp)
                players[player.id] = player
            else:
                player = players[iid]
            try:
                pgs, _ = pbpmodels.PlayerGameStats.objects.get_or_create(game=game,
                    player=player, period=period)
            except Exception as e:
                print game.gamePk, player
                raise e
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
            pgs.team = team
            pgs.save()


def get_game(id=None):
    url = "http://statsapi.web.nhl.com/api/v1/game/<gamePk>/feed/live/".replace("<gamePk>", str(id))
    return get_url(url)


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


def find_unknown_teams():
    players = {}
    tplayers = pmodels.Player.objects.all()
    for t in tplayers:
        players[t.id] = t
    games = set(pbpmodels.PlayerGameStats.objects.values_list("game", flat=True).filter(team=None))
    count = 0
    for gameid in sorted(games):
        with transaction.atomic():
            game = pbpmodels.Game.objects.get(gamePk=gameid)
            count += 1
            if count % 100 == 0:
                print count, len(games), game
            allpgss = []
            allperiods = []
            homeMissed = 0
            awayMissed = 0
            count += 1
            if count % 100 == 0:
                print count, game.gamePk
            j = json.loads(get_game(gameid))
            gd = j["gameData"]
            ld = j["liveData"]
            boxScore = ld["boxscore"]
            lineScore = ld["linescore"]
            cperiod = 1
            for period in lineScore["periods"]:
                if period["num"] > cperiod:
                    cperiod = period["num"]
            hp = boxScore["teams"]["home"]["players"]
            ap = boxScore["teams"]["away"]["players"]
            update_player_stats(hp, game.homeTeam, game, players, cperiod)
            update_player_stats(ap, game.awayTeam, game, players, cperiod)


if __name__ == "__main__":
    main()
    #find_unknown_teams()
