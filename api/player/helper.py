import constants
import helpers


def getPosition(code):
    for key in constants.skaterPositions:
        if key[0] == code:
            return key[1]
    return code


def add_player(existing, newdata, playergames):
    exclude = ["game", "player", "period", "strength",
        "player_id", "game_id", "_state", "toi", "timeOffIce",
        "player__currentTeam__abbreviation", "player__fullName",
        "game__season", "player__height", "player__weight",
        "player__birthDate", "player__primaryPositionCode"]
    for key in newdata:
        if key not in exclude:
            if key not in existing:
                existing[key] = newdata[key]
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
    zeroes = ["gv", "offbsf", "ab", "offmsa", "gf", "ga", "offbsa",
        "fo_l", "hscf", "onbsf", "onsf", "zsn",
        "tk", "msf", "pn", "msa",
        "hit", "assists2", "sca", "sc", "offga",
        "assists", "offgf", "bsf", "bsa", "onmsf",
        "hitt", "hsca", "offmsf", "fo_w", "sf", "zsd",
        "offsf", "offsa", "isc", "ihsc", "sa", "zso",
        "pnDrawn", "goals", "toi", "timeOffIce"]
    for key in data:
        if key not in exclude:
            pdict[key] = data[key]
    for key in zeroes:
        pdict[key] = 0
    pdict["games"] = 1
    if len(pdict["height"]) == 5:
        pdict["height"] = pdict["height"][:3] + "0" + pdict["height"][3:]
    pdict["currentTeamAbbr"] = data["currentTeam__abbreviation"]
    pdict["position"] = getPosition(data["primaryPositionCode"])
    pdict["age"] = helpers.calculate_age(data["birthDate"])
    return pdict


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
