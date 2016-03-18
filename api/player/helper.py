import constants
import helpers


def getPosition(code):
    for key in constants.skaterPositions:
        if key[0] == code:
            return key[1]
    return code


def add_player(existing, newdata, playergames, gameDict):
    exclude = ["game", "player", "period", "strength",
        "player_id", "game_id", "_state", "toi", "timeOffIce",
        "player__currentTeam__abbreviation", "player__fullName",
        "season", "player__height", "player__weight",
        "player__birthDate", "player__primaryPositionCode"]
    if "season" not in existing:
        existing["season"] = gameDict[newdata["game_id"]]
    for key in newdata:
        if key not in exclude:
            if key not in existing:
                existing[key] = newdata[key]
            else:
                existing[key] += newdata[key]
    existing["toi"] += newdata["toi"].minute * 60 + newdata["toi"].second
    existing["timeOffIce"] += newdata["timeOffIce"].minute * 60 + newdata["timeOffIce"].second
    if newdata["game_id"] not in playergames[existing["id"]]:
        existing["games"] += 1
        playergames[existing["id"]].add(newdata["game_id"])



def setup_skater(data):
    pdict = {"name": data["fullName"],
        "team": data["currentTeam__abbreviation"]}
    exclude = ["fullName", "currentTeam__abbreviation",
        "birthDate", "primaryPositionCode"]
    zeroes = ["pnDrawn", "pn", "sf", "msf", "bsf",
       "ab", "onsf", "onmsf", "onbsf", "offgf", "offsf",
       "offmsf", "offbsf", "offga", "offsa", "offmsa",
       "offbsa", "sa", "msa", "bsa", "zso", "zsn", "zsd",
       "toi", "timeOffIce", "ihsc", "isc", "sc", "hscf",
       "hsca", "sca", "fo_w", "fo_l", "hit", "hitt", "gv", "tk"]
    for key in data:
        if key not in exclude:
            pdict[key] = data[key]
    for key in zeroes:
        pdict[key] = 0
    pdict["games"] = 0
    if len(pdict["height"]) == 5:
        pdict["height"] = pdict["height"][:3] + "0" + pdict["height"][3:]
    pdict["currentTeamAbbr"] = data["currentTeam__abbreviation"]
    pdict["position"] = data["primaryPositionCode"]
    pdict["age"] = helpers.calculate_age(data["birthDate"])
    return pdict


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def add_goalie(existing, newdata, playergames):
    exclude = ["game", "player", "period", "strength",
        "player_id", "game_id", "_state", "toi", "timeOffIce",
        "player__currentTeam__abbreviation", "player__fullName",
        "game__season", "player__height", "player__weight",
        "player__birthDate", "player__primaryPositionCode",
        "leagueShotsLow", "leagueShotsMedium", "leagueShotsHigh"]
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
        "team": data["player__currentTeam__abbreviation"], 
        "weight" : data["player__weight"], "height" : data["player__height"]}
    exclude = ["toi", "timeOffIce", "player__fullName",
        "player__currentTeam__abbreviation", "game__season",
        "player__birthDate", "player__primaryPositionCode", "game_id", 
        "player__weight", "player__height"]
    for key in data:
        if key not in exclude:
            pdict[key] = data[key]
    pdict["games"] = 1
    if len(pdict["height"]) == 5:
        pdict["height"] = pdict["height"][:3] + "0" + pdict["height"][3:]
    pdict["currentTeam"] = pdict["team"]
    pdict["position"] = getPosition(data["player__primaryPositionCode"])
    pdict["age"] = helpers.calculate_age(data["player__birthDate"])
    pdict["toi"] = data["toi"].minute * 60 + data["toi"].second
    return pdict