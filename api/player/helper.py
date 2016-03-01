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


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
